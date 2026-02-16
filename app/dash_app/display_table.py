from __future__ import annotations
import math
import uuid
import pandas as pd
import numpy as np
from dash import html, dcc
import dash_bootstrap_components as dbc
from base_core_lib.utils import auto_num_format
from dotenv import load_dotenv
load_dotenv()


class DisplayTableCell:
	def __init__(self,
			  value,
			  style: dict | None = None,
			  className: str | None = None
			  ):
		self.value = value
		self.style = style or {}
		self.className = 'gen-table-cell p-1 mx-2 justify-content-center ' + (className or '')
	
	def render(self) -> dbc.Stack:
		"""
		Renders the display table cell as a Dash Bootstrap Component Stack.
		Returns:
			dbc.Stack: The rendered cell.
		"""
		cell = dbc.Stack(
			self.value,
			className=self.className,
			style=self.style
		)
		return cell

class DisplayTableHeaderCell(DisplayTableCell):
# Inherits from DisplayTableCell
	def __init__(self,
			  value,
			  style: dict | None = None,
			  className: str | None = None
			  ):
		
		style = style or {}
		super().__init__(value, style, className)
		self.style 			= {**self.style, 'font-weight': 'bold'}
		self.className		= self.className + ' gen-table-row-header' + (className or '')
		self.button_color 	= 'dark'

	def render(self) -> dbc.Button:
		"""
		Renders the display table header cell as a Dash Bootstrap Component Button.
		Returns:
			dbc.Button: The rendered header cell.
		"""
		header_cell = dbc.Button(
			self.value,
			color=self.button_color,
			className=self.className,
			style=self.style
		)
		return header_cell

class DisplayTableColumn:
	def __init__(self,
			  name: str,
			  series: pd.Series | list,
			  parent: DisplayTable | None = None,
			  size: int | None = None,
			  centered: bool = False,
			  cell_bar: bool = False,
			  cell_highlight: bool = False,
			  highlight_series: pd.Series | list | None = None,
			  highlight_scale: tuple[float, float] | None = None,
			  pos_color: str | None = None,
			  neg_color: str | None = None,
			  col_format: str | None = None, # options: 'auto', 'numeric', 'string', 'percent', 'percent+'
			  header_style: dict | None = None,
			  col_style: dict | None = None,
			  show_headers: bool = True,
		):
		self.name = name
		self.series = series
		self.parent = parent
		self.size = size or 1
		self.centered = centered
		self.cell_bar = cell_bar
		self.cell_highlight = cell_highlight
		self.highlight_scale = highlight_scale or (0.0, 100.0)
		self.pos_color = pos_color or '42 157 143'
		self.neg_color = neg_color or '231 111 180'
		self.highlight_series = highlight_series
		self.col_format = col_format or 'auto'
		self.show_headers = show_headers

		header_style = header_style or {}
		col_style = col_style or {}
		self.header_cell: DisplayTableHeaderCell | None = None
		self.body_cells: list[DisplayTableCell] = []
		self.className = f'align-items-center justify-content-{"center" if self.centered else "start"}'
		self.style = {**col_style, 'flex': str(self.size)}
		self.header_style = {**header_style, 'flex': str(self.size)} if self.show_headers else {'display':'none'} 
		self.build()
	
	def build(self):
		# Create header cell
		if self.show_headers:
			self.header_cell = DisplayTableHeaderCell(
				value=self.name,
				style=self.header_style
			)

		# Create body cells
		self.body_cells = []
		for i, cell_value in enumerate(self.series):
			val = cell_value
			if self.col_format == 'auto':
				try:
					val = auto_num_format(val)
				except Exception as e:
					pass
			elif self.col_format in ['numeric','int','integer']:
				val = f'{int(val):,.0f}'
			elif self.col_format in ['float', 'decimal']:
				val = f'{float(val):,.1f}'
			elif self.col_format == 'currency':
				val = f'${float(val):,.0f}'
			elif self.col_format == 'currency_decimal':
				val = f'${float(val):,.2f}'
			elif self.col_format == 'string':
				val = str(val)
			elif self.col_format == 'percent':
				val = f'{val:.0%}'
			elif self.col_format == 'percent+':
				val = f'{val:+.0%}'
			elif self.col_format == 'component':
				val = val

			cell_style = self.style
			cell_class = ''
			if self.cell_bar or self.cell_highlight:
				highlight_series = self.highlight_series if self.highlight_series is not None else self.series
				try:
					# Scale percent delta to min and max for indexing
					min_val = min(pd.to_numeric(highlight_series, errors='coerce').dropna())
					max_val = max(pd.to_numeric(highlight_series, errors='coerce').dropna())
					idx_val = self.parent.scale_to(
						pd.to_numeric(highlight_series.iloc[i], errors='coerce'),
						min_val,
						max_val,
						out_min=self.highlight_scale[0],
						out_max=self.highlight_scale[1],
						step=5
					)
					cell_style = {
						**cell_style,
						'--p': str(idx_val),
						'--highlight-pos-rgb': self.pos_color,
						'--highlight-neg-rgb': self.neg_color,
						}
					cell_class = f'grid-cell-highlight' if self.cell_highlight else f'grid-cell-bar-chart-{idx_val}'
				except Exception as e:
					print(f'Error parsing field value as numeric for cell bar: {e}')
					pass
			self.body_cells.append(
				DisplayTableCell(
					value=val,
					style=cell_style,
					className=cell_class
				)
			)

