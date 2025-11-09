#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import hashlib, os, re, stat, subprocess, zipfile
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin, unquote
import requests
from bs4 import BeautifulSoup


def _fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def find_downloads_page(session: requests.Session, mod_root_url: str) -> str:
    html = _fetch_html(session, mod_root_url)
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").strip().lower()
        absurl = urljoin(mod_root_url, href)
        if "/mods/" in absurl and "/downloads" in absurl:
            candidates.append(absurl)
        elif text in {"downloads", "files"} and "/mods/" in absurl:
            candidates.append(absurl)
    if candidates:
        candidates.sort(key=len)
        return candidates[0]
    return mod_root_url.rstrip("/") + "/downloads"


def newest_filepage(session: requests.Session, downloads_url: str) -> str:
    html = _fetch_html(session, downloads_url)
    soup = BeautifulSoup(html, "html.parser")
    file_links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(downloads_url, a["href"])
        if re.search(r"/mods/[^/]+/downloads/[^/]+/?$", href) and "upload" not in href:
            file_links.append(href)
    if not file_links:
        raise RuntimeError("No file entries found on the Downloads page.")
    seen, ordered = set(), []
    for u in file_links:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered[0]


def parse_filepage_for_md5_and_start(
    session: requests.Session, filepage_url: str
) -> Tuple[str, Optional[str], Optional[str]]:
    html = _fetch_html(session, filepage_url)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    md5 = None
    m = re.search(r"MD5 Hash\s*([a-fA-F0-9]{32})", text)
    if m:
        md5 = m.group(1).lower()
    suggested = None
    m2 = re.search(r"Filename\s+([^\s]+)", text)
    if m2:
        suggested = m2.group(1)
    start_url = None
    for a in soup.find_all("a", href=True):
        href = urljoin(filepage_url, a["href"])
        if "/downloads/start/" in href:
            start_url = href
            break
    if not start_url:
        raise RuntimeError("Could not find /downloads/start/<id> on the file page.")
    return start_url, md5, suggested


def startpage_to_direct_url(session: requests.Session, start_url: str) -> str:
    html = _fetch_html(session, start_url)
    soup = BeautifulSoup(html, "html.parser")
    a = soup.find("a", href=True)
    if not a:
        raise RuntimeError("No mirror link found on the start page.")
    return urljoin(start_url, a["href"])


def download_with_optional_md5(
    session: requests.Session, url: str, out_path: Path, md5: Optional[str]
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    tmp.rename(out_path)
    if md5:
        h = hashlib.md5()
        with out_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest().lower() != md5.lower():
            raise RuntimeError("MD5 mismatch after download.")


def maybe_extract_and_pick_payload(archive_path: Path) -> Path:
    if archive_path.suffix.lower() != ".zip":
        return archive_path
    preferred_exts = [".pk3", ".pk7", ".wad"]
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        candidates = [
            m for m in members if any(m.lower().endswith(ext) for ext in preferred_exts)
        ]
        if not candidates:
            zf.extractall(archive_path.parent)
            return archive_path

        def sort_key(n: str):
            nlow = n.lower()
            for i, ext in enumerate(preferred_exts):
                if nlow.endswith(ext):
                    return (i, len(nlow))
            return (99, len(nlow))

        candidates.sort(key=sort_key)
        pick = candidates[0]
        zf.extract(pick, archive_path.parent)
        return (archive_path.parent / pick).resolve()


def ensure_mod_payload(
    mod_root_url: str,
    mods_dir: Path,
    force_redownload: bool = False,
    session: Optional[requests.Session] = None,
) -> Path:
    mods_dir.mkdir(parents=True, exist_ok=True)
    close = False
    if session is None:
        session = requests.Session()
        close = True
    try:
        downloads_url = find_downloads_page(session, mod_root_url)
        filepage_url = newest_filepage(session, downloads_url)
        start_url, md5, suggested = parse_filepage_for_md5_and_start(
            session, filepage_url
        )
        direct_url = startpage_to_direct_url(session, start_url)
        server_filename = unquote(direct_url.split("/")[-1])
        local_name = suggested or server_filename
        local_path = (mods_dir / local_name).resolve()
        need = force_redownload or (not local_path.exists())
        if md5 and local_path.exists() and not force_redownload:
            h = hashlib.md5()
            with local_path.open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            need = h.hexdigest().lower() != md5.lower()
        if need:
            download_with_optional_md5(session, direct_url, local_path, md5)
        return maybe_extract_and_pick_payload(local_path)
    finally:
        if close:
            session.close()


def is_executable(p: Path) -> bool:
    try:
        st = p.stat()
    except FileNotFoundError:
        return False
    if os.name == "nt":
        return p.suffix.lower() in {".exe", ".bat", ".cmd"} and p.exists()
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def which(exe_name: str) -> Optional[Path]:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d) / exe_name
        if is_executable(p):
            return p.resolve()
    return None


def launch_gzdoom(
    gzdoom_executable: Path,
    iwad_path: Path,
    mod_files: Iterable[Path],
    *,
    savedir: Path,
    config_path: Path,
    extra_args: Optional[Iterable[str]] = None,
) -> None:
    cmd = [str(gzdoom_executable), "-iwad", str(iwad_path)]
    for f in mod_files:
        cmd += ["-file", str(f)]
    cmd += ["-savedir", str(savedir), "-config", str(config_path)]
    if extra_args:
        cmd += list(extra_args)
    savedir.mkdir(parents=True, exist_ok=True)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            gzdoom_executable.chmod(gzdoom_executable.stat().st_mode | stat.S_IXUSR)
        except Exception:
            pass
    subprocess.Popen(cmd, close_fds=(os.name != "nt"))
