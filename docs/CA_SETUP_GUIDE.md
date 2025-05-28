# 🔐 Setting up the mitmproxy Certificate Authority (CA)

When you first use `tzMCP`, it works by acting like a “middleman” between your browser and the websites you visit. To do that safely, it uses something called a **Certificate Authority (CA)** — like a special ID card that lets it create secure (HTTPS) connections.

But here's the catch:

## ⚠️ Most browsers don’t trust mitmproxy’s CA by default
That means you’ll see errors like:
- “Your connection is not private”
- “This site is not secure”
- “SEC_ERROR_UNKNOWN_ISSUER”

To fix this, you need to **install mitmproxy’s CA certificate** into your browser or operating system. This tells your computer: “Hey, I trust this tool. Let it show me HTTPS websites without freaking out.”

---

## 🧭 What You Need to Do

1. Launch the proxy and visit:  
   👉 **[http://mitm.it](http://mitm.it)**  
   (This only works when the proxy is running.)

2. You’ll see a page that looks like this:

   > 📥 Download mitmproxy certificate for:  
   > Windows, macOS, Linux, Android, iOS, etc.

3. Click the one that matches your system or browser.
4. Follow the instructions to install the certificate.
5. Once installed, reload any websites that were giving security warnings.

---

## 📘 Need Help?

For more details and advanced steps, check out mitmproxy's official guide:  
👉 [docs.mitmproxy.org/stable/concepts/certificates](https://docs.mitmproxy.org/stable/concepts/certificates/)

It explains:
- How the CA works
- Where to install it (macOS, Firefox, Android, etc.)
- How to uninstall it later if needed

---

## 🛡️ Is it safe?

Yes — **if you only use this tool for yourself**. You are creating a trusted connection for your own computer to inspect your own traffic. But you should **never install someone else’s CA** unless you 100% trust them.
