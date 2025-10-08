# File: backend/api/shared_state.py
from collections import deque
import logging, sys, io, threading

# --- Log capture setup ---
class DequeLogHandler(logging.Handler):
	"""Logging handler that appends formatted log records to a deque."""
	def __init__(self, dq: deque):
		super().__init__()
		self.dq = dq
		self._lock = threading.Lock()
	def emit(self, record):
		try:
			msg = self.format(record)
			with self._lock:
				self.dq.append(msg)
		except Exception:
			pass

class StreamToLogger(io.TextIOBase):
	"""Redirects writes (print/stdout) into logging system."""
	def __init__(self, logger: logging.Logger, level: int):
		self.logger = logger
		self.level = level
	def write(self, buf):
		if not buf:
			return
		text = buf.rstrip()
		if not text:
			return
		for line in text.splitlines():
			self.logger.log(self.level, line)
	def flush(self):
		pass

def install_global_log_capture(target_deque: deque):
	"""Idempotently install a handler that mirrors all logs + stdout/stderr into the deque."""
	root = logging.getLogger()
	# Check if already installed
	for h in root.handlers:
		if isinstance(h, DequeLogHandler):
			return
	handler = DequeLogHandler(target_deque)
	formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
	handler.setFormatter(formatter)
	handler.setLevel(logging.INFO)
	root.addHandler(handler)
	# Optionally lower root level if higher
	if root.level > logging.INFO:
		root.setLevel(logging.INFO)
	# Redirect stdout/stderr (avoid duplicating if already wrapped)
	if not isinstance(sys.stdout, StreamToLogger):
		sys.stdout = StreamToLogger(logging.getLogger('stdout'), logging.INFO)
	if not isinstance(sys.stderr, StreamToLogger):
		sys.stderr = StreamToLogger(logging.getLogger('stderr'), logging.ERROR)

# A deque with a max length will automatically discard old logs.
# This shared state object breaks the circular dependency between main.py and routes.py.
POLLING_LOGS = deque(maxlen=100)
