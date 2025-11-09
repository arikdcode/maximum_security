#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
import os
import platform
import shutil
import stat
import sys
import threading
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Callable

import requests

from mod_launcher import (
    ensure_mod_payload,
    launch_gzdoom,
    is_executable,
    which,
    find_downloads_page,
    newest_filepage,
    parse_filepage_for_md5_and_start,
)

# ---------- Optional UI imports (Tk only used when not --auto) ----------
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None


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
def http_download(
    session: requests.Session,
    url: str,
    out: Path,
    progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with session.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
                    got += len(chunk)
                    if progress:
                        progress(got, total)
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
    progress: Optional[Callable[[int, int], None]] = None,
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
        if (not zpath.exists()) or force_update:
            http_download(session, url, zpath, progress=progress)
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
        if (not out.exists()) or force_update:
            http_download(session, url, out, progress=progress)
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


def _prefer_freedoom_zip(session: requests.Session) -> Tuple[str, str]:
    # Prefer "freedoom" over "freedm"; fallback to first .zip if needed.
    api = "https://api.github.com/repos/freedoom/freedoom/releases/latest"
    r = session.get(api, timeout=30, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    rel = r.json()
    zips = [
        (a.get("name", ""), a.get("browser_download_url", ""))
        for a in rel.get("assets", [])
        if str(a.get("name", "")).lower().endswith(".zip")
    ]
    if not zips:
        raise RuntimeError("No .zip assets in Freedoom latest release.")
    for name, url in zips:
        nl = name.lower()
        if "freedoom" in nl and "freedm" not in nl:
            return name, url
    name, url = zips[0]
    return name, url


def ensure_iwad(
    session: requests.Session,
    prefer_path: Optional[Path] = None,
    force_update: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """
    If --iwad passed, use it. Otherwise:
      1) If ./iwads has any *.wad, pick best (doom2>freedoom2>freedoom1>freedm>any).
      2) Else download Freedoom latest zip, pick best wad inside, copy into ./iwads/.
    """
    if prefer_path and Path(prefer_path).exists():
        return Path(prefer_path).resolve()

    IWADS_DIR.mkdir(parents=True, exist_ok=True)

    if not force_update:
        existing = _pick_best_local_wad(IWADS_DIR)
        if existing:
            return existing.resolve()

    name, url = _prefer_freedoom_zip(session)
    zpath = IWADS_DIR / name
    http_download(session, url, zpath, progress=progress)

    extract_dir = IWADS_DIR / f"unz_{name}"
    if extract_dir.exists():
        for p in sorted(extract_dir.rglob("*"), reverse=True):
            try:
                p.unlink()
            except IsADirectoryError:
                pass
        for p in sorted(extract_dir.glob("*")):
            try:
                p.rmdir()
            except Exception:
                pass
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zpath, "r") as zf:
        zf.extractall(extract_dir)

    wad = _pick_best_local_wad(extract_dir)
    if not wad:
        raise RuntimeError("No *.wad found inside Freedoom archive.")

    final = IWADS_DIR / wad.name
    final.write_bytes(wad.read_bytes())
    return final.resolve()


# -------- ensure IWAD sits next to gzdoom.exe (requested behavior) --------
def mirror_iwad_next_to_gzdoom(iwad: Path, gzdoom_exe: Path) -> Path:
    dst = gzdoom_exe.parent / iwad.name
    try:
        if (not dst.exists()) or (dst.stat().st_size != iwad.stat().st_size):
            shutil.copy2(str(iwad), str(dst))
    except Exception:
        # Non-fatal; we also pass -iwad explicitly.
        pass
    return dst


# ------------------------------ UI helpers ------------------------------
def _enable_hidpi_awareness():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _scrolling_frame(parent):
    canvas = tk.Canvas(parent, highlightthickness=0)
    vbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = ttk.Frame(canvas)
    win = canvas.create_window(0, 0, window=inner, anchor="nw")

    def _cfg(_e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win, width=canvas.winfo_width())

    inner.bind("<Configure>", _cfg)
    canvas.bind("<Configure>", _cfg)
    return canvas, inner


def show_preflight_and_run(plan: dict, worker_func) -> bool:
    """
    plan: { gzdoom: {...}, iwad: {...}, mod: {...} }
    worker_func(update_stage_progress) -> raises on error
    Returns True iff downloads finished; False if user exited early.
    """
    _enable_hidpi_awareness()
    root = tk.Tk()
    root.title("Maximum Security – Setup")

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w = max(820, int(sw * 0.5))
    h = max(600, int(sh * 0.6))
    root.geometry(f"{w}x{h}")
    root.minsize(680, 520)

    outer = ttk.Frame(root, padding=12)
    outer.pack(fill="both", expand=True)

    # ---------- Preflight ----------
    preflight = ttk.Frame(outer)
    preflight.pack(fill="both", expand=True)
    canvas, content = _scrolling_frame(preflight)

    def add_section(title, lines):
        box = ttk.Labelframe(content, text=title, padding=(10, 10))
        box.pack(fill="x", expand=False, pady=(0, 10))
        for t in lines:
            ttk.Label(box, text=t, anchor="w", justify="left", wraplength=w - 80).pack(
                fill="x"
            )

    gz = plan["gzdoom"]
    add_section(
        "GZDoom",
        [
            f"Latest asset: {gz['latest_asset']}",
            f"Local present: {'yes' if gz['local_present'] else 'no'}",
            f"Will download: {'yes' if gz['will_download'] else 'no'}",
        ],
    )
    iw = plan["iwad"]
    add_section(
        "IWAD",
        [
            f"Choice: {iw['choice']}",
            f"Source: {iw['source']}",
            f"Will fetch Freedoom: {'yes' if iw['will_fetch_freedoom'] else 'no'}",
        ],
    )
    md = plan["mod"]
    add_section(
        "Mod (ModDB)",
        [
            f"Newest file: {md['latest_filename']}",
            f"Will update: {'yes' if md['will_update'] else 'no'}",
        ],
    )

    pre_btns = ttk.Frame(outer)
    pre_btns.pack(fill="x", pady=(8, 0))
    proceed = {"go": False}

    def on_exit():
        proceed["go"] = False
        root.destroy()

    def on_continue():
        proceed["go"] = True
        preflight.pack_forget()
        pre_btns.pack_forget()
        progress_page()

    ttk.Button(pre_btns, text="Exit", command=on_exit).pack(side="right")
    ttk.Button(pre_btns, text="Continue", command=on_continue).pack(
        side="right", padx=(0, 8)
    )
    root.bind("<Escape>", lambda e: on_exit())
    root.bind("<Return>", lambda e: on_continue())

    # ---------- Progress page ----------
    bars = {}
    status_vars = {}

    def progress_page():
        page = ttk.Frame(outer)
        page.pack(fill="both", expand=True)

        hdr = ttk.Label(
            page, text="Downloading / Preparing assets…", font=("", 12, "bold")
        )
        hdr.pack(anchor="w", pady=(0, 8))

        for key, label in (
            ("gzdoom", "GZDoom"),
            ("iwad", "IWAD"),
            ("mod", "Mod payload"),
        ):
            frame = ttk.Labelframe(page, text=label, padding=(10, 10))
            frame.pack(fill="x", pady=(0, 10))
            pb = ttk.Progressbar(
                frame, orient="horizontal", mode="determinate", maximum=100
            )
            pb.pack(fill="x")
            txt = tk.StringVar(value="Waiting…")
            ttk.Label(frame, textvariable=txt).pack(anchor="w", pady=(6, 0))
            bars[key] = pb
            status_vars[key] = txt

        log_box = ttk.Labelframe(page, text="Log", padding=(10, 10))
        log_box.pack(fill="both", expand=True)
        text = tk.Text(log_box, height=10)
        text.pack(fill="both", expand=True)

        def log(msg):
            text.insert("end", msg + "\n")
            text.see("end")
            text.update_idletasks()

        def update(stage, got, total, note=None):
            if total > 0:
                frac = min(100, int(got * 100 / total))
                bars[stage]["value"] = frac
            else:
                val = (bars[stage]["value"] + 3) % 100
                bars[stage]["value"] = val
            if note:
                status_vars[stage].set(note)
            else:
                status_vars[stage].set(
                    f"{got/1e6:.1f} MB"
                    + (f" / {total/1e6:.1f} MB" if total > 0 else "")
                )
            page.update_idletasks()

        done = {"ok": False, "err": None}

        def _work():
            try:
                worker_func(update)
                done["ok"] = True
            except Exception as e:
                done["err"] = e
            finally:
                root.after(60, _finish)

        def _finish():
            if done["ok"]:
                root.destroy()
            else:
                log(f"ERROR: {done['err']}")
                status_vars["gzdoom"].set("Failed")
                # Window remains open for inspection.

        threading.Thread(target=_work, daemon=True).start()

    root.update_idletasks()
    root.mainloop()
    return bool(proceed["go"])


# ------------------------------ Planning + setup ------------------------------
def build_plan(session: requests.Session, mod_url: str) -> dict:
    # GZDoom
    try:
        gz_name, _ = github_latest_asset(session, "ZDoom/gzdoom", ("windows", ".zip"))
    except Exception:
        gz_name = "(unknown)"
    gz_local = any(BIN_DIR.rglob("gzdoom.exe"))
    plan_gz = {
        "latest_asset": gz_name,
        "local_present": bool(gz_local),
        "will_download": not gz_local,
    }

    # IWAD
    local_iwad = _pick_best_local_wad(IWADS_DIR)
    plan_iw = {
        "choice": local_iwad.name if local_iwad else "(none)",
        "source": "local" if local_iwad else "Freedoom (auto)",
        "will_fetch_freedoom": bool(not local_iwad),
    }

    # Mod (ModDB)
    try:
        dl = find_downloads_page(session, mod_url)
        fp = newest_filepage(session, dl)
        _, _, suggested = parse_filepage_for_md5_and_start(session, fp)
        latest_name = suggested or "(unknown)"
    except Exception:
        latest_name = "(unknown)"
    local_mods = list(sorted(MODS_DIR.glob("*.pk*")) + sorted(MODS_DIR.glob("*.wad")))
    plan_mod = {
        "latest_filename": latest_name,
        "will_update": (
            False if local_mods else True
        ),  # display hint; actual behavior depends on flags
    }
    return {"gzdoom": plan_gz, "iwad": plan_iw, "mod": plan_mod}


def setup_all(session: requests.Session, args, update) -> dict:
    # GZDoom
    def gz_cb(got, total):
        update("gzdoom", got, total, "Downloading GZDoom…")

    gzdoom_path = ensure_gzdoom(
        session,
        prefer_path=args.gzdoom,
        force_update=args.update_gzdoom,
        progress=gz_cb,
    )
    update("gzdoom", 1, 1, f"Ready: {gzdoom_path.name}")

    # IWAD
    if args.iwad and Path(args.iwad).exists():
        iwad_path = Path(args.iwad).resolve()
        update("iwad", 1, 1, f"Using IWAD: {iwad_path.name}")
    else:
        local_iwad = _pick_best_local_wad(IWADS_DIR)
        if local_iwad and not args.update_iwad:
            iwad_path = Path(local_iwad).resolve()
            update("iwad", 1, 1, f"Using local IWAD: {iwad_path.name}")
        else:

            def fd_cb(got, total):
                update("iwad", got, total, "Downloading Freedoom…")

            name, url = _prefer_freedoom_zip(session)
            zpath = IWADS_DIR / name
            http_download(session, url, zpath, progress=fd_cb)
            with zipfile.ZipFile(zpath, "r") as zf:
                zf.extractall(IWADS_DIR / f"unz_{name}")
            pick = _pick_best_local_wad(IWADS_DIR / f"unz_{name}")
            if not pick:
                raise RuntimeError("Freedoom archive did not contain a WAD.")
            iwad_path = IWADS_DIR / pick.name
            iwad_path.write_bytes(pick.read_bytes())
            update("iwad", 1, 1, f"Ready: {iwad_path.name}")

    # Mirror IWAD next to gzdoom
    mirror_iwad_next_to_gzdoom(iwad_path, gzdoom_path)

    # Mod payload
    def mod_cb(got, total):
        update("mod", got, total, "Fetching latest mod…")

    payload: Path
    if args.skip_mod_update and MODS_DIR.exists():
        candidates = list(
            sorted(MODS_DIR.glob("*.pk*")) + sorted(MODS_DIR.glob("*.wad"))
        )
        if candidates:
            payload = candidates[0]
            update("mod", 1, 1, f"Using local mod: {Path(payload).name}")
        else:
            payload = ensure_mod_payload(
                args.mod_url,
                MODS_DIR,
                force_redownload=False,
                session=session,
                progress=mod_cb,
            )
            update("mod", 1, 1, f"Ready: {Path(payload).name}")
    else:
        payload = ensure_mod_payload(
            args.mod_url,
            MODS_DIR,
            force_redownload=args.force_mod_redownload,
            session=session,
            progress=mod_cb,
        )
        update("mod", 1, 1, f"Ready: {Path(payload).name}")

    return {"gzdoom_path": gzdoom_path, "iwad_path": iwad_path, "payload": payload}


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

    # Update controls
    ap.add_argument("--skip-mod-update", dest="skip_mod_update", action="store_true")
    ap.add_argument("--force-mod-redownload", action="store_true")
    ap.add_argument("--update-gzdoom", action="store_true")
    ap.add_argument("--update-iwad", action="store_true")

    # UI / mode
    ap.add_argument(
        "--auto",
        action="store_true",
        help="Run headless (no window). Also enabled if env MS_AUTO=1.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    extras = [Path(e) for e in args.extra_file]
    auto_env = os.environ.get("MS_AUTO", "") == "1"
    headless = bool(args.auto or auto_env)

    with requests.Session() as s:
        if headless or tk is None or ttk is None:
            # Headless mode: print simple progress to stdout.
            def printer(stage, got, total, note=None):
                base = f"[{stage}]"
                if note:
                    print(f"{base} {note}")
                else:
                    if total > 0:
                        print(f"{base} {got/1e6:.1f}/{total/1e6:.1f} MB")
                    else:
                        print(f"{base} {got/1e6:.1f} MB")

            setup = setup_all(s, args, printer)
        else:
            # Interactive: show preflight, then progress, keep window until ready to launch.
            plan = build_plan(s, args.mod_url)

            # The worker we hand to the UI
            setup_box = {}

            def worker(update_cb):
                res = setup_all(s, args, update_cb)
                setup_box.update(res)

            ok = show_preflight_and_run(plan, worker)
            if not ok:
                return
            setup = setup_box

    # Launch (UI closed just before this in interactive mode).
    launch_gzdoom(
        gzdoom_executable=setup["gzdoom_path"],
        iwad_path=setup["iwad_path"],
        mod_files=[setup["payload"], *extras],
        savedir=args.savedir,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
