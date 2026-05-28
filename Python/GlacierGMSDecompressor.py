#--------------------------------------------------------------------
# IO Interactive Glacier Engine .GMS Decompressor
#--------------------------------------------------------------------
# Usage: Drag and drop the extracted .gms file on top of this script
#--------------------------------------------------------------------

import os, sys, zlib, struct, argparse

class GMSDecompressor:
    HEADER_FORMAT = "<IIB" # Little-Endian: uint32 (uncompressed), uint32 (compressed), uint8 (flag)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, file_path: str):
        self.file_path = file_path

    def decompress(self) -> bytes:
        if not os.path.exists(self.file_path): raise FileNotFoundError(f"Target file not found: {self.file_path}")

        file_size = os.path.getsize(self.file_path)
        if file_size < self.HEADER_SIZE: raise ValueError("File is too small to contain a valid GMS header.")

        with open(self.file_path, 'rb') as f:
            header_data = f.read(self.HEADER_SIZE)
            uncompressed_size, compressed_size, flag = struct.unpack(self.HEADER_FORMAT, header_data)

            print(f"[*] Analyzing Header for: {os.path.basename(self.file_path)}")
            print(f"    - Expected Uncompressed Size: {uncompressed_size} bytes")
            print(f"    - Expected Compressed Size:   {compressed_size} bytes")
            print(f"    - Metadata Flag:              0x{flag:02X}")

            compressed_payload = f.read(compressed_size)

            # Using -zlib.MAX_WBITS to force raw DEFLATE decompression (RFC 1951)
            decompressor = zlib.decompressobj(-zlib.MAX_WBITS)

            try:
                decompressed_data = decompressor.decompress(compressed_payload)
                # Flush any remaining data in the buffer
                decompressed_data += decompressor.flush()
            except zlib.error as e:
                raise RuntimeError(f"Deflate decompression failed. Stream might be corrupted: {e}")

        # Validation
        actual_size = len(decompressed_data)
        if actual_size != uncompressed_size: print(f"[!] WARNING: Size mismatch! Expected {uncompressed_size}, got {actual_size}.")
        else: print("[+] Decompression successful and verified against header size.")

        return decompressed_data

    def save_decompressed(self, output_path: str):
        data = self.decompress()
        with open(output_path, 'wb') as f:
            f.write(data)
        print(f"[+] Saved decompressed payload to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Glacier 1 .GMS Archive Decompressor")
    parser.add_argument("input_file", help="Path to the compressed .GMS file")
    parser.add_argument("-o", "--output", help="Optional: Output file path. Defaults to <input>_decompressed.gms", default=None)
    
    args = parser.parse_args()
    
    input_path = args.input_file
    output_path = args.output if args.output else f"{os.path.splitext(input_path)[0]}_decompressed.gms"

    try:
        extractor = GMSDecompressor(input_path)
        extractor.save_decompressed(output_path)
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()