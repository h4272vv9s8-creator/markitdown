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


def install():
    if sys.platform != "darwin" or sys.version_info < (3, 10):
        raise SystemExit("Run on macOS with Python 3.10 or newer.")
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
