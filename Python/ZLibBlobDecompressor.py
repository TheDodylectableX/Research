#------------------------------------------------------------------------------
# ZLib Data Blob Decompressor
#------------------------------------------------------------------------------
# This is for files sliced out of a hex editor directly or something adjacent.
# Usage: Drag and drop the extracted blob on top of this script
#------------------------------------------------------------------------------

import os, sys, zlib, array
from pathlib import Path
from typing import Optional, Tuple

def execute_decompression(data: bytes, wbits: int) -> Optional[bytes]:
    try:
        decompressor = zlib.decompressobj(wbits)
        unpacked = decompressor.decompress(data)
        # Verify we actually produced an output stream
        if unpacked and len(unpacked) > 0:
            return unpacked
    except (zlib.error, ValueError, MemoryError):
        pass
    return None

def try_compression_format(data: bytes) -> Optional[Tuple[bytes, str]]:
    formats = {
        15: "Standard Zlib Stream",
        -15: "Raw DEFLATE Stream",
        31: "Gzip Archive Stream"
    }

    for wbits, fmt_name in formats.items():
        result = execute_decompression(data, wbits)
        if result: return result, fmt_name

    return None

def process_buffer(raw_bytes: bytes) -> Tuple[Optional[bytes], str]:
    if not raw_bytes: return None, "Empty Buffer"

    # --- Pass 1: Check Native Data Stream ---
    outcome = try_compression_format(raw_bytes)
    if outcome: return outcome

    # --- Pass 2: Check 16-bit (Short) Word Swapping ---
    # Common when console memory states or file systems dump 2-byte swapped pairs
    if len(raw_bytes) % 2 == 0:
        try:
            short_array = array.array('H', raw_bytes)
            short_array.byteswap()
            swapped_16 = short_array.tobytes()
            outcome = try_compression_format(swapped_16)
            if outcome: return outcome[0], f"{outcome[1]} (Fixed via 16-bit ByteSwap)"
        except (ValueError, OverflowError):
            pass

    # --- Pass 3: Check 32-bit (Int) Word Swapping ---
    # Common on Big-Endian architectures (Xbox 360 / PS3) where raw 4-byte values are inverted
    if len(raw_bytes) % 4 == 0:
        try:
            int_array = array.array('I', raw_bytes)
            int_array.byteswap()
            swapped_32 = int_array.tobytes()
            outcome = try_compression_format(swapped_32)
            if outcome: return outcome[0], f"{outcome[1]} (Fixed via 32-bit ByteSwap)"
        except (ValueError, OverflowError):
            pass

    return None, "Unrecognized Compression Format or Corrupted File Data"

def main():
    if len(sys.argv) < 2:
        print("Usage: Drag and drop a file onto this script or run via CLI: [python ZLibBlobDecompressor.py <compressed_file> <decompressed_file>].")
        input("\nPress Enter to exit...")
        sys.exit(1)

    for file_str in sys.argv[1:]:
        input_path = Path(file_str).resolve()
        if not input_path.is_file():
            print(f"[-] Skipped: '{input_path.name}' is not a valid file.")
            continue

        print(f" Analyzing: {input_path.name} ({input_path.stat().st_size} bytes)...")

        try:
            with open(input_path, "rb") as f:
                raw_payload = f.read()

            decompressed_data, status_msg = process_buffer(raw_payload)

            if decompressed_data:
                output_name = f"{input_path.stem}_uncompressed{input_path.suffix}"
                output_path = input_path.with_name(output_name)

                with open(output_path, "wb") as out_f:
                    out_f.write(decompressed_data)

                print(f"    Detected: {status_msg}")
                print(f"    Extracted: {output_path.name} ({len(decompressed_data)} bytes)\n")
            else:
                print(f"    Failed: {status_msg}\n")

        except IOError as ioe:
            print(f"    Disk I/O Crash: {ioe}\n")
        except Exception as e:
            print(f"    Unexpected anomaly: {e}\n")

if __name__ == "__main__":
    main()
