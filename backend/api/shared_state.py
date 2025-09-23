# File: backend/api/shared_state.py
from collections import deque

# A deque with a max length will automatically discard old logs.
# This shared state object breaks the circular dependency between main.py and routes.py.
POLLING_LOGS = deque(maxlen=100)
