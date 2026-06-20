#!/usr/bin/env python3
"""
Load-validation harness for Maximum Security.

Runs GZDoom headlessly (xvfb + software GL) with -norun, which forces a full
compile of ALL ZScript/DECORATE and a parse of every definition lump, then
exits before entering the main loop. We then scan the log to decide pass/fail.

What this GUARANTEES when it passes:
  - All ZScript/DECORATE compiled (eager: any syntax/type error is fatal here).
  - All definition lumps were parsed (warnings are surfaced, not hidden).
  - GZDoom reached game-setup (sprite/actor tables built).
What it does NOT guarantee (lazy in the engine, covered by other tools):
  - ACS runtime behavior, per-map load, missing-on-use assets/sounds.

Usage:
    python3 tools/validate.py game            # validate the source folder
    python3 tools/validate.py assets/X.pk3    # validate a packaged pk3
    python3 tools/validate.py game --warnings # also print parser warnings
Exit code 0 = pass, 1 = fail (suitable for CI / pre-commit).
"""
import argparse
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GZDOOM = "/usr/games/gzdoom"
IWAD = REPO / "assets" / "DOOM2.WAD"

# Unambiguous failure signals. We deliberately do NOT key off exit code:
# -norun exits 57 on success, and fatal compile errors abort with their own text.
FATAL_PATTERNS = [
    r"DIED WITH FATAL ERROR",
    r"Execution could not continue",
    r"\bScript error\b",
    r"\d+ errors? while parsing scripts",
    r"\bFatal error\b",
]
# If we never see this, the load aborted before completing.
COMPLETE_MARKER = "D_CheckNetGame"
WARN_SUMMARY = re.compile(r"(\d+) warnings? while parsing scripts")


def _read(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


# A diagnostic block (a "Script error/warning" header + its message lines) ends
# at the next header, a blank line, or a normal log-phase line. GZDoom does NOT
# blank-separate consecutive warnings, so we can't rely on blank lines alone.
_BLOCK_STOP_RE = re.compile(
    r"while parsing scripts|script parsing took|^[A-Za-z_]\w*:\s|^Adding |^Patch installed"
)


def _extract_blocks(log: str, header_re: re.Pattern) -> list[str]:
    """Group each matching header line with the message lines beneath it, so we
    report full diagnostics, not just the header. Deduplicated, since GZDoom
    repeats identical deprecation warnings."""
    lines = log.splitlines()
    blocks, seen, i = [], set(), 0
    while i < len(lines):
        if header_re.search(lines[i]):
            block = [lines[i].strip()]
            j = i + 1
            while (j < len(lines) and lines[j].strip()
                   and not header_re.search(lines[j])
                   and not _BLOCK_STOP_RE.search(lines[j])):
                block.append(lines[j].strip())
                j += 1
            text = "\n      ".join(block)
            if text not in seen:
                seen.add(text)
                blocks.append(text)
            i = j
        else:
            i += 1
    return blocks


def run_gzdoom(target: Path, iwad: Path, timeout: int) -> str:
    """Run GZDoom -norun headless, but watch the log live and kill it the moment
    we have a verdict. On a fatal error GZDoom blocks on an (invisible) dialog
    under xvfb, so we must not wait for it to exit on its own."""
    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="gzval_")
    os.close(log_fd)
    env = dict(os.environ, LIBGL_ALWAYS_SOFTWARE="1")
    cmd = [
        "xvfb-run", "-a", "-s", "-screen 0 1280x720x24",
        GZDOOM,
        "-iwad", str(iwad),
        "-file", str(target),
        "-norun",
        "+logfile", log_path,
    ]
    fatal_re = re.compile("|".join(FATAL_PATTERNS))
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    # On failure GZDoom prints ALL script errors in a burst, then blocks on an
    # (invisible) fatal dialog. There's no reliable terminal line after the
    # burst, so once we see the first error we wait for the log to stop growing
    # (burst finished) before killing -- this captures every error, not just one.
    settling = False
    settle_cap = None
    last_size = -1
    try:
        while True:
            if proc.poll() is not None:
                break  # exited on its own (success path exits fast)
            text = _read(log_path)
            size = len(text)
            if COMPLETE_MARKER in text:
                break  # success; -norun exits immediately after anyway
            if not settling and fatal_re.search(text):
                settling = True
                settle_cap = time.time() + 5.0  # hard cap on burst wait
            if settling and (size == last_size or time.time() > settle_cap):
                break  # error burst has stopped growing -> we have them all
            last_size = size
            if time.time() > deadline:
                break
            time.sleep(0.25)
    finally:
        # Kill the whole group (xvfb-run + Xvfb + gzdoom). TERM first so xvfb-run
        # can clean up its lock, then KILL if anything lingers.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(os.getpgid(proc.pid), sig)
            except ProcessLookupError:
                break
            try:
                proc.wait(timeout=3)
                break
            except subprocess.TimeoutExpired:
                continue

    text = _read(log_path)
    try:
        os.unlink(log_path)
    except OSError:
        pass
    return text


def validate(target: Path, iwad: Path, timeout: int, show_warnings: bool) -> bool:
    if not target.exists():
        print(f"FAIL: target not found: {target}", file=sys.stderr)
        return False
    if not iwad.exists():
        print(f"FAIL: IWAD not found: {iwad}", file=sys.stderr)
        return False

    log = run_gzdoom(target, iwad, timeout)

    fatal_re = re.compile("|".join(FATAL_PATTERNS))
    warn_re = re.compile(r"Script warning", re.IGNORECASE)

    errors = _extract_blocks(log, fatal_re)
    warnings = _extract_blocks(log, warn_re)
    completed = COMPLETE_MARKER in log

    warn_summary = WARN_SUMMARY.search(log)
    warn_count = int(warn_summary.group(1)) if warn_summary else len(warnings)

    ok = completed and not errors
    label = "PASS" if ok else "FAIL"
    print(f"[{label}] {target}  ({len(errors)} errors, {warn_count} warnings, "
          f"reached game-setup: {completed})")

    if errors:
        print("  --- errors ---")
        for e in errors:
            print(f"    {e}")
    if not completed and not errors:
        print("  load aborted before game-setup (no explicit error captured; check timeout)")

    if warnings:
        shown = warnings if show_warnings else warnings[:10]
        print("  --- warnings ---")
        for w in shown:
            print(f"    {w}")
        if len(warnings) > len(shown):
            print(f"    (+{len(warnings) - len(shown)} more; pass --warnings to see all)")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Headless GZDoom load validator")
    ap.add_argument("target", type=Path, help="folder or .pk3 to validate")
    ap.add_argument("--iwad", type=Path, default=IWAD)
    ap.add_argument("--timeout", type=int, default=30,
                    help="hard cap seconds; healthy runs finish in ~2s, so this is "
                         "deliberately aggressive. Bump it only if a run gets cut off.")
    ap.add_argument("--warnings", action="store_true", help="print parser warnings")
    args = ap.parse_args()
    ok = validate(args.target, args.iwad, args.timeout, args.warnings)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
