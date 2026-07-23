# 🌐 How to Connect a Browser to tzMCP

`tzMCP` is a media capture proxy tool. To use it, you’ll need to **launch a browser and tell it to route its traffic through tzMCP’s proxy**. This guide shows you exactly how to do that — step by step.

---

## 🧠 How It Works

tzMCP runs a local proxy on the configured port (by default):

```
127.0.0.1:8888
```

When you launch a browser through tzMCP, it:
- Creates a temporary profile
- Pre-configures it to use the proxy above
- Opens the browser ready to capture web traffic

No system settings are changed. It’s safe, scoped, and temporary.

---

## ✅ Easiest Way: Use the Built-In Browser Launcher

1. Open the tzMCP app
2. Go to the **“Browser Launch”** tab
3. Click **“Add Portable Browser…”**
   - Choose the `.exe` file for Firefox, Chrome, Brave, etc.
   - It should be a **portable** or standalone version
4. Give it a name if prompted
5. Select your browser from the dropdown list
6. (Optional) Enter the URL you want to visit (e.g., `http://mitm.it`)
7. (Optional) Check “Private / Incognito Mode” if desired
8. Click **“Launch Browser”**

That’s it! The browser will open and all its traffic will be routed through tzMCP.

---

## 🧪 What Happens Under the Hood

- tzMCP configures the browser to use the configured local proxy port
- If it’s a new session, it creates a fresh user profile
- When the app closes, it automatically:
  - Stops the proxy
  - Cleans up the browser profile
  - Ends the browser process (if still running)

---

## 🧰 Manual Browser Configuration (Advanced)

If you **really want to configure your own browser manually**, here’s how:

1. Open your browser’s proxy settings
2. Set the HTTP and HTTPS proxy to:
   ```
   127.0.0.1
   Port: 8888 (or the `proxy_port` in `media_proxy_config.yaml`)
   ```
3. Save and restart your browser

> ⚠️ You’ll also need to install the mitmproxy CA certificate, or HTTPS sites will show security errors.  
> See [CA Setup Guide](./CA_SETUP_GUIDE.md)

---

## 🔐 Remember

Only traffic going through the selected browser is captured. This protects:
- Your system
- Your default browser
- Other apps on your machine

---

## 🧠 Summary

| Task                    | Recommended |
|-------------------------|-------------|
| Use portable browser    | ✅ Yes       |
| Launch via GUI          | ✅ Yes       |
| Configure manually      | ⚠️ Advanced  |
| Install mitmproxy CA    | ✅ Required for HTTPS |

---

Let tzMCP handle the proxy setup so you can focus on browsing and capturing content — without breaking your system.
