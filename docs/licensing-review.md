# tzMCP licensing and appliance distribution review

Review date: October 25, 2026.

**Recommendation:** license the original tzMCP code under standard MIT terms, and describe the VM as a distribution of separately licensed components. Do not describe the entire VM as MIT-licensed. The inspected build is not yet demonstrably ready for compliant public distribution.

This is a technical compliance assessment, not a legal opinion or a certification. It identifies concrete gaps and a practical release process. Interpretation of the Ubuntu and Firefox branding policies deserves focused confirmation from their owners or qualified counsel.

## Scope and confidence

Inspected the working tree's package metadata, dependency list, installed Windows development-environment metadata and selected bundled license texts, Packer configuration, provisioning and cleanup scripts, Windows setup, release scripts/workflows, contributor guidance, and usage notice. Used the code graph to inspect Firefox profile creation. Checked primary license and publisher-policy sources linked below.

This did **not** inspect a completed OVA, inventory its filesystem, audit every dependency's embedded code, establish the provenance of every project file, or inspect published GitHub releases. Existing unrelated working-tree edits were left intact. Only this advisory report was added.

The installed Windows venv is evidence about dependencies, **not the VM's bill of materials**. It even has Brotli 1.2.0 while the build override requests 1.2.1. Linux selects different packages, notably `mitmproxy-linux`. Exact release contents remain to be established.

## 1. License your own code

`pyproject.toml` declares `license = "MIT"`; README and CONTRIBUTING link to MIT. However, the tracked root `LICENSE` is **zero bytes**. Populate it with the complete standard MIT text and an accurate copyright notice. The repository identifies Matthew Craig as author and records the LICENSE file in 2025; `Copyright (c) 2025-2026 Matthew Craig` is a reasonable proposed notice if those are the correct ownership dates. Preserve other owners' notices.

