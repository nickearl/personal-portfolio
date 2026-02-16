import os
import logging
import flask
import json
import io
import zipfile
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta
import dash
from dash import html, dcc, Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from dash_app.pages.ai import UInterface as ai_ui
from dash_app.pages.home import UInterface as home_ui
from dash_app.pages.dashboard import UInterface as dashboard_ui
from dash_app.pages.sales_enablement import UInterface as sales_ui

REDIS_URL = os.environ['REDIS_URL']

logger = logging.getLogger(__name__)

AI_UI = None
HOME_UI = None
DASHBOARD_UI = None

def register_callbacks(app):
	from app import BACKGROUND_CALLBACK_MANAGER

	global AI_UI, DASHBOARD_UI, HOME_UI
	if AI_UI is None: AI_UI = ai_ui()
	if HOME_UI is None: HOME_UI = home_ui()
	if DASHBOARD_UI is None:  DASHBOARD_UI  = dashboard_ui()

#######################
# Global
#######################

	app.clientside_callback(
		"""
		function(n_intervals) {
			if (n_intervals > 0) {
				window.location.reload(true);
			}
			return ''; 
		}
		""",
		Output('full-refresh-script','children'),
		Input('full-refresh-interval','n_intervals'),
	)

	@app.callback(
		Output('offcanvas-sidebar','is_open'),
		Input('nav-logo','n_clicks')
	)
	def open_sidebar(n_clicks):
		logger.info('[' + str(datetime.now()) + '] | '+ '[open_sidebar] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			raise PreventUpdate
		if n_clicks !=None:
			return True



	@app.callback(
		Output('download-results-downloader', 'data'),
		Input('download-results-button','n_clicks'),
		State('download-results-store','data'),
		prevent_initial_call=True
	)
	def download_files(n_clicks, data):
		"""
			Download results as zip of csv files
			The dcc.Store has data in the format:
			{
				'table_name_1': [ {row1}, {row2}, ... ],
				'table_name_2': [ {row1}, {row2}, ... ],
				...
			}
		"""
		logger.info(f'[{datetime.now()}] | [download_files] | trig_id: [{dash.ctx.triggered_id}]')
		if n_clicks == None:
			raise PreventUpdate
		else:
			try:
				results = json.loads(data)
			except Exception as e:
				logger.error(f'Error loading data from store: {e}')
				raise PreventUpdate
			for key, value in results.items():
				if not isinstance(value, list):
					try:
						value = json.loads(value)
					except Exception as e:
						logger.error(f'Error loading table {key} data: {e}')
						raise PreventUpdate
				results[key] = pd.DataFrame(value)
			zip_buffer = io.BytesIO()
			with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
				for name,df in results.items():
					csv_buffer = io.StringIO()
					df.to_csv(csv_buffer, index=False)
					zf.writestr(f"{name}.csv", csv_buffer.getvalue())

			zip_buffer.seek(0)  # Rewind the buffer for reading
			return dcc.send_bytes(zip_buffer.getvalue(), 'results.zip')
			# single file version:
			# df = pd.DataFrame().from_dict(json.loads(data))
			# csv_string = df.to_csv(index=False)
			# return dcc.send_string(csv_string, 'results.csv')

#######################
# Home
########################


	@app.callback(
		Output('article-carousel','active_index'),
		Input('a-list-button-0','n_clicks'),
		Input('a-list-button-1','n_clicks'),
		Input('a-list-button-2','n_clicks'),
		Input('a-list-button-3','n_clicks'),
	)
	def article_links(n0,n1,n2,n3):
		logger.info('[' + str(datetime.now()) + '] | '+ '[article_links] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			raise PreventUpdate
		if n0 !=None or n1 !=None or n2 !=None:
			if dash.ctx.triggered_id == 'a-list-button-0':
				return 0
			elif dash.ctx.triggered_id == 'a-list-button-1':
				return 2
			elif dash.ctx.triggered_id == 'a-list-button-2':
				return 3
			elif dash.ctx.triggered_id == 'a-list-button-3':
				return 5
			
	@app.callback(
		Output("home-image-modal", "is_open"),
		Output("home-modal-image", "src"),
		Input("home-carousel-wrapper", "n_clicks"),
		State("article-carousel", "active_index"),
		State("home-image-modal", "is_open"),
		prevent_initial_call=True,
	)
	def toggle_home_modal(n_clicks, active_index, is_open):
		if n_clicks:
			if active_index is None: active_index = 0
			try:
				img_src = HOME_UI.carousel_items[active_index]['modal_src']
				return not is_open, img_src
			except Exception as e:
				logger.error(f"Error opening modal: {e}")
				return is_open, None
		return is_open, None

#######################
# AI Demos
#######################


	@app.callback(
		Output('ai-image-container','children'),
		Input('ai-input-image-submit', 'n_clicks'),
		State('ai-input-image-text','value'),
		running=[
			(Output('ai-input-image-submit', 'disabled'), True, False),
			(Output('ai-input-image-submit', 'children'), [dbc.Spinner(size='sm'),' Asking Gemini...'], [html.I(className='bi bi-robot'),' Submit']),
		],
		prevent_initial_call=True,
		background=True,
    	manager=BACKGROUND_CALLBACK_MANAGER,
	)
	def ai_generate_image(n_clicks,input_prompt):
		logger.info('[' + str(datetime.now()) + '] | '+ '[ai_generate_image] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			raise PreventUpdate
		else:
			if n_clicks != None and n_clicks > 0:
				image_url = None
				ui = ai_ui()
				try:
					image_url = ui.ai_generate_image(input_prompt, style='anime')
				except Exception as e:
					logger.error(f'Error getting image url: {e}')
				return html.Img(src=image_url,style={'width':'100%','border-radius':'4rem','padding':'2rem'})


	@app.callback(
		Output('ai-chart-container','children'),
		Input('ai-input-colors-submit', 'n_clicks'),
		State('ai-input-colors-text','value'),
		running=[
			(Output('ai-colors-chart-object','style'), {'display':'none'}, None),
			(Output('loading-card', 'style'), None, {'display':'none'}),
			(Output('ai-input-colors-submit', 'disabled'), True, False),
			(Output('ai-input-colors-submit', 'children'), [dbc.Spinner(size='sm'),' Asking Gemini...'], [html.I(className='bi bi-robot'),' Submit']),
		],
		prevent_initial_call=True,
		background=True,
    	manager=BACKGROUND_CALLBACK_MANAGER,
	)
	def ai_custom_colors(n_clicks,input_prompt):
		logger.info('[' + str(datetime.now()) + '] | '+ '[ai_custom_colors] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			raise PreventUpdate
		else:
			if n_clicks != None and n_clicks > 0:
				o = None
				colors = []
				ui = ai_ui()
				try:
					colors = ui.ai_color_sequence(input_prompt)
					o = dashboard_ui().render_summary_charts(w=750,h=400,chart_only=True,colors=colors)
				except Exception as e:
					logger.warning('Retrying ...')
					logger.warning(e)
					try:
						colors = ui.ai_color_sequence(input_prompt)
						o = dashboard_ui().render_summary_charts(w=750,h=400,chart_only=True,colors=colors)
					except Exception as e:
						logger.error('Retry failed, falling back to default colors')
						o = dbc.Stack([
							ui.show_alert("We didn't get a usable response from Gemini. Sometimes you get a miss!  Try your prompt again, or try modifying it slightly.",color='warning'),
							dashboard_ui().render_summary_charts(w=750,h=400,chart_only=True),
						],gap=3)
				return o
		 
	@app.callback(
		Output('sales-pitch-output', 'children'),
		Output('sales-download-deck', 'data'),
		Input('sales-pitch-submit', 'n_clicks'),
		State('sales-input-company', 'value'),
		State('sales-input-industry', 'value'),
		State('sales-input-audience', 'value'),
		State('sales-input-style', 'value'),
		State('sales-input-length', 'value'),
		prevent_initial_call=True,
		background=True,
		manager=BACKGROUND_CALLBACK_MANAGER,
	)
	def sales_generate_deck(n_clicks, company, industry, audience, style, length):
		logger.info(f'[{datetime.now()}] | [sales_generate_deck] | trig_id: [{dash.ctx.triggered_id}]')
		if not n_clicks:
			raise PreventUpdate
		
		ui = sales_ui()
		result = ui.ai_generate_deck(company, industry, audience, style, length)
		
		if 'error' in result:
			return dcc.Markdown(result['error']), None
		
		if 'component' in result:
			return result['component'], None
			
		return dcc.Markdown("Error: No content generated."), None

	@app.callback(
		Output("sales-onboarding-modal", "is_open"),
		Input("close-onboarding-modal", "n_clicks"),
		prevent_initial_call=True,
	)
	def close_sales_modal(n):
		return False

#######################
# Dashboard
#######################

	@app.callback(
		Output('store-configs','data'),
		Input('filter-date','value'),
		Input('filter-country','value'),
		Input('filter-device-type','value'),
		Input('filter-video-category','value'),
		Input('filter-video-title', 'value'),
		Input('filter-num-chart-items','value'),
		State('filter-date','value'),
		State('filter-country','value'),
		State('filter-device-type','value'),
		State('filter-video-category','value'),
		State('filter-video-title', 'value'),
		Input('filter-num-chart-items','value'),
		State('store-configs','data'),
	)
	def set_configs(in_date,in_country,in_device_type,in_video_category,in_video_title,in_num_chart_items,st_date,st_country,st_device_type,st_video_category,st_video_title,st_num_chart_items,store_data):
		logger.info('[' + str(datetime.now()) + '] | '+ '[set_configs] | ' + str(dash.ctx.triggered_id))
		# if dash.ctx.triggered_id == None:
		# 	raise PreventUpdate
		ui = dashboard_ui()
		data = ui.default_configs
		try:
			data = json.loads(store_data)
		except Exception as e:
			logger.error(f'Could not load configs from store: {e}')
			pass
		try:
			data['date'] = st_date
			data['country'] = st_country
			data['device_type'] = st_device_type
			data['video_category'] = st_video_category
			data['video_title'] = st_video_title
			data['num_chart_items'] = st_num_chart_items
		except Exception as e:
			logger.error(f'Error setting config values: {e}')
		return json.dumps(data)



	@app.callback(
		Output('tab-summary','children'),
		Output('tab-content-performance','children'),
		Output('tab-devices','children'),
		Input('store-configs','data'),
		State('tab-summary','children'),
		State('tab-content-performance','children'),
		State('tab-devices','children'),
	)
	def visualize_results(data,s1,s2,s3):
		logger.info('[' + str(datetime.now()) + '] | '+ '[visualize_results] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			if s1 == None or s1 == [] or s2 == None or s2 == [] or s3 == None or s3 == []:
				logger.info('initial chart load')
				pass
			else:
				raise PreventUpdate
		chart_configs = None
		try:
			chart_configs = json.loads(data)
		except Exception as e:
			logger.warning(f'No config, using default: {e}')
			pass
		ui = dashboard_ui()
		grid = ui.render_daily_grid(chart_configs)
		line_chart = ui.render_daily_line_chart(chart_configs)
		device_pie = ui.render_device_share(chart_configs)
		content_sun = ui.render_category_share(chart_configs)

		summary = ui.render_summary_charts(chart_configs)
		
		content_perf = dbc.Container([
			content_sun,
			html.Br(),
			line_chart,
			html.Br(),
			grid,

		])
		devices = dbc.Container([
			device_pie
		])

		return summary, content_perf, devices

	@app.callback(
		Output('daily-chart-grid', 'exportDataAsCsv'),
		Input('download-csv', 'n_clicks'),
	)
	def download_csv(n_clicks):
		logger.info('[' + str(datetime.now()) + '] | '+ '[download_csv] | ' + str(dash.ctx.triggered_id))
		if dash.ctx.triggered_id == None:
			raise PreventUpdate
		if n_clicks != None and n_clicks > 0:
			return True
		else:
			return False