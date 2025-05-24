import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from tzMCP.gui_bits.config_manager import ConfigManager, Config, MIME_GROUPS


class ConfigTab(ttk.Frame):
    """Config tab for the GUI."""
    def __init__(self, parent, config_manager: ConfigManager, config: Config):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config
        self.mime_group_vars = {}
        self._build_ui()

    def _build_ui(self):
        # Save Directory
        tk.Label(self, text="Save Directory:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.save_dir_var = tk.StringVar(value=str(self.config.save_dir))
        tk.Entry(self, textvariable=self.save_dir_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        tk.Button(self, text="Browse", command=self._browse).grid(row=0, column=2, padx=5, pady=2)

        # MIME Groups
        tk.Label(self, text="Allowed MIME Groups:").grid(row=1, column=0, sticky='nw', padx=5, pady=2)
        mime_frame = ttk.Frame(self)
        mime_frame.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        for i, group in enumerate(MIME_GROUPS.keys()):
            var = tk.BooleanVar(value=group in self.config.allowed_mime_groups)
            cb = tk.Checkbutton(mime_frame, text=group.capitalize(), variable=var)
            cb.grid(row=0, column=i, sticky='w')
            self.mime_group_vars[group] = var

        # Whitelist
        tk.Label(self, text="Whitelist Domains (one per line):").grid(row=2, column=0, sticky='nw', padx=5, pady=2)
        self.whitelist_box = tk.Text(self, height=4, width=40)
        self.whitelist_box.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.whitelist_box.insert(tk.END, '\n'.join(self.config.whitelist))

        # Blacklist
        tk.Label(self, text="Blacklist Domains (one per line):").grid(row=3, column=0, sticky='nw', padx=5, pady=2)
        self.blacklist_box = tk.Text(self, height=4, width=40)
        self.blacklist_box.grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.blacklist_box.insert(tk.END, '\n'.join(self.config.blacklist))

        # File Size Filter
        tk.Label(self, text="File Size Filter (bytes):").grid(row=4, column=0, sticky='nw', padx=5, pady=2)
        fs_frame = ttk.Frame(self)
        fs_frame.grid(row=4, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.min_bytes = tk.IntVar(value=self.config.filter_file_size.get("min_bytes", 1))
        self.max_bytes = tk.IntVar(value=self.config.filter_file_size.get("max_bytes", 157286400))
        tk.Label(fs_frame, text="Min:").grid(row=0, column=0, padx=2)
        tk.Entry(fs_frame, textvariable=self.min_bytes, width=10).grid(row=0, column=1, padx=2)
        tk.Label(fs_frame, text="Max:").grid(row=0, column=2, padx=2)
        tk.Entry(fs_frame, textvariable=self.max_bytes, width=10).grid(row=0, column=3, padx=2)

        # Pixel Dimension Filter
        tk.Label(self, text="Pixel Dimension Filter:").grid(row=5, column=0, sticky='nw', padx=5, pady=2)
        pd_frame = ttk.Frame(self)
        pd_frame.grid(row=5, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.min_width = tk.IntVar(value=self.config.filter_pixel_dimensions.get("min_width", 1))
        self.min_height = tk.IntVar(value=self.config.filter_pixel_dimensions.get("min_height", 1))
        self.max_width = tk.IntVar(value=self.config.filter_pixel_dimensions.get("max_width", 12000))
        self.max_height = tk.IntVar(value=self.config.filter_pixel_dimensions.get("max_height", 12000))
        tk.Label(pd_frame, text="Min WxH:").grid(row=0, column=0, padx=2)
        tk.Entry(pd_frame, textvariable=self.min_width, width=6).grid(row=0, column=1, padx=2)
        tk.Entry(pd_frame, textvariable=self.min_height, width=6).grid(row=0, column=2, padx=2)
        tk.Label(pd_frame, text="Max WxH:").grid(row=0, column=3, padx=2)
        tk.Entry(pd_frame, textvariable=self.max_width, width=6).grid(row=0, column=4, padx=2)
        tk.Entry(pd_frame, textvariable=self.max_height, width=6).grid(row=0, column=5, padx=2)

        # Flags
        self.log_internal_debug = tk.BooleanVar(value=self.config.log_internal_debug)
        self.log_seen_domains = tk.BooleanVar(value=self.config.log_seen_domains)
        self.auto_reload_config = tk.BooleanVar(value=self.config.auto_reload_config)
        flag_frame = ttk.Frame(self)
        flag_frame.grid(row=6, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Checkbutton(flag_frame, text="Log Internal Debug", variable=self.log_internal_debug).grid(row=0, column=0, sticky='w', padx=5)
        tk.Checkbutton(flag_frame, text="Log Seen Domains", variable=self.log_seen_domains).grid(row=0, column=1, sticky='w', padx=5)
        tk.Checkbutton(flag_frame, text="Auto Reload Config", variable=self.auto_reload_config).grid(row=0, column=2, sticky='w', padx=5)

        # Save Button
        tk.Button(self, text="Save Configuration", command=self._save).grid(row=10, column=0, columnspan=3, pady=10)

        for i in range(3):
            self.columnconfigure(i, weight=1)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.save_dir_var.set(path)

    def _save(self):
        try:
            selected_mime_groups = [group for group, var in self.mime_group_vars.items() if var.get()]
            new_cfg = Config(
                save_dir=Path(self.save_dir_var.get()),
                whitelist=[line.strip() for line in self.whitelist_box.get("1.0", tk.END).splitlines() if line.strip()],
                blacklist=[line.strip() for line in self.blacklist_box.get("1.0", tk.END).splitlines() if line.strip()],
                allowed_mime_groups=selected_mime_groups,
                filter_pixel_dimensions={
                    "enabled": True,
                    "min_width": self.min_width.get(),
                    "min_height": self.min_height.get(),
                    "max_width": self.max_width.get(),
                    "max_height": self.max_height.get(),
                },
                filter_file_size={
                    "enabled": True,
                    "min_bytes": self.min_bytes.get(),
                    "max_bytes": self.max_bytes.get(),
                },
                log_internal_debug=self.log_internal_debug.get(),
                log_seen_domains=self.log_seen_domains.get(),
                auto_reload_config=self.auto_reload_config.get()
            )
            self.config_manager.save_config(new_cfg)
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.config = new_cfg
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
