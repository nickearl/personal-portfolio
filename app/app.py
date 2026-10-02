import os
import logging
import uuid
import re
import socket
from datetime import date, datetime, timedelta
import flask
from werkzeug.middleware.proxy_fix import ProxyFix
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dotenv import load_dotenv, find_dotenv
from flask.helpers import get_root_path
import pandas as pd
import plotly.io as pio
from conf import GlobalUInterface, DISPLAY_NAME, BASE_PATH as APP_SLUG
load_dotenv(find_dotenv())

"""
Base Dash App Template

Core dependencies:
	pip install flask gunicorn requests dash dash-bootstrap-components python-dotenv pandas numpy plotly pytz bs4
	OR for UV
	uv add flask gunicorn requests dash dash-bootstrap-components python-dotenv pandas numpy plotly pytz bs4
LLMs (Optional):
	pip install google-generativeai openai

Slack (Optional):
	pip install slack-sdk

Running the app:
	flask --app app run -p 1701    # Run the app on port 1701
"""

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SERVER_NAME = os.environ.get('SERVER_NAME')
BASE_PATH = f'/{APP_SLUG}'
FLASK_SECRET_KEY = os.environ['FLASK_SECRET_KEY']
SITE_URL = 'https://portfolio.nickearl.net'

# Dash builds each page's link-preview meta tags by matching the request path against page paths, but
# compares the full path ("portfolio/dashboard") with paths registered without the routes prefix
# ("dashboard"), so no page ever matched and previews fell back to blank. Strip the prefix first.
_dash_path_to_page = dash._pages._path_to_page
dash._pages._path_to_page = lambda path_id: _dash_path_to_page(path_id.removeprefix(APP_SLUG).strip('/'))
ui = GlobalUInterface()

def serve_app_layout():
	def layout():
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
		# gzip responses: Cloud Run doesn't compress, and plotly.js plus the dashboard's data payload are ~13MB raw
		compress=True,
		external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP,dbc.icons.FONT_AWESOME])
	logger.info(f'host ip: {socket.gethostbyname(socket.gethostname())}')
	logger.info(f'host name: {socket.gethostname()}')
	logger.info(f'environment: {os.environ["DEPLOY_ENV"]}')
	app.layout = serve_app_layout()
	return app

def create_dash_app(server):

	from dash_app.callbacks import register_callbacks
	logger.info(f'Creating Dash app: {SERVER_NAME} at /{APP_SLUG}/')
	register_dash_app(server, 'dash_app', DISPLAY_NAME, APP_SLUG, assemble_dash_app_from_components, register_callbacks)

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
					# Link previews (og:/twitter: tags); image is relative to the assets folder
					description=page_config['share_description'],
					image=f'images/share/{page_name}.jpg',
					layout=page_layout(page_ui()))

		register_callbacks_fun(new_dash_app)

def create_flask_server():
	server = flask.Flask(__name__)
	# Cloud Run terminates TLS; trust its X-Forwarded-Proto so generated URLs (link previews) use https
	server.wsgi_app = ProxyFix(server.wsgi_app, x_proto=1)
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
			return 'ok', 200

		@server.route('/')
		def index():
			return flask.redirect(BASE_PATH)

		@server.route('/robots.txt')
		def robots():
			return flask.Response(f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n', mimetype='text/plain')

		@server.route('/sitemap.xml')
		def sitemap():
			urls = ''.join(f'<url><loc>{SITE_URL}{p["full_path"]}</loc></url>' for p in ui.pages.values() if p['enabled'])
			return flask.Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', mimetype='application/xml')

		@server.route('/favicon.ico')
		def favicon():
			return flask.send_from_directory(get_root_path(__name__) + '/dash_app/assets', 'favicon.ico')

	logger.info('Flask routes configured.')

	return server

	
logger.info('app.py successfuly initialized')
server = create_flask_server()
logger.info('Flask server successfuly initialized')
server = create_dash_app(server)
logger.info('Dash app successfuly initialized')