# ⚠️ Legal & Ethical Notice

By using this project (`tzMCP` - Taggedz Media Capture Proxy), you agree to the following terms:

---

## 🔍 Nature of This Tool

- `tzMCP` operates as a **local capture proxy** using [mitmproxy](https://mitmproxy.org/). The capture browser is configured to send traffic through it.
- For HTTPS capture, the browser trusts the proxy's CA certificate. The proxy terminates the browser's TLS connection and creates a separate connection to the website, allowing it to inspect decrypted responses.
- It selectively saves response bodies received through the proxy. Capture filters do not make those files safe or grant permission to reuse them.
- Do not enter passwords, payment details, recovery codes, or other sensitive information in a capture session. See the [security guide](DEVELOPER_SECURITY_GUIDE.md#security-model-and-trust-boundaries) for the trust model and limitations.

---

## 🧑‍⚖️ User Responsibility

By using this software, you acknowledge that:

- You are solely responsible for how you use this tool.
- You must only use tzMCP on systems and networks **you own or are explicitly authorized to access**.
- You must only capture media that you **have the legal right to download, store, or analyze**.
- You agree not to use this tool for:
  - Spying on others
  - Capturing copyrighted material without permission
  - Circumventing security measures or terms of service

---

## 🙅 Liability Disclaimer

The creator(s) of this project **disclaim all liability** for any misuse, damage, or legal issues arising from the use of this tool.

This project is provided **as-is**, for **educational**, **development**, and **ethical research** purposes only.

---

## 📜 Summary

> You are responsible for your actions.  
> This tool does not break encryption — it captures traffic the browser already sends.  
> Use it legally. Use it ethically.
