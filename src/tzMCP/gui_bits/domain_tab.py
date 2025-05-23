import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from tzMCP.gui_bits.domain_viewer import generate_regex_for_domains

# File where seen domains are appended by the proxy
DOMAINS_FILE = Path(__file__).parent.parent / "logs" / "domains_seen.txt"


class DomainTab(ttk.Frame):
    """Tab for generating regex patterns from the list of seen domains."""
    def __init__(self, parent):
        super().__init__(parent)
        self.domains: list[str] = []
        self._build_ui()
        self._load_domains()

    def _build_ui(self):
        # Domains list
        ttk.Label(self, text="Domains Seen:").pack(anchor='w', padx=5, pady=(5, 0))
        lb_frame = ttk.Frame(self)
        lb_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.lb = tk.Listbox(lb_frame, selectmode='extended')
        scrollbar = ttk.Scrollbar(lb_frame, orient='vertical', command=self.lb.yview)
        self.lb.config(yscrollcommand=scrollbar.set)
        self.lb.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='left', fill='y')

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="Generate Regex", command=self._generate).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Copy to Clipboard", command=self._copy_to_clipboard).pack(side='left', padx=5)

        # Regex output
        ttk.Label(self, text="Generated Regex:").pack(anchor='w', padx=5, pady=(5, 0))
        self.regex_box = ScrolledText(self, height=4)
        self.regex_box.pack(fill='x', padx=5, pady=(0,5))
        self.regex_box.config(state='disabled')

    def _load_domains(self):
        """Reload the domains list from the file."""
        self.lb.delete(0, tk.END)
        if DOMAINS_FILE.exists():
            try:
                with DOMAINS_FILE.open('r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                self.domains = lines
                for dom in lines:
                    self.lb.insert(tk.END, dom)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load domains: {e}")
        else:
            self.domains = []

    def _generate(self):
        """Generate a regex pattern from selected or all domains."""
        indices = self.lb.curselection()
        if indices:
            domains = [self.lb.get(i) for i in indices]
        else:
            domains = self.domains
        pattern = generate_regex_for_domains(domains).pattern
        self.regex_box.config(state='normal')
        self.regex_box.delete('1.0', tk.END)
        self.regex_box.insert('1.0', pattern)
        self.regex_box.config(state='disabled')

    def _copy_to_clipboard(self):
        """Copy the generated regex to the system clipboard."""
        text = self.regex_box.get('1.0', 'end-1c')
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Regex pattern copied to clipboard.")