MIT permits commercial use, modification, redistribution, and sale subject to preservation of its notice. It does not require downstream users to publish their modifications. Use the unmodified [standard MIT license](https://opensource.org/license/mit).

Keep the package's MIT SPDX identifier. Explicitly declare `license-files = ["LICENSE"]` in project metadata, then inspect a freshly built wheel and source distribution to confirm the complete text is included. Add other applicable notice files as they become real artifacts, without implying their components have become MIT.

Recommended README wording:

> Original tzMCP code is licensed under the MIT License. The appliance includes third-party software under its own licenses. See the release's third-party notices and source-code information. Those licenses continue to govern the respective components.

`docs/CYA_NOTICE.md` currently begins with agreement language and limits the software to educational, development, and ethical research purposes “only.” Rewrite that as usage/safety guidance, not additional license conditions. State that it does not narrow MIT or third-party license rights. Keep accurate reminders about authorization and applicable law. A disclaimer does not provide blanket immunity from liability.

The current CONTRIBUTING statement that contributions are offered under MIT is useful. Confirm rights to copied snippets, images, documentation, fonts, and other imported material before applying MIT to them. Git history identifying authors does not prove ownership. No comprehensive provenance audit was performed.

## 2. The appliance is a collection of licenses

Independent programs sharing a VM do not automatically become one GPL program. Linking or copying protected code into another program needs separate analysis. The [GNU licensing FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation) explains this distinction.

Based on the inspected design, there is no identified reason to abandon MIT for original tzMCP code. There **are** obligations for the other components distributed with it.

| Component group | Evidence in this project | Required treatment / unresolved work |
| --- | --- | --- |
| tzMCP code and original build scripts | `pyproject.toml`, repository | Complete MIT grant; verify ownership and package inclusion. |
| mitmproxy 12.3.0 | Dependency metadata and installed LICENSE | MIT; retain its notices and separately review its dependencies and vendored code. [Upstream license](https://github.com/mitmproxy/mitmproxy/blob/main/LICENSE). |
| Typical Python dependencies | Installed metadata identifies requests/watchdog as Apache-2.0, psutil as BSD-3-Clause, PyYAML/filetype as MIT | Retain exact notices and license texts. Apache components also require applicable NOTICE content and notices of modified files. [Apache 2.0, section 4](https://www.apache.org/licenses/LICENSE-2.0). |
| ldap3 2.9.1 and urwid | Installed ldap3 license grants LGPL-3.0-or-later; installed urwid 3.0.5 metadata says LGPL-2.1-only | Preserve GPL/LGPL texts and attribution; meet applicable source and replacement/relinking requirements. Confirm the Linux-resolved versions. |
| certifi and publicsuffix2 data | Installed certifi metadata: MPL-2.0; publicsuffix2: MIT and MPL-2.0 | Preserve the separate data/code notices and provide required covered source. Public-suffix and CA data count as shipped material too. |
| Native Python/Rust binaries | `mitmproxy_rs`, Linux platform package, cryptography, Pillow, compression/QUIC packages | Inspect the actual Linux wheels and embedded libraries. A top-level Python license label is insufficient. Local `mitmproxy_rs` metadata did not declare a license. Resolve from exact-version upstream material. |
| Ubuntu 24.04.4 base and system packages | Packer ISO and apt provisioning | Inventory all installed packages, including inherited OS packages, with exact source-package versions; preserve notices and meet each license. Resolve Ubuntu branding below. |
| Desktop, media tools, fonts, guest integration | Xfce, LightDM, Ristretto, Tumbler, Parole, Mousepad, PulseAudio, GStreamer, DejaVu/Noto, VirtualBox guest packages | These have multiple licenses and dependencies. Include firmware, codecs, artwork, font notices and any reserved-font-name conditions where applicable. Do not infer permission from apt availability alone. |
| Firefox | Official Mozilla APT package | MPL/source obligations plus separate branding/distribution policy. See below. |
| pip and uv | `install-tzmcp.sh` leaves them in `/opt/tzmcp/venv` | They are distributed components despite their installation role; include vendored dependency notices. |
| Windows-only dependencies | requirements include pydivert, mitmproxy-windows, python-magic-bin | Assess if distributing a Windows bundle; do not assume these are in the Linux VM. Inspect bundled DLLs/drivers separately. |

Pillow provides a concrete example: its installed LICENSE contains MIT-CMU terms **and** notices for bundled native libraries. Preserve that complete content, not a generic MIT template.

LGPL normally allows separately licensed applications, but its conditions still matter. The installed ldap3 `COPYING.LESSER.txt`, section 4, requires notices and a compliant way to replace/recombine the library, and protects modification/debugging rights. Keeping Python sources and dependencies replaceable is helpful; verify this in the released image. Do not treat ordinary root-owned files as automatically violating LGPL, or weaken the capture account's security. Document how an owner can modify their VM offline or through maintenance access.

MPL applies at the covered-file level; executable distribution requires corresponding covered source availability and directions for obtaining it. It does not require unrelated original tzMCP files to become MPL. See [MPL 2.0 sections 3.1–3.3](https://www.mozilla.org/en-US/MPL/2.0/).

## 3. Two branding questions to resolve before publishing

### Ubuntu

The recipe installs a customized desktop/application system using Ubuntu binaries. Canonical's policy expressly addresses modified VM redistribution and association with Ubuntu trademarks; it also states that component open-source licenses retain their effect. Its described alternative involves trademark removal and recompilation. Therefore, simply changing the VM's name is not a verified resolution. [Canonical policy, sections 2–4](https://ubuntu.com/legal/intellectual-property-policy).

Ask Canonical to confirm the permitted route for this exact recipe: free public tzMCP OVA, official Ubuntu packages, added Xfce/application, changed login/startup configuration, and retained system branding. Record any permission and conditions. This report does not conclude that all customized Ubuntu images are prohibited or that all binaries must legally be rebuilt regardless of their licenses.

If that route is burdensome, evaluate a Debian-based appliance as an engineering alternative; Debian explicitly supports derivatives, though it still requires license and branding compliance. It would be a migration with compatibility testing, not an immediate drop-in fix. [Debian derivatives guidance](https://www.debian.org/derivatives/index.html).

### Firefox

The build installs Mozilla's official binary. `FirefoxSession.create_profile()` creates proxy preferences at runtime in a separate profile; the inspected recipe does not patch Firefox source. This is relevant but not conclusive.

Mozilla's branded-distribution policy restricts alterations, changed defaults, charging, and collection of personal information in connection with distribution. It also calls for the current version. Confirm that a preinstalled appliance with a runtime-managed capture profile falls within the policy, or obtain written permission. Do not infer that MPL alone grants trademark rights. [Mozilla distribution policy](https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/).

A post-install download directly from Mozilla may reduce redistribution scope, but is a product change and should not be presented as an automatic exemption from every relevant term. Preserve updates and Firefox's bundled notices in any chosen arrangement.

## 4. VirtualBox and build tools

The Windows setup finds an existing VirtualBox installation; it does not bundle/install the host program. Guest packages **are** installed in the VM, so inventory their exact Ubuntu package licenses and source versions. Do not substitute the current host VirtualBox license for the license of an older guest package.

The Oracle Extension Pack is distinct from Guest Additions and has separate terms. The inspected recipe does not explicitly install it and disables USB/VRDE in the distributed configuration. Keep it outside the distribution unless separate rights are established; do not tell business users that personal-use terms cover their use. [Oracle download/licensing information](https://www.virtualbox.org/wiki/Downloads?lang=en).

Packer, its plugin, host VirtualBox, and the host sanitation utilities are build tools rather than intended guest contents. Their use does not by itself relicense original output, but their own usage and any redistribution must be permitted. Packer's newer releases use Business Source License terms; assess the exact tool/plugin versions and use. [HashiCorp licensing FAQ](https://www.hashicorp.com/en/license-faq). Check for unintentionally retained installer media or tool binaries in the final VM.

## 5. Recommended release compliance design

This is the proposed maintainer process, not a claim that these artifacts already exist.

| Release artifact | Purpose |
| --- | --- |
| `LICENSE` | Standard MIT text covering the project's original material. |
| `THIRD_PARTY_NOTICES.md` and `licenses/` | Component attribution, exact license texts, applicable NOTICE files, and scope statement. |
| `sbom.spdx.json` or equivalent | Software bill of materials: exact packages, versions, origins, hashes, licenses, and relationships. An SBOM is an inventory, not proof of compliance. |
| `SOURCE_CODE.md` | Map shipped components to exact source archives, patches and build instructions; explain how users obtain them. |
| Versioned source archives | Complete corresponding source required by the shipped licenses, including distribution patches and required build/install scripts. |
| Release manifest and checksums | Bind the OVA, notices, inventory and source bundle to the same release. |

Generate the inventory **from the finished Linux guest**, not just requirements.txt. Record dpkg binary and source-package names, versions and architectures; capture Python resolved distributions, wheel origins/hashes, and package license files. Inspect nested native/Rust dependencies and assets separately. The current build uses moving apt repositories, upgrades pip, and resolves version ranges, so the same recipe can produce different contents.

Preserve `/usr/share/doc/*/copyright`, referenced `/usr/share/common-licenses/` texts, and Python distribution license directories. The inspected cleanup does not explicitly erase these, but the finished-image check must verify them. Add an easy-to-find appliance license/source index, for example `/usr/share/doc/tzmcp/`, and distribute the notices alongside the OVA too.

For GPL binaries, publish matching complete source with equivalent access alongside the download; merely linking an upstream homepage is insufficient. GPLv2 and GPLv3 have different source-delivery options. Avoid a written-offer scheme unless prepared to meet its audience, duration and fulfillment obligations. Recommended design: retain your own release-matched source archive. [GNU FAQ on binary/source distribution](https://www.gnu.org/licenses/gpl-faq.en.html#UnchangedJustBinary).

Collect sources while the exact package versions remain available. For distribution packages, retain source archives and distribution patches, not just an upstream git tag. A wheel or `.deb` is generally not a substitute for its required source. For an unmodified Python package already shipped as full preferred-form source, record that fact and location instead of assuming it is binary-only.

Do not treat a successful license scanner as final approval. Make missing licenses, unexplained binaries, unavailable required source, and unresolved branding terms release blockers. Re-run the process when rebuilding. A user's independent update differs from your publishing a new updated image; every image you distribute needs matching evidence.

## 6. How GitHub fits

GitHub hosts your code and release assets; it does not clear third-party rights or make an entire appliance MIT. A real root LICENSE supports its license detection. Public visibility by itself is not a complete open-source permission grant. [GitHub repository licensing](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

Use a tagged GitHub Release for the OVA, notices, SBOM, checksums and source information. GitHub's automatically generated source ZIP contains the repository at the tag, **not all Ubuntu/Python dependency source**. Attach the additional source bundles or provide durable compliant hosting with clear access instructions. Each release asset must currently be under 2 GiB; partition large source collections into usable archives or use suitable hosting. [GitHub release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

Do not add an appliance EULA that overrides recipients' third-party rights. Recommended release statement:

> The tzMCP application and original project scripts are MIT-licensed. This appliance includes separately licensed third-party software. Their copyright notices, licenses, and source availability information accompany this release and are accessible inside the appliance. No endorsement by the upstream projects is implied.

## Next two actions

1. Complete the repository's MIT setup and reconcile the usage notice, then verify the built package contains the license. This can proceed without changing the appliance platform.
2. Before publishing an OVA, resolve Ubuntu/Firefox distribution terms and build the exact-image inventory, notices and source archive. If a previous image was already distributed, include it in the review rather than assuming a new release fixes earlier obligations.

No application tests were run: this review changes no executable code. No license grant, release publication, upstream contact, or appliance rebuild was performed.
