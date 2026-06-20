#!/usr/bin/env python3
"""
Unpack a Maximum Security .pk3 into an editable folder tree (game/).

A .pk3 is just a zip, but GZDoom archives can legally contain a *file* and a
*directory* with the same name (e.g. the root `ZSCRIPT` lump alongside a
`ZSCRIPT/` folder of includes). Real filesystems can't represent that, so this
tool detects those collisions and renames the colliding *file* lump to a form
GZDoom still recognises when loading from a directory.

The rename map is written to <dest>/.pk3meta.json so pack.py can reverse it and
reproduce a byte-faithful archive.

Usage:
    python3 tools/unpack.py                      # newest assets/*.pk3 -> game/
    python3 tools/unpack.py --pk3 assets/X.pk3 --dest game
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"

# GZDoom auto-loads these root lumps by base name; a recognised extension keeps
# them working when a same-named folder forces us to rename the file lump.
SPECIAL_LUMP_EXT = {
    "ZSCRIPT": ".zsc",
    "DECORATE": ".txt",
    "MAPINFO": ".txt",
    "SNDINFO": ".txt",
    "GLDEFS": ".txt",
    "ANIMDEFS": ".txt",
    "TERRAIN": ".txt",
    "CVARINFO": ".txt",
    "KEYCONF": ".txt",
    "MENUDEF": ".txt",
    "LANGUAGE": ".txt",
    "SBARINFO": ".txt",
    "TEXTURES": ".txt",
    "MODELDEF": ".txt",
}


def newest_pk3() -> Path:
    pk3s = sorted(
        ASSETS_DIR.glob("Maximum_Security_v*.pk3"),
        key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)],
    )
    if not pk3s:
        raise FileNotFoundError(f"No Maximum_Security_v*.pk3 found in {ASSETS_DIR}")
    return pk3s[-1]


def main():
    ap = argparse.ArgumentParser(description="Unpack a .pk3 into an editable folder tree")
    ap.add_argument("--pk3", type=Path, default=None, help="Source pk3 (default: newest in assets/)")
    ap.add_argument("--dest", type=Path, default=REPO_ROOT / "game", help="Destination folder (default: game/)")
    args = ap.parse_args()

    pk3 = args.pk3 or newest_pk3()
    dest = args.dest
    if not pk3.exists():
        print(f"Error: pk3 not found: {pk3}", file=sys.stderr)
        sys.exit(1)

    print(f"Unpacking {pk3.name} -> {dest}/")
    with zipfile.ZipFile(pk3) as zf:
        infos = zf.infolist()
        # Every path segment that is used as a directory by some entry.
        dir_paths = set()
        for info in infos:
            name = info.filename
            if name.endswith("/"):
                dir_paths.add(name.rstrip("/"))
            else:
                parts = name.split("/")
                for i in range(1, len(parts)):
                    dir_paths.add("/".join(parts[:i]))

        rename_map = {}  # on-disk relative path -> original lump name in the pk3
        collisions = []
        for info in infos:
            name = info.filename
            if name.endswith("/"):
                continue
            if name in dir_paths:  # file lump collides with a directory of the same name
                base = Path(name).name
                ext = SPECIAL_LUMP_EXT.get(base.upper())
                if ext is None:
                    print(f"  ! Unhandled collision for lump '{name}'. Refusing to guess; "
                          f"add it to SPECIAL_LUMP_EXT.", file=sys.stderr)
                    sys.exit(2)
                new_name = name + ext
                rename_map[new_name] = name
                collisions.append((name, new_name))

        count = 0
        for info in infos:
            name = info.filename
            if name.endswith("/"):
                (dest / name).mkdir(parents=True, exist_ok=True)
                continue
            out_name = name
            for new_name, orig in rename_map.items():
                if orig == name:
                    out_name = new_name
                    break
            out_path = dest / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            count += 1

    meta = {
        "source_pk3": pk3.name,
        "renames": rename_map,  # disk_path -> original lump name
    }
    (dest / ".pk3meta.json").write_text(json.dumps(meta, indent=2))

    print(f"  Extracted {count} files")
    if collisions:
        print(f"  Resolved {len(collisions)} file/dir name collision(s):")
        for orig, new in collisions:
            print(f"    '{orig}'  ->  '{new}'")
    print(f"  Wrote rename map to {dest.name}/.pk3meta.json")
    print("Done.")


if __name__ == "__main__":
    main()
