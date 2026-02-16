#!/usr/bin/env python
# coding: utf-8

import os, json, random, re, base64, io, uuid, time, socket, calendar, math, logging
import pathlib
from dotenv import load_dotenv, find_dotenv
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, ALL, MATCH, Patch, callback
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import date, datetime


# Get environment variables
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class UInterface:
	def __init__(self):
		logger.info('Initializing Dashboard UI')
		self.init_time = datetime.now()
		self.product_name = 'BI Demo | Dashboard | Nick Earl'
		self.styles = {
			'color_sequence': ['#FD486D', '#9F4A86', '#F5D107', '#86D7DC', '#333D79', '#E5732D', '#4CAF8E', '#722B5C', '#FFC10A', '#005580'],
			'portrait_colors': ['#86D7DC', '#9B004E','#FA005A','#FFC500','#520044'],
			'comp_colors':['#54898d','#9F4A86'],
			'category_color_map': {},
			'category_color_legend': [],
		}
		# Resolve paths relative to this file to support running from root or app/ dir
		self.base_dir = pathlib.Path(__file__).parent.parent.resolve()
		self.data = {
			'traffic_daily': pd.read_csv(self.base_dir / 'assets' / 'data' / 'traffic_daily.csv'),
			'traffic_summary': None,
			'content_metadata': None,
		}
		self.default_configs = {
			'country':None,
			'date':None,
			'device_type':None,
			'video_category':None,
			'video_title':None,
			'num_chart_items':None,
		}
		dates =  self.data['traffic_daily']['date'].unique()
		countries = self.data['traffic_daily']['country'].unique()
		device_types = self.data['traffic_daily']['device_type'].unique()
		video_categories = self.data['traffic_daily']['video_category'].unique()
		video_titles = self.data['traffic_daily']['video_title'].unique()
		i = 0
		for cat in self.data['traffic_daily']['video_category'].unique():
			self.styles['category_color_map'][cat] = self.styles['color_sequence'][i]
			i = i+1
		for cat,color in self.styles['category_color_map'].items():
			self.styles['category_color_legend'].append(
				dbc.Stack([
					html.Div([],style={'height':'25px','width':'25px','background-color':color}),
					html.Span(cat,style={'font-weight':'bold'}),
				],direction='horizontal',gap=3,className='d-flex align-items-center justify-content-start')
			)

		self.layout = {
			'filters': dbc.Container([
				dbc.Stack([
					dcc.Dropdown(options=dates,placeholder='Date',id='filter-date',className='filter-dropdown',multi=True),
					dcc.Dropdown(options=countries,placeholder='Country',id='filter-country',className='filter-dropdown',multi=True),
					dcc.Dropdown(options=device_types,placeholder='Device Type',id='filter-device-type',className='filter-dropdown',multi=True),
					dcc.Dropdown(options=video_categories,placeholder='Video Category',id='filter-video-category',className='filter-dropdown',multi=True),
					dcc.Dropdown(options=video_titles,placeholder='Video Title',id='filter-video-title',className='filter-dropdown',multi=True),
					dcc.Dropdown(options=[x+1 for x in range(10)],placeholder='Num Chart Items',id='filter-num-chart-items',className='filter-dropdown'),
				],direction='horizontal',gap=3,className='d-flex align-items-center justify-content-center'),
			],fluid=True),
			'loading_modal': dbc.Modal([
				dbc.Card([
					dbc.CardHeader([
						dbc.Progress(id='loading-modal-bar',value=0, striped=True, animated=True, color='#86D7DC',style={'background-color':'#3A434B'}),
						html.H3(['Searching over 50MM pages for insights...'],id='loading-modal-text',style={'color':'white'}),
						dbc.ListGroup([],id='loading-modal-list'),
					]),
					dbc.CardBody([
						html.Div([],id='loading-modal-quote-container')
					]),
				],className='loading-card'),
			],is_open=False,className='loading-modal',id='loading-modal'),
			'header': dbc.Stack([
				html.Img(src='assets/images/uhf_logo.png',style={'width':'160px','height':'100px'}),
				html.H3(['UHF+ | Key Stats']),
				html.Div([
					html.Span(
						[
							'This interactive dashboard is built entirely in python using ',
							html.A('free open-source tools',href='https://plotly.com/graphing-libraries/',target='_blank'),
							', without any proprietary BI solution.',
						],
					),
					html.Br(),
					html.Span([
							"Here we're analyzing video data from an up-and-coming streaming service in the ",
							html.Span('FAST',id='fast-acro',style={'font-weight':'bold','color':self.styles['color_sequence'][1]}),
							' space.'
							],
					),
					dbc.Popover(
						[
							dbc.PopoverHeader(dcc.Markdown('**F**ree **A**d-**S**upported **T**elevision')),
							dbc.PopoverBody('eg, PlutoTV, Tubi... and UHF+!'),
						],
						target='fast-acro',
						trigger='hover',	
					),
					dbc.Stack([
						html.Span('What is this dataset?',style={'font-size':'1rem','color':self.styles['color_sequence'][1]}),
						html.I(id='about-dataset-info',className='bi bi-info-circle-fill',style={'font-size':'1.5rem','color':self.styles['color_sequence'][1]}),
					],direction='horizontal',gap=3,className='d-flex align-items-center flex-row justify-items-end'),
					dbc.Popover(
						[
							dbc.PopoverHeader('About This Dataset'),
							dbc.PopoverBody([
								dbc.Stack([
									html.Span("I didn't want to just use a boring generic sample dataset for this app, so I wrote an algorithm to generate a reasonably realistic dummy dataset that might be interesting to visualize."),
									html.Span([
										'You can ',
										html.A('view the script in my Github repo',href='https://github.com/nickearl/bi-demo/blob/main/scripts/gen_datasets.ipynb',target='_blank',style={'font-weight':'bold'}),
										'.',
									]),
								],gap=3),
							]),
						],
						placement='top',
						target='about-dataset-info',
						trigger='hover',
					),

				]),
				
			],direction='horizontal',gap=3,className='header d-flex justify-content-center align-items-center'),
			# 'footer': dbc.Stack([
			# 	html.Span(f'Nick Earl © {datetime.now().year}', className='footer-text'),
			# 	html.A('linkedin.com/in/nickearl',href='https://www.linkedin.com/in/nickearl/',className='footer-text'),
			# 	html.A('github.com/nickearl',href='https://github.com/nickearl',className='footer-text'),
			# 	html.A('nickearl.net',href='https://www.nickearl.net',className='footer-text'),
			# ],direction='horizontal',gap=3, className='footer d-flex justify-content-center align-items-center'),
		}
		self.layout['grid_container'] = dbc.Container([
			dcc.Loading(
				dbc.Card([],id='grid-container'),
				type='default',
				overlay_style={'visibility':'visible', 'filter': 'blur(2px)'},
				custom_spinner=self.layout['loading_modal']
			)	
		],fluid=True)
		tabs = []
		for tab in ['Summary','Content Performance','Devices']:
			idx = f'tab-{tab.replace(' ','-').lower()}'
			tabs.append(dbc.Tab([],id=idx,label=tab,labelClassName='tab-label',activeLabelClassName='tab-label-active'))

		self.layout['tabs_container'] = dbc.Stack([
			dcc.Loading(
				dbc.Tabs(tabs,id='tabs-container'),
				type='default',
				overlay_style={'visibility':'visible', 'filter': 'blur(2px)'},
				custom_spinner=self.layout['loading_modal']
			)	
		],direction='horizontal',gap=3,className='header d-flex justify-content-center align-items-center')

	def get_quote(self):
		pathname = self.base_dir / 'assets' / 'data' / 'quotes.csv'
		df = pd.read_csv(pathname)
		df = df.sample().fillna(0)
		quotee = df['quotee'].iloc[0]
		source_media = df['source_media'].iloc[0]
		if source_media == 0:
			source_media = ''
		quote_text = df['quote_text'].iloc[0]
		image_path = 'assets/images/default.png'
		try:
			image_path = 'assets/images/' + df['image'].iloc[0]
		except Exception as e:
			logger.warning('no image available, using default')
			pass
		cid = random.randrange(0,len(self.styles['portrait_colors']))
		color_code = self.styles['portrait_colors'][cid]
		card = dbc.Card([
			dbc.CardBody([
				dbc.Stack([
						dbc.Stack([
							html.Div([],className='quote-card-image',style={
								'background-image':f'url("{image_path}"),radial-gradient(circle at center, {color_code} 0, #3b434b 85%)',
								'background-size':'100px 100px',
								'width':'100px',
								'height':'100px',
							}),
							html.Span(f'"{quote_text}"',className='quote-card-text'),
						],direction='horizontal',gap=3),
						dbc.Stack([
							html.Span(f'- {quotee}',className='quote-card-quotee'),
							html.Span(f'{source_media}',className='quote-card-source-media'),
						],className='d-flex justify-content-end align-items-end'),
				],gap=3),
			]),
		],className='quote-card')

		return card

	def get_random_song(self):
		pathname = self.base_dir / 'assets' / 'data' / 'taylor_swift_songs.csv'
		with open(pathname) as g:
			df = pd.read_csv(g, sep=",", header=0)
		r = random.randrange(len(df.index))
		q = df.iloc[r]
		return q

	def render_daily_grid(self, configs=None):
		logger.info('rendering daily grid')
		df = self.data['traffic_daily']
		df['plays_per_user'] = df['video_plays'] / df['users']
		if configs == None:
			configs = self.default_configs
		for k,v in configs.items():
			if v != None and v != []:
				if k == 'num_chart_items':
					pass
				else:
					try:
						df = df[df[k] == v]
					except ValueError as e:
						df = df[df[k].isin(v)]
						pass


		columnDefs = []
		# for i in range(len(df.columns)):  # Easier but not as pretty
		# 	 columnDefs.append({
		# 		 'field': df.columns[i],
		# 	 }) 
		columnDefs.append({
			'field': df.columns[0],
			'headerName': 'Date',
		})
		columnDefs.append({
			'field': df.columns[1],
			'headerName': 'Country',
		})
		columnDefs.append({
			'field': df.columns[2],
			'headerName': 'Device Type',
		})
		columnDefs.append({
			'field': df.columns[3],
			'headerName': 'Video Category',
		})
		columnDefs.append({
			'field': df.columns[4],
			'headerName': 'Video Title',
		})
		columnDefs.append({
			'field': df.columns[5],
			'headerName': 'Users',
			'valueFormatter': {'function': "d3.format(',.0f')(params.value)"},
		})
		columnDefs.append({
			'field': df.columns[7],
			'headerName': 'Video Plays',
			'valueFormatter': {'function': "d3.format(',.0f')(params.value)"},
		})
		columnDefs.append({
			'field': df.columns[8],
			'headerName': 'Avg. Plays / User',
			'valueFormatter': {'function': "d3.format(',.1f')(params.value)"},
		})

		
		grid = dag.AgGrid(
			id='daily-chart-grid',
			rowData=df.to_dict('records'),
			columnDefs=columnDefs,
			className="ag-theme-quartz",
			dashGridOptions={
				'pagination':True,
				'tooltipShowDelay': 0,
				'tooltipHideDelay': 1000
			 },
			columnSize = 'autoSize',
		)
		grid = dbc.Stack([
			grid,
			dbc.Stack([
				dbc.Button(children=[html.I(className='bi bi-download'),' Download'], id='download-csv', color='success'),
			],direction='horizontal',gap=3,className='d-flex flex-row-reverse align-items-center justify-content-start'),
		],gap=3)
		return grid

	def render_daily_line_chart(self, configs=None):
		logger.info('rendering daily line chart')
		df = self.data['traffic_daily']
		df['plays_per_user'] = df['video_plays'] / df['users']
		item_limit = 5
		if configs == None:
			configs = self.default_configs
		for k,v in configs.items():
			if v != None and v != []:
				if k == 'num_chart_items':
					item_limit = v
				else:
					try:
						df = df[df[k] == v]
					except ValueError as e:
						df = df[df[k].isin(v)]
						pass
		top_items = df.groupby('video_title',as_index=False).sum('users').sort_values(by='users',ascending=False).head(item_limit)
		marker_colors = self.styles['color_sequence']
		fig = make_subplots(specs=[[{'secondary_y': True}]])
		mkr = 0
		for show in top_items['video_title'].unique():
			_df = df[df['video_title'] == show]
			_df = _df.groupby(['date','video_category','video_title'],as_index=False).agg({'users':'sum','video_plays':'sum'})
			fig.add_trace(
				go.Scatter(
					mode='lines',
					x=_df['date'],
					y=_df['users'],
					name=show,
					offsetgroup=0,
					textfont=dict(
						weight='bold',
						size=12,
					),
					line=dict(
						color=marker_colors[mkr],
						width=4,
						# dash='dash'
					),
				),
				#secondary_y=True,
			)
			mkr = mkr + 1

		fig.update_layout(
			title_text=f'Daily Audience by Show',
			uniformtext_minsize=10,
			uniformtext_mode='hide',
			template='plotly_white'
		)
		fig.update_xaxes(title_text='<b>Date</b>')
		fig.update_yaxes(title_text='<b>Total</b>', secondary_y=False)
		#fig.update_yaxes(title_text='<b>Avg. Imps / PV</b>', secondary_y=True))
		fig.update_yaxes(
			title_text='<b>Avg</b>',
			secondary_y=True)

		chart = dbc.Card([
			dcc.Graph(
				figure=fig,
				animate=False,
			)
		],className='viz-background-card')
		return chart
	
	def render_device_share(self, configs=None):
		logger.info('rendering device share chart')
		df = self.data['traffic_daily']
		
		if configs == None:
			configs = self.default_configs
		for k,v in configs.items():
			if v != None and v != []:
				if k == 'num_chart_items':
					pass
				else:
					try:
						df = df[df[k] == v]
					except ValueError as e:
						df = df[df[k].isin(v)]
						pass
		
		marker_colors = self.styles['color_sequence']
		w = 500
		h = 500
		fig = go.Figure()
		_df = df.groupby(['device_type'],as_index=False).agg({'video_plays':'sum'})
		_df['share_of_plays'] = _df['video_plays'].apply(lambda x: x / _df['video_plays'].sum())
		fig.add_trace(
			go.Pie(
				name='Plays by Device Type',
				labels=_df['device_type'],
				values=_df['video_plays'],
				hole=.5,
				marker_colors=marker_colors[3:],
			),
		)

		fig.update_layout(
			title_text=f'Mobile vs Desktop Share of Video Plays',
			uniformtext_minsize=10,
			uniformtext_mode='hide',
			template='plotly_white',
			width=w,
			height=h,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			)
		)


		fig2 = go.Figure()
		_df = df.groupby(['device_type'],as_index=False).agg({'users':'sum','video_plays':'sum'})
		_df['plays_per_user'] = _df['video_plays'] / ( _df['users'] * 0.7 ) # simulate user duplication across content
		fig2.add_trace(
			go.Bar(
				y=_df['device_type'],
				x=_df['plays_per_user'],
				orientation='h',
				marker_color=marker_colors,
				customdata=np.stack( (_df['device_type'],_df['plays_per_user'],), axis=-1),
				hovertemplate=
				"<b>%{customdata[0]}</b><br>" +
				"Avg. Plays per User: %{customdata[1]:.2f}<br>" +
				"<extra></extra>",
			),
		)

		fig2.update_layout(
			title_text=f'Mobile vs Desktop Engagement',
			uniformtext_minsize=10,
			uniformtext_mode='hide',
			template='plotly_white',
			width=w,
			height=h,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			)
		)

		fig3 = go.Figure()
		_df = df.groupby(['device_type','video_category','video_title'],as_index=False).agg({'users':'sum','video_plays':'sum'})
		_df['mobile_share'] = _df.apply(lambda x: x['users'] / _df['users'].sum() ,axis=1)
		_df = _df[_df['device_type'].str.lower() == 'mobile']
		_df['mobile_share_index'] = _df.apply(lambda x: (x['mobile_share'] / _df['mobile_share'].mean())-1,axis=1)
		_df = _df.sort_values(by='mobile_share_index',ascending=False)
		engagement_colors = []
		vals = []
		base_vals = []
		title_formatted = []
		for i in range(len(_df)):
			engagement_colors.append(self.styles['category_color_map'].get(_df['video_category'].iloc[i]))
			vals.append( abs(_df['mobile_share_index'].iloc[i] ) )
			base_vals.append( min(_df['mobile_share_index'].iloc[i],0)  )
			title_formatted.append(f'{_df['video_title'].iloc[i]} ({_df['mobile_share_index'].iloc[i]:+.2f})')
		fig3.add_trace(
			go.Bar(
				name='Mobile Share Index By Show',
				y=_df['video_title'],
				x=vals,
				orientation='h',
				marker_color=engagement_colors,
				base=base_vals,
				text=title_formatted,
				textposition='auto',
				customdata=np.stack( (_df['video_category'],_df['video_title'],_df['mobile_share_index']), axis=-1),
				hovertemplate=
				"<b>%{customdata[0]}</b><br>" +
				"%{customdata[1]}<br><br>" +
				"<b>Mobile Share (index vs site avg): %{customdata[2]:.2f}<b><br>" +
				"<extra></extra>",
			),
		)

		fig3.update_layout(
			title_text=f'Mobile Share Index by Show',
			uniformtext_minsize=10,
			uniformtext_mode='hide',
			template='plotly_white',
			width=w,
			height=h * 2,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			)
		)
		#fig3.update_xaxes(showticklabels=False)
		fig3.update_yaxes(showticklabels=False)

		chart = dbc.Card([
			dbc.Stack([
				dbc.Stack([
					dcc.Graph(
						figure=fig3,
						animate=False,
					),
				],direction='horizontal',gap=3,className='d-flex align-items-center justify-content-center'),
				dbc.Stack([
					dcc.Graph(
						figure=fig,
						animate=False,
					),
					dbc.Stack([
						html.Span('Source: internal data'),
						html.Span('How to Read These Charts',className='ms-auto'),
						html.I(id='info-icon-devices',className='bi bi-info-circle-fill',style={'font-size':'2rem','color':self.styles['color_sequence'][1]}),
					],direction='horizontal',gap=3,className='d-flex align-items-center flex-row justify-items-between'),
					dbc.Popover(
						[
							dbc.PopoverHeader('How to Read These Charts'),
							dbc.PopoverBody([
								dbc.Stack([
									dbc.Stack([
										html.Span([
											'The bar chart on the left displays the share of mobile traffic indexed relative to site average (0 index). ',
											html.Span('Positive values represent how much more likely it is for mobile users to interact with this content than the average show; ',style={'font-weight':'bold'}),
											'negative values mean users are more likely to interact with the content via desktop devices',
										]),
										html.Span([
											'A value of 0 would mean a show has exactly the same share of mobile users as the site average,'
											'while values of -.2 or 1.5 would mean a 20% smaller share or 150% larger share (respectively) of mobile users than average',
										]),
										html.Span('The minimum possible negative value is -1 (representing -100%, i.e., no mobile traffic), whereas positive values are can be infinite (representing +∞, i.e, exclusively mobile traffic) '),
										html.Span('The color of each bar represents the category of video.',),
										dbc.Stack(self.styles['category_color_legend'],gap=0),
									],gap=3),
									#html.Div([],style={'height':'100%', 'border-left': '2px solid black'}),
									html.Hr([],className='vt-rule'),
									dbc.Stack([
										dbc.Stack([
											html.Span("The donut chart on the top right displays the overall breakdown between desktop & mobile traffic, averaged across all days and content"),
											html.Span("We should generally not expect to see sudden changes in these shares over time, but it can be interesting to apply global filters to examine how this breakdown varies by content, category, or date."),
										],gap=3),
										html.Hr([],className='hz-rule'),
										dbc.Stack([
											html.Span("The bar chart on the bottom right compares video engagement (avg plays per user) for desktop vs mobile traffic, averaged across all days and content"),
										],gap=3),
									],gap=3),
								],direction='horizontal',gap=3,style={'max-height':'100%','min-height':'750px','height':'750px'}),
							]),
						],
						placement='top',
						target='info-icon-devices',
						trigger='hover',
						className='help-icon'
					),
					dcc.Graph(
						figure=fig2,
						animate=False,
					),
				],gap=3,className='d-flex align-items-center justify-content-center'),
			],direction='horizontal',gap=3)
		],className='viz-background-card')
		return chart

	def render_category_share(self, configs=None):
		logger.info('rendering video category share chart')
		df = self.data['traffic_daily']
		
		if configs == None:
			configs = self.default_configs
		item_limit = 50
		for k,v in configs.items():
			if v != None and v != []:
				if k == 'num_chart_items':
					item_limit = v
					pass
				else:
					try:
						df = df[df[k].isin(v)]
						
					except ValueError as e:
						df = df[df[k] == v]
						pass
		
		marker_colors = self.styles['color_sequence']
		w = 750
		h = 750
		fig = go.Figure()
		_df = df.groupby(['video_category','video_title'],as_index=False).agg({'video_plays':'sum'})
		_df_cat = df.groupby(['video_category'],as_index=False).agg({'video_plays':'sum'})
		ids = []
		labels = []
		parents = []
		values = []
		share = []
		c1 = []
		c2 = []
		colors = []
		for i in range(len(_df_cat)):
			ids.append(_df_cat['video_category'].iloc[i])
			labels.append(_df_cat['video_category'].iloc[i])
			parents.append('')
			values.append(_df_cat['video_plays'].iloc[i])
			s = _df_cat['video_plays'].iloc[i] / _df_cat['video_plays'].sum()
			fs = (_df_cat['video_plays'].sum() / len(_df_cat['video_category'].unique()) ) / _df_cat['video_plays'].sum()
			share.append(s)
			c1.append(s / fs)
		for i in range(len(_df)):
			ids.append(f'{_df['video_category'].iloc[i]}|{_df['video_title'].iloc[i]}')
			labels.append(_df['video_title'].iloc[i])
			parents.append(_df['video_category'].iloc[i])
			values.append(_df['video_plays'].iloc[i])
			s = _df['video_plays'].iloc[i] / _df['video_plays'].sum()
			fs = (_df['video_plays'].sum() / len(_df['video_title'].unique()) ) / _df['video_plays'].sum()
			share.append(s)
			c2.append(s / fs)
		for cs in [c1,c2]:
			max_score = max(cs)
			cs = [x / max_score for x in cs]
			colors.extend(cs)
		avg_share = sum(colors) / len(colors)
		fig.add_trace(
			go.Sunburst(
				name='Video Plays by Category & Show',
				labels=labels,
				parents=parents,
				values=values,
				branchvalues='total',
				marker = dict(
					colors=colors,
					#colorscale='Tropic',
					colorscale=[(0, marker_colors[0]), (1, marker_colors[3])],
					# cmid=.5,
					colorbar=dict(
						title=dict(text='Performance Index', side='bottom'),
						orientation='h',
						tickmode='array',
						tickvals=[.2,1],
						ticktext=['Underperforming','Overperforming'],
						x=.5,
						yanchor='middle',
						y=-.1,
						#ticks='outside',
					),
				),
				customdata=np.stack( (parents,labels,values,share,colors), axis=-1),
				hovertemplate=
				"<b>%{customdata[0]}</b><br>" +
				"%{customdata[1]}<br><br>" +
				"<b>Total Plays: %{customdata[2]:,.0f}<b><br>" +
				"<b>% of Total:  %{customdata[3]:.1%}</b><br>" +
				"<b>Performance Index:  %{customdata[4]:.2f}</b><br>" +
				"<extra></extra>",
			),
		)

		fig.update_layout(
			title_text=f'Video Plays by Category & Show',
			# uniformtext_minsize=8,
			# uniformtext_mode='show',
			template='plotly_white',
			width=w,
			height=h,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			)
		)


		engagement_fig = go.Figure()
		_df = df.groupby(['date','video_category','video_title'],as_index=False).agg({'users':'sum','video_plays':'sum'})
		_df = _df.sort_values(by='video_plays',ascending=False)
		_df['plays_per_user'] = _df.apply(lambda x: (x['video_plays'] / x['users']) if (x['video_plays'] > 0) and (x['users'] > 0) else 0 , axis=1)
		_df = _df.groupby(['video_category','video_title'],as_index=False).agg({'plays_per_user':'mean'})
		_df = _df.sort_values(by='plays_per_user',ascending=True).head(item_limit)
		engagement_colors = []
		for i in range(len(_df)):
			engagement_colors.append(self.styles['category_color_map'].get(_df['video_category'].iloc[i])) 
		engagement_fig.add_trace(
			go.Bar(
				name='Engagement By Show',
				y=_df['video_title'],
				x=_df['plays_per_user'],
				orientation='h',
				marker_color=engagement_colors,
				customdata=np.stack( (_df['video_category'],_df['video_title'],_df['plays_per_user']), axis=-1),
				hovertemplate=
				"<b>%{customdata[0]}</b><br>" +
				"%{customdata[1]}<br><br>" +
				"<b>Avg. Daily Plays per User: %{customdata[2]:,.2f}<b><br>" +
				"<extra></extra>",
			),
		)
		engagement_fig.add_trace(
			go.Scatter(
				mode='lines',
				name='Site Avg',
				y=_df['video_title'],
				x= [_df['plays_per_user'].mean() for x in _df['video_title']],
				orientation='h',
				text=[f'{_df['plays_per_user'].mean()}'],
				hovertemplate=
				"<b>Site Avg: %{x:,.2f}</b><br>" +
				"<extra></extra>",
				textfont=dict(
					weight='bold',
					size=12,
				),
				line=dict(color='darkgray', width=4,dash='dash'),
			),
		)

		engagement_fig.update_layout(
			title_text=f'Engagement By Show',
			template='plotly_white',
			width=w *.65,
			height=h *.9,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			),
			legend={
				'x': 0.5,
				'y': 0.9,
				'xref': 'container',
				'yref': 'container',
			},
			showlegend=False,
		)


		# color_legend_vals = []
		# for cat,color in self.styles['category_color_map'].items():
		# 	color_legend_vals.append(
		# 		dbc.Stack([
		# 			html.Div([],style={'height':'25px','width':'25px','background-color':color}),
		# 			html.Span(cat,style={'font-weight':'bold'}),
		# 		],direction='horizontal',gap=3,className='d-flex align-items-center justify-content-start')
		# 	)

		chart = dbc.Card([
			dbc.Stack([
				dcc.Graph(
					figure=fig,
					animate=False,
				),
				dbc.Stack([
					dcc.Graph(
						figure=engagement_fig,
						animate=False,
					),
					dbc.Stack([
						html.Span('Source: internal data'),
						html.Span('How to Read These Charts',className='ms-auto'),
						html.I(id='info-icon',className='bi bi-info-circle-fill',style={'font-size':'2rem','color':self.styles['color_sequence'][1]}),
					],direction='horizontal',gap=3,className='d-flex align-items-center flex-row justify-items-between'),
					dbc.Popover(
						[
							dbc.PopoverHeader('How to Read These Charts'),
							dbc.PopoverBody([
								dbc.Stack([
									dbc.Stack([
										html.Span([
											'The chart on the left is a ',
											html.A('sunburst',href='https://www.quanthub.com/what-is-a-sunburst-chart/',target='_blank',style={'font-weight':'bold'}),
											' chart, which is a much more fun alternative to pie charts for displaying hierarchical data.',
										]),
										html.Span("It displays both the share of total like a pie or donut chart as well as the parent/child relationships of different objects in the hierarchy and their relative contribtuion to the whole."),
										html.Span('This one is color-coded by how each show indexes for share of total video plays vs site average. Shows and categories in blue are doing well; ones in red are underperforming.'),
										html.Span('Areas where colors contrast sharply often indicate potential problems or opportunities.'),
									],gap=3),
									#html.Div([],style={'height':'100%', 'border-left': '2px solid black'}),
									html.Hr([],className='vt-rule'),
									dbc.Stack([
										html.Span("The chart on the right displays average daily video plays per user for each show, with bar color representing the video category."),
										dbc.Stack(self.styles['category_color_legend'],gap=0),
										html.Span("The higher the number, the more engaged users are with the content.  High engagement is correlated with higher margins for monetization and long-term staying power of the content."),
									],gap=3),
								],direction='horizontal',gap=3),
							]),
						],
						placement='top',
						target='info-icon',
						trigger='hover',
						className='help-icon'
					),
				],gap=3,className='d-flex flex-column justify-content-between'),
			],direction='horizontal',gap=3),
		],className='viz-background-card')
		return chart

	def render_summary_charts(self, configs=None, w=1000, h=400, chart_only=False, colors=[]):
		logger.info('rendering summary charts')
		if colors == []:
			colors = self.styles['color_sequence']
		df = self.data['traffic_daily']
		
		if configs == None:
			configs = self.default_configs
		item_limit = 50
		for k,v in configs.items():
			if v != None and v != []:
				if k == 'num_chart_items':
					item_limit = v
					pass
				else:
					try:
						df = df[df[k].isin(v)]
						
					except ValueError as e:
						df = df[df[k] == v]
						pass
		
		#marker_colors = self.styles['color_sequence']

		line_chart_fig = go.Figure()
		_df = df.groupby(['date'],as_index=False).agg({'users':'sum','video_plays':'sum'})
		_df['users'] = _df['users'].apply(lambda x: math.floor(x * .7) )# Simulate user deduplication across shows
		_df['plays_per_user'] = _df['video_plays'] / _df['users']
		_df['date'] = pd.to_datetime(_df['date'])
		_df['display_date'] = _df['date'].apply(lambda x: x.strftime('%b %d %Y'))
		_df_offset = _df[['date','users','video_plays']]
		#_df_offset['date'] = pd.to_datetime(_df_offset['date']).dt.date
		_df_offset['date'] = (_df_offset['date'] + pd.DateOffset(days=7))
		_df_offset = _df_offset.rename(columns={'users': 'users_prior_week', 'video_plays': 'video_plays_prior_week'})
		_df_offset['users_prior_year'] = _df_offset['users_prior_week'] *1.2 # Simulate some y/y data for comparison
		_df = _df.merge(_df_offset, how='left', on='date',suffixes=(None,'_y'))

		line_chart_fig.add_trace(
			go.Bar(
				name='Video Plays',
				x=_df['date'],
				y=_df['video_plays'],
				#width=[2.0 for x in _df['date']],
				offset=-1,
				#marker_color=marker_colors[1],
				marker_color=colors[0],
				#customdata=np.stack( ([x.strftime('%b %d %Y') for x in _df['date']],_df['users'],_df['plays_per_user']), axis=0),
				customdata=_df[['display_date','users','video_plays','plays_per_user']],
				hovertemplate=
				"<b>%{customdata[0]:'%b %d %Y'}</b><br><br>" +
				"Users: %{customdata[1]:,.0f}<br><br>" +
				"Plays: %{customdata[2]:,.0f}<br><br>" +
				"Avg. Daily Plays per User: %{customdata[3]:,.2f}<br>" +
				"<extra></extra>",
			),
		),
		line_chart_fig.add_trace(
			go.Bar(
				name='Users',
				x=_df['date'],
				y=_df['users'],
				#width=[2.0 for x in _df['date']],
				#marker_color=marker_colors[3],
				marker_color=colors[1],
				#customdata=np.stack( ([x.strftime('%b %d %Y') for x in _df['date']],_df['users'],_df['plays_per_user']), axis=0),
				customdata=_df[['display_date','users','video_plays','plays_per_user']],
				hovertemplate=
				"<b>%{customdata[0]:'%b %d %Y'}</b><br><br>" +
				"Users: %{customdata[1]:,.0f}<br><br>" +
				"Plays: %{customdata[2]:,.0f}<br><br>" +
				"Avg. Daily Plays per User: %{customdata[3]:,.2f}<br>" +
				"<extra></extra>",
			),
		),
		line_chart_fig.add_trace(
			go.Scatter(
				mode='lines',
				x=_df['date'],
				y=_df['users_prior_week'],
				name='Users Prior Week',
				offsetgroup=0,
				textfont=dict(
					weight='bold',
					size=12,
				),
				line=dict(
					#color=marker_colors[2],
					color=colors[2],
					width=4,
					# dash='dash'
				),
			)
		)

		line_chart_fig.add_trace(
			go.Scatter(
				mode='lines',
				x=_df['date'],
				y=_df['users_prior_year'],
				name='Users Prior Year',
				offsetgroup=0,
				textfont=dict(
					weight='bold',
					size=12,
				),
				line=dict(
					#color=marker_colors[0],
					color=colors[3],
					width=4,
					# dash='dash'
				),
			)
		)

		line_chart_fig.update_layout(
			title_text=f'Topline Traffic by Date',
			template='plotly_white',
			width=w,
			height=h,
			barmode='group',
			bargap=0.1,
			bargroupgap=0.1,
			hoverlabel=dict(
				bgcolor='#ecf0f1',
				font_size=16,
				font_family='Ubuntu'
			)
		)

		_df = df.groupby('date').agg({'users':'sum','video_plays':'sum'})
		v1 = _df['users'].mean()
		v2 = _df['video_plays'].mean()
		kpi_data = [
			{'name':'Avg. Daily Users', 'value': v1},
			{'name':'Avg. Daily Plays', 'value': v2},
			{'name':'Avg. Plays per User', 'value': v2 / v1},
		]
		kpis = []
		for kpi in kpi_data:
			kpis.append(self.create_kpi_box(kpi['value'],kpi['name'],'Daily average across time period'))
		kpi_row = dbc.Stack(kpis,direction='horizontal',className='d-flex align-items-center justify-content-between kpi-row')
		chart = dbc.Card([
			dbc.Stack([
				kpi_row,
				dbc.Stack([
					html.Span('Source: internal data'),
					html.Span('How to Read These Charts',className='ms-auto'),
					html.I(id='info-icon-summary',className='bi bi-info-circle-fill',style={'font-size':'2rem','color':self.styles['color_sequence'][1]}),
				],direction='horizontal',gap=3,className='d-flex align-items-center flex-row justify-items-between'),
				dbc.Popover(
					[
						dbc.PopoverHeader('How to Read These Charts'),
						dbc.PopoverBody([
							dbc.Stack([
								dbc.Stack([
									html.Img(src='assets/images/kpi_box_example.png',style={'width':'100px','height':'100px'}),
									dbc.Stack([
										html.Span('The KPI charts in the top row represent the daily mean of each metric over the past 7 days, across all content.'),
										html.Span([
											'The ',
											html.Span('WoW',style={'font-weight':'bold'}),
											' metric compares the average for the most recent 7 days vs the 7 days prior.',
										]),
										html.Span([
											'The ',
											html.Span('YoY',style={'font-weight':'bold'}),
											' metric compares the average for the most recent 7 days vs the same days of the week 52 weeks prior.',
										]),
									],gap=3),
								],direction='horizontal',gap=3),
								#html.Div([],style={'height':'100%', 'border-left': '2px solid black'}),
								html.Hr([],className='hz-rule'),
								dbc.Stack([
									html.Span('The chart below displays bars representing users and video plays across all content by day. The line traces represent prior week & prior year user benchmarks for comparison.'),
									html.Span('When traffic is stable we should typically expect to see alignment between highs and lows across each series; sudden shifts in this pattern indicate potential problems or opportunities'),
								],gap=3),
							],gap=3),
						]),
					],
					placement='top',
					target='info-icon-summary',
					trigger='hover',
					className='help-icon'
				),
				dcc.Graph(
					figure=line_chart_fig,
					animate=False,
				),
			],gap=3),
		],className='viz-background-card')

		if chart_only == True:
			return dcc.Graph(
					figure=line_chart_fig,
					animate=False,
					id='ai-colors-chart-object'
				)
		else:
			return chart

	def auto_num_format(self,raw_number):
		num = float(f'{raw_number:.3g}')
		magnitude = 0
		while abs(num) >= 1000:
			magnitude += 1
			num /= 1000.0
		return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), 
					 ['', 'K', 'M', 'B', 'T'][magnitude])
		n = f'{num:f}'.rstrip('0').rstrip('.')
		m = ['', 'K', 'M', 'B', 'T'][magnitude]
		return f'{n}{m}'

	def create_kpi_box(self,value,header_text=None,vs1=None,vs2=None):
		comp_vals = [.01,-.03]
		comp_colors = [self.styles['comp_colors'][0] if x >= 0 else self.styles['comp_colors'][1] for x in comp_vals]
		comps = [
			dbc.Stack([
				html.Span('WoW',className='percent-comp-text'),
				html.Span(f'{comp_vals[0]:+.0%}',className='percent-comp-val d-flex align-items-center justify-content-center',style={'color':comp_colors[0]} ),
			],className='percent-comp d-flex align-items-center'),
			dbc.Stack([
				html.Span('YoY',className='percent-comp-text'),
				html.Span(f'{comp_vals[1]:+.0%}',className='percent-comp-val d-flex align-items-center justify-content-center',style={'color':comp_colors[1]} ),
			],className='percent-comp d-flex align-items-center'),
		]
		box = dbc.Card([
			dbc.CardHeader(header_text,className='kpi-box-header'),
			dbc.CardBody([
				dbc.Stack([
					html.Span(f'{self.auto_num_format(value)}',className='kpi-box-value'),
				],direction='horizontal',gap=3),
			],className='kpi-box-body d-flex align-items-center justify-content-center'),
			dbc.CardFooter([
				dbc.Stack(comps,direction='horizontal',className='d-flex justify-content-center'),
			],className='kpi-box-footer')
		])

		return box

def create_app_layout(ui):

	layout = dbc.Container([
		dbc.Row([
			dbc.Col([
				ui.layout['header'],
				html.Br(),
				ui.layout['filters'],
				html.Br(),
				ui.layout['tabs_container']
			]),
		]),
		ui.layout['loading_modal'],
		dcc.Store(id='store-configs'),
		dcc.Interval(id='interval-10-sec',interval=10*1000,n_intervals=0),
	],fluid=True,className='global-container')

	return layout
