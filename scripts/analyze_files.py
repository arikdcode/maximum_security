import os
import sys

def is_binary(filepath):
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return True, chunk
            # Check for high byte count?
            # Simple null byte check is usually enough for code vs binary assets.
            return False, chunk
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False, b''

def get_extension(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() if ext else None

def identify_binary_type(chunk, filename):
    # Magic numbers
    if chunk.startswith(b'\x89PNG\r\n\x1a\n'): return "PNG Image"
    if chunk.startswith(b'\xff\xd8\xff'): return "JPEG Image"
    if chunk.startswith(b'GIF8'): return "GIF Image"
    if chunk.startswith(b'BM'): return "BMP Image"
    if chunk.startswith(b'PK\x03\x04'): return "ZIP Archive / Office Doc"
    if chunk.startswith(b'MZ'): return "Windows Executable (EXE/DLL)"
    if chunk.startswith(b'\x7fELF'): return "ELF Executable"
    if chunk.startswith(b'RIFF') and chunk[8:12] == b'WAVE': return "WAV Audio"
    if chunk.startswith(b'OggS'): return "OGG Audio"
    if chunk.startswith(b'ID3'): return "MP3 Audio"
    if chunk.startswith(b'%PDF'): return "PDF Document"
    if chunk.startswith(b'IWAD'): return "Doom IWAD"
    if chunk.startswith(b'PWAD'): return "Doom PWAD"
    if chunk.startswith(b'FLAC'): return "FLAC Audio"

    # Doom specific / specific text formats that might look binary?
    # LMP files (Demos/Lumps) don't always have a clear header, but we can check extensions
    ext = get_extension(filename)
    if ext == '.lmp': return "Doom Lump/Demo (inferred from ext)"
    if ext == '.md3': return "MD3 Model (inferred from ext)"
    if ext == '.obj': return "OBJ Model (inferred from ext)"
    if ext == '.fon2': return "Font (inferred from ext)"
    if ext == '.zscript': return "ZScript (likely text but detected as binary?)"

    return "Unknown Binary"

def main():
    root_dir = 'game_src'
    if not os.path.exists(root_dir):
        print(f"Directory '{root_dir}' not found.")
        return

    ignore_dirs = {'.git', 'node_modules', '.cursor', '__pycache__', 'dist', 'build', '.dist_repo'}

    text_files = []
    binary_files = []

    text_ext_stats = {'with_ext': 0, 'no_ext': 0}
    binary_ext_stats = {'with_ext': 0, 'no_ext': 0}

    binary_types = {}

    print(f"Scanning {os.getcwd()}...")

    for root, dirs, files in os.walk(root_dir):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, root_dir)

            is_bin, chunk = is_binary(filepath)
            ext = get_extension(file)

            if is_bin:
                binary_files.append(rel_path)
                if ext:
                    binary_ext_stats['with_ext'] += 1
                else:
                    binary_ext_stats['no_ext'] += 1

                btype = identify_binary_type(chunk, file)
                binary_types[btype] = binary_types.get(btype, 0) + 1
            else:
                text_files.append(rel_path)
                if ext:
                    text_ext_stats['with_ext'] += 1
                else:
                    text_ext_stats['no_ext'] += 1

    print("\n=== Summary ===")
    print(f"Total Files Scanned: {len(text_files) + len(binary_files)}")
    print(f"Text Files: {len(text_files)}")
    print(f"Binary Files: {len(binary_files)}")

    print("\n--- Text Files Extension Stats ---")
    print(f"With Extension: {text_ext_stats['with_ext']}")
    print(f"No Extension:   {text_ext_stats['no_ext']}")

    print("\n--- Binary Files Extension Stats ---")
    print(f"With Extension: {binary_ext_stats['with_ext']}")
    print(f"No Extension:   {binary_ext_stats['no_ext']}")

    print("\n--- Binary File Types (Inferred) ---")
    # Sort by count desc
    sorted_types = sorted(binary_types.items(), key=lambda x: x[1], reverse=True)
    for btype, count in sorted_types:
        print(f"{btype}: {count}")

    # Write debug files
    with open('debug_text_files.txt', 'w') as f:
        f.write('\n'.join(sorted(text_files)))

    with open('debug_binary_files.txt', 'w') as f:
        f.write('\n'.join(sorted(binary_files)))

    print("\nLists written to 'debug_text_files.txt' and 'debug_binary_files.txt'")

if __name__ == "__main__":
    main()
