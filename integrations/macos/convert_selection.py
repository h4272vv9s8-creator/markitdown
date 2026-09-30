"""Convert the emails selected in Finder or Apple Mail to Markdown.

Finder: selected .eml/.msg files are saved as Markdown beside each original.
Mail: selected messages are saved as Markdown in ~/Downloads.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from convert_email import convert_email, save_markdown

FINDER = "com.apple.finder"
MAIL = "com.apple.mail"
DOWNLOADS = Path.home() / "Downloads"
FINDER_SELECTION = """
tell application "Finder" to set picked to selection as alias list
set out to ""
repeat with item_ in picked
    set out to out & POSIX path of item_ & linefeed
end repeat
return out
"""
MAIL_SELECTION = """
JSON.stringify(Application("Mail").selection().map(m => ({subject: m.subject(), source: m.source()})));
"""


def osascript(script: str, language: str = "AppleScript") -> str:
    return subprocess.run(
        ["osascript", "-l", language, "-e", script],
        capture_output=True, text=True, check=True,
    ).stdout


def front_app() -> str:
    front = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
    info = subprocess.run(["lsappinfo", "info", "-only", "bundleid", front], capture_output=True, text=True).stdout
    match = re.search(r'(?:bundleID|"CFBundleIdentifier")="([^"]+)"', info)
    return match.group(1) if match else ""


def safe_name(subject: str) -> str:
    """Filename stem from an untrusted email subject."""
    name = re.sub(r"[/:\\\x00-\x1f]+", " ", subject or "").strip(" .")
    return (name or "Email")[:120]


def notify(message: str) -> None:
    script = f"display notification {json.dumps(message, ensure_ascii=False)} with title \"Save as Markdown\""
    subprocess.run(["osascript", "-e", script], check=False)


def convert(jobs: list[tuple[Path, Path]]) -> tuple[list[Path], list[str]]:
    """Convert each (email file, output anchor) pair; the anchor's stem names the .md."""
    saved, failed = [], []
    for source, anchor in jobs:
        try:
            saved.append(save_markdown(anchor, convert_email(source)))
        except Exception as exc:
            failed.append(f"{anchor.name}: {exc}")
            print(failed[-1], file=sys.stderr)
    return saved, failed


def from_finder() -> tuple[list[Path], list[str]]:
    paths = [Path(line) for line in osascript(FINDER_SELECTION).splitlines() if line]
    return convert([(path, path) for path in paths])


def from_mail() -> tuple[list[Path], list[str]]:
    messages = json.loads(osascript(MAIL_SELECTION, "JavaScript") or "[]")
    with tempfile.TemporaryDirectory() as temp:
        jobs = []
        for index, message in enumerate(messages):
            source = Path(temp) / f"{index}.eml"
            source.write_bytes(message["source"].encode("utf-8", "surrogateescape"))
            jobs.append((source, DOWNLOADS / (safe_name(message["subject"]) + ".eml")))
        return convert(jobs)


def main() -> int:
    app = front_app()
    if app not in (FINDER, MAIL):
        notify("Use this in Finder or Mail.")
        return 1
    try:
        saved, failed = from_finder() if app == FINDER else from_mail()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        notify("Couldn't read the selection. Allow access in System Settings → Privacy & Security → Automation.")
        return 1
    if not saved and not failed:
        notify("Select one or more emails first.")
        return 1
    for path in saved:
        print(path)
    if saved and app == MAIL:
        subprocess.run(["open", "-R", str(saved[-1])], check=False)
    where = " to Downloads" if app == MAIL else ""
    notify(f"Saved {len(saved)}{where}" + (f", {len(failed)} failed" if failed else ""))
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
