# Connect a capture browser

## Appliance workflow

The appliance manages Firefox, its separate profile, proxy settings, and certificate trust. Your host browser stays outside this workflow.

1. In **Capture Session**, select **Start proxy** and wait for it to be ready.
2. Select **Launch Firefox**.

Select file types and save them in **Capture Rules** before starting. Use **Activity** to check what was saved or skipped. When finished, select **Stop**, then **Export Session**. See the [first-capture walkthrough](../README.md#your-first-capture).

## Native developer workflow

Native operation is for development. In **Capture Session**, **Add...** selects a dedicated portable browser executable. Start the proxy first, select the browser, acknowledge the dedicated-browser notice, and use **Launch safe browser**.

The configured listener is `127.0.0.1:8888` by default. Adapters pass browser-specific proxy/profile settings; compatibility and certificate behavior vary. They do not establish appliance isolation. See the [native workflow and its current GUI limitation](DEVELOPER_SECURITY_GUIDE.md#native-browser-development) before testing.

Avoid changing the system proxy or your everyday browser. Private/incognito mode does not hide traffic from the capture proxy.