class DisplayTable:
	
	def __init__(self,
			  df: pd.DataFrame | None = None,
			  table_id: str | None = None,
			  row_ids: list | None = None,
			  href_vals: list | None = None,
			  cell_bars: list | None = None,
			  cell_highlights: list | None = None,
			  cell_highlight_series: list | None = None,
			  cell_highlight_scales: list | None = None,
			  pos_colors: list | None = None,
			  neg_colors: list | None = None,
			  col_formats: list | None = None,
			  centered_cols: list | None = None,
			  col_sizes: list | None = None,
			  header_styles: list | None = None,
			  header_cells: list | None = None,
			  col_styles: list | None = None,
			  header_col_aliases: list | None = None,
			  show_headers: bool = True,
		):
		"""
			Create a display table from a dataframe with optional formatting.
			
			Args:
				df (pd.DataFrame, optional): The dataframe to display.
				table_id (str, optional): The ID for the table. Defaults to a random UUID.
				row_ids (list, optional): List of row IDs for each row. Defaults to range(len(df)).
				href_vals (list, optional): List of href values for each row (makes each row-button a clickable link). Defaults to None.
				cell_bars (list, optional): List of booleans indicating if cell bars should be shown for each column. Defaults to False.
				cell_highlights (list, optional): List of booleans indicating if cell highlights should be shown for each column. Defaults to False.
				cell_highlight_series (list, optional): List of series to use for cell highlighting for each column. Defaults to None (uses column's own series).
				cell_highlight_scales (list, optional): List of tuples indicating the (min, max) scale for cell highlights for each column. Defaults to (0.0, 100.0).
				col_formats (list, optional): List of formats for each column ('auto', 'numeric', 'string', 'percent', 'percent+'). Defaults to 'auto'.
				centered_cols (list, optional): List of booleans indicating if columns should be centered. Defaults to False.
				col_sizes (list, optional): List of flex sizes for each column. Defaults to 1.
				header_styles (list, optional): List of style dicts for each header column. Defaults to empty dicts.
				header_cells (list, optional): List of objects to use directly as each header cell. Defaults to None.
				col_styles (list, optional): List of style dicts for each body column. Defaults to empty dicts.
				header_col_aliases (list, optional): List of Dash objects to render as column header values. Defaults to title-cased column names.
				show_headers (bool, optional): Whether to show header row. Defaults to True.
		"""
		print('Initializing DisplayTable...')
		self.conf = {
			'table_id': table_id,
			'row_ids': row_ids,
			'href_vals': href_vals,
			'cell_bars': cell_bars,
			'cell_highlights': cell_highlights,
			'cell_highlight_series': cell_highlight_series,
			'cell_highlight_scales': cell_highlight_scales,
			'pos_colors': pos_colors,
			'neg_colors': neg_colors,
			'col_formats': col_formats,
			'centered_cols': centered_cols,
			'col_sizes': col_sizes,
			'header_styles': header_styles,
			'header_cells': header_cells,
			'col_styles': col_styles,
			'header_col_aliases': header_col_aliases,
			'show_headers': show_headers
		}
		self.data: pd.DataFrame | None = df
		self.table_id = table_id or uuid.uuid4().hex
		self.show_headers: bool = show_headers
		self.row_ids: list = []
		self.row_href_vals: list = []
		self.cell_bars: list = []
		self.cell_highlights: list = []
		self.cell_highlight_series: list = []
		self.cell_highlight_scales: list = []
		self.pos_colors: list = []
		self.neg_colors: list = []
		self.col_formats: list = []
		self.centered_cols: list = []
		self.col_sizes: list = []
		self.header_styles: list = []
		self.header_cells: list = []
		self.col_styles: list = []
		self.header_col_aliases: list = []
		self.columns: list[DisplayTableColumn] = []

		self.build(self.conf)

	def _set_row_defaults(self) -> tuple[list, list]:
		row_range = range(len(self.data))
		default_row_ids = [x for x in row_range]
		default_href_vals = [None for x in row_range]
		return default_row_ids, default_href_vals

	def _set_column_defaults(self) -> tuple[list, list, list, list, list, list]:

		col_range = range(len(self.data.columns))

		formats = []
		centered = []
		sizes = []
		default_none = [None for x in col_range]
		default_false = [False for x in col_range]
		default_empty_dict = [{} for x in col_range]

		for col in self.data.columns:
		# Determine each column's data type and set default formattings
			dtype = col.dtype if isinstance(col, pd.Series) else pd.api.types.infer_dtype(col, skipna=True)
			if pd.api.types.is_numeric_dtype(dtype):
				# 'currency' if value of col.lower() contains a currency keyword  else 'numeric'
				currency_keywords = ['revenue','dollars','price','cost','profit','margin']
				percent_keywords = ['percent','pct','%', 'share']
				delta_keywords = ['delta','change','growth','difference','diff']
				if any(kw in str(col).lower() for kw in percent_keywords):
					if any(kw in str(col).lower() for kw in delta_keywords):
						formats.append( 'percent+' )
					else:
						formats.append( 'percent' )
				elif any(kw in str(col).lower() for kw in currency_keywords):
					formats.append( 'currency' )
				else:
					formats.append( 'numeric' )
				centered.append( True )
				sizes.append( 1 )
			elif pd.api.types.is_string_dtype(dtype):
				formats.append( 'string' )
				centered.append( False )
				sizes.append(2)

		return formats, centered, sizes, default_none, default_false, default_empty_dict

	def _scale_val(self,
				val: float | int,
				low: float,
				high: float,
				out_min: float | None = None,
				out_max: float | None = None,
				step: int | None = None):
		"""
		Scale a single number from input range (low→high)
		into output range (out_min→out_max).

		Supports reversed ranges and step/bin rounding.
		"""
		out_min = out_min or 0.0
		out_max = out_max or 100.0
		# Guard bad inputs
		if any(math.isnan(x) for x in [low, high, val]) or low == high:
			return out_min

		# Normalize to 0–1
		t = (val - low) / (high - low)

		# Clamp 0–1
		t = max(0.0, min(1.0, t))

		# Map into output range
		p = out_min + t * (out_max - out_min)

		# Step/bin rounding if requested
		if step and step > 1:
			p = round(p / step) * step
		else:
			p = round(p)

		return p

	def scale_to(self,
			val: float | int | pd.Series | np.ndarray | list,
			low: float | int,
			high: float | int,
			out_min: float | None = None,
			out_max: float | None = None,
			step: int | None = None):
		"""
		General scaling function:
		Maps val from (low→high) into (out_min→out_max).
		Works for scalar or iterable input.
		"""
		out_min = out_min or 0.0
		out_max = out_max or 100.0

		low = float(pd.to_numeric(low, errors='coerce'))
		high = float(pd.to_numeric(high, errors='coerce'))

		# Cannot scale if low/high invalid
		if math.isnan(low) or math.isnan(high) or low == high:
			if isinstance(val, (pd.Series, np.ndarray, list)):
				return [out_min for _ in val]
			return out_min

		# Convert val to numeric
		if isinstance(val, (pd.Series, np.ndarray, list)):
			val = pd.to_numeric(val, errors='coerce')
			return [
				self._scale_val(v, low, high, out_min, out_max, step)
				for v in val
			]
		else:
			v = float(pd.to_numeric(val, errors='coerce'))
			return self._scale_val(v, low, high, out_min, out_max, step)

	def build(self,
		   conf: dict | None = None
		   ):
		
		if self.data is None:
			print('Initializing empty DisplayTable.')
			return

		# Row settings
		default_row_ids, default_href_vals = self._set_row_defaults()
		self.row_ids = self.row_ids or conf['row_ids'] or default_row_ids
		self.row_href_vals = self.row_href_vals or conf['href_vals'] or default_href_vals

		# Column settings
		default_formats, default_centered, default_sizes, default_none, default_false, default_empty_dict = self._set_column_defaults()
		self.cell_bars = self.cell_bars or conf['cell_bars'] or default_false
		self.cell_highlights = self.cell_highlights or conf['cell_highlights'] or default_false
		self.cell_highlight_series = self.cell_highlight_series or conf['cell_highlight_series'] or default_none
		self.cell_highlight_scales = self.cell_highlight_scales or conf['cell_highlight_scales'] or default_none
		self.pos_colors = self.pos_colors or conf['pos_colors'] or default_none
		self.neg_colors = self.neg_colors or conf['neg_colors'] or default_none
		self.col_formats = self.col_formats or conf['col_formats'] or default_formats
		self.centered_cols = self.centered_cols or conf['centered_cols'] or default_centered
		self.col_sizes = self.col_sizes or conf['col_sizes'] or default_sizes
		self.header_styles = self.header_styles or conf['header_styles'] or default_empty_dict
		self.header_cells = self.header_cells or conf['header_cells'] or default_none
		self.col_styles = self.col_styles or conf['col_styles'] or default_empty_dict
		self.header_col_aliases = self.header_col_aliases or conf['header_col_aliases'] or [str(x).replace('_',' ').title() for x in self.data.columns]
		self.show_headers = self.show_headers or conf['show_headers'] if 'show_headers' in conf else True

		for i, col in enumerate(self.data.columns):
			self.columns.append(
				DisplayTableColumn(
					name=self.header_col_aliases[i],
					series = self.data[col],
					parent = self,
					size = self.col_sizes[i],
					centered = self.centered_cols[i],
					cell_bar = self.cell_bars[i],
					cell_highlight = self.cell_highlights[i],
					highlight_scale = self.cell_highlight_scales[i],
					highlight_series=self.cell_highlight_series[i],
					pos_color = self.pos_colors[i],
					neg_color = self.neg_colors[i],
					col_format = self.col_formats[i],
					header_style = self.header_styles[i],
					col_style = self.col_styles[i],
					show_headers = self.show_headers
				)
			)

	def render_footer(self,
				   page_num:int | str,
				   page_size:int | str,
				   page_count:int | str,
				   download_button: bool = True
				) -> dbc.Stack:
		"""
		Renders the footer of the display table as a Dash Bootstrap Component Stack.
		Args:
			page_num (int | str): The current page number (0-indexed).
			page_size (int | str): The number of rows per page.
			page_count (int | str): The total number of pages.
			download_button (bool, optional): Whether to include a download button. Defaults to True.
		Returns:
			dbc.Stack: The rendered footer.
		"""
		page_num = int(page_num) if isinstance(page_num, str) else page_num
		page_size = int(page_size) if isinstance(page_size, str) else page_size
		page_count = int(page_count) if isinstance(page_count, str) else page_count

		page_number_selector = 	dbc.Stack([
			html.Span(f'Page '),
			dbc.Input(
				type='number',
				debounce=True,
				min=1,
				value=page_num,
				style={'width':'5rem','color':'black'},
				id={'type':'table-page-num-input','table':self.table_id}
			),
			html.Span(f'of {page_count}'),
		],direction='horizontal',gap=2,className='align-items-center justify-content-center')

		page_size_selector = dbc.Stack([
			html.Span('Rows per page:', className='gen-table-row-footer-text'),
			dcc.Dropdown(
				options=[10,25,50,100,500],
				value=page_size,
				style={'width':'5rem','color':'black'},
				id={'type':'table-page-size-input','table':self.table_id}
			),
		],direction='horizontal',gap=2,className='align-items-center justify-content-center')
		
		download_button = html.Div() if not download_button else dbc.Button(
			"Download CSV",
			color='success',
			id='download-results-button',
			className='gen-table-row-footer-button',
			style={'font-weight':'bold','padding':'.5rem 1rem'}
		)

		footer = dbc.Card([
			dbc.Stack(
				[
					page_number_selector,
					page_size_selector,
					download_button,
				],
				direction='horizontal',
				gap=1,
				className='align-items-center justify-content-between gen-table-row-footer',
			)],
			color='dark',
			className='gen-table-row',
			style={'padding':'0.5rem','font-weight':'bold','color':'white'}
		
		)
		return footer

	def render(self,
			page_num:int | None = None,
			page_size:int | None = None,
			download_button: bool = True
			) -> dbc.Stack:
		"""
		Renders the viewable part of the display table as a Dash Bootstrap Component Stack.
		Args:
			page_num (int, optional): The page number to display (0-indexed). Defaults to None (0).
			page_size (int, optional): The number of rows per page. Defaults to None (50).
			download_button (bool, optional): Whether to include a download button in the footer. Defaults to True.
		Returns:
			dbc.Stack: The rendered table.
		"""
		display_page_num = page_num or 1
		page_num = max(0,display_page_num - 1)
		page_size = page_size or 50 # default to 50 rows per page
		page_count = math.ceil(len(self.data) / page_size)
		header_cells = [col.header_cell.render() for col in self.columns] if self.show_headers else []
		header_row = dbc.Card(
			dbc.Stack(
				header_cells,
				direction='horizontal',
				className='align-items-center justify-content-between'
			),
			color='dark',
			className='gen-table-row',
		)
		body_rows = [header_row] if self.show_headers else []

		for i in range(len(self.data)):
			if i < page_num * page_size or i >= (page_num + 1) * page_size:
				continue
			row_cells = [col.body_cells[i].render() for col in self.columns]
			row = dbc.Button(
				dbc.Stack(
					row_cells,
					direction='horizontal',
					className='align-items-center justify-content-between'
				),
				external_link=True if self.row_href_vals[i] != None else False,
				color='light',
				href=self.row_href_vals[i],
				target='_blank',
				className='gen-table-row-outer',
				id={'type':'row-click','table':self.table_id,'index':self.row_ids[i]}
			)
			body_rows.append(row)
		footer_rows = [self.render_footer(display_page_num, page_size, page_count, download_button)]
		body_rows.extend(footer_rows)
		table = dbc.Stack(
			body_rows,
			gap=0,
			className='gen-table justify-content-start align-items-stretch',
			style={'flex':'1'}
		)
		return table