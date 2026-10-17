# Portable browsers for native development

The intended user product uses managed Firefox inside the [VirtualBox appliance](appliance.md). You do not need to download a separate portable browser for that workflow.

Portable browser selection remains available for native developer tests. A portable browser is a separate browser installation you can dedicate to capture. It still executes untrusted web content and does not guarantee privacy or isolation.

## Choose and configure a test browser

1. Obtain a browser from a source you trust and reserve it for capture tests.
2. Use **Add...** in **Capture Session** to select its actual executable rather than an installer or wrapper.

The launcher recognizes browser families by path/name and selects a matching adapter. An adapter being present does not guarantee compatibility with every browser release. Use a dedicated profile and inspect proxy/certificate behavior before testing HTTPS.

Current native adapters can reuse per-browser profile directories until cleanup; they do not provide the appliance's unique managed Firefox profile lifecycle. Read [native browser development](DEVELOPER_SECURITY_GUIDE.md#native-browser-development) for launch details and current limits.

Do not use saved accounts, passwords, payments, or private credentials. Incognito mode does not prevent the proxy from reading HTTPS traffic.
