# Save as Markdown (Finder and Mail)

Install on macOS from the repository root:

```sh
python3 integrations/macos/install_quick_action.py
```

The installer needs Python 3.10 or newer. If `python3` is the older one that
ships with macOS, it re-runs itself with the newest 3.10+ it finds from
Homebrew, python.org or your `PATH`; if there is none, install one with
`brew install python`.

The installer creates a dedicated virtual environment, installs this checkout
with the Outlook dependency, and registers one service, **Save as Markdown**,
for Finder and Apple Mail. Keep the checkout in place: the service runs its
conversion script and editable MarkItDown package directly. Re-run the
installer after moving it. Earlier Finder-only and Mail-only services are
backed up and replaced.

Use it from the app's **Services** menu or press **Shift-Option-Command-M**:

- **Finder:** select one or more `.eml` or `.msg` files. Markdown is saved
  beside each original.
- **Mail:** select one or more messages. Markdown is saved in `~/Downloads`,
  named after each subject, and the newest file is revealed in Finder.

Existing output is preserved with numbered filenames, such as
`Message (1).md`. Source emails are never modified. Conversion runs locally
without sending email contents to a cloud service. A notification reports how
many emails were saved or failed. The first run in each app asks permission to
read its selection; if it was denied, allow it under System Settings → Privacy
& Security → Automation. If the service is hidden or the shortcut clashes,
change it under System Settings → Keyboard → Keyboard Shortcuts → Services.

EML conversion decodes MIME headers and body encodings, prefers the HTML body,
and lists attachment names without extracting them. HTML layout tables are
flattened, label/value rows become `**Label:** value` lines, and tracking
pixels and undescribed images are dropped; tables with header cells or a
consistent grid of three or more columns are kept as Markdown tables. MSG
conversion uses the existing MarkItDown converter, which extracts From, To,
Subject and plain-text body; it does not extract attachments or render
HTML/RTF-only MSG bodies.

To uninstall, remove `~/Library/Services/Save as Markdown.workflow`.
The dedicated environment and backups reside in
`~/Library/Application Support/MarkItDown Quick Action`.

Run the integration tests from the repository root with the installed runtime:

```sh
"$HOME/Library/Application Support/MarkItDown Quick Action/venv/bin/python" \
  -m unittest discover -s integrations/macos -p 'test_*.py' -v
```
