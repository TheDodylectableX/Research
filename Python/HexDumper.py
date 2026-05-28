#-------------------------------------------------------------------
# Hex Dumper
#-------------------------------------------------------------------
# Usage: Drag and drop the target binary file on top of this script
#-------------------------------------------------------------------

import sys
from pathlib import Path

def generate_hex_dump(file_path, bytes_per_line=16):
    target_path = Path(file_path)

    if not target_path.is_file():
        print(f"[!] Error: File not found -> {target_path}")
        return

    # Create the output text file name (e.g., massive_mesh.smb.hex.txt)
    out_path = target_path.with_suffix(target_path.suffix + '.hex.txt')

    print(f"[*] Generating Hex Dump for: {target_path.name}")
    print(f"[*] This might take a second for larger files...")

    # Performance Consideration: Read/Write in chunks
    # We read exactly enough bytes to fill one line at a time to keep RAM usage negligible.
    try:
        with open(target_path, 'rb') as f_in, open(out_path, 'w', encoding='utf-8') as f_out:
            offset = 0

            while True:
                chunk = f_in.read(bytes_per_line)
                if not chunk: break # EOF reached

                # 1. Format the offset (e.g., 00000140)
                offset_str = f"{offset:08X}"

                # 2. Format the hex bytes (e.g., 02 00 00 00 3C 01...)
                # We pad with spaces if the final chunk is less than bytes_per_line
                hex_str = ' '.join(f"{b:02X}" for b in chunk)
                hex_padding = '   ' * (bytes_per_line - len(chunk))

                # 3. Format the ASCII representation
                # Edge Case Handling: Replace non-printable ASCII with a dot '.'
                # 32 (space) to 126 (tilde) are standard readable characters
                ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)

                # Combine and write the line
                line = f"{offset_str}  {hex_str}{hex_padding}  |{ascii_str}|\n"
                f_out.write(line)

                offset += len(chunk)

        print(f"[+] Success! Dump saved to: {out_path.name}")

    except Exception as e:
        print(f"[!] A fatal error occurred: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("[!] Usage: Drag and drop any file onto this script to generate a hex dump.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    target_file = sys.argv[1]
    generate_hex_dump(target_file)
    input("\nPress Enter to exit...")
