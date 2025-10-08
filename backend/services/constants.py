"""Central constants and reusable text fragments for AssistIQ agent backend.

Keeping these in one file prevents string drift and duplicate sign‑offs across
activities and workflows.
"""

AGENT_SIGNATURE = "\n\n— AssistIQ Agent"

# Guardrail patterns considered unsafe / to be stripped from LLM drafted steps.
UNSAFE_COMMAND_PATTERNS = [
    "DROP TABLE", "DELETE FROM", "TRUNCATE ", "SHUTDOWN IMMEDIATE", "rm -rf /",
    "format c:", "ALTER SYSTEM", "GRANT ALL"
]

# Minimum citation tokens required per non-empty paragraph.
MIN_CITATION_PER_PARAGRAPH = 1

# Citation markers
INTERNAL_MARKER = "[INT:"
EXTERNAL_MARKER = "[WEB:"
