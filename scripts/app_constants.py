# app_constants.py
"""
Shared constants for the Media Download Proxy Controller application.
"""
import re

# Adjustable maximum number of log lines in the ScrolledText buffer
LOG_BUFFER_SIZE = 2000

# ANSI escape sequence regex pattern for color codes
ANSI_PATTERN = re.compile(r"\x1b\[(?P<code>\d+)(?:;\d+)*m")

# Map ANSI color codes to Tkinter text tag names
ANSI_COLORS = {
    '30': 'black',
    '31': 'red',
    '32': 'green',
    '33': 'yellow',
    '34': 'blue',
    '35': 'magenta',
    '36': 'cyan',
    '37': 'white'
}

# Status bar colors keyed by state
STATUS_COLORS = {
    'stopped': '#f44336',  # red
    'running': '#4caf50',  # green
    'error': '#ff9800'     # orange
}
