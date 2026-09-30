"""Install the Finder service using this checkout and a dedicated environment."""

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

NAME = "Convert Email to Markdown"


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
    subprocess.run([str(python), "-c", "from markitdown.converters import HtmlConverter, OutlookMsgConverter; import olefile"], check=True)
    command = "exec " + shlex.join([str(python), str(repo / "integrations/macos/convert_email.py")]) + ' "$@"'
    action = {
        "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
        "ActionName": "Run Shell Script",
        "ActionParameters": {"COMMAND_STRING": command, "shell": "/bin/zsh", "inputMethod": 1, "source": "", "CheckedForUserDefaultShell": True},
        "AMAccepts": {"Container": "List", "Optional": False, "Types": ["com.apple.cocoa.string"]},
        "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
        "AMActionVersion": "2.0.3", "AMApplication": ["Automator"],
        "BundleIdentifier": "com.apple.RunShellScript", "Class Name": "RunShellScriptAction",
        "UUID": str(uuid.uuid4()), "InputUUID": str(uuid.uuid4()), "OutputUUID": str(uuid.uuid4()),
    }
    metadata = {
        "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        "applicationBundleID": "com.apple.finder",
        "applicationPath": "/System/Library/CoreServices/Finder.app",
        "serviceApplicationBundleID": "com.apple.finder",
        "serviceApplicationPath": "/System/Library/CoreServices/Finder.app",
        "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
        "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
        "outputTypeIdentifier": "com.apple.Automator.nothing",
        "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
        "presentationMode": 15, "processesInput": False, "serviceProcessesInput": False,
        "useAutomaticInputType": False,
    }
    workflow = {"AMDocumentVersion": "2", "actions": [{"action": action}], "connectors": {}, "workflowMetaData": metadata}
    info = {"NSServices": [{
        "NSMenuItem": {"default": NAME}, "NSMessage": "runWorkflowAsService",
        "NSSendFileTypes": ["public.data"],
        "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
    }]}
    target = Path.home() / "Library/Services" / (NAME + ".workflow")
    staging = support / ("staging-" + str(uuid.uuid4()) + ".workflow")
    contents = staging / "Contents"
    contents.mkdir(parents=True)
    for name, data in [("Info.plist", info), ("document.wflow", workflow)]:
        with (contents / name).open("wb") as stream:
            plistlib.dump(data, stream)
    if target.exists():
        backup = support / ("backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".workflow")
        shutil.copytree(target, backup)
        shutil.rmtree(target)
        print("Previous service backed up to", backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.rename(staging, target)
    subprocess.run(["/System/Library/CoreServices/pbs", "-update"], check=True)
    print("Installed:", target)
    print("Keep this checkout at:", repo)


if __name__ == "__main__":
    install()
