#!/usr/bin/env python
# coding: utf-8

import os, json, random, re, base64, io, uuid, time, socket, calendar, logging, hmac, hashlib
import pathlib
from dotenv import load_dotenv, find_dotenv
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, ALL, MATCH, Patch, callback
from dash.exceptions import PreventUpdate
import flask
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import date, datetime
from google import genai
from google.genai import types
from conf import GlobalUInterface
from dash_app.utils import load_secret
try:
	import google.auth
	from googleapiclient.discovery import build
	from googleapiclient.http import MediaIoBaseDownload
	from google.cloud import storage
except ImportError:
	build = None
	storage = None

# Get environment variables
load_dotenv(find_dotenv())
PAGE = 'sales_enablement'
TEXT_MODEL = 'gemini-3.8-flash'
IMAGE_MODEL = 'gemini-3.1-flash-image'
pd.set_option('future.no_silent_downcasting', True)

logger = logging.getLogger(__name__)

class UInterface:
	def __init__(self):
		self.global_ui = GlobalUInterface()
		# Note: 'sales_enablement' must be added to conf.py pages for this to work at runtime
		self.conf = self.global_ui.pages.get(PAGE, {'display_name': 'Sales Enablement', 'image': '', 'summary_header': ''})
		logger.info(f'Initializing {self.conf["display_name"]} UI')
		self.init_time = datetime.now()
		self.placeholders = {
			'company': random.choice(["Soylent Corp", "Initech", "Umbrella Corp", "Weyland-Yutani", "Cyberdyne Systems", "Stark Industries", "Wayne Enterprises"]),
			'industry': random.choice(["Technology", "Consumer Goods", "Automotive", "Healthcare", "Financial Services"]),
			'audience': random.choice(["C-Level Executives", "Marketing Team", "Product Managers", "Procurement Dept", "Investors"]),
			'style': random.choice(["Modern & Minimalist", "Bold & Energetic", "Corporate & Professional", "Tech & Futuristic", "Elegant & Luxury"]),
			'length': random.choice(["Short & Punchy", "Comprehensive", "10 minute pitch", "Just key stats", "Detailed analysis"]),
		}
		self.styles = {
			'color_sequence': ['#FD486D', '#9F4A86', '#F5D107', '#86D7DC', '#333D79', '#E5732D', '#4CAF8E', '#722B5C', '#FFC10A', '#005580'],
			'portrait_colors': ['#86D7DC', '#9B004E','#FA005A','#FFC500','#520044'],
			'comp_colors':['#54898d','#9F4A86'],
		}
		
		# Resolve paths relative to this file to support running from root or app/ dir
		self.base_dir = pathlib.Path(__file__).parent.parent.resolve()
		
		# Load data for RAG context
		df = pd.read_csv(self.base_dir / 'assets' / 'data' / 'traffic_daily.csv')
		self.stats = {
			'avg_daily_users': int(df.groupby('date')['users'].sum().mean()),
			'top_show': df.groupby('video_title')['video_plays'].sum().idxmax(),
			'total_plays': int(df['video_plays'].sum()),
			'growth_rate': '+12% MoM' # Hardcoded for demo, or calculate from df
		}
		self.data = {
			'traffic_daily': pd.read_csv(self.base_dir / 'assets' / 'data' / 'traffic_daily.csv'),
		}

		self.default_plaque = self._create_plaque(
			"Weyland-Yutani", "Heavy Industry", "Technical Team", "Cyberpunk", "Short and funny"
		)
		self.example_deck = html.Div([
			self.deck_grid([(None, self.slide_image(f'assets/images/weyland-yutani_{n}.jpeg')) for n in range(1, 6)]),
			self.default_plaque,
		])

		self.layout = {
			'header': dbc.Stack([
				dbc.Stack([
					# html.Img(src='assets/images/robot_and_human.png',style={'width':'150px','height':'150px'}),
					html.Img(src=self.conf['image'],style={'width':'150px','height':'150px'}),
					html.H3(self.conf['display_name']),
				],direction='horizontal',gap=3,className='justify-content-end',style={'width':'50%','max-width':'500px'}),
				dbc.Stack([
					html.Span(self.conf['summary_header'],style={'font-weight':'bold'}),
					html.Span("This tool uses the Google GenAI SDK to generate personalized sales collateral using real-time platform data."),
					html.Span('>More Info<',id='ai-more-info',style={'font-weight':'bold','color':self.styles['color_sequence'][1]}),
					dbc.Popover(
						[
							dbc.PopoverHeader(dcc.Markdown('**How it works**')),
							dbc.PopoverBody([
								dcc.Markdown("This page demonstrates **Retrieval Augmented Generation (RAG)** on a small scale. We inject actual aggregate statistics from the dashboard dataset (Daily Users, Top Shows) into the LLM prompt context, allowing Gemini to write factually accurate sales pitches."),
							]),
						],
						placement='bottom',
						target='ai-more-info',
						trigger='hover',
						style={'min-width':'50vw'},
					),

				],gap=1,className='justify-content-start',style={'width':'50%','max-width':'500px'}),
				
			],direction='horizontal',gap=3,className='header d-flex justify-content-center align-items-center'),
		}
		
		self.layout['onboarding_modal'] = dbc.Modal(
			[
				dbc.ModalHeader(dbc.ModalTitle("One-Click Sales Pitch Generator")),
				dbc.ModalBody([
					dcc.Markdown("""
						** Generative AI + Good Data = Value **

						Unlocking real value comes from effectively integrating Generative AI tools with **high-quality, optimized datasets**.
						This **One-Click Sales Pitch Generator** is simple enough to be embedded directly into existing workflows and tools (Salesforce record pages, dashboards, Notion, etc).

						**Try it out:**

						The example pitch deck on this page was prepared for **Weyland-Yutani** using this tool.
						
						1.  Describe the Prospect Company, Industry, Target Audience, Visual Style, and Length/Detail.
						2.  Click **Generate Deck**.
						
						Gemini plans a 3-5 slide deck from platform data, then renders every slide at once with Gemini 3.1 Flash Image. Slides appear as they finish.
					"""),
				]),
				dbc.ModalFooter(
					dbc.Button("Got it, let's pitch!", id="close-onboarding-modal", className="ms-auto", n_clicks=0, style={"padding":"0.5rem"})
				),
			],
			id="sales-onboarding-modal",
			is_open=True,
			size="lg",
			centered=True,
		)

		self.layout['pitch_generator'] = dbc.Container([
			dbc.Card([
				dbc.CardHeader([
					html.H4('Smart Slide Deck Generator')
				]),
				dbc.CardBody([
					dbc.Row([
						dbc.Col([
							dbc.Stack([
								html.Label("Prospect Company Name"),
								dbc.Input(id='sales-input-company', placeholder=f"e.g. {self.placeholders['company']}", type="text"),
								html.Label("Industry"),
								dbc.Input(id='sales-input-industry', placeholder=f"e.g. {self.placeholders['industry']}", type="text"),
								html.Label("Target Audience"),
								dbc.Input(id='sales-input-audience', placeholder=f"e.g. {self.placeholders['audience']}", type="text"),
								html.Label("Visual Style / Theme"),
								dbc.Input(id='sales-input-style', placeholder=f"e.g. {self.placeholders['style']}", type="text"),
								html.Label("Length / Detail"),
								dbc.Input(id='sales-input-length', placeholder=f"e.g. {self.placeholders['length']}", type="text"),
								html.Br(),
								dbc.Button([html.I(className='bi bi-easel'), " Generate Deck"], id='sales-pitch-submit', color='primary', className='w-100'),
							], gap=2),
						], width=4, style={'border-right': '1px solid #eee'}),
						dbc.Col([
							dcc.Loading(
								id='sales-pitch-loading',
								children=[
									html.Div(
										self.example_deck,
										id='sales-pitch-output',
										style={'padding': '2rem', 'background-color': '#f8f9fa', 'border-radius': '0.5rem', 'min-height': '400px'}
									),
								],
								# Only the planning step blocks the panel; slides then fill in one by one
								target_components={'sales-pitch-output': 'children'},
								custom_spinner=html.Div([
									html.Div(className="ai-spinner"),
									html.Div("Planning Pitch Deck...", className="loading-text"),
									html.Div("Gemini is drafting slides from platform data.", className="text-muted small")
								], className="d-flex flex-column align-items-center justify-content-center p-5 bg-white shadow rounded"),
								overlay_style={"visibility":"visible", "filter": "blur(4px)", "opacity": "0.8", "background-color": "white"},
							)
						], width=8),
					]),
				]),
			]),
		])

	def _create_plaque(self, company, industry, audience, style, length):
		return html.Div([
			html.H6("Generation Parameters", className="text-uppercase text-muted mb-3", style={'letter-spacing': '1px'}),
			dbc.Stack([
				html.Div([html.Small("Company", className="fw-bold text-secondary"), html.Div(company, className="fs-5 text-dark")]),
				html.Div([html.Small("Industry", className="fw-bold text-secondary"), html.Div(industry)]),
				html.Div([html.Small("Audience", className="fw-bold text-secondary"), html.Div(audience)]),
				html.Div([html.Small("Style", className="fw-bold text-secondary"), html.Div(style)]),
				html.Div([html.Small("Length", className="fw-bold text-secondary"), html.Div(length)]),
			], gap=3)
		], className="mt-4 p-4 rounded shadow-sm", style={'background-color': '#e9ecef', 'border-left': '5px solid #6c757d'})

	def _client(self):
		api_key = load_secret("GEMINI_API_KEY")
		if not api_key:
			logger.error("GEMINI_API_KEY is None or empty.")
			return None
		return genai.Client(api_key=api_key)

	def plan_deck(self, company, industry, audience, style, length):
		"""Ask the text model for 3-5 slide titles and image prompts. Returns {'slides': [...]} or {'error': message}."""
		logger.info(f'Planning sales deck for {company}')
		client = self._client()
		if client is None:
			return {'error': "Error: API Key missing."}

		prompt = f"""
		You are a senior sales executive for UHF+, a fast-growing Free Ad-Supported TV (FAST) streaming service.
		Plan a visual sales presentation for {company}, a company in the {industry} industry.

		Target Audience: \"\"\"{audience}\"\"\"
		Visual Style Description: \"\"\"{style}\"\"\"
		Desired Length/Depth: \"\"\"{length}\"\"\"

		Use the following internal platform data to back up your pitch:
		- Average Daily Active Users: {self.stats['avg_daily_users']:,}
		- Our #1 Hit Show: "{self.stats['top_show']}"
		- Total Video Plays (Last 30 Days): {self.stats['total_plays']:,}
		- User Growth: {self.stats['growth_rate']}
		
		Plan between 3 and 5 slides, choosing the count from the requested length/depth (5 if it is unclear).

		Format: Return a valid JSON object with the following structure:
		{{
			"slides": [
				{{
					"title": "Slide Title",
					"image_prompt": "A detailed prompt for an AI image generator to render this specific slide as a high-quality image. Describe the visual style ({style}), the background, and explicitly state the text that must appear on the slide (Title and 1-2 short bullet points). Ask for high contrast and legible text."
				}}
			]
		}}
		Ensure the JSON is valid. Do not include markdown formatting (like ```json) around the JSON.
		"""

		try:
			response = client.models.generate_content(
				model=TEXT_MODEL,
				contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
				config=types.GenerateContentConfig(response_mime_type="application/json"),
			)
			slides = [s for s in json.loads(response.text).get('slides', []) if s.get('image_prompt')][:5]
			if not slides:
				return {'error': "Sorry, Gemini didn't return a usable plan. Please try again."}
			return {'slides': slides}
		except Exception as e:
			logger.error(f"Error planning pitch: {e}")
			return {'error': "Sorry, I couldn't generate a pitch at this time. Please try again."}

	def generate_slide_image(self, image_prompt):
		"""Render one slide. Returns a data URI, or None on failure."""
		client = self._client()
		if client is None:
			return None
		try:
			response = client.models.generate_content(
				model=IMAGE_MODEL,
				contents=[types.Content(role="user", parts=[types.Part.from_text(text=image_prompt)])],
				config=types.GenerateContentConfig(
					image_config=types.ImageConfig(image_size="1K"),
					response_modalities=["IMAGE"],
				)
			)
			for part in response.parts or []:
				if part.inline_data and part.inline_data.data:
					b64_data = base64.b64encode(part.inline_data.data).decode('utf-8')
					return f"data:{part.inline_data.mime_type or 'image/png'};base64,{b64_data}"
		except Exception as e:
			logger.error(f"Error generating slide image: {e}")
		return None

	@staticmethod
	def _slide_signature(deck_id, index, image_prompt):
		message = f'{deck_id}|{index}|{image_prompt}'.encode()
		return hmac.new(flask.current_app.secret_key.encode(), message, hashlib.sha256).hexdigest()

	def verify_slide_job(self, job):
		"""Only render prompts this server planned, so the slide callback can't be used as a free image generator."""
		try:
			return hmac.compare_digest(self._slide_signature(job['deck'], job['index'], job['prompt']), job['sig'])
		except (KeyError, TypeError):
			return False

	def render_deck(self, plan, company, industry, audience, style, length):
		"""Deck with a placeholder per slide. Each placeholder's signed job triggers its own render callback, so slides render in parallel and appear as they finish."""
		deck_id = uuid.uuid4().hex[:12]
		slides = []
		for i, slide in enumerate(plan['slides']):
			job = {'deck': deck_id, 'index': i, 'prompt': slide['image_prompt']}
			job['sig'] = self._slide_signature(deck_id, i, slide['image_prompt'])
			slides.append((slide.get('title'), html.Div([
				html.Div(self.slide_placeholder(i), id={'type': 'sales-slide', 'deck': deck_id, 'index': i}),
				dcc.Store(id={'type': 'sales-slide-job', 'deck': deck_id, 'index': i}, data=job),
			])))
		return html.Div([self.deck_grid(slides), self._create_plaque(company, industry, audience, style, length)])

	def deck_grid(self, slides):
		"""First slide full width, the rest two per row. Each slide is a (title or None, body) pair."""
		cols = []
		for i, (title, body) in enumerate(slides):
			cols.append(dbc.Col([
				html.Div(title, className='small fw-bold text-secondary mb-1') if title else None,
				body,
			], xs=12, md=12 if i == 0 else 6, className='mb-3'))
		return dbc.Row(cols)

	def slide_image(self, src):
		return html.Img(src=src, style={'width': '100%', 'aspect-ratio': '16 / 9', 'object-fit': 'contain', 'border-radius': '0.5rem', 'background-color': 'white'})

	def slide_placeholder(self, index):
		return self._slide_box([dbc.Spinner(size='sm', color='secondary'), html.Span(f'Rendering slide {index + 1}...', className='text-muted small')])

	def slide_message(self, text):
		return self._slide_box([html.I(className='bi bi-exclamation-triangle text-warning'), html.Span(text, className='text-muted small')])

	def _slide_box(self, children):
		return html.Div(children, className='d-flex align-items-center justify-content-center gap-2 p-3 text-center',
			style={'aspect-ratio': '16 / 9', 'background-color': '#e9ecef', 'border-radius': '0.5rem'})

	def _hex_to_rgb_float(self, hex_color):
		try:
			hex_color = hex_color.lstrip('#')
			return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
		except:
			return (0, 0, 0)

	def _upload_to_gcs(self, image_stream):
		bucket_name = os.environ.get('GCS_BUCKET_NAME')
		if not bucket_name or not storage:
			logger.warning("GCS_BUCKET_NAME not set or storage lib missing. Skipping image upload.")
			return None
		try:
			client = storage.Client()
			bucket = client.bucket(bucket_name)
			blob = bucket.blob(f"slide_assets/{uuid.uuid4()}.png")
			blob.upload_from_file(image_stream, content_type='image/png')
			return blob.public_url
		except Exception as e:
			logger.error(f"GCS Upload failed: {e}")
			return None

	def show_alert(self, text, color='warning'):
		icon = None
		dismissable = True
		if color in ['warning','danger']:
			icon = 'bi bi-exclamation-triangle-fill'
		else:
			icon = 'bi bi-info-circle-fill'
		alert = dbc.Alert([
			dbc.Stack([
				html.I(className=icon),
				html.Span(text),
			],direction='horizontal',gap=3),
		],color=color,dismissable=dismissable, className=f'alert-{color}')
		return alert

	def get_random_song(self):
		pathname = os.path.join(self.base_dir, 'assets', 'data', 'taylor_swift_songs.csv')
		with open(pathname) as g:
			df = pd.read_csv(g, sep=",", header=0)
		r = random.randrange(len(df.index))
		q = df.iloc[r]
		return q

	
def create_app_layout(ui):

	layout = dbc.Container([
		dbc.Row([
			dbc.Col([
				ui.layout['header'],
				html.Hr(),
				ui.layout['pitch_generator'],
				ui.layout['onboarding_modal'],
			],className='d-flex flex-column justify-content-center align-items-center'),
		]),
		dcc.Interval(id='interval-10-sec',interval=10*1000,n_intervals=0),
	],fluid=True)

	return layout
