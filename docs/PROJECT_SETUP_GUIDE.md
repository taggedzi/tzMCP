# Project setup

For the intended everyday-user installation, use the [appliance guide](appliance.md). The appliance is still in development; no published production OVA is supplied by this repository.

For Python source installation, dependencies, entry points, tests, and platform notes, follow the [development setup](DEVELOPER_SECURITY_GUIDE.md#development-setup). This replaces the older native setup walkthrough.

Native operation is a developer facility and does not provide the VM's host boundary. Use a dedicated test browser and profile. Do not install the proxy CA into your everyday browser or system as a routine setup step.

Live configuration belongs in the [per-user runtime data directory](DEVELOPER_SECURITY_GUIDE.md#runtime-storage), not the checkout's example `config/` folder. The GUI tabs are **Capture Session**, **Capture Rules**, and **Activity**.
