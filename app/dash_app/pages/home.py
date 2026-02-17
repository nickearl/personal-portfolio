import os
import logging
import pathlib
import random
from dotenv import load_dotenv, find_dotenv
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import date, datetime
from conf import GlobalUInterface
# from dash_app.query_tool import QueryTool

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class UInterface:
	def __init__(self):
		logger.info('Initializing Home')
		self.init_time = datetime.now()
		self.carousel_items = []
		self.conf = {
			'panel_width': '80vw',
			'panels': {},
			'articles': {
				'Variety': {
					'logo': 'variety_logo.png',
					'url': 'https://variety.com/lists/video-game-tv-series-ideas-study/',
					'text': 'What Video Games Should Streamers Adapt?',
					'images': ['variety_1.png','variety_2.png'],
				},
				'Ad Week': {
					'logo': 'adweek_logo.png',
					'url': 'https://www.adweek.com/convergent-tv/streamer-releases-weekly-binge/',
					'text': "Binge or Weekly? Here's the Best Way for Streamers to Release Shows",
					'images': ['adweek_1.png'],
				},
				'LA Times': {
					'logo': 'latimes_logo.png',
					'url': 'https://www.latimes.com/entertainment-arts/tv/newsletter/2024-08-09/the-boys-bridgerton-house-of-the-dragon-the-bear-weekly-binge-screen-gab',
					'text': "Weekly Episode Drops are Better Than Binge.  And There's Data to Back it Up.",
					'images': ['latimes_1.png','latimes_2.png'],
				},
				'TheWrap': {
					'logo': 'thewrap_logo.png',
					'url': 'https://www.thewrap.com/fandom-avatar-top-gun-oscars-fan-vote/',
					'text': 'What if Fans Voted for the Oscars?',
					'images': ['thewrap_1.png'],
				},
			}
		}
		self.global_ui = GlobalUInterface()
		
		# 1. Add Custom Panels (Virtual Interview)
		self.conf['panels']['virtual_interview'] = {
			'display_name': 'Demo: AI Agents',
			'summary_header': "Interactive Chat / Voice AI agents",
			'summary_text': """
				Explore different AI personas equipped with specialized knowledge sets, powered by ElevenLabs Conversational AI:

				1. **Nick's AI Clone**: Trained on my professional background.
				2. **Bedtime Monster**: A creative storyteller.
				3. **Maya**: A virtual dental assistant.
			""",
			'image': 'assets/images/ai_interview.png',
			'enabled': True,
		}

		# 2. Merge Global Pages
		for k,v in self.global_ui.pages.items():
			if v['enabled']:
				self.conf['panels'][k] = v

		# 3. Add Analyses Panel
		analyses_content = self.create_article_content()
		self.conf['panels']['analyses'] = {
			'display_name': 'Analyses',
			'summary_header': 'Select press coverage of analyses my teams and I have performed',
			'summary_text': None,
			'image': None,
			'enabled': True,
			'content_left': analyses_content[0],
			'content_right': analyses_content[1],
		}

		agent_configs = {
			'nick': {
				'name': "Nick's AI Clone: Virtual Interview",
				'id': "agent_7701kha7yzdzew5v1da6tmx3mw4s",
				'image': 'assets/images/pixel_nick_synthwave_cropped_lo_res.png',
				'description': "An AI digital twin trained on my professional history, leadership & technical skills, and project portfolio.",
				'technical_details': "Built using RAG (Retrieval Augmented Generation) on a structured career dataset.",
				'topics': [
					'Talk to me about "Undashboarding".',
					"What AI-powered tools have you delivered that drove real business impact?",
					"What is your philosophy on team building and leadership?",
					"Describe your background in data science and business insights."
				]
			},
			'monster': {
				'name': "Bedtime Monster: Creative Storyteller",
				'id': "agent_9301kh7mfbt9e0ksvxpw0cfwrwb8",
				'image': 'assets/images/bedtime_monster_scaled.png',
				'description': "A friendly, imaginative monster designed to tell bedtime stories.",
				'technical_details': "Configured with a high temperature for creativity and a whimsical system prompt. It demonstrates the versatility of LLMs to generate creative fiction on the fly.",
				'topics': [
					"Tell me a story about a dragon but not a scary dragon a nice dragon.",
					"Do monsters brush their teeth?",
					"Why do I have to go to sleep?",
					"Sing me a lullaby."
				]
			},
			'maya': {
				'name': "Maya: Dental Office Assistant",
				'id': "agent_4401kh7af5kee1b9e7k1am38csd2",
				'image': 'assets/images/maya_scaled.png',
				'description': "A demo agent developed for the American Association of AI in Dental, showcasing how AI agents can be customized for specific industry verticals and customer service tasks.",
				'technical_details': "Equipped with knowledge base developed by medical professionals for informational, non-diagnostic purposes. Strict guardrails against attempting diagnosis, restrict response lengths/types given medium (typically a phone call).",
				'topics': [
					"How often should I go to the dentist?",
					"What is a root canal?",
					"I need to schedule a cleaning.",
					"What kinds of insurance do you accept?"
				]
			}
		}

		def create_agent_tab(agent_key):
			config = agent_configs[agent_key]
			
			info_panel = dbc.Card([
				dbc.CardBody([
					html.H4(config['name'], className="card-title text-center", style={'color': '#2c3e50', 'font-weight': 'bold'}),
					html.Hr(),
					html.H6([html.I(className="bi bi-info-circle-fill me-2"), "What is this?"], className="text-primary", style={'font-weight': 'bold'}),
					html.P(config['description'], className="card-text"),
					html.Br(),
					html.H6([html.I(className="bi bi-cpu-fill me-2"), "Build Considerations"], className="text-primary", style={'font-weight': 'bold'}),
					html.P(config['technical_details'], className="card-text", style={'font-size': '0.9rem'}),
					html.Br(),
					html.H6([html.I(className="bi bi-chat-quote-fill me-2"), "Suggested Topics"], className="text-primary", style={'font-weight': 'bold'}),
					dbc.Stack([
						dbc.Badge(topic, color="white", text_color="primary", className="border border-primary p-2 shadow-sm", style={'font-weight': 'normal', 'font-size': '0.85rem', 'text-wrap':'wrap'}) 
						for topic in config['topics']
					], gap=2, style={'flex-wrap': 'wrap'})
				])
			], className="h-100 border-0 bg-light", style={'border-radius': '0'})

			widget_container = html.Div([
				html.Div(style={
					'position': 'absolute',
					'top': 0, 'left': 0, 'width': '100%', 'height': '100%',
					'background-image': f"url('{config['image']}')",
					'background-size': 'cover',
					'background-position': 'center',
					'background-repeat': 'no-repeat',
					'opacity': 0.25,
					'z-index': 0
				}),
				html.Iframe(
					srcDoc=f"""
						<style>
							body {{ 
								margin: 0; 
								overflow: hidden; 
								background-color: transparent;
								font-family: sans-serif;
								display: flex;
								flex-direction: column;
								align-items: center;
								justify-content: center;
								height: 100vh;
							}}
						</style>
						<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
						<elevenlabs-convai agent-id="{config['id']}"></elevenlabs-convai>
					""",
					style={'width': '100%', 'height': '600px', 'border': 'none', 'position': 'relative', 'z-index': 1},
					allow="microphone"
				)
			], style={'position': 'relative', 'height': '600px', 'background-color': '#f8f9fa'})

			return dbc.Row([
				dbc.Col(info_panel, width=12, lg=4, className="p-0"),
				dbc.Col(widget_container, width=12, lg=8, className="p-0")
			], className="g-0")

		self.layout = {
			'intro': dbc.Card([
				dbc.Stack([
					dcc.Markdown(self.global_ui.layout['intro_text'],className='intro-text px-2'),
					dbc.Stack([
						html.Img(src='assets/images/pixel_nick_synthwave_cropped_lo_res.png',className='intro-image'),
						html.A([html.I(className='bi bi-linkedin'),' linkedin.com/in/nickearl'],href='https://www.linkedin.com/in/nickearl/',target='_blank',className='intro-link'),
						html.A([html.I(className='bi bi-github'),' github.com/nickearl'],href='https://github.com/nickearl/',target='_blank',className='intro-link'),
						html.A([html.I(className='bi bi-at'),' nickearl.net'],href='https://www.nickearl.net',target='_blank',className='intro-link'),
					],gap=3, className='align-items-center justify-content-start'),
				],direction='horizontal', gap=3)
			],color='light',className='shadow-lg align-items-center justify-content-center',style={'flex':'1','border-radius':'1rem','border-width':'3px','max-width': self.conf['panel_width'],'width':'100%','padding':'1rem'}),
			'virtual_interview': dbc.Card([
				dbc.CardHeader([
					dbc.Stack([
						html.Span(self.conf['panels']['virtual_interview']['summary_header'],style={'font-weight':'bold','font-size':'1.2rem'}),
					],gap=3,className='align-items-center justify-content-start'),
				]),
				dbc.CardBody([
					dbc.Tabs([
						dbc.Tab(create_agent_tab("nick"), label=agent_configs['nick']['name'], labelClassName="modern-tab-label", activeLabelClassName="modern-tab-label-active"),
						dbc.Tab(create_agent_tab("monster"), label=agent_configs['monster']['name'], labelClassName="modern-tab-label", activeLabelClassName="modern-tab-label-active"),
						dbc.Tab(create_agent_tab("maya"), label=agent_configs['maya']['name'], labelClassName="modern-tab-label", activeLabelClassName="modern-tab-label-active"),
					])
				]),
			],style={'flex':'2','align-self':'stretch','border-top-right-radius':'1rem','border-bottom-right-radius':'1rem'}),
			'image_modal': dbc.Modal(
				[
					dbc.ModalHeader(dbc.ModalTitle("Image Preview"), close_button=True),
					dbc.ModalBody(html.Img(id='home-modal-image', style={'width': '100%', 'height': 'auto'})),
				],
				id="home-image-modal",
				size="xl",
				centered=True,
				is_open=False,
			),
		}
		
		logo_imgs = []
		logo_dir = pathlib.Path(__file__).parent.parent / 'assets' / 'images' / 'company_logos'
		if logo_dir.exists():
			files = [f for f in logo_dir.iterdir() if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.svg']]
			random.shuffle(files)
			for f in files:
				logo_imgs.append(
					html.Img(src=f'assets/images/company_logos/{f.name}', className='employer-logo', title=f.stem.replace('_', ' ').title())
				)

		self.layout['logos'] = dbc.Stack(logo_imgs, direction='horizontal', gap=4, className='justify-content-center align-items-center my-4')
		
		self.conf['panels']['virtual_interview']['content_right'] = self.layout['virtual_interview']

		toc_links = []
		for k,v in self.conf['panels'].items():
			if v.get('enabled', True) and k != 'home':
				p = self.create_home_content_panel(v)
				toc_links.append(p)
		self.layout['toc'] = dbc.Stack(toc_links,gap=5,className='align-items-center justify-content-center')
	
	def create_article_content(self):
		alist_buttons = []
		carousel_images = []
		summary_header = 'Select press coverage of analyses my teams and I have performed'
		a_count = 0
		i_count = 0
		for k,v in self.conf['articles'].items():
			o = dbc.NavItem([
				dbc.Button([
					dbc.Stack([
						dbc.Stack([
							html.Img(src=f'assets/images/{v['logo']}', className='a-list-logo')
						],className='d-flex align-items-start justify-content-center w-100 ps-2',style={'min-width':'100px'}),
						dbc.Stack([
							html.A(v['text'],href=v['url'],target='_blank',className='carousel-link'),
						],className='bg-light d-flex align-items-center justify-content-center w-100',style={'border-top-right-radius':'.5rem','border-bottom-right-radius':'.5rem'}),
					],direction='horizontal',gap=1,className='d-flex justify-content-start align-items-center',style={'min-height':'6rem'}),
				],className='bg-dark a-list-button',id=f'a-list-button-{a_count}',style={'background':'none'})
			])
			alist_buttons.append(o)
			alist_buttons.append(html.Br())
			for image in v['images']:
				carousel_item = {
					'key': f'{i_count + 1}',
					'src': f'assets/images/slide_preview_{image}',
					'img_className': 'carousel-image',
					'img_style': {},
				}
				carousel_images.append(carousel_item)
				modal_item = carousel_item.copy()
				modal_item['modal_src'] = f'assets/images/{image}'
				self.carousel_items.append(modal_item)
				i_count = i_count + 1
			a_count = a_count + 1
			content_left = dbc.Stack([
				html.Span(summary_header,style={'font-size':'1.1rem'}),
				html.Hr(),
				dbc.Nav(
					alist_buttons,
					vertical=True,pills=True
				)
			],gap=3,className='bg-light align-items-center justify-content-center',style={'flex':'1','border-radius':'1rem','width':'100%','padding':'1rem'})
			content_right = dbc.Stack([
				html.Div(
					dbc.Carousel(
						items=carousel_images,
						controls=True,
						indicators=True,
						# ride='carousel',
						variant='dark',
						interval=5000,
						id='article-carousel',
						style={'border-radius':'1rem', 'height': '800px', 'overflow': 'hidden'}
					),
					id='home-carousel-wrapper',
					style={'cursor': 'pointer', 'height': '100%', 'width': '100%'}
				)
			],gap=3,className='align-items-center justify-content-center',style={'flex':'2','border-radius':'1rem','width':'100%'})
		return content_left, content_right
	
	def create_home_content_panel(self,config:dict)->dbc.Card:
		"""
			config:
			{
				'prefix':'dash',
				'image': 'assets/images/dashboard_screenshot.png',
				'display_name': 'Interactive Data Visualization',
				'summary_header': 'An interactive demo dashboard for a fictional new streaming service',
				'summary_text': ""
				'enabled': True,
				'content_left': [] # Optional list of dbc components to replace default left side content
				'content_right': [] # Optional list of dbc components to replace default right side content
			}
		"""
		
		content_left = config['content_left'] if 'content_left' in config.keys() and config['content_left'] != None else dbc.Stack([
			html.Img(src=config['image'],style={'width':'100%','border-radius':'1rem'}),
		],gap=3,className='align-items-center justify-content-center',style={'flex':'1','border-radius':'1rem'})
		
		content_right = config['content_right'] if 'content_right' in config.keys() else dbc.Stack([
			html.Span(config['summary_header'],style={'font-weight':'bold','font-size':'1.1rem'}) if config['summary_header'] else None,
			dcc.Markdown(config['summary_text'],style={'text-align':'left','font-size':'1rem'}) if config['summary_text'] else None,
		],gap=3,className='align-items-center justify-content-center',style={'flex':'2','border-radius':'1rem'})

		card = dbc.Card([
			dbc.CardHeader(config['display_name'],style={'font-size':'1.5rem','font-weight':'bold','border-top-left-radius':'1rem','border-top-right-radius':'1rem','width':'100%'}),
			dbc.CardBody([
				dbc.Stack([
					dbc.Button([
						dbc.Stack([
							content_left,
							content_right
						],direction='horizontal',gap=3,className='align-items-start justify-content-around'),
					],href=config['full_path'] if 'full_path' in config.keys() and config['full_path'] else None,className='shadow-lg bg-light',style={'color':'black','flex':'1','border': '0px black solid','border-radius':'1rem','width':'75vw'}),
				],gap=3,className='align-items-center justify-content-center')
			])
		],color='light',className='shadow-lg align-items-center justify-content-center',style={'flex':'1','border-radius':'1rem','border-width':'3px','max-width': self.conf['panel_width'],'width':'100%'})
		return card

def create_app_layout(ui):

	layout = dbc.Container([
		dbc.Row([
			dbc.Col([
				ui.layout['intro'],
				ui.layout['logos'],
				html.Br(),
				ui.layout['toc'],
				ui.layout['image_modal'],
			]),
		]),
	],fluid=True,className='d-flex flex-column align-items-center justify-content-center')

	return layout
