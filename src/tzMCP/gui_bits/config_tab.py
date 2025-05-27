import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from tzMCP.gui_bits.config_manager import ConfigManager, Config, MIME_GROUPS
from tzMCP.common_utils.cleanup_logs import clean_old_logs
from tzMCP.common_utils.cleanup_profiles import clean_old_profiles
from tzMCP.common_utils.log_config import setup_logging, log_gui
setup_logging()

class ConfigTab(ttk.Frame):
    """Config tab for the GUI."""
    def __init__(self, parent, config_manager: ConfigManager, config: Config):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config
        self.mime_group_vars = {}
        self._build_ui()

    def _build_ui(self):
        # -------------------------
        # Proxy and Download Settings
        # -------------------------
        proxy_frame = ttk.LabelFrame(self, text="Proxy and Download Settings")
        proxy_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        tk.Label(proxy_frame, text="Save Directory:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.save_dir_var = tk.StringVar(value=str(self.config.save_dir))
        tk.Entry(proxy_frame, textvariable=self.save_dir_var, width=40).grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        tk.Button(proxy_frame, text="Browse", command=self._browse).grid(row=0, column=2, padx=5, pady=2)

        tk.Label(proxy_frame, text="Allowed MIME Groups:").grid(row=1, column=0, sticky='nw', padx=5, pady=2)
        mime_frame = ttk.Frame(proxy_frame)
        mime_frame.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        for i, group in enumerate(MIME_GROUPS.keys()):
            var = tk.BooleanVar(value=group in self.config.allowed_mime_groups)
            cb = tk.Checkbutton(mime_frame, text=group.capitalize(), variable=var)
            cb.grid(row=0, column=i, sticky='w')
            self.mime_group_vars[group] = var

        tk.Label(proxy_frame, text="Whitelist Domains (one per line):").grid(row=2, column=0, sticky='nw', padx=5, pady=2)
        self.whitelist_box = tk.Text(proxy_frame, height=4, width=40)
        self.whitelist_box.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.whitelist_box.insert(tk.END, '\n'.join(self.config.whitelist))

        tk.Label(proxy_frame, text="Blacklist Domains (one per line):").grid(row=3, column=0, sticky='nw', padx=5, pady=2)
        self.blacklist_box = tk.Text(proxy_frame, height=4, width=40)
        self.blacklist_box.grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.blacklist_box.insert(tk.END, '\n'.join(self.config.blacklist))

        tk.Label(proxy_frame, text="File Size Filter (bytes):").grid(row=4, column=0, sticky='nw', padx=5, pady=2)
        fs_frame = ttk.Frame(proxy_frame)
        fs_frame.grid(row=4, column=1, columnspan=2, sticky='ew', padx=5, pady=2)
        self.min_bytes = tk.IntVar(value=self.config.filter_file_size.get("min_bytes", 1))
        self.max_bytes = tk.IntVar(value=self.config.filter_file_size.get("max_bytes", 157286400))
        tk.Label(fs_frame, text="Min:").grid(row=0, column=0, padx=2)
        tk.Entry(fs_frame, textvariable=self.min_bytes, width=10).grid(row=0, column=1, padx=2)
        tk.Label(fs_frame, text="Max:").grid(row=0, column=2, padx=2)
        tk.Entry(fs_frame, textvariable=self.max_bytes, width=10).grid(row=0, column=3, padx=2)

        tk.Label(proxy_frame, text="Image Dimension Filter:").grid(row=5, column=0, sticky='nw', padx=5, pady=2)
        pd_frame = ttk.Frame(proxy_frame)
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

        # -------------------------
        # Logging Settings
        # -------------------------
        logging_frame = ttk.LabelFrame(self, text="Logging Settings")
        logging_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.log_to_file = tk.BooleanVar(value=self.config.log_to_file)
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level = tk.StringVar(value=self.config.log_level)
        tk.Checkbutton(logging_frame, text="Log to File", variable=self.log_to_file).grid(row=0, column=0, sticky='w', padx=5)
        tk.Label(logging_frame, text="Log Level:").grid(row=0, column=1, sticky='e', padx=5)
        ttk.OptionMenu(logging_frame, self.log_level, self.log_level.get(), *log_levels).grid(row=0, column=2, sticky='w')

        # -------------------------
        # Feature Flags
        # -------------------------
        flag_frame = ttk.LabelFrame(self, text="tzMCP Options")
        flag_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.auto_reload_config = tk.BooleanVar(value=self.config.auto_reload_config)
        self.enable_persistent_dedup = tk.BooleanVar(value=self.config.enable_persistent_dedup)
        tk.Checkbutton(flag_frame, text="Auto Reload Config", variable=self.auto_reload_config).grid(row=0, column=0, sticky='w', padx=5)
        tk.Checkbutton(flag_frame, text="Enable Persistent Deduplication", variable=self.enable_persistent_dedup).grid(row=0, column=1, sticky='w', padx=5)

        # -------------------------
        # Save and Manual Cleanup
        # -------------------------
        control_frame = ttk.LabelFrame(self, text="Maintenance and Save")
        control_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        tk.Button(control_frame, text="Save Configuration", command=self._save).grid(row=0, column=0, columnspan=2, pady=5, padx=5)
        tk.Button(control_frame, text="Clean Old Logs Now", command=self._manual_clean_logs).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(control_frame, text="Clean Old Profiles Now", command=self._manual_clean_profiles).grid(row=1, column=1, padx=5, pady=5)

        for i in range(3):
            self.columnconfigure(i, weight=1)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.save_dir_var.set(path)

    def _manual_clean_logs(self):
        log_dir = Path(__file__).parent.parent.parent / "logs"
        deleted = clean_old_logs(log_dir)
        messagebox.showinfo("Cleanup Logs", f"Removed {len(deleted)} log file(s).")

    def _manual_clean_profiles(self):
        profile_dir = Path(__file__).parent.parent.parent / "profiles"
        deleted = clean_old_profiles(profile_dir)
        messagebox.showinfo("Cleanup Profiles", f"Removed {len(deleted)} expired profile(s).")

    def reload_config(self, config: Config):
        self.config = config
        self.save_dir_var.set(str(config.save_dir))
        for group, var in self.mime_group_vars.items():
            var.set(group in config.allowed_mime_groups)
        self.whitelist_box.delete("1.0", tk.END)
        self.whitelist_box.insert(tk.END, "\n".join(config.whitelist))
        self.blacklist_box.delete("1.0", tk.END)
        self.blacklist_box.insert(tk.END, "\n".join(config.blacklist))
        self.min_bytes.set(config.filter_file_size.get("min_bytes", 1))
        self.max_bytes.set(config.filter_file_size.get("max_bytes", 157286400))
        self.min_width.set(config.filter_pixel_dimensions.get("min_width", 1))
        self.min_height.set(config.filter_pixel_dimensions.get("min_height", 1))
        self.max_width.set(config.filter_pixel_dimensions.get("max_width", 12000))
        self.max_height.set(config.filter_pixel_dimensions.get("max_height", 12000))
        self.log_to_file.set(config.log_to_file)
        self.log_level.set(config.log_level)
        self.auto_reload_config.set(config.auto_reload_config)
        self.enable_persistent_dedup.set(config.enable_persistent_dedup)

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
                auto_reload_config=self.auto_reload_config.get(),
                log_to_file=self.log_to_file.get(),
                log_level=self.log_level.get(),
                enable_persistent_dedup=self.enable_persistent_dedup.get()
            )
            self.config_manager._validate_config(new_cfg)
            self.config_manager.save_config(new_cfg)
            messagebox.showinfo("Success", "Configuration saved successfully.")
            self.config = new_cfg
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
