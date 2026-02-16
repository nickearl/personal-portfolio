# auth.py
import os
import re
import logging
import json
import uuid
import requests
import redis
from datetime import timedelta

import google.auth
import flask
from cryptography.fernet import Fernet
from google.cloud import secretmanager
from flask_dance.contrib.google import make_google_blueprint, google
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from werkzeug.middleware.proxy_fix import ProxyFix
from dash import html, get_asset_url
import dash_bootstrap_components as dbc
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------- Env & globals ----------
CACHE_KEY = os.environ.get('SERVER_NAME').lower()
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(REDIS_URL)

FLASK_ENCRYPTION_KEY = os.environ['FLASK_ENCRYPTION_KEY']  # required
ENABLE_GOOGLE_AUTH = os.getenv('ENABLE_GOOGLE_AUTH', 'true').lower() == 'true'

# Optional: comma-separated string 'basemakers.com,base-bi.com'
try:
	AUTHORIZED_DOMAINS = [
		d.strip().lower()
		for d in os.getenv('AUTHORIZED_DOMAINS', '').split(',')
		if d.strip()
	]
except Exception:
	AUTHORIZED_DOMAINS = []

GOOGLE_SCOPES = [
	'https://www.googleapis.com/auth/userinfo.email',
	'https://www.googleapis.com/auth/userinfo.profile',
	'openid',
]

# ---------- Secret Manager helpers (OAuth client JSON) ----------
def _read_secret_json(secret_name: str, version: str = 'latest', project_id: str | None = None) -> dict:
	project_id = project_id or os.getenv('GCP_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')
	
	# If env vars are missing, try to auto-detect from GCloud environment
	if not project_id:
		try:
			_, project_id = google.auth.default()
		except Exception:
			pass

	if not project_id:
		raise RuntimeError('GCP project id not set (GCP_PROJECT or GOOGLE_CLOUD_PROJECT). Are you signed in to gcloud cli?')
	client = secretmanager.SecretManagerServiceClient()
	name = f'projects/{project_id}/secrets/{secret_name}/versions/{version}'
	resp = client.access_secret_version(request={'name': name})
	return json.loads(resp.payload.data.decode('utf-8'))

def _select_redirect_uri(uris: list[str], base_path: str) -> str | None:
    """
    Picks a Google OAuth redirect URI for this app.

    Rules:
      1) If GOOGLE_REDIRECT_URL is set, use it.
      2) Dev: prefer localhost/127.0.0.1 that matches {base_path}/login/google/authorized
      3) Prod: prefer HTTPS, non-localhost match for that same suffix
      4) Otherwise: first match, else first URI
    """
    import os
    from urllib.parse import urlparse

    uris = uris or []

    override = os.getenv('GOOGLE_REDIRECT_URL')
    if override:
        return override

    # normalize suffix for this app
    if not base_path.startswith('/'):
        base_path = '/' + base_path
    suffix = f'{base_path}/login/google/authorized'

    def matches(u: str) -> bool:
        return u.rstrip('/').endswith(suffix)

    def is_local(u: str) -> bool:
        h = (urlparse(u).hostname or '').lower()
        return h in {'localhost', '127.0.0.1'}

    is_dev = os.getenv('DEPLOY_ENV', 'prod').lower() in {'dev', 'local'}

    candidates = [u for u in uris if matches(u)]
    if not candidates:
        return uris[0] if uris else None

    if is_dev:
        # Prefer localhost in dev
        for u in candidates:
            if is_local(u):
                return u
        return candidates[0]

    # Prod: prefer https and non-localhost
    for u in candidates:
        if u.startswith('https://') and not is_local(u):
            return u
    return candidates[0]


_secret_name = os.getenv('GOOGLE_OAUTH_SECRET_NAME', 'overview-app-oauth-json')
_secret_version = os.getenv('GOOGLE_OAUTH_SECRET_VERSION', 'latest')

if ENABLE_GOOGLE_AUTH:
	_creds_blob = _read_secret_json(_secret_name, _secret_version)
	_section = _creds_blob.get('web') or _creds_blob.get('installed') or _creds_blob
	GOOGLE_CLIENT_ID = _section['client_id']
	GOOGLE_CLIENT_SECRET = _section['client_secret']
