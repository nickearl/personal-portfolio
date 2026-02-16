#!/usr/bin/env python
# coding: utf-8

import os, json, random, re, base64, io, uuid, time, socket, calendar, logging
import pathlib
from dotenv import load_dotenv, find_dotenv
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, State, ALL, MATCH, Patch, callback
from dash.exceptions import PreventUpdate
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
REDIS_URL = os.environ['REDIS_URL']
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

		example_items = [
			{"key": "1", "src": "assets/images/weyland-yutani_1.jpeg", "img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}},
			{"key": "2", "src": "assets/images/weyland-yutani_2.jpeg", "img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}},
			{"key": "3", "src": "assets/images/weyland-yutani_3.jpeg", "img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}},
			{"key": "4", "src": "assets/images/weyland-yutani_4.jpeg", "img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}},
			{"key": "5", "src": "assets/images/weyland-yutani_5.jpeg", "img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}},
		]
		self.example_carousel = dbc.Carousel(items=example_items, controls=True, indicators=True, variant="dark")
		self.default_plaque = self._create_plaque(
			"Weyland-Yutani", "Heavy Industry", "Technical Team", "Cyberpunk", "Short and funny"
		)

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
						
						Gemini plans a 5-slide deck and generates high-fidelity slide images using Imagen 3.
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
										[self.example_carousel, self.default_plaque],
										id='sales-pitch-output',
										style={'padding': '2rem', 'background-color': '#f8f9fa', 'border-radius': '0.5rem', 'min-height': '400px'}
									),
									dcc.Download(id='sales-download-deck'),
								],
								custom_spinner=html.Div([
									html.Div(className="ai-spinner"),
									html.Div("Generating Pitch Deck...", className="loading-text"),
									html.Div("Gemini is analyzing data and rendering slides.", className="text-muted small")
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

	def ai_generate_deck(self, company, industry, audience, style, length):
		logger.info(f'Generating sales deck for {company}')
		api_key = load_secret("GEMINI_API_KEY")
		if api_key:
			logger.debug(f"GEMINI_API_KEY loaded. Length: {len(api_key)}")
			api_key = api_key.strip()
		else:
			logger.error("GEMINI_API_KEY is None or empty.")
			return {'error': "Error: API Key missing."}

		client = genai.Client(api_key=api_key)
		
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
		
		Generate a plan for EXACTLY 5 slides, regardless of the requested length.

		Format: Return a valid JSON object with the following structure:
		{{
			"slides": [
				{{
					"title": "Slide Title",
					"image_prompt": "A detailed prompt for an AI image generator (Imagen 3) to render this specific slide as a high-quality image. Describe the visual style ({style}), the background, and explicitly state the text that must appear on the slide (Title and 1-2 short bullet points). Ask for high contrast and legible text."
				}}
			]
		}}
		Ensure the JSON is valid. Do not include markdown formatting (like ```json) around the JSON.
		"""
		
		try:
			response = client.models.generate_content(
				model="gemini-3-flash-preview",
				contents=[
					types.Content(
						role="user",
						parts=[types.Part.from_text(text=prompt)],
					),
				],
				config=types.GenerateContentConfig(
					response_mime_type="application/json",
				)
			)
			
			deck_data = json.loads(response.text)
			slides = deck_data.get('slides', [])[:5] # Enforce max 5 slides
			
			# Generate Images
			carousel_items = []
			for i, slide in enumerate(slides):
				logger.info(f"Generating image for slide {i+1}/{len(slides)}")
				img_src = self._generate_slide_image(client, slide['image_prompt'])
				if img_src:
					carousel_items.append({
						"key": f"{i}",
						"src": img_src,
						"img_style": {"height": "500px", "width": "100%", "object-fit": "contain"}
					})
			
			if not carousel_items:
				return {'error': "Failed to generate slide images."}

			carousel = dbc.Carousel(
				items=carousel_items,
				controls=True,
				indicators=True,
				variant="dark"
			)
			
			plaque = self._create_plaque(company, industry, audience, style, length)
			
			return {'component': html.Div([carousel, plaque])}

		except Exception as e:
			logger.error(f"Error generating pitch: {e}")
			return {'error': f"Sorry, I couldn't generate a pitch at this time. Error: {str(e)}"}

	def _hex_to_rgb_float(self, hex_color):
		try:
			hex_color = hex_color.lstrip('#')
			return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
		except:
			return (0, 0, 0)

	def _generate_slide_image(self, client, image_prompt):
		try:
			response = client.models.generate_content(
				model="gemini-3-pro-image-preview",
				contents=[types.Content(role="user", parts=[types.Part.from_text(text=image_prompt)])],
				config=types.GenerateContentConfig(
					image_config=types.ImageConfig(image_size="1K"),
					response_modalities=["IMAGE"],
				)
			)
			if response.parts:
				for part in response.parts:
					if part.inline_data and part.inline_data.data:
						b64_data = base64.b64encode(part.inline_data.data).decode('utf-8')
						mime_type = part.inline_data.mime_type or "image/png"
						return f"data:{mime_type};base64,{b64_data}"
		except Exception as e:
			logger.error(f"Error generating slide image: {e}")
		return None

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
