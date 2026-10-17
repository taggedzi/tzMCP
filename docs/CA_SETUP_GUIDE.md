# Certificates and HTTPS capture

A certificate authority (CA) can issue certificates a browser trusts. tzMCP uses mitmproxy's CA so the capture browser can accept HTTPS connections through the proxy. This lets the proxy inspect plaintext traffic, including any credentials entered during the session.

## Appliance users

The appliance prepares this automatically:

1. Start the proxy in **Capture Session**.
2. Select **Launch Firefox** to use the managed profile.

The CA is specific to the VM. Only its public certificate is imported into the managed Firefox profile. The private key remains in the guest. The normal workflow does not add trust to the Windows host or the guest system certificate store.

If managed Firefox reports certificate errors, stop and inspect **Activity**. Do not fix an appliance problem by installing certificates on your host. See the [appliance guide](appliance.md).

## Native developer tests

Native browser adapters differ from managed appliance Firefox and do not provide the same trust setup. Use a dedicated test profile and verify which mitmproxy configuration directory supplied its CA. If needed, import only the public CA certificate into that profile's authorities store and remove that trust when testing is complete. Do not import a private key or distribute the CA directory.

See [native browser development](DEVELOPER_SECURITY_GUIDE.md#native-browser-development) and the [security model](DEVELOPER_SECURITY_GUIDE.md#security-model-and-trust-boundaries) for implementation details and limits. Never enter personal account credentials in a capture session.
