import contextlib
import io
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from convert_email import convert_email, main, save_markdown


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

    def test_real_msg(self):
        fixture = Path(__file__).resolve().parents[2] / "packages/markitdown/tests/test_files/test_outlook_msg.msg"
        result = convert_email(fixture)
        self.assertIn("**Subject:**", result)
        self.assertIn("## Content", result)


if __name__ == "__main__":
    unittest.main()
