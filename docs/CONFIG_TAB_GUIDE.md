# ⚙️ Understanding the Configuration Tab in tzMCP

The **Configuration Tab** in tzMCP lets you control exactly what files get saved when browsing through the proxy. This guide explains what each option does so you can fine-tune your capture behavior.

---

## 🗂️ Save Directory

**What it does:**  
Specifies the folder where all downloaded files will be saved.

**Tips:**
- Use a dedicated folder
- Ensure it’s on a drive with enough space
- You can change this any time

---

## 📦 Allowed MIME Groups

**What it does:**  
Controls what types of files tzMCP is allowed to save based on their **MIME group** — like "image", "video", "html", etc.

**How it works:**
- tzMCP scans every file’s actual content to detect its true type
- Only files matching the selected MIME groups will be saved

**Example:**  
If you only check “image” and “video”, tzMCP will skip HTML, CSS, and other types.

---

## 🌐 Domain Whitelist

**What it does:**  
Lets you **only allow downloads from specific domains**.

**How to use:**
- Leave empty to allow **all** domains
- Add one domain per line (e.g., `example.com` or `cdn.example.net`)
- Wildcards are supported (`.*`, `ads\..*`, etc.)

**Example:**  
Only want media from `wikipedia.org`? Add:
```
wikipedia.org
```

---

## 🚫 Domain Blacklist

**What it does:**  
Lets you **block** media from certain domains, even if they match MIME rules.

**How to use:**
- Add one domain or pattern per line
- If a domain matches the blacklist, its files will be skipped

**Example:**
```
ads\..*
.*\.doubleclick\.net
```

---

## 📏 File Size Filter (in bytes)

**What it does:**  
Lets you ignore files that are **too small** or **too large**.

**Common use cases:**
- Avoid saving icons, trackers, or tiny images
- Skip huge video files or blobs

**Example settings:**
- **Min:** 10240 = 10 KB
- **Max:** 157286400 = 150 MB

---

## 📐 Image Dimension Filter

**What it does:**  
Allows you to control what images get saved based on their **width and height**.

**Useful for:**
- Skipping tiny thumbnails or tracking pixels
- Avoiding massive full-page scans

**How to use:**
- Set min/max width and height
- Leave as default if you’re unsure

---

## 📓 Logging Options

### ✔️ Log to File

- When enabled, logs will be saved in the `logs/` folder for future review

### 🧠 Log Level

Controls how much detail is shown:
- `DEBUG`: Everything
- `INFO`: Most messages
- `WARNING`: Only potential issues
- `ERROR`: Serious problems only
- `CRITICAL`: Crashes or failures

---

## 🧪 tzMCP Options

### 🔁 Auto Reload Config

- Watches the config file for changes
- If enabled, the system reloads settings automatically

### 🧬 Enable Persistent Deduplication

- Tracks downloaded content using a SHA256 hash
- Prevents re-downloading the same file again
- Uses a small local database

---

## 🧹 Manual Cleanup Buttons

At the bottom, you’ll find buttons to:
- **Clean old logs**
- **Clean expired browser profiles**

These are safe to run and help keep your project folder tidy.

---

## 🧠 Final Tips

- Use MIME groups and size/dimension filters together for best results
- Adjust settings, then browse a few sites and check what gets saved
- View logs in the GUI to understand what was skipped and why

You’re in full control. Capture what you want, skip what you don’t.

