"""Install the Save as Markdown service for Finder and Mail using this checkout."""

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

NAME = "Save as Markdown"
SHORTCUT = "@~M"  # Shift-Option-Command-M (uppercase letter = Shift)
APPS = ["com.apple.finder", "com.apple.mail"]
# Earlier versions installed separate Finder and Mail services.
REPLACES = ["Convert Email to Markdown", "Save Email as Markdown"]


def find_python():
    """Newest Python 3.10+ from Homebrew, python.org or PATH (macOS ships 3.9)."""
    names = [f"python3.{minor}" for minor in range(20, 9, -1)]
    folders = ["/opt/homebrew/bin", "/usr/local/bin"]
    folders += [f"/Library/Frameworks/Python.framework/Versions/3.{minor}/bin" for minor in range(20, 9, -1)]
    candidates = [os.path.join(folder, name) for folder in folders for name in names]
    candidates += [found for found in map(shutil.which, names) if found]
    for candidate in candidates:
        if os.access(candidate, os.X_OK):
            check = subprocess.run([candidate, "-c", "import sys; sys.exit(sys.version_info < (3, 10))"])
            if check.returncode == 0:
                return candidate
    return None


def install():
    if sys.platform != "darwin":
        raise SystemExit("Run on macOS.")
    if sys.version_info < (3, 10):
        python = find_python()
        if not python:
            raise SystemExit("Python 3.10 or newer is required. Install one with: brew install python")
        print(f"Python {sys.version.split()[0]} is too old; re-running with {python}", flush=True)
        os.execv(python, [python, os.path.abspath(__file__)] + sys.argv[1:])
    repo = Path(__file__).resolve().parents[2]
    support = Path.home() / "Library/Application Support/MarkItDown Quick Action"
    support.mkdir(parents=True, exist_ok=True)
    environment = support / "venv"
    if not (environment / "bin/python").exists():
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    python = environment / "bin/python"
    subprocess.run([str(python), "-m", "pip", "install", "-e", str(repo / "packages/markitdown") + "[outlook]"], check=True)
    subprocess.run([str(python), "-c", "from markitdown.converters import HtmlConverter, OutlookMsgConverter; import olefile, bs4"], check=True)
    command = "exec " + shlex.join([str(python), str(repo / "integrations/macos/convert_selection.py")])
    action = {
        "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
        "ActionName": "Run Shell Script",
        "ActionParameters": {"COMMAND_STRING": command, "shell": "/bin/zsh", "inputMethod": 1, "source": "", "CheckedForUserDefaultShell": True},
        "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
        "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
        "AMActionVersion": "2.0.3", "AMApplication": ["Automator"],
        "BundleIdentifier": "com.apple.RunShellScript", "Class Name": "RunShellScriptAction",
        "UUID": str(uuid.uuid4()), "InputUUID": str(uuid.uuid4()), "OutputUUID": str(uuid.uuid4()),
    }
    metadata = {
        "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        "inputTypeIdentifier": "com.apple.Automator.nothing",
        "serviceInputTypeIdentifier": "com.apple.Automator.nothing",
        "outputTypeIdentifier": "com.apple.Automator.nothing",
        "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
        "presentationMode": 11, "processesInput": False, "serviceProcessesInput": False,
        "useAutomaticInputType": False,
    }
    workflow = {"AMDocumentVersion": "2", "actions": [{"action": action}], "connectors": {}, "workflowMetaData": metadata}
    info = {"NSServices": [{
        "NSMenuItem": {"default": NAME}, "NSMessage": "runWorkflowAsService",
        "NSKeyEquivalent": {"default": SHORTCUT},
        "NSRequiredContext": [{"NSApplicationIdentifier": app} for app in APPS],
    }]}
    services = Path.home() / "Library/Services"
    staging = support / ("staging-" + str(uuid.uuid4()) + ".workflow")
    contents = staging / "Contents"
    contents.mkdir(parents=True)
    for name, data in [("Info.plist", info), ("document.wflow", workflow)]:
        with (contents / name).open("wb") as stream:
            plistlib.dump(data, stream)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for old in [NAME] + REPLACES:
        existing = services / (old + ".workflow")
        if existing.exists():
            backup = support / f"backup-{stamp}-{old}.workflow"
            shutil.copytree(existing, backup)
            shutil.rmtree(existing)
            print("Previous service backed up to", backup)
    services.mkdir(parents=True, exist_ok=True)
    os.rename(staging, services / (NAME + ".workflow"))
    subprocess.run(["/System/Library/CoreServices/pbs", "-update"], check=True)
    print("Installed:", services / (NAME + ".workflow"))
    print("Use it in Finder or Mail: Services > Save as Markdown, or Shift-Option-Command-M")
    print("Keep this checkout at:", repo)


if __name__ == "__main__":
    install()
