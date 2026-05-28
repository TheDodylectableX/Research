#--------------------------------------------------------------------
# Ubisoft JADE Engine .BIN Decompressor
#--------------------------------------------------------------------
# Supports only the three Prince of Persia games and TMNT 2007
# Usage: Drag and drop the extracted .bin file on top of this script
#--------------------------------------------------------------------
# REQUIRES LZO MODULE TO BE INSTALLED!
#--------------------------------------------------------------------

import os, sys, struct

try: import lzo
except ImportError:
    print("[!] Error: 'lzo' module not found.")
    print("    Please install it using: pip install python-lzo")
    sys.exit(1)

def extract_jade_bin(input_path):
    # Enforce the requested output naming convention: (filename)_decompressed.bin
    base_name = os.path.splitext(input_path)[0]
    output_path = f"{base_name}_decompressed.bin"

    if not os.path.exists(input_path):
        print(f"[!] Error: File '{input_path}' does not exist.")
        return

    with open(input_path, 'rb') as f_in:
        # 1. Read DVD Sector Wrapper (4 bytes)
        sector_data = f_in.read(4)
        if len(sector_data) < 4:
            print("[!] Error: File too small to contain a sector wrapper.")
            return

        sector_data_size = struct.unpack('<I', sector_data)[0]

        # 2. Check for the Developer Sentinel / Version Tag
        sentinel_data = f_in.read(4)
        sentinel_check = struct.unpack('<I', sentinel_data)[0]
        
        if sentinel_check == 0x78563412: # 0x12345678 in Little-Endian
            print("[-] Sentinel 'Version Tag' detected. This is not a compressed file.")
            return
        
        f_in.seek(4) # Rewind past the sentinel check

        print(f"[+] Expanding: {os.path.basename(input_path)}")
        
        total_uncompressed = 0
        chunk_count = 0

        with open(output_path, 'wb') as f_out:
            # 3. The Extraction Loop
            # We strictly respect the DVD sector limit to avoid trailing garbage
            while f_in.tell() < (sector_data_size + 4):
                header = f_in.read(8)
                if len(header) < 8: break
                
                uncompressed_size, compressed_size = struct.unpack('<II', header)

                # Break Condition: Double-Zero Marker
                if uncompressed_size == 0 and compressed_size == 0:
                    print(f"[-] Zero-marker detected at 0x{f_in.tell() - 8:X}. Halting chunk read.")
                    break
                
                if compressed_size == 0: continue

                # Read exact payload without pulling in DVD sector padding
                compressed_payload = f_in.read(compressed_size)
                if len(compressed_payload) < compressed_size:
                    print("[!] Warning: Unexpected end of file during payload read.")
                    break

                # 4. Execute LZO Decompression
                try:
                    # LZO expects: data, optimize_flag, uncompressed_size
                    decompressed_payload = lzo.decompress(compressed_payload, False, uncompressed_size)
                    
                    if len(decompressed_payload) != uncompressed_size: print(f"[!] Warning: Chunk {chunk_count} size mismatch. Expected {uncompressed_size}, got {len(decompressed_payload)}")
                    
                    # Instantly flush to disk to maintain O(1) memory scaling
                    f_out.write(decompressed_payload)
                    total_uncompressed += len(decompressed_payload)
                    chunk_count += 1

                except Exception as e:
                    print(f"[!] LZO Decompression error at Chunk {chunk_count} (File Offset: 0x{f_in.tell() - compressed_size:X}):")
                    print(f"    {e}")
                    print("    Aborting to prevent corrupt output.")
                    break

        print(f"    -> Extracted {chunk_count} chunks.")
        print(f"    -> Total Uncompressed: {total_uncompressed} bytes.")
        print(f"    -> Saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2: print("Usage: python jade_extractor.py <input.bin>")
    else: extract_jade_bin(sys.argv[1])
