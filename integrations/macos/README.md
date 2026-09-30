# Finder Quick Action

Install on macOS with Python 3.10 or newer from the repository root:

```sh
python3 integrations/macos/install_quick_action.py
```

The installer creates a dedicated virtual environment, installs this checkout
with the Outlook dependency, and registers **Convert Email to Markdown** in
Finder. Keep the checkout in place: the service runs its conversion script and
editable MarkItDown package directly. Re-run the installer after moving it.
An existing service with this name is backed up before replacement.

Select one or more `.eml` or `.msg` files, right-click, and choose **Quick Actions
→ Convert Email to Markdown** (or **Services → Convert Email to Markdown**).
Markdown is saved beside each original. Existing output is preserved with
numbered filenames, such as `Message (1).md`. Source emails are never modified.
Conversion runs locally without sending email contents to a cloud service.

The service accepts Finder files because MSG file type associations vary between
Macs; selecting an unsupported file reports an error. Other selected emails are
still processed. Finder/Automator displays conversion failures. If the action is
hidden, enable it in System Settings under Keyboard → Keyboard Shortcuts →
Services, or the Finder extensions/Quick Actions settings for your macOS version.

EML conversion decodes MIME headers and body encodings, prefers the HTML body,
and lists attachment names without extracting them. MSG conversion uses the
existing MarkItDown converter, which extracts From, To, Subject and plain-text
body; it does not extract attachments or render HTML/RTF-only MSG bodies.

To uninstall, remove `~/Library/Services/Convert Email to Markdown.workflow`.
The dedicated environment and backups reside in
`~/Library/Application Support/MarkItDown Quick Action`.

Run the integration tests from the repository root with the installed runtime:

```sh
"$HOME/Library/Application Support/MarkItDown Quick Action/venv/bin/python" \
  -m unittest discover -s integrations/macos -p 'test_*.py' -v
```
