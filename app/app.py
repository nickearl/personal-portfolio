import os
import logging
import uuid
import re
import socket
from datetime import date, datetime, timedelta
import flask
from flask import Flask, request, make_response, session
import dash
from dash import CeleryManager, html, dcc
import dash_bootstrap_components as dbc
from dotenv import load_dotenv, find_dotenv
import redis
from flask.helpers import get_root_path
from celery import Celery, Task
import pandas as pd
import plotly.io as pio
from conf import GlobalUInterface, DISPLAY_NAME, BASE_PATH as APP_SLUG
from auth import is_app_authenticated
load_dotenv(find_dotenv())

"""
Base Dash App Template

Core dependencies:
	pip install flask gunicorn requests dash dash-bootstrap-components python-dotenv redis celery pandas numpy plotly pytz bs4
	OR for UV
	uv add flask gunicorn requests dash dash-bootstrap-components python-dotenv redis celery pandas numpy plotly pytz bs4
LLMs (Optional):
	pip install google-generativeai openai

Google Auth (Optional):
	pip install flask-dance google-auth google-auth-oauthlib oauthlib cryptography

Slack (Optional):
	pip install slack-sdk

Running the app:
	Open two terminals and run the following:
	flask --app app run -p 1701    # Run the app on port 1701
	celery -A app:celery_app worker --loglevel=INFO --concurrency=2 -Q {queue id}    # Run the celery worker, replace {queue id} with value like 'prefix-queue' where 'prefix' is your app prefix
"""

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEPLOY_ENV = os.getenv('DEPLOY_ENV', 'prod')
if DEPLOY_ENV.lower() == 'dev':
	os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
REDIS_URL = os.environ['REDIS_URL']
SERVER_NAME = os.environ.get('SERVER_NAME')
BASE_PATH = f'/{APP_SLUG}'
FLASK_SECRET_KEY = os.environ['FLASK_SECRET_KEY'] 
# Boolean flag from env; accepts 1/true/yes/on
ENABLE_GOOGLE_AUTH = os.getenv('ENABLE_GOOGLE_AUTH', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
redis_client = redis.from_url(REDIS_URL)
cache_uuid = uuid.uuid4().hex
ui = GlobalUInterface()

def serve_app_layout():
	def layout():
		if ENABLE_GOOGLE_AUTH and not is_app_authenticated():
				return html.Div(["You are not authorized to view this page. Please ",html.A("log in.",href=f'{BASE_PATH}/login')])
		logger.info('Serving protected layout...')
		logger.debug(f'Flask session id: {flask.session.get("session_id")}')
		return ui.render_global_wrapper(flask.session)
	return layout

def assemble_dash_app_from_components(server, url_base_pathname, assets_folder, meta_tags, use_pages=False, pages_folder=''):

	logger.info('root path: {}'.format(get_root_path('.dash_app')))
	pd.options.mode.copy_on_write = True
	pd.options.display.float_format = '{:.2f}'.format
	pd.options.display.precision = 4
	pio.templates.default = "plotly_white"

	app = dash.Dash(
		server=server,
		assets_folder=assets_folder,
		meta_tags=meta_tags,
		routes_pathname_prefix=url_base_pathname,
		suppress_callback_exceptions=True,
		prevent_initial_callbacks='initial_duplicate',
		update_title=None,
		use_pages=use_pages,
		pages_folder=pages_folder,
		external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP,dbc.icons.FONT_AWESOME])
	logger.info(f'host ip: {socket.gethostbyname(socket.gethostname())}')
	logger.info(f'host name: {socket.gethostname()}')
	logger.info(f'environment: {os.environ["DEPLOY_ENV"]}')
	app.layout = serve_app_layout()
	return app

