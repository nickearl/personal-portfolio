"""
Per-visitor daily caps on the AI demos, which call paid Gemini models.

Counts live in this process's memory. gunicorn runs a single worker and Cloud Run normally runs a single
instance, so a visitor's count is exact; if the service scales out, each instance counts separately.
"""
import math
import threading
import time
from collections import defaultdict, deque

import flask

WINDOW_SECONDS = 24 * 3600
LIMITS = {
	'sales_deck': 5,      # deck plans; each also renders up to 5 slides
	'sales_slide': 30,    # slide renders, leaving room for retries
	'design_theme': 30,
	'design_image': 10,
}
LABELS = {
	'sales_deck': 'decks',
	'sales_slide': 'slide renders',
	'design_theme': 'themes',
	'design_image': 'images',
}

_hits = defaultdict(deque)
_lock = threading.Lock()


def visitor_id():
	# Cloud Run appends the real client IP as the last X-Forwarded-For entry; earlier entries are client-supplied
	forwarded = flask.request.headers.get('X-Forwarded-For', '')
	return forwarded.split(',')[-1].strip() or flask.request.remote_addr or 'unknown'


def check(action):
	"""Record one use of `action` by the current visitor. Returns 0 if allowed, else seconds until a slot frees up."""
	now = time.time()
	cutoff = now - WINDOW_SECONDS
	with _lock:
		hits = _hits[(action, visitor_id())]
		while hits and hits[0] <= cutoff:
			hits.popleft()
		if len(hits) >= LIMITS[action]:
			return math.ceil(hits[0] - cutoff)
		hits.append(now)
		if len(_hits) > 10000:
			for key in [k for k, v in _hits.items() if not v or v[-1] <= cutoff]:
				del _hits[key]
		return 0


def limit_message(action, retry_after):
	hours = retry_after / 3600
	wait = f'about {math.ceil(hours)} hour{"s" if math.ceil(hours) != 1 else ""}' if hours >= 1 else f'about {math.ceil(retry_after / 60)} minutes'
	return (f"You've reached today's limit of {LIMITS[action]} {LABELS[action]} for this demo, which keeps it free to run. "
		f"Try again in {wait}.")
