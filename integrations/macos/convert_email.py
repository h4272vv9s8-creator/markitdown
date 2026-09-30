"""Convert .eml and .msg files to Markdown."""

import re
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup
from markitdown import StreamInfo
from markitdown.converters import HtmlConverter, OutlookMsgConverter


def _rows(table):
    return [row for row in table.find_all("tr") if row.find_parent("table") is table]


def _cells(row):
    return row.find_all(["td", "th"], recursive=False)


def _filled(cells):
    return [cell for cell in cells if cell.get_text(strip=True) or cell.find("img")]


def _is_data_table(table) -> bool:
    """Header cells, or a grid of simple cells with a consistent width (3+)."""
    if table.find(["table", "div"]):
        return False
    rows = _rows(table)
    if any(cell.name == "th" for row in rows for cell in _cells(row)):
        return True
    widths = {len(_filled(_cells(row))) for row in rows}
    return len(rows) >= 2 and len(widths) == 1 and widths.pop() >= 3


def clean_email_html(html: str) -> str:
    """Flatten layout tables and drop decoration common in HTML email."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["head", "style", "script", "title"]):
        tag.decompose()
    for tag in soup.select('[style*="display:none"], [style*="display: none"]'):
        tag.decompose()
    for img in soup.find_all("img"):
        tiny = img.get("width") in ("0", "1") or img.get("height") in ("0", "1")
        if tiny or not (img.get("alt") or "").strip():
            img.decompose()
    for link in soup.find_all("a"):
        if not link.get_text(strip=True) and not link.find("img"):
            link.decompose()
    # Innermost tables first, so layout cells no longer contain layout tables.
    for table in reversed(soup.find_all("table")):
        if _is_data_table(table):
            continue
        block = soup.new_tag("div")
        for row in _rows(table):
            cells = _filled(_cells(row))
            label = " ".join(cells[0].get_text(" ", strip=True).split()) if cells else ""
            if len(cells) == 2 and len(label) <= 40 and not cells[0].find(["table", "div", "img"]):
                line = soup.new_tag("p")
                strong = soup.new_tag("strong")
                strong.string = label.rstrip(":") + ":"
                line.append(strong)
                line.append(" ")
                for paragraph in cells[1].find_all("p"):
                    paragraph.insert_after(" ")
                    paragraph.unwrap()
                line.extend(list(cells[1].contents))
                block.append(line)
            else:
                for cell in cells:
                    part = soup.new_tag("div")
                    part.extend(list(cell.contents))
                    block.append(part)
        table.replace_with(block)
    return str(soup)


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
            content = HtmlConverter().convert_string(clean_email_html(content)).markdown
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
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