def create_celery_server(server):

	class FlaskTask(Task):
		def __call__(self, *args: object, **kwargs: object) -> object:
			with server.app_context():
				return self.run(*args, **kwargs)

	celery_app = Celery(
		server.name,
		#imports = ('tasks',), # uncomment and add files like 'tasks.py' that scheduled tasks need access to as 'tasks'
		broker=REDIS_URL,
		backend=REDIS_URL,
		task_ignore_result=True,
		task_cls=FlaskTask,
		include=['dash_app.callbacks'],
	)

	# Set a unique queue name per app to avoid issues when multiple apps share the same Redis server
	queue_name = SERVER_NAME
	celery_app.conf.task_default_queue = queue_name
	celery_app.conf.task_routes = {
		'app.*': {'queue': queue_name},
		'long_callback_*': {'queue': queue_name},
	}

	celery_app.conf.update(
		event_serializer='json',
		task_serializer='json',
		result_serializer='json',
		accept_content=['json'],
		)
	celery_app.set_default()
	server.extensions["celery"] = celery_app
	return celery_app

def create_dash_app(server):

	from dash_app.callbacks import register_callbacks
	logger.info(f'Creating Dash app: {SERVER_NAME} at /{APP_SLUG}/')
	register_dash_app(server, 'dash_app', SERVER_NAME, APP_SLUG, assemble_dash_app_from_components, register_callbacks)

	return server

def register_dash_app(app, app_dir, title, base_pathname, create_dash_fun, register_callbacks_fun):
	import importlib
	meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}
	with app.app_context():
		new_dash_app = create_dash_fun(
			server=app,
			url_base_pathname=f'/{base_pathname}/',
			assets_folder=get_root_path(__name__) + f'/{app_dir}/assets/',
			meta_tags=[meta_viewport],
			use_pages=True,
			pages_folder=get_root_path(__name__) + f'/{app_dir}/pages/',
		)
		new_dash_app.title = title

		# Register all pages configured in conf.py
		for page_name, page_config in ui.pages.items():
			if page_config['enabled']:
				logger.info(f'Registering page: {page_name}')
				module = importlib.import_module(f'dash_app.pages.{page_name}')
				page_ui = getattr(module, 'UInterface')
				page_layout = getattr(module, 'create_app_layout')
				dash.register_page(
					page_config['display_name'],
					title=f'{DISPLAY_NAME} | {page_config["display_name"]}',
					path=page_config['path'],
					layout=page_layout(page_ui()))

		register_callbacks_fun(new_dash_app)

def create_flask_server():
	server = flask.Flask(__name__)
	logger.info('* Initializing Flask server * ')
	server.secret_key = FLASK_SECRET_KEY
	logger.info(f'Got secret key')
	server.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)

	logger.info('About to configure Flask routes...')
	with server.app_context():

		@server.before_request
		def ensure_session():
			# Mark the session as permanent so the PERMANENT_SESSION_LIFETIME applies
			flask.session.permanent = True
			# Only generate a new session_id if one doesn't exist
			if 'session_id' not in flask.session:
				new_session_id = str(uuid.uuid4())
				flask.session['session_id'] = new_session_id
				server.logger.info(f'New session_id created.')
				logger.info(f'New session_id created.')

		@server.route('/healthz')
		def healthz():
			try:
				redis_client.ping()
				return 'ok', 200
			except Exception:
				return 'degraded', 503

	if ENABLE_GOOGLE_AUTH:
		logger.info('* Google Auth enabled * ')
		from auth import setup_oauth
		server = setup_oauth(server=server, base_path=BASE_PATH)
		logger.info('OAuth setup complete.')
	else:
		@server.route('/')
		def index():
			return flask.redirect(BASE_PATH)
	
		logger.info('Flask routes configured.')

	return server

	
logger.info('app.py successfuly initialized')
server = create_flask_server()
logger.info('Flask server successfuly initialized')
celery_app = create_celery_server(server)
logger.info('Celery succesfully initialized')
BACKGROUND_CALLBACK_MANAGER = CeleryManager(celery_app)
logger.info('Celery/Dash integration complete')
server = create_dash_app(server)
logger.info('Dash app successfuly initialized')