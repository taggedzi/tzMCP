# 🌐 Using Portable Browsers with tzMCP

`tzMCP` is designed to work best with **portable browsers** — special versions of browsers that don't install system-wide and don't interfere with your regular browser settings.

---

## 🤔 Why Portable Browsers?

Using a portable browser gives you:

### ✅ **Better Proxy Control**
Installed browsers often ignore local proxy settings or use system-wide rules. Portable browsers let `tzMCP` apply settings directly, so you:
- Don’t need to change OS-level proxy settings
- Don’t affect your daily browsing

### 🔒 **Better Security and Privacy**
- No changes to your normal browser profile
- Temporary profiles get deleted automatically
- No risk of leaking credentials, cookies, or saved data

### 🧹 **Automatic Cleanup**
tzMCP creates a fresh browser profile every time you launch, and cleans it up when the app closes. This keeps things fast, safe, and isolated.

---

## 🔍 Where to Find Portable Browsers

Here are trusted sources to download portable versions:

- 🔗 [https://portableapps.com/](https://portableapps.com/)
- 🔗 [https://www.winpenpack.com](https://www.winpenpack.com)
- 🔗 Official browser developer sites (some offer ZIP or standalone builds)

Look for browsers like:

| Browser         | Keywords to Search         |
|----------------|----------------------------|
| Firefox        | "Firefox Portable"         |
| Chromium       | "Chromium Portable ZIP"    |
| Brave          | "Brave Portable"           |
| Vivaldi        | "Vivaldi Portable ZIP"     |
| Opera          | "Opera Portable"           |
| Iron Browser   | "SRWare Iron Portable"     |
| K-Meleon       | "K-Meleon Portable"        |

> ❗ Avoid wrappers (like `.paf.exe`) if possible — instead, use standalone `.exe` files inside the unzipped folder.

---

## 🚀 How to Add and Launch a Browser

1. Go to the **Browser Launch** tab in the tzMCP app.
2. Click **“Add Portable Browser...”**
3. Browse to the actual browser executable (`firefox.exe`, `chrome.exe`, etc.)  
   _Avoid launcher/wrapper EXEs — use the one inside the folder._
4. tzMCP will try to detect the browser type automatically.
5. Once added, pick it from the dropdown and click **“Launch Browser”**.

It will:
- Create a temp profile folder
- Start the browser with the proxy preconfigured
- Clean up after you close the app

---

## 🧠 Pro Tips

- You can add as many browsers as you want
- Use the **Incognito/Private Mode** toggle for extra privacy
- If a browser doesn’t launch, check that it isn’t blocked by antivirus or Windows Defender

---

That's it! Using portable browsers with tzMCP keeps your system clean and your sessions secure.
