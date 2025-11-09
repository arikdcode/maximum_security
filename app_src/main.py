#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
import os
import platform
import shutil  # <-- NEW
import stat
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import requests

from mod_launcher import (
    ensure_mod_payload,
    launch_gzdoom,
    is_executable,
    which,
)

# ----------------------------- Paths ------------------------------
# Use the *EXE directory* as the persistent root when frozen (PyInstaller onefile).
if getattr(sys, "frozen", False):
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    EXE_DIR = Path(__file__).resolve().parent

APP_DIR = EXE_DIR
BIN_DIR = APP_DIR / "bin" / "gzdoom"
IWADS_DIR = APP_DIR / "iwads"
MODS_DIR = APP_DIR / "mods"
SAVES_DIR = APP_DIR / "saves" / "MaximumSecurity"
CFG_PATH = APP_DIR / "gzdoom-maximumsecurity.ini"

DEFAULT_MOD_URL = "https://www.moddb.com/mods/maximum-security"


# -------------------------- HTTP helpers --------------------------
def http_download(session: requests.Session, url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with session.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    tmp.rename(out)


def github_latest_asset(
    session: requests.Session, repo: str, tokens: Tuple[str, ...]
) -> Tuple[str, str]:
    api = f"https://api.github.com/repos/{repo}/releases/latest"
    r = session.get(api, timeout=30, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    rel = r.json()
    for a in rel.get("assets", []):
        name = a.get("name", "")
        if all(t.lower() in name.lower() for t in tokens):
            return name, a["browser_download_url"]
    names = [a.get("name", "") for a in rel.get("assets", [])]
    raise RuntimeError(f"No asset matched {tokens} in {repo}. Available: {names}")


# ---------------------- GZDoom installation -----------------------
def ensure_gzdoom(
    session: requests.Session,
    prefer_path: Optional[Path] = None,
    force_update: bool = False,
) -> Path:
    if prefer_path and is_executable(prefer_path):
        return prefer_path.resolve()

    system = platform.system().lower()
    local = BIN_DIR / ("gzdoom.exe" if os.name == "nt" else "gzdoom")
    if local.exists() and is_executable(local) and not force_update:
        return local.resolve()

    path_hit = which("gzdoom.exe" if os.name == "nt" else "gzdoom")
    if path_hit and not force_update:
        return path_hit

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    if system == "windows":
        name, url = github_latest_asset(session, "ZDoom/gzdoom", ("windows", ".zip"))
        zpath = BIN_DIR.parent / name
        if not zpath.exists():
            http_download(session, url, zpath)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(BIN_DIR)
        exe = next((p for p in BIN_DIR.rglob("gzdoom.exe")), None)
        if not exe:
            raise RuntimeError("gzdoom.exe not found after extracting Windows ZIP.")
        return exe.resolve()

    if system == "linux":
        idx = "https://zdoom.org/files/gzdoom/bin/"
        r = session.get(idx, timeout=30)
        r.raise_for_status()
        appimage = None
        for line in r.text.splitlines():
            line = line.strip()
            if ".AppImage" in line and "href=" in line:
                s = line.find("href=")
                q1 = line.find('"', s)
                q2 = line.find('"', q1 + 1)
                href = line[q1 + 1 : q2]
                if href.lower().endswith(".appimage"):
                    appimage = href
                    break
        if not appimage:
            raise RuntimeError("Could not find a GZDoom AppImage on zdoom.org.")
        url = idx + appimage
        out = BIN_DIR / Path(appimage).name
        if not out.exists() or force_update:
            http_download(session, url, out)
            out.chmod(out.stat().st_mode | stat.S_IXUSR)
        return out.resolve()

    raise RuntimeError(f"Unsupported OS for auto-install: {system}")


# -------------------------- IWAD helpers --------------------------
def _score_wad_name(p: Path) -> tuple[int, int]:
    n = p.name.lower()
    if n == "doom2.wad":
        return (0, len(n))
    if n == "freedoom2.wad":
        return (1, len(n))
    if n == "freedoom1.wad":
        return (2, len(n))
    if n == "freedm.wad":
        return (3, len(n))
    return (9, len(n))


def _pick_best_local_wad(root: Path) -> Optional[Path]:
    cands = list(root.glob("*.wad")) or list(root.rglob("*.wad"))
    if not cands:
        return None
    cands.sort(key=_score_wad_name)
    return cands[0]


def ensure_iwad(
    session: requests.Session,
    prefer_path: Optional[Path] = None,
    force_update: bool = False,
) -> Path:
    if prefer_path and Path(prefer_path).exists():
        return Path(prefer_path).resolve()
    IWADS_DIR.mkdir(parents=True, exist_ok=True)
    if not force_update:
        existing = _pick_best_local_wad(IWADS_DIR)
        if existing:
            return existing.resolve()
    # If we got here, you want the auto-Freedoom path — omitted here since you’ve placed DOOM2.WAD.
    raise RuntimeError(
        "No IWAD found in ./iwads and auto-download disabled in this build."
    )


# -------- ensure IWAD sits next to gzdoom.exe (requested behavior) --------
def mirror_iwad_next_to_gzdoom(iwad: Path, gzdoom_exe: Path) -> Path:
    dst = gzdoom_exe.parent / iwad.name
    try:
        if (not dst.exists()) or (dst.stat().st_size != iwad.stat().st_size):
            shutil.copy2(str(iwad), str(dst))
    except Exception as e:
        # Don’t fail the whole run if mirror fails; we still pass -iwad explicitly.
        pass
    return dst


# ------------------------------ CLI ------------------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Portable GZDoom + ModDB updater/launcher."
    )
    ap.add_argument("--mod-url", default=DEFAULT_MOD_URL)
    ap.add_argument("--gzdoom", type=Path)
    ap.add_argument("--iwad", type=Path)
    ap.add_argument("--savedir", type=Path, default=SAVES_DIR)
    ap.add_argument("--config", type=Path, default=CFG_PATH)
    ap.add_argument("--extra-file", action="append", default=[])
    ap.add_argument("--skip-mod-update", dest="skip_mod_update", action="store_true")
    ap.add_argument("--force-mod-redownload", action="store_true")
    ap.add_argument("--update-gzdoom", action="store_true")
    ap.add_argument("--update-iwad", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    extras = [Path(e) for e in args.extra_file]

    with requests.Session() as s:
        gzdoom_path = ensure_gzdoom(
            s, prefer_path=args.gzdoom, force_update=args.update_gzdoom
        )

        # Prefer explicit --iwad; else look in ./iwads (portable next to EXE)
        if args.iwad and Path(args.iwad).exists():
            iwad_path = Path(args.iwad).resolve()
        else:
            iwad_path = ensure_iwad(s, prefer_path=None, force_update=args.update_iwad)

        # Put the IWAD next to gzdoom.exe as demanded.
        mirror_iwad_next_to_gzdoom(iwad_path, gzdoom_path)

        # Update or use local mod payload
        if args.skip_mod_update and MODS_DIR.exists():
            candidates = list(
                sorted(MODS_DIR.glob("*.pk*")) + sorted(MODS_DIR.glob("*.wad"))
            )
            if candidates:
                payload = candidates[0]
            else:
                payload = ensure_mod_payload(
                    args.mod_url, MODS_DIR, force_redownload=False, session=s
                )
        else:
            payload = ensure_mod_payload(
                args.mod_url,
                MODS_DIR,
                force_redownload=args.force_mod_redownload,
                session=s,
            )

    # Launch with explicit -iwad to be extra safe even though we mirrored it.
    launch_gzdoom(
        gzdoom_executable=gzdoom_path,
        iwad_path=iwad_path,
        mod_files=[payload, *extras],
        savedir=args.savedir,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
