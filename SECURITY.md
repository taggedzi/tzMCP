# Security policy

tzMCP is alpha software maintained by one developer with limited time. Security reports and fixes are handled on a best-effort basis. There is no guaranteed acknowledgment, response, investigation, fix, or release timeline, and some reports may not receive a response. This project does not provide continuous security monitoring or incident response services.

## Versions considered for fixes

Security work focuses on the current `main` branch and the latest release, when one exists. Older versions, development snapshots, and appliance builds are not guaranteed fixes or backports. This scope is not a promise that any version is free of vulnerabilities or will receive a fix.

## Report a vulnerability privately

Email [taggedzi.mpc@gmail.com](mailto:taggedzi.mpc@gmail.com) with a subject such as `tzMCP security report`.

Include what you know:

- Affected version or commit and, if applicable, appliance build and host/guest environment.
- The affected component, likely impact, and any relevant code location.
- Minimal reproduction steps or a proof of concept using synthetic data.
- Any workaround or suggested fix.

Do not open a public issue or pull request containing sensitive exploit details before private coordination. Never send live credentials, cookies, CA private keys, browser profiles, private capture archives, or another person's traffic. Email is not a secure upload channel for secrets; describe the issue using sanitized examples.

Please allow time for review and avoid repeated follow-ups. A lack of response does not mean a report has been assessed or the problem is safe. If you need to coordinate a disclosure date, propose it in your report; the maintainer cannot promise to meet it. There is no fixed embargo period or requirement to wait indefinitely for a response. Before publishing, consider the risk to users and remove personal data and secrets.

## Safe testing and use

Test only systems and traffic you own or have explicit permission to test. Do not access other people's data, disrupt services, or run destructive tests against live systems.

tzMCP inspects HTTPS traffic and saves untrusted content. Avoid sensitive accounts in the capture browser, treat captured files and exports as untrusted, and review the [usage and safety guidance](README.md#before-you-begin). If a reported issue puts your data or system at risk, stop the affected workflow until you have a suitable mitigation; do not rely on an immediate project response.
