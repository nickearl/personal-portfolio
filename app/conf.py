import os
from datetime import date, datetime
import re
from typing import Callable, Any
import dash_bootstrap_components as dbc
import dash
from dash import html, dcc, get_asset_url
import flask
from flask.sessions import SessionMixin
import plotly.graph_objects as go
from dotenv import load_dotenv, find_dotenv
import uuid
import math
import pandas as pd
import numpy as np
load_dotenv(find_dotenv())

"""
	Everything here controls UI layout and cosmetic look and feel of the app
"""

SERVER_NAME = os.environ['SERVER_NAME'].lower()
DISPLAY_NAME = "Nick Earl Portfolio | Building AI & Data Solutions for Media Giants and High Growth Startups | Fractional Data & AI Leadership"
BASE_PATH = re.sub(r'[_\s]+', '-', SERVER_NAME)

class GlobalUInterface:
	def __init__(self):
		self.init_time = datetime.now()
		self.logo_paths = {
			'light': 'assets/images/cyberpunk_portfolio_transparent.webp',
			'dark': 'assets/images/cyberpunk_portfolio_transparent.webp',
		}
		self.colors = {
			'comp_colors': ['#54898D', '#9F4A86'],
			'brand': ['#2b2bcf'],
			'success': ['#18bc9c', '#14a085', '#13967d'],
			'background': ['#7b8a8b'],
			'sequence': [
				'#78CFDB',
				'#70BBCC',
				'#78C2DB',
				'#70AFCC',
				'#78B5DB',
				'#70A3CC',
				'#78A9DB',
				'#7097CC',
				'#789CDB',
				'#708BCC',
				'#788FDB',
				'#707FCC',
				'#7882DB',
				'#78DBBD',
				'#70CCB5',
				'#78DBC9',
				'#70CCC0',
				'#78DBD5',
				'#70CCCC',
				'#78D5DB'],
			'balanced_spectrum': [
				'#D85656',
				'#BF6E4C',
				'#D8A456',
				'#BFB34C',
				'#BED856',
				'#85BF4C',
				'#70D856',
				'#4CBF57',
				'#56D88A',
				'#4CBF9C',
				'#56D8D8',
				'#4C9CBF',
				'#568AD8',
				'#4C57BF',
				'#7056D8',
				'#854CBF',
				'#BE56D8',
				'#BF4CB3',
				'#D856A4',
				'#BF4C6E'],
			'blue_green_coast': [
				'#61D8CA',
				'#59C6BF',
				'#61D8D7',
				'#59C2C6',
				'#61CDD8',
				'#59B6C6',
				'#61C0D8',
				'#59AAC6',
				'#61B3D8',
				'#599EC6',
				'#61A6D8',
				'#5993C6',
				'#6199D8',
				'#5987C6',
				'#618CD8',
				'#597BC6',
				'#6180D8',
				'#596FC6',
				'#6173D8',
				'#5963C6'],
			'cool_night': [
				'#5B7BCC',
				'#5267B7',
				'#5B6BCC',
				'#5259B7',
				'#5B5CCC',
				'#5952B7',
				'#6A5BCC',
				'#6752B7',
				'#7A5BCC',
				'#7552B7',
				'#895BCC',
				'#8252B7',
				'#995BCC',
				'#9052B7',
				'#A85BCC',
				'#9E52B7',
				'#B85BCC',
				'#AC52B7',
				'#C75BCC',
				'#B752B4'],
			'desert_dusk': [
				'#CC7B61',
				'#BA7459',
				'#CC8361',
				'#BA7B59',
				'#CC8B61',
				'#BA8259',
				'#CC9261',
				'#BA8959',
				'#CC9A61',
				'#BA9059',
				'#CCA261',
				'#BA9759',
				'#CCAA61',
				'#AA61CC',
				'#A659BA',
				'#C361CC',
				'#BA59B6',
				'#CC61BB',
				'#BA599F',
				'#CC61A1'],
			'earth_and_clay': [
				'#C65959',
				'#B25850',
				'#C66B59',
				'#B26750',
				'#C67C59',
				'#B27750',
				'#C68E59',
				'#B28750',
				'#C6A059',
				'#B29850',
				'#C6B359',
				'#B2A950',
				'#C6C659',
				'#BEC659',
				'#A2B250',
				'#ABC659',
				'#91B250',
				'#98C659',
				'#80B250',
				'#85C659'],
			'forest_and_moss': [
				'#89C659',
				'#76B250',
				'#7FC659',
				'#6DB250',
				'#74C659',
				'#63B250',
				'#6AC659',
				'#5AB250',
				'#5FC659',
				'#51B250',
				'#59C65D',
				'#50B258',
				'#59C668',
				'#50B262',
				'#59C672',
				'#50B26B',
				'#59C67D',
				'#50B275',
				'#59C687',
				'#50B27E'
			],
			'jewel_tones': [
				'#B23535',
				'#9E502F',
				'#B28035',
				'#9E932F',
				'#99B235',
				'#669E2F',
				'#4EB235',
				'#2F9E3A',
				'#35B267',
				'#2F9E7C',
				'#35B2B2',
				'#2F7C9E',
				'#3567B2',
				'#2F3A9E',
				'#4E35B2',
				'#662F9E',
				'#9935B2',
				'#9E2F93',
				'#B23580',
				'#9E2F50'
			],
			'nord_breeze': [
				'#78CFDB',
				'#70BBCC',
				'#78C2DB',
				'#70AFCC',
				'#78B5DB',
				'#70A3CC',
				'#78A9DB',
				'#7097CC',
				'#789CDB',
				'#708BCC',
				'#788FDB',
				'#707FCC',
				'#7882DB',
				'#78DBBD',
				'#70CCB5',
				'#78DBC9',
				'#70CCC0',
				'#78DBD5',
				'#70CCCC',
				'#78D5DB'
			],
			'soft_pastels': [
				'#F29D9D',
				'#E0A991',
				'#F2D09D',
				'#E0D891',
				'#E1F29D',
				'#B9E091',
				'#AEF29D',
				'#91E099',
				'#9DF2BF',
				'#91E0C8',
				'#9DF2F2',
				'#91C8E0',
				'#9DBFF2',
				'#9199E0',
				'#AE9DF2',
				'#B991E0',
				'#E19DF2',
				'#E091D8',
				'#F29DD0',
				'#E091A9'
			],
			'stone_and_steel': [
				'#B28080',
				'#A38375',
				'#B29E80',
				'#A39E75',
				'#A8B280',
				'#8CA375',
				'#8AB280',
				'#75A37A',
				'#80B294',
				'#75A395',
				'#80B2B2',
				'#7595A3',
				'#8094B2',
				'#757AA3',
				'#8A80B2',
				'#8C75A3',
				'#A880B2',
				'#A3759E',
				'#B2809E',
				'#A37583'
			],
			'vibrant_but_tame': [
				'#DB4141',
				'#C6653B',
				'#DB9D41',
				'#C6B83B',
				'#BCDB41',
				'#81C63B',
				'#60DB41',
				'#3BC649',
				'#41DB7F',
				'#3BC69D',
				'#41DBDB',
				'#3B9DC6',
				'#417FDB',
				'#3B49C6',
				'#6041DB',
				'#813BC6',
				'#BC41DB',
				'#C63BB8',
				'#DB419D',
				'#C63B65'
			],
			'warm_sunset': [
				'#D84B8F',
				'#BF4275',
				'#D84B7B',
				'#BF4263',
				'#D84B66',
				'#BF4251',
				'#D84B52',
				'#BF4542',
				'#D8594B',
				'#BF5742',
				'#D86D4B',
				'#BF6942',
				'#D8814B',
				'#BF7B42',
				'#D8964B',
				'#BF8D42',
				'#D8AA4B',
				'#BF9F42',
				'#D8BE4B',
				'#BFB142'
			],
			'distinct_primary_20': [
				'#FF4D4D', '#FF7A1A', '#FFBD2A', '#D6E04A', '#6ED66A',
				'#18C49A', '#00B7C9', '#25A0FF', '#4E79FF', '#7A49FF',
				'#A23CFF', '#D43CFF', '#FF3CE0', '#FF3CA8', '#FF6BA8',
				'#FF6B6B', '#FF9A4D', '#FFD34D', '#A4E04D', '#4ED6B8'
			],
			'distinct_mid_20': [
				'#E65C5C', '#E6843A', '#E6C252', '#C6D56A', '#7BCF7B',
				'#4EC3A8', '#3AB9C9', '#4FA7F0', '#6C86F0', '#8A64F0',
				'#A656E6', '#C24FE6', '#E64FD2', '#E64F9F', '#E66F9F',
				'#E66F6F', '#E69B6C', '#E6CD6C', '#98D66C', '#6ACFBE'
			],
			'neon_noir_20': [
				'#FF2D95', '#FF6B00', '#FCEE0A', '#00FFD5', '#00A6FF',
				'#7A3CFF', '#FF00A0', '#00FF7A', '#FFA64D', '#5CFFEA',
				'#66A3FF', '#B366FF', '#FF66CC', '#FF6666', '#66FF66',
				'#FFD24D', '#4DFFFF', '#80A6FF', '#C680FF', '#FF80DC'
			],
			'solar_ice_20': [
				'#E4572E', '#17BEBB', '#F0A202', '#76B041', '#3C91E6',
				'#D7263D', '#14919B', '#F7B32B', '#58A65C', '#2E59BA',
				'#B62D65', '#2AA6A4', '#FAD25A', '#7AC47F', '#5A7BEF',
				'#8C2D9E', '#25C0BC', '#F5D97A', '#9BD19E', '#7FA1FF'
			],
			'colorblind_safe_20': [
				'#0072B2', '#E69F00', '#D55E00', '#009E73', '#CC79A7',
				'#56B4E9', '#F0E442', '#000000', '#999999', '#7F3C8D',
				'#11A579', '#3969AC', '#F2B701', '#E73F74', '#80BA5A',
				'#E68310', '#008695', '#CF1C90', '#F97B72', '#4B4B8F'
			],
			'pastel_distinct_20': [
				'#F6A6A6', '#F4C19A', '#F7E39A', '#D4E79A', '#AEE7B2',
				'#A7E4D9', '#A8D5F2', '#B8B0F6', '#D3A7F2', '#F2A7CF',
				'#F6B8B8', '#F2D0B0', '#F6E7B8', '#DDEBB8', '#BDEBCB',
				'#BDE7E7', '#BFD8F2', '#CABFF6', '#E0BFF2', '#F2BFD9'
			],
			'deep_tones_20': [
				'#B33A3A', '#B35F2E', '#B38A2E', '#7FA33A', '#329973',
				'#2F8696', '#2E64B3', '#5246B3', '#7A3AB3', '#B33A8C',
				'#A33A3A', '#A35A2E', '#A3842E', '#76963A', '#2E8E6A',
				'#2B7C8A', '#2A5AA3', '#4B3DA3', '#7033A3', '#A33A82'
			],
			'bright_ink_20': [
				'#FF3D57', '#FFA000', '#FFE600', '#70E000', '#00D4A6',
				'#00B3FF', '#3A6CFF', '#7A3CFF', '#C13CFF', '#FF3CE0',
				'#FF6F7D', '#FFB24D', '#FFF066', '#9CF066', '#66E7CC',
				'#66CCFF', '#7F98FF', '#A47FFF', '#D47FFF', '#FF99EA'
			],
			'earth_sea_20': [
				'#9E3D2E', '#B4622D', '#C28A3A', '#A8A243', '#6E9E4D',
				'#3E8F6A', '#2F8D8D', '#2B7CA6', '#2E60A8', '#394C9E',
				'#804C3C', '#9C6B3D', '#A88A52', '#919954', '#6E8F58',
				'#4E836C', '#497E85', '#4A6F93', '#4E5A94', '#5C4F8A'
			],
			'cool_warm_20': [
				'#2F80ED', '#56CCF2', '#6FCF97', '#27AE60', '#2D9CDB',
				'#9B51E0', '#BB6BD9', '#EB5757', '#F2994A', '#F2C94C',
				'#1C7AD9', '#46B7E6', '#5ACF8F', '#1F8C57', '#268ECC',
				'#8D45D1', '#A85CDF', '#D64E4E', '#E38C3D', '#E5BC3F'
			],
			'darkmode_distinct_20': [
				'#FF5C5C', '#FF8E3C', '#FFCE3C', '#A4E85C', '#5CE8B9',
				'#4AD6FF', '#6FA1FF', '#9B7BFF', '#D36EFF', '#FF6FE1',
				'#FF7373', '#FFA261', '#FFDA61', '#BBEE7A', '#7DE8CA',
				'#6EE0FF', '#8FB6FF', '#B099FF', '#DA95FF', '#FF98E7'
			],
			'muted_modern_20': [
				'#C94F4F', '#C37A4F', '#C4A54F', '#9FBD5E', '#69B08A',
				'#5AA3B8', '#5C82C4', '#7A6CC7', '#A265C1', '#C65F9E',
				'#B24F4F', '#AE704F', '#AF9A4F', '#8FAF5E', '#5FA681',
				'#5298AD', '#5376B2', '#6D61B6', '#945CAE', '#B85797'
			],
			'mono_plus_accents_20': [
				'#E0E0E0', '#C6C6C6', '#ADADAD', '#959595', '#7D7D7D',
				'#656565', '#4E4E4E', '#383838', '#222222', '#0F0F0F',
				'#FF5E5E', '#FFB35E', '#FFE45E', '#7BE45E', '#5EE4C3',
				'#5EC1FF', '#7E8AFF', '#B67EFF', '#FF7EE9', '#FF7EA6'
			]
		}
		self.permission_groups = {
			'EXECUTIVE': {'departments': ['Executive', 'Executive Suite']},
			'TECHNOLOGY': {'departments': ['Technology', 'Business Intelligence']},
			'BIZ_DEV': {'departments': ['Business Development']},
			'PEOPLE': {'departments': ['People', 'People Operations']},
			'FIELD_LEADERSHIP': {'departments': ['Field Sales', 'Field Sales Leadership']},
			'BPM': {'departments': ['Brand Partner Management']},
		}
		self.available_templates = ['ggplot2', 'seaborn', 'simple_white', 'plotly', 'plotly_white', 'plotly_dark', 'presentation', 'xgridoff', 'ygridoff', 'gridon', 'none']
		self.pages = {
			'home': {
				'prefix': 'home',
				'icon': 'bi-house-door-fill',
				'display_name': 'Home',
				'summary_header': 'Home Header',
				'summary_text': """
							- Explore the various tools and insights available in this app.

						""",
				'image': 'assets/images/pixel_nick_synthwave_cropped_lo_res.png',
				'enabled': True,
			},
			'dashboard': {
				'prefix': 'dash',
				'icon': 'bi-bar-chart-line-fill',
				'image': 'assets/images/dashboard_screenshot.png',
				'display_name': 'Interactive Data Visualization',
				'summary_header': 'An interactive demo dashboard for a fictional new streaming service',
				'summary_text': """
					- BI & data visualization best practices
					- Stakeholder guidance
					- Procedural dataset generation via python

						""",
				'enabled': True,
			},
			'sales_enablement': {
				'prefix': 'sales',
				'icon': 'bi-graph-up-arrow',
				'image': 'assets/images/sales_enablement.png',
				'display_name': 'Sales Enablement',
				'summary_header': 'AI-Powered Sales Tools',
				'summary_text': """
					- **Smart Slide Deck Generator**: Generate data-driven sales presentation outlines customized for specific prospects and audiences.
				""",
				'enabled': True,
			},
			'ai': {
				'prefix': 'ai',
				'icon': 'bi-stars',
				'image': 'assets/images/cyberbrain.png',
				'display_name': 'Design Lab',
				'summary_header': 'AI-Powered Design & Asset Generation',
				'summary_text': """
					- **Theme Generator**  
					Generate data-driven color palettes and dashboard themes from natural language descriptions.

					- **Asset Generator**  
					Create consistent, on-brand visual assets and imagery using style-tuned image generation models.

				""",
				'enabled': True,
			},
		}
		self._set_page_defaults()
		years_exp = self.init_time.year - 2008
		self.layout = {
			'intro_text': f"""
			> ### "I don't build dashboards.
			
			> ### I build the systems that make them obsolete."

			I'm **Nick Earl**. I architect 0-1 data platforms and AI tools that move beyond the hype to deliver measurable impact. I build the systems that generate proactive insights and automatically activate them to drive revenue and scale growth without manual intervention.

			With **{years_exp}+ years of hands-on leadership in data & tech**, I re-engineer the underlying workflows and business strategies required to move organizations from reactive reporting to proactive automation. By combining deep analytics experience with LLM implementation and robust ETL pipelines, I build the nervous system of a business so it can sense, decide, and act in real-time.

			#### **How I Help Businesses Run Themselves:**

			*   **Agentic AI Orchestration** Deploying no-hype, intelligent agents and models that handle complex decision-making processes with human-in-the-loop, at scale.
			*   **Strategy & Change Management:** Guiding teams and organizations through the process and culture shifts required to move from gut-feeling decisions to systems that automatically trigger action based on data insights.
			*   **Closed-Loop Automation:** Moving beyond traditional BI to build data applications that trigger automated workflows across Marketing, Sales, and Product.
			*   **Cross-Platform Orchestration:** Architecting seamless automation & data workflows that bridge the gap between siloed SaaS environments. I build integrated "connective tissue" across stacks like Salesforce, Slack, and Google Workspace to ensure data flows and triggers actions across the entire enterprise without manual handoffs.
			*   **Analytics Engineering:** Creating the high-integrity data foundations (Python, SQL, Databricks) required for automation to function safely and accurately.
			*   **Scalable Architecture:** Designing modern data stacks (CDP, CRM, Data Lakes) optimized for speed and automated activation.
			*   **Strategic Growth:** Partnering with executives to identify high-leverage opportunities for AI to replace manual bottlenecks and drive LTV.

			***
			
			**Domain Expertise:**
			Media & Entertainment | CPG | Streaming | Digital Marketing | A/B Testing & Optimization				
			""",
			'sidebar' : html.Div([
				html.Div([
					html.Img(src=self.logo_paths['light'], className='sidebar-logo'),
				], className='sidebar-header'),
				dbc.Nav(self._build_nav_links(),
					vertical=True,
					pills=True,
					className='sidebar-nav'
				),
			], className='sidebar shadow-sm'),
			'navbar': dbc.Navbar([
				dbc.Container([
					dbc.NavbarBrand(DISPLAY_NAME, className='me-auto fw-bold', style={'font-size': '1.25rem', 'color': '#2c3e50'}),
					html.Img(src=self.logo_paths['light'], height='32px'),
				], fluid=True)
			], color='white', sticky='top', className='border-bottom py-2', style={'z-index': '1020'}),
			'footer': dbc.Stack([
				html.Span(f'Nick Earl © {datetime.now().year}', className='footer-text'),
				html.A([html.I(className='bi bi-linkedin me-2'), 'linkedin.com/in/nickearl'],href='https://www.linkedin.com/in/nickearl/',className='footer-text'),
				html.A([html.I(className='bi bi-github me-2'), 'github.com/nickearl'],href='https://github.com/nickearl',className='footer-text'),
				html.A([html.I(className='bi bi-globe me-2'), 'nickearl.net'],href='https://www.nickearl.net',className='footer-text'),
			],direction='horizontal',gap=3, className='footer d-flex justify-content-center align-items-center'),
			'loading_modal': dbc.Modal([
			dbc.Card([
				dbc.CardHeader([
					dbc.Progress(id='loading-modal-bar',value=0, striped=True, animated=True, color='#86D7DC',style={'background-color':'#3A434B'}),
					html.H3(['Loading...'],id='loading-modal-text',style={'color':'white'}),
					dbc.ListGroup([],id='loading-modal-list'),
				]),
				dbc.CardBody([
					html.Img(src='assets/images/loading_loop.gif',style={'width':'100%','height':'auto'}),
					dbc.ListGroup([],id='loading-modal-average-duration'),
				]),
			],className='loading-card'),
			dcc.Store(id='loading-modal-data'),
			dcc.Interval(id='loading-modal-refresh-interval', interval=1 * 1000, n_intervals=0)
		],is_open=False,backdrop='static',keyboard=False,className='loading-modal',id='loading-modal'),
		}
		self.styles = {
			'card': {
				'border-radius':'.5rem',
				'display':'flex',
				'align-self': 'stretch',
				'box-shadow': '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.06)',
				'width':'100%',
			},
			'button': {
				'padding':'.5rem 1rem',
			},
			'dropdown': {
				'width':'100%',
				'min-width':'10rem',
			}
		}
		self.short_titles = {
			'field sales representative': 'Field Rep',
			'district manager': 'DM',
			'brand partner manager ': 'BPM',
			'Sales Director': 'SD',
		}

	def render_global_wrapper(self, flask_session: SessionMixin)-> dbc.Container:
		return dbc.Container([
			self.layout['sidebar'],
			html.Div([
				self.layout['navbar'],
				dash.page_container,
				self.layout['loading_modal'],
				self.layout['footer'],
				html.Div([],id='dev-null'),
			], className='content-wrapper'),
			dcc.Store(id='session-id-store', data=flask_session.get('session_id')),
			dcc.Store(id='download-results-store'),
			dcc.Download(id='download-results-downloader'),
		], fluid=True, className='p-0')

	def render_fail_card(self,
					  message:str | None = None,
					  image:str | None = None
					  ) -> dbc.Card:
		image = image or 'images/fail_cart.png'
		message = message or "Sorry, we couldn't find what you were looking for."
		return dbc.Card([
			dbc.Stack([
				html.H2(message),
				html.Img(src=get_asset_url(image), style={'height':'30vh','border-radius':'1rem'}),
			],className='align-items-center justify-content-center'),
		],style={'border-radius':'1rem','padding':'2rem','margin':'2rem'})

	def render_filter(self,
				   filter_type:str,
				   options: list | None = None,
				   label: Any | None = None,
				   value: Any | None = None,
				   placeholder: str | None = None,
				   id:str | None = None,
				   multi: bool = True,
				   outer_style: dict | None = None,
				   inner_style: dict | None = None,
				   ) -> dbc.Stack:
		
		outer_style = outer_style or {}
		inner_style = inner_style or {}

		if isinstance(label,str):
			label = html.Span(label, style={'font-weight':'bold'})
		content_map = {
			'dropdown': dcc.Dropdown(
				id=id,
				options=options or [],
				value=value,
				placeholder=placeholder,
				style={**self.styles['dropdown'], **inner_style},
				multi=multi,
			)
		}
		content = content_map.get(filter_type, html.Span('Unknown filter type'))

		filter_object = dbc.Stack([
			label,
			content,
		],gap=0,className='justify-content-center',style={**outer_style, 'width':'100%'})
		return filter_object

	def _build_nav_links(self):
		links = []
		for k, v in self.pages.items():
			if v['enabled']:
				links.append(
					dbc.NavLink(
						html.Span(v['display_name'], className="sidebar-text"),
					href=v['full_path'],
					active='exact',
					className='sidebar-link')
				)
		return links
	
	def _set_page_defaults(self):
		"""
			Set defaults, etc
		"""
		for page_name, page_config in self.pages.items():
			page_key = re.sub(r'[_\s]+', '-', page_name).lower()
			page_config['path'] = f'/{page_key}' if page_name.lower() != 'home' else '/'
			page_config['full_path'] = f'/{BASE_PATH}{page_config['path']}'
			page_config['image'] = page_config['image'] if 'image' in page_config.keys() and not page_config['image'] == '' else f'assets/images/{page_key}.webp'
			page_config['cache_path'] = f'{SERVER_NAME}:{page_config['prefix']}:cache'
			page_config['s3_path'] = page_config['s3_path'] if 's3_path' in page_config.keys() and not page_config['s3_path'] == '' else f'{BASE_PATH}/{page_key}/'
			page_config['cache_ttl'] = page_config['cache_ttl'] if 'cache_ttl' in page_config.keys() else 60*60*24*30  # 30 days

	@staticmethod
	def _stack_kpi_cards(cards: list[dbc.Card])-> dbc.Stack:
		""" Create stacks of up to 4 cards each, then stack those stacks vertically. """
		stacks = []
		for i in range(0, len(cards), 4):
			stacks.append(dbc.Stack(
				cards[i:i+4],
				direction='horizontal',
				gap=3,
				className='align-items-center justify-content-center',
				style={'flex':'1','flex-wrap':'wrap'}
			))
		return dbc.Stack(
			stacks,
			direction='vertical',
			gap=3,
			className='align-items-center justify-content-center',
			style={'flex':'1','flex-wrap':'wrap'}
		)

	def create_kpi_card(
					self,
					title: str,
					value: str,
					icon: str | None = None,
					description: str | None = None,
					comps: list[dict] | None = None,
					tips: list[dict] | None = None,
					format: str | None = None,
					button_id: str | None = None,
					card_size: str | None = None,
					higher_is_better: bool = True,
					hover_content: list | None = None,
					hover_header: str | None = None,
					type: str | None = None,
					)-> dbc.Card:
		"""
			Create a KPI card with optional comparison to previous value and goal value.

			Args:
				title (str): Title of the KPI.
				value (str): Current value of the KPI.
				icon (str, optional): Icon class for the KPI. Defaults to None.
				description (str, optional): Description hover text for the KPI. Defaults to None.
				comps (list, optional): List of additional comparison dicts. Each dict should have a 'label' key
					and either 'value' (to compare against KPI value to calculate percentage) or 'percent' (pre-calculated percentage value). Defaults to None.
				tips (list, optional): List of additional text dicts to show below the comps.
					Each dict should have a 'label' key and optional 'min' and 'max' values that determines which text items to show based on the KPI value. Defaults to None.
				format (str, optional): Format of the value. Options: 'number', 'percent', 'float', 'currency'. Defaults to 'number'.
				button_id (str, optional): If provided, the KPI box is a clickable button with this ID. Defaults to None.
				card_size (str, optional): Size of the card. Options: 'small', 'medium', 'large'. Defaults to medium.
				higher_is_better (bool, optional): If True, higher values are better. Affects color of comparison text. Defaults to True.
				hover_content (list, optional): List of Dash content objects to show in a popover on hover. Defaults to None.
				hover_header (str, optional): Header text for the hover popover. If excluded, no header is shown. Defaults to None.
				type (str, optional): 'kpi' or 'indicator'.

		"""
		pos_color = self.colors['comp_colors'][0] if higher_is_better else self.colors['comp_colors'][1]
		neg_color = self.colors['comp_colors'][1] if higher_is_better else self.colors['comp_colors'][0]
		tricolor_spread = [
			self.colors['cool_night'][0],  # good
			self.colors['cool_night'][5],  # okay
			self.colors['cool_night'][19], # bad
		]
		header_hover_id = str(uuid.uuid4())
		body_hover_id = str(uuid.uuid4())
		format = format or 'number'
		type = type or 'kpi'
		size_indices = [
			'small',
			'medium',
			'large',
		]
		size_index = size_indices.index(card_size) if card_size in size_indices else 1
		# core styling across everything
		base_style = {'flex':'1','display':'flex','align-self': 'stretch','box-shadow': '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.06)'}
		size_styles = {
			'title_size': (1, 1.5, 2),
			'primary_metric_size': (2, 2.5, 3),
			'secondary_metric_size': (1, 1.2, 2),
			'text_size': (.9, 1.1, 1.3),
			'icon_size': (2,3,4),
			'container_min_size': (8,15,20),
			'container_max_size': (10,20,30),
			'border_radius': (0.5, 1, 1.5),
			'padding_top': (0.5, 1, 1.5),
			'padding_bottom': (0.5, 1, 1.5),
			'padding_left': (0.1, .5, 1),
			'padding_right': (0.1, .5, 1),
		}
		selected_style = {k: f'{v[size_index]}rem' for k,v in size_styles.items()}	
		container_style = {**base_style, **{
			'min-width': selected_style['container_min_size'],
			'max-width': selected_style['container_max_size'],
			'border-radius': selected_style['border_radius'],
		}}
		# Ensure value is a number
		# handle pd.Na, nan, None, etc
		if value in [None, np.nan, pd.NaT] or (isinstance(value, float) and np.isnan(value)) or (isinstance(value, str) and value.lower() in ['nan','null','none','n/a','']):
			value = 0
		if isinstance(value, str):
			value = value.replace(',','').replace('$','').replace('%','')
			value = float(value) if '.' in value else int(value)
		# formats
		formats = {
			'number': lambda x: f'{int(x):,}',
			'percent': lambda x: f'{float(x):.1%}',
			'float': lambda x: f'{float(x):,.1f}',
			'currency': lambda x: f'${float(x):,.0f}',
		}
		display_value = formats[format](value) if format in formats else str(value)

		# Comp text
		comps = comps or []
		comp_obj = html.Div()
		kpi_comps = []
		for comp in comps:
			comp_percent = 0
			if 'percent' in comp.keys():
				comp_percent = float(comp['percent'])
			elif 'value' in comp.keys():
				try:
					comp_percent = float(value) / float(comp['value']) - 1
				except Exception as e:
					pass
			comp_color = pos_color if comp_percent >= 0 else neg_color
			comp_text = html.Span(f"{comp_percent:+.1%}", style={'color': comp_color,'font-weight':'bold','font-size': selected_style['secondary_metric_size']})
			label_object = dbc.Stack([comp['label']],direction='horizontal',gap=1, style={'font-size': selected_style['text_size']})
			kpi_comps.append( dbc.Stack([comp_text, label_object],direction='horizontal',gap=1,className='align-items-center justify-content-center',style={'text-align':'center','flex-wrap':'wrap'}) )
		if kpi_comps:
			comp_obj = dbc.Stack(kpi_comps,gap=1,className='align-items-center justify-content-center',style={'text-align':'center','flex-wrap':'wrap'})

		# Icon
		icon_obj = html.Div()
		if icon:
			icon_obj = html.I(className=f'{icon} me-2', style={'font-size': selected_style['icon_size'], 'flex':'1'})
		
		# Description popover
		description_obj = html.Div()
		if description:
			description_obj = dbc.Popover(
				[
					dbc.PopoverBody(description),
				],
				target=f'tooltip-target-{header_hover_id}',
				trigger="hover",
				placement='top',
			)

		# Tips text
		tips_style = {'font-size': selected_style['text_size'],'border':'2px solid lightgray', 'border-radius':'0.5rem','padding':'.5rem'}
		tips_obj = html.Div()
		if tips:
			tip_items = []
			for tip in tips:
				show_tip = True
				if 'min' in tip.keys() and tip['min'] is not None:
					if value < tip['min']:
						show_tip = False
				if 'max' in tip.keys():
					if value >= tip['max'] and tip['max'] is not None:
						show_tip = False
				if show_tip:
					tip_items.append(
						html.Span(
							tip['label'],
							style=tips_style,
						)
					)
			if tip_items:
				tips_obj = dbc.Stack(tip_items,gap=1,className='align-items-center justify-content-center',style={'text-align':'center','flex-wrap':'wrap'})


		# Hover popover
		hover_content_obj = html.Div()
		if hover_content:
			hover_content_obj = dbc.Popover([
				dbc.PopoverHeader(hover_header) if hover_header else html.Div(),
				dbc.PopoverBody(hover_content) if hover_content else html.Div(),
				]
				,
				target=f'tooltip-target-{body_hover_id}',
				trigger="hover",
			)
		
		# Visual
		visualization_object = 	html.Span(
			display_value,
			className='text-center',
			style={
				'font-size':selected_style['primary_metric_size'],
				'font-weight':'bold',
				}
			)
		if type == 'indicator':
			number_color = tricolor_spread[0] if value <= 0.25 else (tricolor_spread[1] if value <=0.5 else tricolor_spread[2])
			fig = go.Figure(go.Indicator(
				mode='gauge+number',
				value=value,
				number={
					'valueformat':'.2f',
					'font': {'color': number_color}
					},
				gauge=dict(
					shape='angular',                 # radial / semicircle
					axis=dict(
						range=[0, 1],
						tickvals=[0, 0.5, 1],
						ticktext=['0 🤩', '.5 🙂', '1 😡'],
						tickfont=dict(size=16),
					),
					bar=dict(color=self.colors['blue_green_coast'][0], thickness=0.6),   
					steps=[                          # HHI zones (normalized 0–1)
						{'range':[0.00, 0.25], 		'color':tricolor_spread[0]},   # Good
						{'range':[0.25, 0.5], 		'color':tricolor_spread[1]},   # Ok
						{'range':[0.5, 1.00], 		'color':tricolor_spread[2]},   # Bad
					],
					threshold=dict(                  # optional highlight at value
						value=value,
						line=dict(color=self.colors['blue_green_coast'][0], width=2),
						thickness=0.9
					)
				),
				domain={'x':[0,1],'y':[0,1]}
			))
			# fig.update_layout(margin=dict(l=45, r=45, t=40, b=10))
			fig.update_layout(
				margin=dict(l=45, r=45, t=0, b=0),
				height=180, 
			)


			# visualization_object = dcc.Graph(figure=fig, style={'width':'100%','height':'100%','min-height':'30vh'})
			visualization_object = dcc.Graph(figure=fig, style={'width':'100%','height':'100%'})


		card = dbc.Card([
			dbc.CardHeader(
				dbc.Stack([
					icon_obj,
					html.Span(title, style={'cursor':'pointer','flex':'5'}),
				],direction='horizontal',gap=0, className='align-items-center',),
			id=f'tooltip-target-{header_hover_id}',
			className='bg-dark text-white d-flex align-items-center',
			style={'flex':'1','font-size':selected_style['title_size'],'font-weight':'bold','border-top-left-radius': selected_style['border_radius'],'border-top-right-radius': selected_style['border_radius']}),
			dbc.CardBody([
				dbc.Stack([
					visualization_object,
					comp_obj,
					tips_obj,
					hover_content_obj,
				],gap=1, className='align-items-center justify-content-center',style={'flex':'1'}),
			],id=f'tooltip-target-{body_hover_id}', style={'flex':'2','align-self':'stretch','padding-top':selected_style['padding_top'],'padding-bottom':selected_style['padding_bottom'],'padding-left':selected_style['padding_left'],'padding-right':selected_style['padding_right'],'display':'flex','flex-direction':'column','justify-content':'center','align-items':'center'}),
			description_obj
		],style=container_style)
		container = dbc.Button(card, color='light', id=button_id,style=container_style) if button_id else dbc.Stack(card,style=container_style)
		return container
	
	@staticmethod
	def hex_to_rgb(
				hex_color: str,
				format:str|None=None,
				alpha:float|None=None,
				) -> tuple[int, int, int] | str | list[int]:
		"""Convert a hex color string like '#FFFFFF' or 'FFFFFF' to an (R, G, B) tuple.
		Args:
			hex_color (str): Hex color string.
			format (str, optional): Output format: 'tuple', 'string', 'list' or 'rgba'. Defaults to 'tuple'.
		Returns:
			tuple[int, int, int] | str | list[int]: RGB color in the specified format.
		"""
		alpha = alpha or 1.0
		hex_color = hex_color.lstrip('#')
		if len(hex_color) != 6:
			raise ValueError(f"Invalid hex color: {hex_color}")
		outputs = {
			'tuple' : tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)),
			'string' : ' '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4)),
			'list' : [int(hex_color[i:i+2], 16) for i in (0, 2, 4)],
			'rgba' : f'rgba({int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}, {alpha})',
		}
		format = format or 'tuple'
		return outputs[format]

	@staticmethod
	def scale_0_100(
			val:float,
			low:float,
			high:float,
			step:int|None = None)-> int:
		"""Scale a value to 0-100 given low and high bounds, with optional step binning."""
		step = step or 1
		low = pd.to_numeric(low, errors='coerce')
		high = pd.to_numeric(high, errors='coerce')
		val  = pd.to_numeric(val, errors='coerce')
		if low is None or high is None or not np.isfinite(low) or not np.isfinite(high) or high <= low:
			return 0
		# 2) Guard NaNs and degenerate ranges
		if pd.isna(low) or pd.isna(high) or pd.isna(val):
			return 0
		low, high, val = float(low), float(high), float(val)
		if not math.isfinite(low) or not math.isfinite(high) or high <= low:
			return 0
		if not np.isfinite(val):
			return 0
		p = (val - low) / (high - low) * 100.0
		p = max(0.0, min(100.0, p))           # clamp
		if step and step > 1:
			p = round(p / step) * step         # bin to step
		else:
			p = round(p)
		return int(p)