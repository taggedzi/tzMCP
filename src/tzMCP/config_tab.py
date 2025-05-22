import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.config_manager import ConfigManager, Config
from src.app_constants import LOG_BUFFER_SIZE, ANSI_PATTERN, ANSI_COLORS, STATUS_COLORS

class ConfigTab(ttk.Frame):
    """Tab for viewing and editing application configuration."""
    def __init__(self, parent, config_manager: ConfigManager, config: Config):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config
        self._build_ui()

    def _build_ui(self):
        # Save Directory
        tk.Label(self, text="Save Directory:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.save_dir_var = tk.StringVar(value=str(self.config.save_dir))
        tk.Entry(self, textvariable=self.save_dir_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        tk.Button(self, text="Browse", command=self._browse).grid(row=0, column=2, padx=5, pady=2)

        # Extensions
        tk.Label(self, text="Extensions (comma-separated):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.ext_var = tk.StringVar(value=','.join(self.config.extensions))
        tk.Entry(self, textvariable=self.ext_var).grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        # Whitelist
        tk.Label(self, text="Whitelist (comma-separated):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.whitelist_var = tk.StringVar(value=','.join(self.config.whitelist))
        tk.Entry(self, textvariable=self.whitelist_var).grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        # Blacklist
        tk.Label(self, text="Blacklist (comma-separated):").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.blacklist_var = tk.StringVar(value=','.join(self.config.blacklist))
        tk.Entry(self, textvariable=self.blacklist_var).grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=2)

        # Pixel Dimensions Filter
        self.pix_filter_var = tk.BooleanVar(value=self.config.filter_pixel_dimensions.get('enabled', False))
        tk.Checkbutton(self, text="Enable Pixel Filter", variable=self.pix_filter_var, command=self._toggle_pixel_fields).grid(row=4, column=0, columnspan=3, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Min Width:").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        self.min_width_var = tk.StringVar(value=str(self.config.filter_pixel_dimensions.get('min_width', '')))
        self.min_width_entry = tk.Entry(self, textvariable=self.min_width_var, width=10)
        self.min_width_entry.grid(row=5, column=1, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Min Height:").grid(row=5, column=2, sticky='w', padx=5, pady=2)
        self.min_height_var = tk.StringVar(value=str(self.config.filter_pixel_dimensions.get('min_height', '')))
        self.min_height_entry = tk.Entry(self, textvariable=self.min_height_var, width=10)
        self.min_height_entry.grid(row=5, column=3, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Max Width:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        self.max_width_var = tk.StringVar(value=str(self.config.filter_pixel_dimensions.get('max_width', '')))
        self.max_width_entry = tk.Entry(self, textvariable=self.max_width_var, width=10)
        self.max_width_entry.grid(row=6, column=1, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Max Height:").grid(row=6, column=2, sticky='w', padx=5, pady=2)
        self.max_height_var = tk.StringVar(value=str(self.config.filter_pixel_dimensions.get('max_height', '')))
        self.max_height_entry = tk.Entry(self, textvariable=self.max_height_var, width=10)
        self.max_height_entry.grid(row=6, column=3, sticky='w', padx=5, pady=2)

        # File Size Filter
        self.size_filter_var = tk.BooleanVar(value=self.config.filter_file_size.get('enabled', False))
        tk.Checkbutton(self, text="Enable File Size Filter", variable=self.size_filter_var, command=self._toggle_size_fields).grid(row=7, column=0, columnspan=3, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Min Bytes:").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        self.min_bytes_var = tk.StringVar(value=str(self.config.filter_file_size.get('min_bytes', '')))
        self.min_bytes_entry = tk.Entry(self, textvariable=self.min_bytes_var, width=12)
        self.min_bytes_entry.grid(row=8, column=1, sticky='w', padx=5, pady=2)
        tk.Label(self, text="Max Bytes:").grid(row=8, column=2, sticky='w', padx=5, pady=2)
        self.max_bytes_var = tk.StringVar(value=str(self.config.filter_file_size.get('max_bytes', '')))
        self.max_bytes_entry = tk.Entry(self, textvariable=self.max_bytes_var, width=12)
        self.max_bytes_entry.grid(row=8, column=3, sticky='w', padx=5, pady=2)

        # Flags
        self.log_seen_var = tk.BooleanVar(value=self.config.log_seen_domains)
        tk.Checkbutton(self, text="Log Seen Domains", variable=self.log_seen_var).grid(row=9, column=0, sticky='w', padx=5, pady=2)
        self.reload_var = tk.BooleanVar(value=self.config.auto_reload_config)
        tk.Checkbutton(self, text="Auto Reload Config", variable=self.reload_var).grid(row=9, column=1, sticky='w', padx=5, pady=2)

        # Save Button
        tk.Button(self, text="Save Configuration", command=self._save).grid(row=10, column=0, columnspan=4, pady=10)

        # Configure grid weights
        for i in range(4):
            self.columnconfigure(i, weight=1)

        # Initialize field states
        self._toggle_pixel_fields()
        self._toggle_size_fields()

    def _toggle_pixel_fields(self):
        state = 'normal' if self.pix_filter_var.get() else 'disabled'
        for widget in [self.min_width_entry, self.min_height_entry, self.max_width_entry, self.max_height_entry]:
            widget.config(state=state)

    def _toggle_size_fields(self):
        state = 'normal' if self.size_filter_var.get() else 'disabled'
        for widget in [self.min_bytes_entry, self.max_bytes_entry]:
            widget.config(state=state)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.save_dir_var.set(path)

    def _save(self):
        try:
            new_cfg = Config(
                save_dir=Path(self.save_dir_var.get()),
                extensions=[e.strip() for e in self.ext_var.get().split(',') if e.strip()],
                whitelist=[e.strip() for e in self.whitelist_var.get().split(',') if e.strip()],
                blacklist=[e.strip() for e in self.blacklist_var.get().split(',') if e.strip()],
                filter_pixel_dimensions={
                    'enabled': self.pix_filter_var.get(),
                    'min_width': int(self.min_width_var.get()),
                    'min_height': int(self.min_height_var.get()),
                    'max_width': int(self.max_width_var.get()),
                    'max_height': int(self.max_height_var.get())
                },
                filter_file_size={
                    'enabled': self.size_filter_var.get(),
                    'min_bytes': int(self.min_bytes_var.get()),
                    'max_bytes': int(self.max_bytes_var.get())
                },
                log_seen_domains=self.log_seen_var.get(),
                auto_reload_config=self.reload_var.get()
            )
            self.config_manager.save_config(new_cfg)
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.config = new_cfg
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
