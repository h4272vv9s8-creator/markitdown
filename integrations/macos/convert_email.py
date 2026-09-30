"""Local email conversion entry point for the Finder Quick Action."""

import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

from markitdown import StreamInfo
from markitdown.converters import HtmlConverter, OutlookMsgConverter


def convert_email(path: Path) -> str:
    if path.suffix.lower() == ".msg":
        converter = OutlookMsgConverter()
        with path.open("rb") as stream:
            info = StreamInfo(extension=".msg")
            if not converter.accepts(stream, info):
                raise ValueError("Not a valid Outlook MSG file")
            stream.seek(0)
            return converter.convert(stream, info).markdown
    if path.suffix.lower() != ".eml":
        raise ValueError("Select .eml or .msg files")
    with path.open("rb") as stream:
        message = BytesParser(policy=policy.default).parse(stream)
    if not any(message.get(key) for key in ("From", "To", "Subject", "Date")):
        raise ValueError("No email headers found")
    lines = ["# Email Message", ""]
    for key in ("From", "To", "Cc", "Date", "Subject"):
        if message.get(key):
            value = " ".join(str(message[key]).splitlines())
            lines.append(f"**{key}:** {value}")
    body = message.get_body(preferencelist=("html", "plain"))
    content = ""
    if body is not None:
        content = body.get_content()
        if body.get_content_type() == "text/html":
            content = HtmlConverter().convert_string(content).markdown
    lines.extend(["", "## Content", "", content])
    attachments = [part.get_filename() or "Unnamed attachment" for part in message.iter_attachments()]
    if attachments:
        lines.extend(["", "## Attachments (not extracted)", ""])
        lines.extend("- " + " ".join(name.splitlines()) for name in attachments)
    return "\n".join(lines).strip()


def save_markdown(source: Path, content: str) -> Path:
    """Reserve a fresh filename atomically; never overwrite existing files."""
    index = 0
    while True:
        suffix = "" if index == 0 else f" ({index})"
        output = source.with_name(source.stem + suffix + ".md")
        try:
            stream = output.open("x", encoding="utf-8")
        except FileExistsError:
            index += 1
            continue
        try:
            with stream:
                stream.write(content + "\n")
        except BaseException:
            output.unlink()
            raise
        return output


def main(paths: list[str]) -> int:
    if not paths:
        print("Select one or more .eml or .msg files in Finder.", file=sys.stderr)
        return 1
    failed = False
    for value in paths:
        path = Path(value).absolute()
        try:
            result = save_markdown(path, convert_email(path))
            print(result)
        except Exception as exc:
            failed = True
            print(f"{path.name}: {exc}", file=sys.stderr)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
