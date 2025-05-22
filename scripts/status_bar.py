import tkinter as tk

# Status colors
STATUS_COLORS = {
    'stopped': '#f44336',  # red
    'running': '#4caf50',  # green
    'error': '#ff9800'     # orange
}

class StatusBar(tk.Label):
    """A status bar label that can be color-coded."""
    def __init__(self, parent):
        super().__init__(parent, bd=1, relief='sunken', anchor='w')
        self.state = 'stopped'
        self._update()

    def set_state(self, state: str):
        """Update status text and background color."""
        self.state = state
        self._update()

    def _update(self):
        color = STATUS_COLORS.get(self.state, STATUS_COLORS['error'])
        text = self.state.capitalize()
        self.config(text=f"Status: {text}", bg=color)
