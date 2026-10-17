# Getting started with tzMCP

Start with the [README](../README.md). It explains the project, current release status, and first capture in short stages, with diagrams.

The intended everyday-user workflow is the VirtualBox appliance. It is still in development, and no published production OVA is supplied by this repository. The native Python/browser setup is for developers and testing.

## Choose your guide

| What you need | Guide |
| --- | --- |
| Understand capture and make a first session | [README](../README.md#your-first-capture) |
| Import the appliance and export files | [Appliance guide](appliance.md) |
| Change which files are saved | [Capture Rules](CONFIG_TAB_GUIDE.md) |
| Install from source or change the code | [Developer and security guide](DEVELOPER_SECURITY_GUIDE.md) |
| Review certificate trust | [CA guide](CA_SETUP_GUIDE.md) |

The current tabs are **Capture Session**, **Capture Rules**, and **Activity**. Start the proxy before launching the capture browser. Select and save at least one file type before capture; none are enabled by default.

HTTPS traffic is decrypted by the proxy. Do not enter private credentials in the capture browser. Read the [usage notice](CYA_NOTICE.md) before capturing content.