else:
	GOOGLE_CLIENT_ID = 'disabled'
	GOOGLE_CLIENT_SECRET = 'disabled'
# ---------- Encrypted Redis token cache ----------
class AuthCredentials:
	def __init__(self, cache_key: str, encryption_secret_key: str):
		self.cache_key = cache_key
		self.cipher = Fernet(encryption_secret_key)

	def encrypt_data(self, data: str) -> str:
		return self.cipher.encrypt(data.encode()).decode()

	def decrypt_data(self, data: str) -> str:
		return self.cipher.decrypt(data.encode()).decode()

	def save_google_credentials(self, session_id: str, credentials: dict) -> None:
		key = f'{self.cache_key}:session:{session_id}'
		encrypted_credentials = self.encrypt_data(json.dumps(credentials))
		redis_client.setex(key, timedelta(days=30), encrypted_credentials)

	def get_google_credentials(self, session_id: str) -> dict | None:
		key = f'{self.cache_key}:session:{session_id}'
		encrypted_credentials = redis_client.get(key)
		if encrypted_credentials:
			return json.loads(self.decrypt_data(encrypted_credentials.decode()))
		return None

def check_authorization() -> bool:
	"""
	If Google OAuth is authorized, fetch user info, enforce domain allowlist,
	and hydrate Flask session + Redis. Returns True on success, False otherwise.
	Does NOT perform redirects.
	"""
	if not ENABLE_GOOGLE_AUTH:
		return True

	if not google.authorized:
		return False

	creds_store = AuthCredentials(CACHE_KEY, FLASK_ENCRYPTION_KEY)

	try:
		resp = google.get('/oauth2/v1/userinfo')
		if not resp or not resp.ok:
			return False
		user_info = (resp.json() or {})
		user_email = (user_info.get('email') or '').lower()
		user_domain = user_email.split('@')[-1] if '@' in user_email else ''

		# Domain allowlist (optional)
		if AUTHORIZED_DOMAINS and user_domain not in AUTHORIZED_DOMAINS:
			flask.abort(403, description='Access denied: Unauthorized email domain')

		# Ensure we have a session_id
		session_id = flask.session.get('session_id')
		if not session_id:
			session_id = str(uuid.uuid4())
			flask.session['session_id'] = session_id

		# Persist (encrypted) in Redis
		creds_store.save_google_credentials(session_id, {
			'user_info': user_info,
			'google_oauth_token': flask.session.get('google_oauth_token'),
		})

		# Also cache a light user obj in the Flask session for quick checks
		flask.session['user'] = {
			'email': user_email,
			'domain': user_domain,
			'name': (user_info.get('name') or ''),
			'picture': (user_info.get('picture') or ''),
		}

		return True

	except TokenExpiredError:
		# Let caller decide to restart OAuth; we do NOT redirect from here.
		return False
	except Exception:
		# Be conservative; caller can handle UX
		return False


