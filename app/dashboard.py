import dash_bootstrap_components as dbc
from dash import html, dcc
from conf import GlobalUInterface
from auth import is_app_authenticated, render_unauthorized_page

GLOBAL_UI = GlobalUInterface()
PAGE = 'dashboard'

class UInterface:
	def __init__(self):
		self.global_ui = GLOBAL_UI
		self.conf = self.global_ui.pages[PAGE]

	def render(self):
		return dbc.Container([
			dbc.Row([
				dbc.Col([
					html.H1(self.conf['display_name']),
					html.Hr(),
					html.P("Interactive Data Visualization Demo"),
					dbc.Alert("This page is under construction.", color="info"),
					html.Img(src=self.conf['image'], style={'width': '100%', 'max-width': '800px', 'border-radius': '1rem'})
				])
			])
		], fluid=True)

def create_app_layout(ui: UInterface):
	def layout():
		# Optional: Check auth if required
		# if not is_app_authenticated():
		# 	return render_unauthorized_page()
		
		return dbc.Container([
			ui.render()
		], fluid=True)
	return layout