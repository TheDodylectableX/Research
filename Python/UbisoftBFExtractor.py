#---------------------------------------------------------
# Ubisoft JADE Engine .BF (BIG) Extractor
#---------------------------------------------------------
# Supports only BF archive that have the magic (BIG)
# Usage: Drag and drop the .bf file on top of this script
#---------------------------------------------------------

import os, sys, struct

def clean_filename(raw_bytes: bytes) -> str:
    try:
        # Decode as latin-1 or utf-8, strip null bytes and whitespace
        name = raw_bytes.split(b'\x00', 1)[0].decode('latin-1').strip()
        # Normalize slashes to the current OS standard
        return os.path.normpath(name.replace('\\', '/'))
    except Exception as e: return f"UNKNOWN_FILE_{hash(raw_bytes)}.bin"

def extract_bf_archive(filepath: str):
    print(f"[*] Analyzing Archive: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"[!] Error: File not found at {filepath}")
        return

    # Prepare output directory
    base_dir = os.path.dirname(filepath)
    archive_name = os.path.splitext(os.path.basename(filepath))[0]
    out_dir = os.path.join(base_dir, f"{archive_name}_extracted")
    os.makedirs(out_dir, exist_ok=True)

    with open(filepath, 'rb') as f:
        # 1. Parse Magic and Version
        magic = f.read(4)
        if magic[:3] != b'BIG':
            print(f"[!] Error: Invalid magic number. Expected 'BIG', got {magic}")
            return
        
        # Read Version, FileCount, FolderCount (3 uints = 12 bytes)
        header_data = f.read(12)
        version, file_count, folder_count = struct.unpack('<3I', header_data)
        
        print(f"Version: {version} | Files: {file_count} | Folders: {folder_count}")

        # Skip the rest of the header
        f.seek(52, os.SEEK_CUR)

        # 2. Parse Offset Table (8 bytes per file: Offset + Unknown)
        print(f"[*] Reading Offset Table...")
        file_offsets = []
        for _ in range(file_count):
            offset_data = f.read(8)
            file_offset, unk_val = struct.unpack('<2I', offset_data)
            file_offsets.append(file_offset)

        # 3. Skip zero bytes until we hit the actual file listing block
        print(f"[*] Skipping dynamic padding...")
        skipped_bytes = 0
        while True:
            byte = f.read(1)
            if not byte:
                print("[!] Reached unexpected EOF while skipping padding.")
                return
            if byte != b'\x00':
                # We hit data! Step back one byte so we don't consume the start of the file listing.
                f.seek(-1, os.SEEK_CUR)
                break
            skipped_bytes += 1
        
        print(f"[*] Skipped {skipped_bytes} bytes of zero-padding.")

        # 4. Parse File Listings
        print(f"[*] Reading File Metadata...")
        file_entries = []
        for i in range(file_count):
            # Read the base 84-byte entry: 5 uints (20 bytes) + 64 chars
            meta_data = f.read(84)
            file_size, unk_a, unk_b, file_flags, file_hash = struct.unpack('<5I', meta_data[:20])
            raw_name = meta_data[20:84]
            clean_name = clean_filename(raw_name)

            # Version 42 has an extra 40 bytes per entry
            if version == 42: f.seek(40, os.SEEK_CUR)

            file_entries.append({
                'name': clean_name,
                'offset': file_offsets[i],
                'size': file_size,
                'flags': file_flags
            })

        # 5. File Extraction
        print(f"[*] Beginning extraction to: {out_dir}")
        successful = 0
        
        for idx, entry in enumerate(file_entries):
            out_path = os.path.join(out_dir, entry['name'])
            
            # Security: Prevent Directory Traversal (e.g., if a filename is "../../windows/system32/bad.exe")
            if not os.path.abspath(out_path).startswith(os.path.abspath(out_dir)):
                print(f"[!] Warning: Skipping malicious path: {entry['name']}")
                continue

            # Create required subdirectories
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            # Dump data
            f.seek(entry['offset'])
            bytes_remaining = entry['size']
            
            try:
                with open(out_path, 'wb') as out_f:
                    # Read in chunks of 1MB to keep memory usage flat for large files
                    while bytes_remaining > 0:
                        chunk_size = min(bytes_remaining, 1024 * 1024)
                        chunk = f.read(chunk_size)
                        if not chunk: break # Unexpected EOF
                        out_f.write(chunk)
                        bytes_remaining -= len(chunk)
                successful += 1
                print(f"[*] Extracting: {entry['name']}")
            except IOError as e: print(f"\n[!] Failed to extract {entry['name']}: {e}")

        print(f"\n[*] Extraction Complete! {successful}/{file_count} files successfully written.")

if __name__ == "__main__":
    print("===========================================")
    print("  Ubisoft JADE Engine .BF (BIG) Extractor")
    print("===========================================")
    
    if len(sys.argv) < 2:
        print("\nUsage: Drag and drop a .BF archive onto this script or run via CLI: [python UbisoftBFExtractor.py <prince.bf>].")
        input("\nPress Enter to exit...")
        sys.exit(1)

    target_file = sys.argv[1]
    extract_bf_archive(target_file)
    
    input("\nPress Enter to exit...")
