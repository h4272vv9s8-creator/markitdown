import contextlib
import io
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from convert_email import clean_email_html, convert_email, main, save_markdown
from convert_selection import convert, safe_name
from markitdown.converters import HtmlConverter


def html_to_markdown(html):
    return HtmlConverter().convert_string(clean_email_html(html)).markdown


class EmailQuickActionTests(unittest.TestCase):
    def test_mime_html_headers_and_attachment(self):
        message = EmailMessage()
        message["From"] = "sender@example.com"
        message["Subject"] = "Café review"
        message.set_content("Plain fallback")
        message.add_alternative("<p>Hello <strong>world</strong></p>", subtype="html")
        message.add_attachment(b"private attachment", maintype="application", subtype="octet-stream", filename="notes.bin")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Mail's sample.EML"
            path.write_bytes(message.as_bytes())
            original = path.read_bytes()
            content = convert_email(path)
            self.assertIn("Café review", content)
            self.assertIn("Hello **world**", content)
            self.assertNotIn("Plain fallback", content)
            self.assertIn("notes.bin", content)
            self.assertNotIn("private attachment", content)
            self.assertEqual(path.read_bytes(), original)

    def test_plain_text_charset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_bytes(b'Subject: Test\r\nContent-Type: text/plain; charset=iso-8859-1\r\nContent-Transfer-Encoding: quoted-printable\r\n\r\nCaf=E9')
            self.assertIn("Café", convert_email(path))

    def test_no_overwrite_and_partial_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.eml"
            path.write_text("Subject: Test\n\nBody")
            first = save_markdown(path, "preserve me")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(Path(directory) / "missing.msg"), str(path)]), 1)
            self.assertEqual(first.read_text(), "preserve me\n")
            self.assertIn("Body", (Path(directory) / "message (1).md").read_text())

    def test_layout_tables_flattened(self):
        html = (
            '<table><tr><td><table><tr><td><img src="logo.png" alt="Logo"></td></tr></table></td></tr>'
            '<tr><td></td><td><table><tr><td>Device</td><td>Chrome on Mac</td></tr>'
            '<tr><td>When</td><td>Today</td></tr></table></td><td></td></tr>'
            '<tr><td><a href="https://x.example"><img src="x.png" alt=""></a>'
            '<img src="pixel.gif" width="1" height="1" alt="p"></td></tr></table>'
        )
        message = EmailMessage()
        message["Subject"] = "Alert"
        message.set_content(html, subtype="html")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alert.eml"
            path.write_bytes(message.as_bytes())
            content = convert_email(path)
        self.assertIn("**Device:** Chrome on Mac", content)
        self.assertIn("**When:** Today", content)
        self.assertIn("![Logo](logo.png)", content)
        self.assertNotIn("| --- |", content)
        self.assertNotIn("x.example", content)
        self.assertNotIn("pixel.gif", content)

    def test_data_tables_kept(self):
        header = "<table><tr><th>Item</th><th>Qty</th></tr><tr><td>Widget</td><td>2</td></tr></table>"
        self.assertIn("| Item | Qty |", html_to_markdown(header))
        grid = (
            "<table><tr><td><p>Item</p></td><td>Qty</td><td>Price</td></tr>"
            "<tr><td><p>Widget</p></td><td>2</td><td>$5</td></tr></table>"
        )
        self.assertIn("| Widget | 2 | $5 |", html_to_markdown(grid))
        nested = f"<table><tr><td>{grid}</td></tr><tr><td>Footer</td></tr></table>"
        result = html_to_markdown(nested)
        self.assertIn("| Widget | 2 | $5 |", result)
        self.assertIn("Footer", result)

    def test_outlook_paragraph_labels(self):
        html = "<table><tr><td><p>Device</p></td><td><p>Chrome</p></td></tr></table>"
        self.assertIn("**Device:** Chrome", html_to_markdown(html))

    def test_safe_name(self):
        self.assertEqual(safe_name("Re: Q3/Q4 plan"), "Re  Q3 Q4 plan")
        self.assertEqual(safe_name("../../etc"), "etc")
        self.assertEqual(safe_name(".."), "Email")
        self.assertEqual(safe_name(""), "Email")
        self.assertEqual(len(safe_name("x" * 500)), 120)

    def test_convert_reports_failures_and_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.eml"
            good.write_text("Subject: Hi\n\nBody")
            bad = Path(directory) / "bad.txt"
            bad.write_text("nope")
            anchor = Path(directory) / "out" / "Hello.eml"
            anchor.parent.mkdir()
            with contextlib.redirect_stderr(io.StringIO()):
                saved, failed = convert([(bad, bad), (good, anchor)])
            self.assertEqual(saved, [anchor.with_suffix(".md")])
            self.assertEqual(len(failed), 1)
            self.assertIn("bad.txt", failed[0])

    def test_real_msg(self):
        fixture = Path(__file__).resolve().parents[2] / "packages/markitdown/tests/test_files/test_outlook_msg.msg"
        result = convert_email(fixture)
        self.assertIn("**Subject:**", result)
        self.assertIn("## Content", result)


if __name__ == "__main__":
    unittest.main()
