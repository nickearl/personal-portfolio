#!/usr/bin/env python
# coding: utf-8

import os, json, random, re, base64, io, uuid, time, socket, calendar, logging
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
import pandas as pd
import numpy as np
from datetime import date, datetime
from google import genai
from google.genai import types
from conf import GlobalUInterface
from dash_app.utils import load_secret

# Get environment variables
load_dotenv(find_dotenv())
PAGE = 'ai'
REDIS_URL = os.environ['REDIS_URL']
pd.set_option('future.no_silent_downcasting', True)

logger = logging.getLogger(__name__)

class UInterface:
	def __init__(self):
		self.global_ui = GlobalUInterface()
		self.conf = self.global_ui.pages[PAGE]
		logger.info(f'Initializing {self.conf["display_name"]} UI')
		self.init_time = datetime.now()
		self.styles = {
			'color_sequence': ['#FD486D', '#9F4A86', '#F5D107', '#86D7DC', '#333D79', '#E5732D', '#4CAF8E', '#722B5C', '#FFC10A', '#005580'],
			'portrait_colors': ['#86D7DC', '#9B004E','#FA005A','#FFC500','#520044'],
			'comp_colors':['#54898d','#9F4A86'],
		}
		# Resolve paths relative to this file to support running from root or app/ dir
		self.base_dir = pathlib.Path(__file__).parent.parent.resolve()
		self.data = {
			'traffic_daily': pd.read_csv(self.base_dir / 'assets' / 'data' / 'traffic_daily.csv'),
		}
		self.layout = {
			'header': dbc.Stack([
				dbc.Stack([
					# html.Img(src='assets/images/robot_and_human.png',style={'width':'150px','height':'150px'}),
					html.Img(src=self.conf['image'],style={'width':'150px','height':'150px'}),
					html.H3(self.conf['display_name']),
				],direction='horizontal',gap=3,className='justify-content-end',style={'width':'50%','max-width':'500px'}),
				dbc.Stack([
					html.Span(self.conf['summary_header'],style={'font-weight':'bold'}),
					html.Span("Accelerate creative workflows by using AI to instantly generate dashboard themes and visual assets that adhere to your brand identity."),
					html.Span('>More Info<',id='ai-more-info',style={'font-weight':'bold','color':self.styles['color_sequence'][1]}),
					dbc.Popover(
						[
							dbc.PopoverHeader(dcc.Markdown('**Step by Step**')),
							dbc.PopoverBody([
								dbc.Stack([
									dcc.Markdown("""
										1. Define a template prompt with system instructions and base knowledge that returns some useful information.  The prompt should be tested to ensure it returns a predictably formatted reponse.
										2. Get user input values from the UI or external data source (Retrieval Augmented Generation aka RAG), inject them into the prompt template.
										3. Send the payload to the LLM
										4. Parse response from AI, for example a list of records to insert into a dataframe, or a list of color hex codes.
									"""),
									html.Img(src='assets/images/ai_screenshot.png', style={'max-width':'65vw'}),
									html.Span([
										'You can ',
										html.A('view the source code in my Github repo',href='https://github.com/nickearl/bi-demo',target='_blank',style={'font-weight':'bold'}),
										'.',
									]),
								],gap=3,className='d-flex align-items-center justify-content-center'),
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
				dbc.ModalHeader(dbc.ModalTitle("Design Lab")),
				dbc.ModalBody([
					dcc.Markdown("""
						**AI-Powered Design Automation**

						This workspace demonstrates how Generative AI can streamline the design process for dynamic content like chart visualizations and graphics assets.

						**Try it out:**
						
						*   **Theme Generator:** Describe a brand or mood (e.g., "Starbucks", "Cyberpunk") to recolor the charts.
						*   **Image Generator:** Create custom artwork in the app's specific visual style.
					"""),
				]),
				dbc.ModalFooter(
					dbc.Button("Enter Lab", id="close-onboarding-modal", className="ms-auto", n_clicks=0, style={"padding":"0.5rem"})
				),
			],
			id="ai-onboarding-modal",
			is_open=True,
			size="lg",
			centered=True,
		)

		from dash_app.pages.dashboard import UInterface as dashboard_ui
		self.layout['example_chart'] = dbc.Container([
			dbc.Card([
				dbc.CardHeader([
					html.H4('Branding & Theming')
				]),
				dbc.CardBody([
					dbc.Container([
						dbc.Row([
							dbc.Col([
								dbc.Stack([
									html.Label("Describe a Color Theme", className="fw-bold"),
									dbc.Textarea(id='ai-input-colors-text', placeholder='e.g. "Corporate colors of FedEx" or "80s Synthwave"', style={'height': '100px'}),
									dbc.FormText("Gemini will generate a structured JSON palette based on your description."),
									dbc.Button([html.I(className='bi bi-palette'), " Apply Theme"], id='ai-input-colors-submit', color='primary', className='w-100'),
									html.Hr(),
									dcc.Markdown("""
										**How it works:**
										The app sends your prompt to Gemini with a system instruction to return **only valid JSON** containing hex codes. This data is then parsed and applied directly to the Plotly chart configuration.
									""", className="text-muted small")
								], gap=2),
							], width=12, lg=4, className="border-end"),
							dbc.Col([
								dcc.Loading(
									id='ai-chart-loading',
									children=[
										dbc.Container([
											dashboard_ui().render_summary_charts(w=None, h=400, chart_only=True),
										], id='ai-chart-container', fluid=True)
									],
									custom_spinner=html.Div([
										html.Div(className="ai-spinner"),
										html.Div("Generating Theme...", className="loading-text"),
									], className="d-flex flex-column align-items-center justify-content-center p-5 bg-white shadow rounded"),
									overlay_style={"visibility":"visible", "filter": "blur(4px)", "opacity": "0.8", "background-color": "white"},
								)
							], width=12, lg=8),
						])
					])
				]),
				#dbc.CardFooter([]),
			]),
		])
		self.layout['example_image'] = dbc.Container([
			dbc.Card([
				dbc.CardHeader([
					html.H4('Image Generation')
				]),
				dbc.CardBody([
					dbc.Container([
						dbc.Row([
							dbc.Col([
								dbc.Stack([
									html.Label("Image Subject", className="fw-bold"),
									dbc.Textarea(id='ai-input-image-text', placeholder='e.g. "A futuristic city" or "A cat eating pizza"', style={'height': '100px'}),
									dbc.FormText("The app wraps your prompt in a specific 'Style Persona' to ensure consistency."),
									dbc.Button([html.I(className='bi bi-image'), " Generate Image"], id='ai-input-image-submit', color='primary', className='w-100'),
									html.Hr(),
									html.Div([
										html.Span("View System Prompt", id='ai-show-prompt', className="text-primary", style={'cursor': 'pointer', 'text-decoration': 'underline'}),
									dbc.Popover(
										[
											dbc.PopoverHeader(dcc.Markdown('**Prompt Template**')),
											dbc.PopoverBody([
												dcc.Markdown("""
						 							>
													>
													> Role / Persona
						 							>
													> You are a digital artist with a well defined style, of which all your work is representative.
													>
						 							>
													> Your Style
						 							>
													> 1. Hand-Drawn Anime Look with Digital Enhancements
												 	>							
						 							> The linework has a slightly organic, hand-drawn feel, rather than the perfectly smooth digital look of modern anime.
													> Line weights vary, with thicker outlines around characters but detailed, refined interior lines for facial features and mechanical elements.
													> The shading style uses cel-shading with some soft gradients, adding depth without losing the sharp, high-contrast aesthetic.
													>
						 							>
						 							> 2. Expressive Faces with Larger, More Detailed Eyes
													>
						 							> Eyes are slightly larger than in 1990s anime, inspired by modern anime’s focus on expressiveness, but not exaggerated like in moe or slice-of-life anime.
													> Detailed reflections and highlights in the irises make them feel luminous and alive, but still maintaining a gritty sci-fi intensity.
													> Facial features retain subtle, naturalistic expressions, avoiding exaggerated reactions in favor of nuanced emotions.
													>
						 							>
						 							> 3. Bold Outlines and Rich Shading
													>							
						 							> Characters and objects are defined with thick, confident outlines, similar to 1990s anime.
													> Shading employs multi-tone cel-shading, giving a three-dimensional look with a hand-painted touch.
													> Soft airbrushed lighting effects (used sparingly) enhance the cyberpunk glow.
													>
						 							>
						 							> 4. Muted Yet Striking Colors
													>
						 							> The overall palette is subdued and industrial, like Ghost in the Shell, but with strategic neon accents.
													> Deep blues, purples, and grays dominate, with vibrant neon blue and cyan highlights adding a futuristic glow.
													> Backgrounds remain hand-drawn and painterly, with textured brush strokes, rather than the hyper-polished CGI aesthetic of modern anime.
													>
						 							>
						 							> 5. Cinematic Framing with a Slightly Gritty Look
													>
						 							> A mix of sharp angles and dynamic close-ups, inspired by 1990s cinematography.
													> Glowing effects, digital distortion, and holographic flickering are present but hand-painted rather than fully CGI-rendered.
													> The scene has a slight grain texture, simulating the look of an old-school anime cel transferred to film.
													>
												"""),
											]),
										],
										placement='bottom',
										target='ai-show-prompt',
										trigger='hover',
										style={'min-width':'50vw'},	
									)], className="small text-center")
								], gap=2),
							], width=12, lg=4, className="border-end"),
							dbc.Col([
								dcc.Loading(
									id='ai-image-loading',
									children=[
										html.Div(
											html.Img(src='assets/images/placeholder.png', id='ai-image-output', style={'width':'100%', 'max-height':'500px', 'object-fit':'contain', 'border-radius':'0.5rem'}),
											id='ai-image-container',
											className='d-flex justify-content-center align-items-center bg-light rounded p-3',
											style={'min-height':'400px'}
										),
									],
									custom_spinner=html.Div([
										html.Div(className="ai-spinner"),
										html.Div("Generating Artwork...", className="loading-text"),
									], className="d-flex flex-column align-items-center justify-content-center p-5 bg-white shadow rounded"),
									overlay_style={"visibility":"visible", "filter": "blur(4px)", "opacity": "0.8", "background-color": "white"},
								)
							], width=12, lg=8),
						])
					])
				]),
				#dbc.CardFooter([]),
			]),
		])

	def ai_color_sequence(self, input_prompt):
		api_key = load_secret("GEMINI_API_KEY")
		if api_key:
			print(f"DEBUG: GEMINI_API_KEY loaded. Length: {len(api_key)}")
			api_key = api_key.strip()
		else:
			print("ERROR: GEMINI_API_KEY is None or empty.")
		client = genai.Client(api_key=api_key)
		
		sys_instruction = "You are a graphic design artist. Write code to represent the colors and styles provided by user prompt as python objects. Please return a valid JSON string containing a python list containing 12 hex color code values based on the user's prompt. The list must be sorted in order of colors most to least representative of the prompt. Very light shades of white cannot be used. Include only this JSON string in your response."
		
		try:
			response = client.models.generate_content(
				model="gemini-3-flash-preview",
				contents=[
					types.Content(
						role="user",
						parts=[
							types.Part.from_text(text=f"{sys_instruction}\n\nUser Prompt: {input_prompt}"),
						],
					),
				],
				config=types.GenerateContentConfig(
					response_mime_type="application/json",
				)
			)
			import json
			data = json.loads(response.text)
			if isinstance(data, list):
				return data
			if isinstance(data, dict):
				for v in data.values():
					if isinstance(v, list):
						return v
		except Exception as e:
			logger.error(f"Error generating colors: {e}")
		
		return []

	def ai_generate_image(self, input_prompt:str,style='synthwave')->str:
		logger.info(f'Generating image with prompt: {input_prompt} | style: {style}')
		api_key = load_secret("GEMINI_API_KEY")
		if api_key:
			logger.debug(f"GEMINI_API_KEY loaded. Length: {len(api_key)}")
			api_key = api_key.strip()
		else:
			logger.error("GEMINI_API_KEY is None or empty.")
		client = genai.Client(api_key=api_key)

		prompt = None
		if style == 'synthwave':
			prompt = f"""
				'You are a digital artist.   All of your work uses the Outrun/Synthwave visual aesthetic, often including visual elements like neon lights and colors (but never green),
				palm trees, sunsets, geometric shapes and line patterns, and imagery of the 1980s.  Your work typically has an extremely minimalist design to minimize visual clutter.
				Your clients ask you to create pictures of various subjects in your usual style.  I am your client.'

				{input_prompt}
				"""
		elif style == 'anime':
			prompt = f"""
				Role / Persona
				You are a digital artist with a well defined style, of which all your work is representative.

				Your Style
				1. Hand-Drawn Anime Look with Digital Enhancements
				The linework has a slightly organic, hand-drawn feel, rather than the perfectly smooth digital look of modern anime.
				Line weights vary, with thicker outlines around characters but detailed, refined interior lines for facial features and mechanical elements.
				The shading style uses cel-shading with some soft gradients, adding depth without losing the sharp, high-contrast aesthetic.
				2. Expressive Faces with Larger, More Detailed Eyes
				Eyes are slightly larger than in 1990s anime, inspired by modern anime’s focus on expressiveness, but not exaggerated like in moe or slice-of-life anime.
				Detailed reflections and highlights in the irises make them feel luminous and alive, but still maintaining a gritty sci-fi intensity.
				Facial features retain subtle, naturalistic expressions, avoiding exaggerated reactions in favor of nuanced emotions.
				3. Bold Outlines and Rich Shading
				Characters and objects are defined with thick, confident outlines, similar to 1990s anime.
				Shading employs multi-tone cel-shading, giving a three-dimensional look with a hand-painted touch.
				Soft airbrushed lighting effects (used sparingly) enhance the cyberpunk glow.
				4. Muted Yet Striking Colors
				The overall palette is subdued and industrial, like Ghost in the Shell, but with strategic neon accents.
				Deep blues, purples, and grays dominate, with vibrant neon blue and cyan highlights adding a futuristic glow.
				Backgrounds remain hand-drawn and painterly, with textured brush strokes, rather than the hyper-polished CGI aesthetic of modern anime.
				5. Cinematic Framing with a Slightly Gritty Look
				A mix of sharp angles and dynamic close-ups, inspired by 1990s cinematography.
				Glowing effects, digital distortion, and holographic flickering are present but hand-painted rather than fully CGI-rendered.
				The scene has a slight grain texture, simulating the look of an old-school anime cel transferred to film.

				{input_prompt}
				"""

		if prompt is None:
			raise ValueError('Invalid style provided')
		logger.info(f'Sending prompt to LLM: {prompt}')
		
		try:
			response = client.models.generate_content(
				model="gemini-3-pro-image-preview",
				contents=[
					types.Content(
						role="user",
						parts=[
							types.Part.from_text(text=prompt),
						],
					),
				],
				config=types.GenerateContentConfig(
					image_config=types.ImageConfig(
						image_size="1K",
					),
					response_modalities=["IMAGE"],
				)
			)
			if response.parts:
				for part in response.parts:
					if part.inline_data and part.inline_data.data:
						image_bytes = part.inline_data.data
						mime_type = part.inline_data.mime_type
						b64_image = base64.b64encode(image_bytes).decode('utf-8')
						return f"data:{mime_type};base64,{b64_image}"
			return "assets/images/placeholder.png"
		except Exception as e:
			logger.error(f"Error generating image: {e}")
			return "assets/images/placeholder.png"



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
		pathname = self.base_dir / 'assets' / 'data' / 'taylor_swift_songs.csv'
		with open(pathname) as g:
			df = pd.read_csv(g, sep=",", header=0)
		r = random.randrange(len(df.index))
		q = df.iloc[r]
		return q

@callback(
	Output("ai-onboarding-modal", "is_open"),
	Input("close-onboarding-modal", "n_clicks"),
	prevent_initial_call=True,
)
def close_onboarding_modal(n):
	return False

	
def create_app_layout(ui):

	layout = dbc.Container([
		dbc.Row([
			dbc.Col([
				ui.layout['header'],
				html.Br(),
				ui.layout['example_chart'],
				html.Div(style={'height': '4rem'}),
				html.Hr(className="w-75"),
				html.Div(style={'height': '4rem'}),
				ui.layout['example_image'],
				html.Div(style={'height': '4rem'}),
			],className='d-flex flex-column justify-content-center align-items-center'),
			ui.layout['onboarding_modal'],
		]),
		dcc.Interval(id='interval-10-sec',interval=10*1000,n_intervals=0),
	],fluid=True)

	return layout
