import os
import math
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import google.auth
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

def load_secret(secret_name: str, version: str = "latest") -> str:
	"""
	Load a secret from Google Secret Manager.
	Falls back to environment variable if GSM fails or project ID is missing.
	"""
	project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCS_PROJECT_ID") or os.getenv("GCP_PROJECT")
	
	if not project_id:
		try:
			_, project_id = google.auth.default()
		except Exception as e:
			logger.debug(f"Could not determine project ID via google.auth: {e}")
	
	if project_id:
		logger.info(f"Using Project ID: {project_id} for secret: {secret_name}")
		try:
			client = secretmanager.SecretManagerServiceClient()
			name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
			logger.debug(f"Accessing secret path: {name}")
			response = client.access_secret_version(request={"name": name})
			return response.payload.data.decode("utf-8").strip()
		except Exception as e:
			logger.warning(f"Could not load secret {secret_name} from GSM: {e}")
			logger.error(f"GSM Access failed: {e}")
	else:
		logger.error(f"No Project ID found. Cannot access Secret Manager for {secret_name}")
	
	return os.getenv(secret_name, "")

def normalize_email_column(series: pd.Series) -> pd.Series:
	"""
	Normalize a pandas Series of emails:
	1. Convert to string
	2. Strip whitespace
	3. Lowercase
	4. Replace 'nan', 'none', '' with None
	"""
	if series.empty:
		return series
	
	# Convert to string, strip, lower
	cleaned = series.astype(str).str.strip().str.lower()
	
	# Replace invalid values with None
	invalid = ['nan', 'none', '']
	return cleaned.mask(cleaned.isin(invalid), None)

def auto_num_format(raw_number):
	num = float(f'{raw_number:.2g}')
	magnitude = 0
	while abs(num) >= 1000:
		magnitude += 1
		num /= 1000.0
	return '{} {}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), 
		['', 'K', 'M', 'B', 'T'][magnitude])

class AnchorCalendar:
	def __init__(self, anchor_date=datetime.now()):
		from datetime import date, datetime, timedelta
		anchor_date = pd.to_datetime(anchor_date)
		self.current_date = anchor_date.date()
		self.latest_date = (anchor_date + timedelta(days=-1)).date()
		self.current_quarter = ((anchor_date.month-1)//3) + 1
		self.last_quarter = self.current_quarter - 1 if self.current_quarter != 1 else 4
		self.latest_complete_month_start = (anchor_date + pd.DateOffset(months=-1)).replace(day=1).date()
		self.latest_complete_month_end = (self.latest_complete_month_start + pd.DateOffset(months=1) + pd.DateOffset(days=-1)).date()
		self.current_month_start = self.latest_date.replace(day=1)
		self.current_month_end = (self.latest_date.replace(day=1) + pd.DateOffset(months=1) + pd.DateOffset(days=-1)).date()
		self.latest_complete_week_start = (anchor_date - timedelta(days=anchor_date.isoweekday() - 1) - timedelta(days=7)).date()
		self.latest_complete_week_end = (self.latest_complete_week_start + pd.DateOffset(days=6)).date()
		self.current_week_start = (anchor_date - timedelta(days=anchor_date.isoweekday() - 1)).date()
		self.current_week_end = (self.current_week_start + pd.DateOffset(days=6)).date()
		self.mom = (anchor_date + pd.DateOffset(months=-1)).date()
		self.yoy = (anchor_date + pd.DateOffset(years=-1)).date()



class TextProgressBar:

	def __init__(self,
			  value: float | None = None,
			  length: int | None = None,
			  fill_char: str | None = None,
			  empty_char: str | None = None
		):
		self.value = value or 0
		self.length = length or 20
		self.fill_char = fill_char or '▰'
		self.empty_char = empty_char or '▱'
	
	def render(self, value: float| None = None) -> str:
		value = value or self.value
		filled_length = int(self.length * max(0, min(100, value)) // 100)
		bar = self.fill_char * filled_length + self.empty_char * (self.length - filled_length)
		return f"{bar}"