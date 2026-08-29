# ftp_uploader.py
"""FTP and FTPS uploader module for publishing eCP assets (e.g. verification HTML pages) to webhosting."""

from ftplib import FTP, FTP_TLS
import io
import os
from pathlib import PurePosixPath
import shutil
import socket
import subprocess
import time
from typing import Callable


class FtpUploadError(RuntimeError):
    """Exception raised when FTP upload fails."""
    pass


def _upload_single_file_curl(
    data: bytes,
    remote_path: str,
    ftp_host: str,
    ftp_user: str,
    ftp_password: str,
    ftp_port: int = 21,
    ftp_base_dir: str = "",
    use_tls: bool = False,
    timeout: int = 20,
) -> str:
    """Fast, robust upload using curl."""
    target_full_path = str(PurePosixPath(ftp_base_dir) / PurePosixPath(remote_path)).lstrip("/")
    proto = "ftps" if use_tls else "ftp"
    url = f"{proto}://{ftp_host}:{ftp_port}/{target_full_path}"

    cmd = [
        "curl",
        "-s",
        "--ftp-create-dirs",
        "-u",
        f"{ftp_user}:{ftp_password}",
        "-T",
        "-",
        url,
    ]
    if use_tls:
        cmd.extend(["--ssl-reqd", "-k"])

    proc = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="ignore").strip()
        raise FtpUploadError(f"curl FTP upload failed with exit code {proc.returncode}: {err_msg}")

    return target_full_path


def _get_ftp_connection(
    host: str,
    port: int = 21,
    user: str = "",
    password: str = "",
    use_tls: bool = False,
    timeout: int = 20,
    max_retries: int = 3,
) -> FTP:
    """Creates and returns an authenticated FTP or FTP_TLS connection with retry logic."""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            try:
                resolved_host = socket.gethostbyname(host)
            except Exception:
                resolved_host = host

            if use_tls:
                ftp = FTP_TLS(encoding="latin-1")
            else:
                ftp = FTP(encoding="latin-1")

            ftp.connect(host=resolved_host, port=port, timeout=timeout)
            if use_tls and isinstance(ftp, FTP_TLS):
                ftp.auth()
                ftp.prot_p()

            ftp.login(user=user, passwd=password)
            ftp.set_pasv(True)
            return ftp
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.5)

    raise FtpUploadError(f"FTP connection failed after {max_retries} attempts: {last_err}") from last_err


def _ensure_remote_dir(ftp: FTP, remote_dir: str) -> None:
    """Ensures nested remote directories exist by traversing and creating them if needed."""
    clean_path = PurePosixPath(remote_dir)
    parts = clean_path.parts
    if not parts or parts == ('/',):
        return

    original_cwd = ftp.pwd()
    try:
        if clean_path.is_absolute():
            ftp.cwd('/')

        for part in parts:
            if part in ('/', ''):
                continue
            try:
                ftp.cwd(part)
            except Exception:
                try:
                    ftp.mkd(part)
                    ftp.cwd(part)
                except Exception as mkd_err:
                    try:
                        ftp.cwd(part)
                    except Exception:
                        raise FtpUploadError(f"Failed to create/navigate remote FTP directory '{part}': {mkd_err}")
    finally:
        try:
            ftp.cwd(original_cwd)
        except Exception:
            pass


def upload_bytes_to_ftp(
    data: bytes,
    remote_path: str,
    ftp_host: str,
    ftp_user: str,
    ftp_password: str,
    ftp_port: int = 21,
    ftp_base_dir: str = "",
    use_tls: bool = False,
    timeout: int = 30,
) -> str:
    """Uploads in-memory bytes to a remote path via FTP/FTPS."""
    if not ftp_host or not ftp_user:
        raise FtpUploadError("FTP host and user must be configured for FTP upload.")

    if shutil.which("curl"):
        try:
            return _upload_single_file_curl(
                data=data,
                remote_path=remote_path,
                ftp_host=ftp_host,
                ftp_user=ftp_user,
                ftp_password=ftp_password,
                ftp_port=ftp_port,
                ftp_base_dir=ftp_base_dir,
                use_tls=use_tls,
                timeout=timeout,
            )
        except Exception as e:
            pass

    target_full_path = PurePosixPath(ftp_base_dir) / PurePosixPath(remote_path)
    remote_dir = str(target_full_path.parent)
    remote_filename = target_full_path.name

    ftp = None
    try:
        ftp = _get_ftp_connection(
            host=ftp_host,
            port=ftp_port,
            user=ftp_user,
            password=ftp_password,
            use_tls=use_tls,
            timeout=timeout,
        )

        _ensure_remote_dir(ftp, remote_dir)

        target_file_path = f"{remote_dir.rstrip('/')}/{remote_filename}" if remote_dir not in ('', '.') else remote_filename
        bio = io.BytesIO(data)
        ftp.storbinary(f"STOR {target_file_path}", bio)
        return target_file_path

    except Exception as e:
        if isinstance(e, FtpUploadError):
            raise
        raise FtpUploadError(f"FTP upload failed for '{remote_path}': {e}") from e
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                try:
                    ftp.close()
                except Exception:
                    pass