# ---------- Public entrypoints used by app.py ----------
def setup_oauth(server: flask.Flask, *, base_path: str) -> flask.Flask:
	"""
	Registers the Google OAuth blueprint and the auth routes:
	  - GET '/' (index) -> auth gate + redirect to redirect_path
	  - GET '/login' -> post-login handler (saves creds, redirects)
	  - GET '/login/revoke' -> revokes token and clears session
	"""
	# Trust X-Forwarded-For/Proto/Host from NGINX
	server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1)
	server.config['PREFERRED_URL_SCHEME'] = 'https'

	if not ENABLE_GOOGLE_AUTH:
		return server

	# Register Flask-Dance blueprint
	# google_bp = make_google_blueprint(
	# 	client_id=GOOGLE_CLIENT_ID,
	# 	client_secret=GOOGLE_CLIENT_SECRET,
	# 	redirect_url=GOOGLE_REDIRECT_URL,
	# 	scope=GOOGLE_SCOPES,
	# )

	# # Ask for refresh token
	# google_bp.authorization_url_params['access_type'] = 'offline'
	# google_bp.authorization_url_params['prompt'] = 'consent'
	# server.register_blueprint(google_bp, url_prefix=f'{base_path}/login')

	google_bp = make_google_blueprint(
		client_id=GOOGLE_CLIENT_ID,
		client_secret=GOOGLE_CLIENT_SECRET,
		scope=GOOGLE_SCOPES,
		redirect_to='login_success',
	)
	google_bp.authorization_url_params['access_type'] = 'offline'
	google_bp.authorization_url_params['prompt'] = 'consent'
	server.register_blueprint(google_bp, url_prefix=f'{base_path}/login')

	@server.route('/')
	def index():
		return flask.redirect(f'{base_path}/')


	# @server.route(f'{base_path}/')
	# def base_home():
	# 	# If not authorized yet, start OAuth and ask Google to send us back here
	# 	if not google.authorized:
	# 		return flask.redirect(flask.url_for('google.login', next=f'{base_path}/login-success'))

	# 	# We are authorized: finalize our own session/cache once
	# 	if not check_authorization():
	# 		# Token is missing/expired or userinfo call failed; restart OAuth
	# 		return flask.redirect(flask.url_for('google.login', next=f'{base_path}/login-success'))

	# 	# Land on your real app entry (adjust the path if you want)
	# 	return flask.redirect(f'{base_path}/')


	@server.route(f'{base_path}/login')
	def login_entry():
		# return flask.redirect(flask.url_for('google.login', next=flask.url_for('login_success', _external=True)))
		return flask.redirect(flask.url_for('google.login'))

	@server.route(f'{base_path}/login-success')
	def login_success():
		"""Post-login handler: verifies OAuth success, hydrates session/Redis,
		and redirects to the main app. This needs to be an independent route from anything Dash controls
		hence why this seems redundant with base_home().
		"""
		# If Google didn’t finish for some reason, start again and come back here
		if not google.authorized:
			# return flask.redirect(flask.url_for('google.login', next=flask.url_for('login_success', _external=True)))
			return flask.redirect(flask.url_for('google.login'))

		# Hydrate session/Redis; if this fails, restart OAuth and come back here
		if not check_authorization():
			return flask.redirect(flask.url_for('google.login'))

		return flask.redirect(f'{base_path}/')

	@server.route(f'{base_path}/login/revoke')
	def revoke():
		session_id = flask.session.get('session_id')
		if not session_id:
			return 'No active session to revoke.', 400
		else:
			flask.session.clear()

		# Retrieve credentials from Redis
		creds_store = AuthCredentials(CACHE_KEY, FLASK_ENCRYPTION_KEY)
		cred_data = creds_store.get_google_credentials(session_id)
		if not cred_data:
			logger.debug('No credentials found in Redis for session.')
			return 'No credentials found in Redis.', 400

		logger.debug(f'Retrieved credentials: {cred_data}')
		try:
			if 'google_oauth_token' not in cred_data:
				raise Exception('No oauth token found in session data, please log in again')

			token = cred_data['google_oauth_token'].get('access_token')
			refresh_token = cred_data['google_oauth_token'].get('refresh_token')
			token_uri = 'https://oauth2.googleapis.com/token'
			client_id = GOOGLE_CLIENT_ID
			client_secret = GOOGLE_CLIENT_SECRET
			raw_scopes = cred_data['google_oauth_token'].get('scope', '')
			if isinstance(raw_scopes, str):
				scopes = raw_scopes.split()
			elif isinstance(raw_scopes, list):
				scopes = raw_scopes
			else:
				raise ValueError('Invalid scope format. Expected string or list.')

			if not token:
				logger.debug(f'Missing token in credentials: {cred_data}')
				return 'No valid token found in credentials.', 400
			if not refresh_token:
				logger.debug('Missing refresh_token in credentials.')
				# Continue revocation of access token anyway

			credentials = Credentials(
				token=token,
				refresh_token=refresh_token,
				token_uri=token_uri,
				client_id=client_id,
				client_secret=client_secret,
				scopes=scopes,
			)
			if credentials.expired and credentials.refresh_token:
				credentials.refresh(Request())
				creds_store.save_google_credentials(session_id, {
					'token': credentials.token,
					'refresh_token': credentials.refresh_token,
					'token_uri': credentials.token_uri,
					'client_id': credentials.client_id,
					'client_secret': credentials.client_secret,
					'scopes': credentials.scopes,
				})

			# Revoke the (access) token
			revoke_response = requests.post(
				'https://oauth2.googleapis.com/revoke',
				params={'token': credentials.token},
				headers={'content-type': 'application/x-www-form-urlencoded'},
			)

			# Clear Redis and Flask session
			redis_client.delete(f'{CACHE_KEY}:session:{session_id}')
			flask.session.clear()

			if revoke_response.status_code == 200:
				return 'Credentials successfully revoked and cleared.', 200
			else:
				try:
					error_details = revoke_response.json()
				except Exception:
					error_details = {'error': 'Unknown error'}
				logger.debug(f'Failed to revoke credentials: {error_details}')
				return f"Failed to revoke credentials: {error_details.get('error', 'Unknown error')}", 400

		except Exception as e:
			logger.debug(f'Exception during revocation: {str(e)}')
			return f'An error occurred during revocation: {str(e)}', 500

	return server

