# 🚫 Why tzMCP Does Not Use a System-Wide Proxy

`tzMCP` is designed to **avoid setting a system-wide proxy** on your computer. This choice is intentional — and it's all about **control, safety, and privacy**.

---

## 🔍 What is a System-Wide Proxy?

A **system-wide proxy** routes all your internet traffic through a tool like tzMCP — including:
- Web browsers
- System updates
- Background apps
- Games
- Cloud services

This might sound powerful, but it comes with serious downsides.

---

## ⚠️ Why It's a Bad Fit for tzMCP

### 1. 🔒 Security Risk

If tzMCP sets a global proxy:
- Apps that were never meant to be inspected (e.g., password managers, OS updaters) would route through it
- Those apps might break or leak sensitive data
- If the mitmproxy certificate is installed, you could **accidentally intercept private credentials**

> **tzMCP is designed to inspect only the traffic you choose.**

---

### 2. 😵‍💫 Unpredictable Behavior

Some apps and services:
- Ignore the proxy
- Break silently
- Prompt for weird logins
- Crash

Debugging these issues can be hard — and confusing for new users.

---

### 3. ⚙️ OS Settings Mess

Setting a system-wide proxy:
- Requires admin rights
- Modifies your operating system settings
- Can persist even after tzMCP quits or crashes
- Might affect other user accounts

tzMCP never touches your system configuration — by design.

---

## ✅ Our Approach: Scoped Proxying

Instead of applying a global proxy, tzMCP:
- **Launches portable browsers** with pre-set proxy rules
- Applies the proxy to **just that browser session**
- Deletes the browser profile after use (optional)
- Leaves your OS, default browser, and other apps untouched

This is **cleaner, safer, and easier to undo**.

---

## 🧠 Summary

| Feature                  | System-Wide Proxy ❌ | tzMCP Local Proxy ✅ |
|--------------------------|----------------------|----------------------|
| Affects all apps         | Yes                  | No                   |
| Requires admin rights    | Often                | No                   |
| Breaks system services   | Possibly             | Never                |
| Easy to reset            | No                   | Yes                  |
| Safer for beginners      | No                   | Yes                  |

---

By avoiding system-wide settings, tzMCP stays **user-friendly and non-invasive** — giving you all the power of media capture, with none of the side effects.

