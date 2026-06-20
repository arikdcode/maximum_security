#!/usr/bin/env python3
"""
Inventory every file in the game/ tree by its ACTUAL content type (magic bytes),
independent of whatever extension (or lack of one) it currently has.

Outputs:
  1. A structured YAML map: every leaf file -> detected type (+ nominal extension,
     size, and whether it was a forced rename on unpack). This is the detailed,
     machine-usable artifact we'll drive LFS rules / renaming from.
  2. A concise text summary to stdout: counts by actual type, split by
     extensionless / with-extension / all, plus the unknown count.

This supersedes scripts/analyze_files.py (which targeted a nonexistent game_src/).

Usage:
    python3 tools/inventory.py                  # game/ -> tools/inventory.yaml
    python3 tools/inventory.py --root game --out tools/inventory.yaml
"""
import argparse
import json
import os
import struct
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def detect_type(path: Path) -> str:
    """Best-effort content-type detection by magic bytes + heuristics.
    Returns a lowercase type tag, or 'unknown' when we genuinely can't tell."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            head = f.read(8192)
    except OSError:
        return "unreadable"
    if size == 0:
        return "empty"

    # --- unambiguous magic numbers ---
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:4] in (b"GIF8",):
        return "gif"
    if head[:2] == b"BM":
        return "bmp"
    if head[:4] == b"DDS ":
        return "dds"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if head[:4] == b"MThd":
        return "midi"
    if head[:4] == b"MUS\x1a":
        return "mus"
    if head[:4] == b"IMPM":
        return "it"
    if head[:17] == b"Extended Module: ":
        return "xm"
    if head[44:48] == b"SCRM":
        return "s3m"
    if head[:4] in (b"IDP3", b"IDP2"):
        return "md3" if head[:4] == b"IDP3" else "md2"
    if head[:4] in (b"FON2", b"FON1"):
        return "fon"
    if head[:4] in (b"PWAD", b"IWAD"):
        return "wad"
    if head[:4] == b"PK\x03\x04":
        return "zip"
    if head[:1] == b"\x0a" and len(head) > 1 and head[1] in (0, 2, 3, 4, 5):
        return "pcx"
    if head[:4] in (b"ACS\x00", b"ACSE", b"ACSe"):
        return "acs_object"

    # --- Doom DMX digital sound lump: fmt=3, then a sane sample rate ---
    if size >= 8:
        fmt, rate = struct.unpack("<HH", head[:4])
        if fmt == 3 and 4000 <= rate <= 48000:
            return "dmx_sound"

    # --- Doom picture (patch) format: no magic, validate the header ---
    if size >= 12:
        w, h, left, top = struct.unpack("<4h", head[:8])
        if 0 < w <= 4096 and 0 < h <= 4096 and -4096 <= left <= 4096 and -4096 <= top <= 4096:
            if size >= 8 + 4 * w:
                col0 = struct.unpack("<I", head[8:12])[0]
                if 8 + 4 * w <= col0 < size:
                    return "doom_patch"

    # --- text (after binary formats are ruled out) ---
    # The head looks texty; confirm the WHOLE file is text before trusting it,
    # since the text/binary split decides git-vs-LFS routing.
    if b"\x00" not in head and _looks_text(head):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return "unknown"
        if b"\x00" not in body and _looks_text(body):
            return "text"

    return "unknown"


def _looks_text(b: bytes) -> bool:
    """True if bytes are valid UTF-8, or otherwise overwhelmingly printable."""
    if not b:
        return True
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        printable = sum((32 <= c < 127) or c in (9, 10, 13) for c in b) / len(b)
        return printable > 0.95


def main():
    ap = argparse.ArgumentParser(description="Inventory game/ files by actual type")
    ap.add_argument("--root", type=Path, default=REPO / "game")
    ap.add_argument("--out", type=Path, default=REPO / "tools" / "inventory.yaml")
    args = ap.parse_args()

    root = args.root
    if not root.exists():
        raise SystemExit(f"root not found: {root}")

    # Forced-rename map written by unpack.py (disk_path -> original lump name).
    renames = {}
    meta_path = root / ".pk3meta.json"
    if meta_path.exists():
        renames = json.loads(meta_path.read_text()).get("renames", {})

    files = []
    by_type_all = Counter()
    by_type_noext = Counter()
    by_type_ext = Counter()
    nominal_ext = Counter()

    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name == ".pk3meta.json":
            continue
        rel = p.relative_to(root).as_posix()
        ext = p.suffix.lower()
        has_ext = bool(ext)
        t = detect_type(p)

        by_type_all[t] += 1
        (by_type_ext if has_ext else by_type_noext)[t] += 1
        nominal_ext[ext if has_ext else "(none)"] += 1

        entry = {"path": rel, "ext": ext, "type": t, "size": p.stat().st_size}
        if rel in renames:
            entry["renamed_from"] = renames[rel]
        files.append(entry)

    total = len(files)
    n_ext = sum(by_type_ext.values())
    n_noext = sum(by_type_noext.values())

    doc = {
        "source_pk3": json.loads(meta_path.read_text()).get("source_pk3") if meta_path.exists() else None,
        "root": root.name,
        "forced_renames": [{"disk_path": k, "original_lump": v} for k, v in renames.items()],
        "summary": {
            "total": total,
            "with_extension": n_ext,
            "extensionless": n_noext,
            "by_type_all": dict(by_type_all.most_common()),
            "by_type_extensionless": dict(by_type_noext.most_common()),
            "by_type_with_extension": dict(by_type_ext.most_common()),
            "nominal_extensions": dict(nominal_ext.most_common()),
        },
        "files": files,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False, default_flow_style=False, width=200)

    # --- concise text summary ---
    def show(counter, title):
        print(f"\n{title}")
        for t, c in counter.most_common():
            print(f"  {t:14} {c:>5}")

    print(f"INVENTORY  root=game/  source={doc['source_pk3']}")
    print(f"  total files:      {total}")
    print(f"  with extension:   {n_ext}")
    print(f"  extensionless:    {n_noext}")
    print(f"  forced renames:   {len(renames)}  " +
          ", ".join(f"{v}->{k}" for k, v in renames.items()))
    show(by_type_all, "By actual type (ALL files):")
    show(by_type_ext, "By actual type (WITH extension only):")
    show(by_type_noext, "By actual type (EXTENSIONLESS only):")
    unknown = by_type_all.get("unknown", 0) + by_type_all.get("unreadable", 0)
    print(f"\n  UNKNOWN/unclassified: {unknown}")
    print(f"\nFull per-file map written to: {args.out}")


if __name__ == "__main__":
    main()
