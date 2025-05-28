# ⚙️ Setting Up the tzMCP Project

Welcome! This guide will walk you through setting up the **tzMCP (Taggedz Media Capture Proxy)** on your computer for the first time.

This project lets you capture and filter media from websites using a proxy with a friendly GUI.

---

## 🛠️ System Requirements

- **Python** 3.8 or higher (Windows, Linux, macOS)
- Recommended: A virtual environment (for isolation)
- Internet access to install dependencies
- Optional: A portable web browser (Chrome, Firefox, etc.)

---

## 📦 Step-by-Step Installation

### 1. Download or Clone the Project

```bash
git clone https://github.com/yourusername/tzmcp.git
cd tzmcp
```

Or download the ZIP from GitHub and extract it.

---

### 2. Create and Activate a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If you're working from source and using `pyproject.toml`:

```bash
pip install -e .
```

---

### 4. First Launch (GUI)

```bash
python -m tzMCP.gui
```

This opens the graphical interface with three tabs:
- **Proxy Control**: Start/stop the proxy
- **Browser Launch**: Add and launch portable browsers
- **Configuration**: Set MIME types, filters, logging, etc.

---

## 🔐 Setup the Certificate Authority (CA)

To allow your browser to trust `tzMCP`, you'll need to install a special certificate.  
Follow the guide here:  
📄 [CA_SETUP_GUIDE.md](./CA_SETUP_GUIDE.md)

---

## 🧼 Optional: Clean Up Old Files

tzMCP automatically cleans old log files and browser profiles. You can also do it manually using buttons in the Configuration tab.

---

## 🧪 Want to Test or Hack On It?

- All the code lives under the `tzMCP/` folder
- Main entry point for the GUI: `tzMCP/gui.py`
- Config file: `config/media_proxy_config.yaml`
- Logging output: `logs/`
- Temporary browser profiles: `profiles/`

---

## 🧠 Troubleshooting

- If the GUI won’t launch, make sure `tkinter` is available
- If websites show security errors, install the mitmproxy CA
- Use the terminal output or the "Proxy Control" tab logs for debugging

---

## 🚀 That’s It!

You’re now ready to use tzMCP to capture and filter media from your browser sessions.

Feel free to explore and configure filters to suit your needs. Happy capturing!
