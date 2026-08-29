import io
import unittest
from unittest.mock import MagicMock, patch

from ftp_uploader import (
    FtpUploadError,
    _ensure_remote_dir,
    upload_bytes_to_ftp,
    upload_verification_html_ftp,
    upload_files_to_ftp_batch,
)


class TestFtpUploader(unittest.TestCase):
    def test_upload_bytes_to_ftp_requires_host_and_user(self):
        with self.assertRaises(FtpUploadError):
            upload_bytes_to_ftp(b"<html></html>", "v/test.html", ftp_host="", ftp_user="", ftp_password="")

    @patch("shutil.which", return_value=None)
    @patch("ftp_uploader._get_ftp_connection")
    def test_upload_bytes_to_ftp_success(self, mock_get_conn, mock_which):
        mock_ftp = MagicMock()
        mock_ftp.pwd.return_value = "/"
        mock_get_conn.return_value = mock_ftp

        res = upload_bytes_to_ftp(
            data=b"<!DOCTYPE html><html><body>Test</body></html>",
            remote_path="v/token123.html",
            ftp_host="ftp.sss.sk",
            ftp_user="espeleo_ftp",
            ftp_password="secretpassword",
            ftp_base_dir="sub/ecp",
        )

        mock_get_conn.assert_called_once_with(
            host="ftp.sss.sk",
            port=21,
            user="espeleo_ftp",
            password="secretpassword",
            use_tls=False,
            timeout=30,
        )
        self.assertIn("token123.html", res)
        mock_ftp.storbinary.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch("ftp_uploader.upload_bytes_to_ftp")
    def test_upload_verification_html_ftp_reads_secrets(self, mock_upload):
        mock_upload.return_value = "sub/ecp/v/token123.html"
        secrets_dict = {
            "ftp_host": "ftp.sss.sk",
            "ftp_user": "sss_user",
            "ftp_password": "pass123",
            "ftp_port": "2121",
            "ftp_base_dir": "sub/ecp",
            "ftp_use_tls": "true",
        }

        res = upload_verification_html_ftp(
            blob_name="v/token123.html",
            content_bytes=b"<h1>Verified</h1>",
            get_secret=secrets_dict.get,
        )

        self.assertEqual(res, "sub/ecp/v/token123.html")
        mock_upload.assert_called_once_with(
            data=b"<h1>Verified</h1>",
            remote_path="v/token123.html",
            ftp_host="ftp.sss.sk",
            ftp_user="sss_user",
            ftp_password="pass123",
            ftp_port=2121,
            ftp_base_dir="sub/ecp",
            use_tls=True,
        )

    def test_ensure_remote_dir_creates_missing_folders(self):
        mock_ftp = MagicMock()
        mock_ftp.pwd.return_value = "/"

        calls = []
        def mock_cwd(path):
            if path == "/":
                return
            if path not in calls:
                calls.append(path)
                raise Exception("Directory not found")
        mock_ftp.cwd.side_effect = mock_cwd

        _ensure_remote_dir(mock_ftp, "sub/ecp/v")
        mock_ftp.mkd.assert_any_call("sub")
        mock_ftp.mkd.assert_any_call("ecp")
        mock_ftp.mkd.assert_any_call("v")

    @patch("shutil.which", return_value=None)
    @patch("ftp_uploader._get_ftp_connection")
    def test_upload_files_to_ftp_batch(self, mock_get_conn, mock_which):
        mock_ftp = MagicMock()
        mock_ftp.pwd.return_value = "/"
        mock_get_conn.return_value = mock_ftp

        secrets = {
            "ftp_host": "sss.sk",
            "ftp_user": "automat.sss.sk",
            "ftp_password": "sec",
        }

        files = [
            ("v/cards/abc.jpg", b"jpegdata"),
            ("v/cards/abc.pdf", b"pdfdata"),
            ("v/token.html", b"htmldata"),
        ]

        res = upload_files_to_ftp_batch(files, secrets.get)
        self.assertEqual(len(res), 3)
        self.assertEqual(mock_ftp.storbinary.call_count, 3)
        mock_ftp.quit.assert_called_once()

    @patch("ftp_uploader._upload_single_file_curl", return_value="v/token.html")
    def test_upload_files_to_ftp_batch_curl(self, mock_curl):
        secrets = {
            "ftp_host": "sss.sk",
            "ftp_user": "automat.sss.sk",
            "ftp_password": "sec",
        }
        files = [("v/token.html", b"htmldata")]
        res = upload_files_to_ftp_batch(files, secrets.get)
        self.assertEqual(res, ["v/token.html"])
        mock_curl.assert_called_once()


if __name__ == "__main__":
    unittest.main()