def is_app_authenticated() -> bool:
	if not ENABLE_GOOGLE_AUTH:
		return True
	# Primary signal set by Flask-Dance on successful login:
	if 'google_oauth_token' in flask.session:
		return True
	# Fallback: pull from Redis by session_id and hydrate Flask session
	sid = flask.session.get('session_id')
	if not sid:
		return False
	try:
		from auth import AuthCredentials
		creds = AuthCredentials(CACHE_KEY, FLASK_ENCRYPTION_KEY).get_google_credentials(sid)
		if creds and 'google_oauth_token' in creds:
			flask.session['google_oauth_token'] = creds['google_oauth_token']
			return True
	except Exception as e:
		flask.current_app.logger.debug(f'Auth lookup failed: {e}')
	return False


def render_unauthorized_app() -> html.Div:
	from app import BASE_PATH
	page = dbc.Stack([
		dbc.Card([
			dbc.Stack([
				html.H2("Access Required"),
				html.P("Request access from Nick Earl to view this dashboard."),
				dbc.Button(
					"Sign in",
					color="primary",
					size="lg",
					href=f"{BASE_PATH}/login",   # e.g. "/overview-app/login"
					className="mt-3",
				),
				html.Img(src=get_asset_url('images/fail_cart.png'), style={'min-width':'100px','max-width':'200px','min-height':'100px','max-height':'200px'}),
			],gap=3,className='align-items-center justify-content-center'),
		],style={'max-width':'50vw','min-width':'25vw','max-height':'60vh','min-height':'40vh','border-radius':'1rem','flex':'1','border':'1px lightgray solid','border-radius':'1rem','boxShadow': '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.06)','padding':'1rem'})
	],gap=3,className='align-items-center justify-content-center',style={'height':'100vh','textAlign':'center'})
	return page

def is_page_authenticated(
						auth_list:list[str] | None = None,
						) -> bool:
	"""
		Determines if the current user is authenticated to view the given path + query parameters
		args:
			auth_list: list of authorized user emails (lowercase)
	"""
	if not ENABLE_GOOGLE_AUTH:
		return True

	auth_list = auth_list or []
	auth_list = [a.lower() for a in auth_list]
	check_authorization()
	user = flask.session.get('user')
	if user:
		if auth_list and user.get('email').lower() in auth_list:
			return True
	return False

def render_unauthorized_page() -> html.Div:
	page = dbc.Stack([
		dbc.Card([
			dbc.Stack([
				html.H2("Access Required"),
				html.P("Request access from Nick Earl to view this dashboard."),
				html.Img(src=get_asset_url('images/fail_cart.png'), style={'min-width':'100px','max-width':'200px',',min-height':'100px','max-height':'200px'}),
			],gap=3,className='align-items-center justify-content-center'),
		],style={'max-width':'50vw','min-width':'25vw','max-height':'60vh','min-height':'40vh','border-radius':'1rem','flex':'1','border':'1px lightgray solid','border-radius':'1rem','boxShadow': '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.06)','padding':'1rem'})
	],gap=3,className='align-items-center justify-content-center',style={'height':'100vh','textAlign':'center'})
	return page