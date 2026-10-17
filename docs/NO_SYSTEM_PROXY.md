# Why capture uses a local browser proxy

A system proxy can route supported applications through a shared proxy setting. That can involve unrelated background traffic and affect normal browsing.

tzMCP instead starts its capture listener on `127.0.0.1` and configures the capture browser. This loopback address refers to the computer running the proxy; inside the appliance, that computer is the guest VM.

## Appliance boundary

The standard appliance workflow does not configure the host browser, Windows proxy, or host certificate store. Managed Firefox uses its own profile and CA trust. Shared clipboard, drag and drop, USB passthrough, and VirtualBox remote desktop are disabled by setup.

The VM still has outbound networking. Capture rules decide which responses are saved; they do not restrict browser navigation or guarantee that only intended traffic passes through the proxy. Other local processes can also connect to its loopback listener.

## Native development

Native browser adapters pass browser-specific launch settings rather than changing the system proxy. Their profile and certificate behavior varies. Do not infer that a portable browser is a security sandbox or that local proxying makes downloads safe.

See the [boundary diagram](../README.md#how-the-vm-separates-capture-from-your-computer) and [technical security model](DEVELOPER_SECURITY_GUIDE.md#security-model-and-trust-boundaries).
