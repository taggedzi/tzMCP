# Capture Rules guide

Use **Capture Rules** to choose which response files tzMCP saves. Save changes before starting a session. For the full workflow, see the [README](../README.md#your-first-capture).

## Start with a small test

1. Select **Image**, then select **Save Configuration**.
2. Start a session and check **Activity** for saved/skipped messages.

No MIME groups are selected by default, so a new configuration saves nothing until you select one. MIME means file type.

## File categories

| Group | Intended content |
| --- | --- |
| Image | Supported image types |
| Video | Supported video responses; segments are not assembled |
| Audio | Supported audio files |
| Text | Supported text, including HTML, CSS, and JavaScript |
| Document | Listed PDF, Office, and ebook types |
| Executable | Program/script types; potentially harmful, leave off for normal capture |

Types are selected from a maintained list. The detector checks known URL extensions before inspecting bytes. A selected category is not proof that a file is safe or correctly labeled.

## File size and image dimensions

File size uses bytes. The default range is **10,240 to 157,286,400 bytes** (10 KiB to 150 MiB), including both endpoints. Lower the minimum to keep smaller files.

Image dimensions use pixels. Defaults require width and height each between **301 and 12,000**. For a test that includes thumbnails, lower both minimums before your next session. Dimension checks are not a general image safety validator.

## Domains

The **Whitelist** allows saving only from matching domains. Empty means no domain restriction. The **Blacklist** skips matching sources even when the whitelist permits them.

Enter a hostname such as `example.com`, one per line. It matches that domain and its subdomains. Some pages load media from a separate content-delivery domain; check Activity when an expected file is skipped.

Advanced entries can be Python regular expressions, not shell-style wildcards. Prefer bare hostnames unless you need a pattern. These lists control saving, not which websites the browser can visit.

## Storage and connection

**Proxy Port** defaults to `8888`. Change it only while stopped, then start a new session. The managed browser uses the configured port automatically.

GUI sessions save into their own capture directory. The **Save Directory** field is used by standalone CLI capture and is overridden for GUI sessions. It does not choose the Windows export folder; choose that during appliance setup.

## Logging and duplicate files

**Log to File** enables diagnostic files; **INFO** is a useful normal log level. **DEBUG** is more detailed. Logs can contain browsing information; review them before sharing.

Deduplication compares content fingerprints, not filenames. It avoids another saved copy after a matching response arrives; it does not stop the browser downloading the response. Without **Persistent Deduplication**, fingerprints last for one proxy run. With it, SQLite remembers them across runs, so content saved in an earlier session may be absent from a later export.

## Reload and cleanup

Appliance rules are copied at session start. **Auto Reload Config** does not update a running appliance capture. Restart for changed rules. Normal native snapshot launch paths also have reload limitations documented in the [technical reference](DEVELOPER_SECURITY_GUIDE.md#snapshots-and-reload-behavior).

**Clean Old Logs Now** and **Clean Old Profiles Now** remove eligible old global diagnostic files/native profiles. They do not export or clear completed capture sessions. Keep needed evidence and private data in mind before any cleanup.

For YAML defaults, CLI flags, the dimension-enable caveat, and implementation details, use the [configuration reference](DEVELOPER_SECURITY_GUIDE.md#configuration-reference).