def upload_verification_html_ftp(
    blob_name: str,
    content_bytes: bytes,
    get_secret: Callable[[str], str | None],
) -> str:
    """Helper function called when uploading a single verification HTML file via FTP."""
    ftp_host = (get_secret("ftp_host") or "").strip()
    ftp_user = (get_secret("ftp_user") or "").strip()
    ftp_password = get_secret("ftp_password") or ""
    ftp_port_str = (get_secret("ftp_port") or "21").strip()
    ftp_base_dir = (get_secret("ftp_base_dir") or "").strip()
    ftp_use_tls_str = (get_secret("ftp_use_tls") or "false").strip().lower()

    try:
        ftp_port = int(ftp_port_str)
    except ValueError:
        ftp_port = 21

    use_tls = ftp_use_tls_str in ("1", "true", "yes")

    return upload_bytes_to_ftp(
        data=content_bytes,
        remote_path=blob_name,
        ftp_host=ftp_host,
        ftp_user=ftp_user,
        ftp_password=ftp_password,
        ftp_port=ftp_port,
        ftp_base_dir=ftp_base_dir,
        use_tls=use_tls,
    )


def upload_files_to_ftp_batch(
    files: list[tuple[str, bytes]],
    get_secret: Callable[[str], str | None],
) -> list[str]:
    """Uploads multiple files using the most efficient FTP mechanism."""
    ftp_host = (get_secret("ftp_host") or "").strip()
    ftp_user = (get_secret("ftp_user") or "").strip()
    ftp_password = get_secret("ftp_password") or ""
    ftp_port_str = (get_secret("ftp_port") or "21").strip()
    ftp_base_dir = (get_secret("ftp_base_dir") or "").strip()
    ftp_use_tls_str = (get_secret("ftp_use_tls") or "false").strip().lower()

    if not ftp_host or not ftp_user:
        raise FtpUploadError("FTP host and user must be configured for FTP upload.")

    try:
        ftp_port = int(ftp_port_str)
    except ValueError:
        ftp_port = 21

    use_tls = ftp_use_tls_str in ("1", "true", "yes")

    results = []
    if shutil.which("curl"):
        for remote_path, data in files:
            res = _upload_single_file_curl(
                data=data,
                remote_path=remote_path,
                ftp_host=ftp_host,
                ftp_user=ftp_user,
                ftp_password=ftp_password,
                ftp_port=ftp_port,
                ftp_base_dir=ftp_base_dir,
                use_tls=use_tls,
            )
            results.append(res)
        return results

    ftp = None
    try:
        ftp = _get_ftp_connection(
            host=ftp_host,
            port=ftp_port,
            user=ftp_user,
            password=ftp_password,
            use_tls=use_tls,
            timeout=30,
        )

        for remote_path, data in files:
            target_full_path = PurePosixPath(ftp_base_dir) / PurePosixPath(remote_path)
            remote_dir = str(target_full_path.parent)
            remote_filename = target_full_path.name

            _ensure_remote_dir(ftp, remote_dir)

            target_file_path = f"{remote_dir.rstrip('/')}/{remote_filename}" if remote_dir not in ('', '.') else remote_filename
            bio = io.BytesIO(data)
            ftp.storbinary(f"STOR {target_file_path}", bio)
            results.append(target_file_path)

        return results
    except Exception as e:
        if isinstance(e, FtpUploadError):
            raise
        raise FtpUploadError(f"Batch FTP upload failed: {e}") from e
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                try:
                    ftp.close()
                except Exception:
                    pass
