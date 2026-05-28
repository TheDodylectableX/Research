#---------------------------------------------------------
# Terminal Reality Infernal Engine .POD Extractor
#---------------------------------------------------------

import os, sys, struct
from pathlib import Path

def read_null_terminated_string(f):
    chars = bytearray()
    while True:
        char = f.read(1)
        # Break on EOF or null byte
        if not char or char == b'\x00':
            break
        chars.extend(char)
    # decode with 'replace' to prevent crashes on weirdly encoded strings
    return chars.decode('utf-8', errors='replace') 

def extract_pod(file_path):
    pod_path = Path(file_path)
    
    # 1. Edge Case: Validate file existence
    if not pod_path.is_file():
        print(f"[!] Error: Could not find file {pod_path}")
        return

    # Create an output directory matching the archive's name
    out_dir = pod_path.parent / pod_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Unpacking: {pod_path.name}")
    print(f"[*] Destination: {out_dir}\n")

    # Open in 'rb' (Read Binary) mode
    with open(pod_path, 'rb') as f:
        # --- Header Parsing ---
        magic = f.read(4)
        if magic != b'POD3':
            print(f"[!] Error: Invalid magic signature '{magic}'. Expected 'POD3'.")
            return

        # Jump to offset 88 to grab the File Count
        f.seek(88)
        # '<I' means Little-Endian (<) Unsigned 32-bit Integer (I)
        file_count = struct.unpack('<I', f.read(4))[0]

        # Sanity check to prevent allocating massive loops on corrupted data
        if file_count == 0 or file_count > 1_000_000:
            print(f"[!] Error: Suspicious file count ({file_count}). Aborting.")
            return

        # Jump to offset 264 to grab the File Table Offset
        f.seek(264)
        table_offset = struct.unpack('<I', f.read(4))[0]

        # Calculate where the string table begins
        str_table_offset = table_offset + (file_count * 20)

        print(f"[*] Detected {file_count} files. Starting extraction...\n")
        
        # --- File Table Parsing & Extraction ---
        for i in range(file_count):
            # Seek to the current entry in the file directory
            f.seek(table_offset + (i * 20))
            
            # Read exactly 12 bytes: nameOffset (4), fileSize (4), fileOffset (4)
            # We naturally ignore the trailing 8 padding bytes by simply not reading them.
            entry_data = f.read(12)
            name_offset, file_size, file_offset = struct.unpack('<III', entry_data)

            # Jump to the string table to get the name
            f.seek(str_table_offset + name_offset)
            raw_filename = read_null_terminated_string(f)
            
            # Architecture Note: Sanitize paths! 
            # Games often use Windows backslashes (textures\diffuse.dds). 
            # Replacing them with forward slashes lets pathlib handle it natively on any OS.
            clean_filename = raw_filename.replace('\\', '/')
            target_path = out_dir / clean_filename
            
            # Recreate the internal directory structure
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Jump to the actual file data
            f.seek(file_offset)
            
            # Performance Consideration: Chunked Writing
            # Instead of reading the entire file into RAM at once (which crashes on large files),
            # we write it out in 1MB chunks.
            bytes_left = file_size
            chunk_size = 1024 * 1024 
            
            with open(target_path, 'wb') as out_f:
                while bytes_left > 0:
                    to_read = min(chunk_size, bytes_left)
                    chunk = f.read(to_read)
                    if not chunk:
                        break # Failsafe for unexpected End Of File
                    out_f.write(chunk)
                    bytes_left -= len(chunk)

            print(f"  [+] Extracted: {clean_filename} ({file_size} bytes)")

    print("\n[*] Unpacking complete!")

if __name__ == "__main__":
    print("===================================================")
    print("  Terminal Reality Infernal Engine .POD Extractor")
    print("===================================================")
    
    if len(sys.argv) < 2:
        print("\nUsage: Drag and drop a .POD archive onto this script or run via CLI: [python InfernalPODExtractor.py <COMMON.POD>].")
        input("\nPress Enter to exit...")
        sys.exit(1)

    target_file = sys.argv[1]
    
    try:
        extract_pod(target_file)
    except Exception as e:
        print(f"\n[!] A fatal error occurred: {e}")

    input("\nPress Enter to exit...")