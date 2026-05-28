#---------------------------------------------------------
# Monolith Productions LithTech Engine .REZ Extractor
#---------------------------------------------------------

import os, struct, sys
from pathlib import Path

class RezExtractor:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.output_dir = self.filepath.parent / f"{self.filepath.stem}_extracted"
        self.f = open(self.filepath, "rb")

    def read_u32(self):
        return struct.unpack("<I", self.f.read(4))[0]

    def read_string(self):
        chars = []
        while True:
            c = self.f.read(1)
            if not c or c == b"\x00":
                break
            chars.append(c)
        return b"".join(chars).decode("utf-8", errors="ignore")

    def parse_header(self):
        self.f.seek(127, os.SEEK_SET)
        self.version = self.read_u32()
        self.root_offset = self.read_u32()
        self.root_size = self.read_u32()
        self.f.seek(28, os.SEEK_CUR) 
        
        print(f"--- Archive Metadata ---")
        print(f"Version: {self.version}")
        print(f"Root Offset: {hex(self.root_offset)}")
        print(f"Root Size: {self.root_size} bytes\n")

    def extract_directory(self, offset, size, current_path):
        self.f.seek(offset)
        block_end = offset + size
        current_path.mkdir(parents=True, exist_ok=True)

        while self.f.tell() < block_end:
            entry_type = self.read_u32()
            
            if entry_type == 1: # DIRECTORY
                dir_offset = self.read_u32()
                dir_size = self.read_u32()
                time_stamp = self.read_u32()
                name = self.read_string()
                
                print(f"[DIR]  {name}")
                
                return_pos = self.f.tell()
                self.extract_directory(dir_offset, dir_size, current_path / name)
                self.f.seek(return_pos)
                
            elif entry_type == 0: # FILE
                file_offset = self.read_u32()
                file_size = self.read_u32()
                time_stamp = self.read_u32()
                file_id = self.read_u32()
                
                # FIX: Read and clean extension
                raw_ext = self.f.read(4)
                # Reverse, decode, and strip nulls/whitespace
                extension = raw_ext.decode("utf-8", errors="ignore")[::-1].strip('\x00').strip()
                
                padding = self.read_u32()
                name = self.read_string()
                
                # Jupiter null-alignment check
                pos = self.f.tell()
                if pos < os.path.getsize(self.filepath):
                    if self.f.read(1) != b"\x00": self.f.seek(pos)

                # Construct final filename
                clean_name = name.strip()
                if extension: full_filename = f"{clean_name}.{extension}"
                else: full_filename = clean_name # No extension if it's all nulls

                print(f"[FILE] {full_filename} ({file_size} bytes)")
                
                # Extraction
                return_pos = self.f.tell()
                try:
                    self.f.seek(file_offset)
                    data = self.f.read(file_size) if file_size > 0 else b""
                    
                    with open(current_path / full_filename, "wb") as out_file:
                        out_file.write(data)
                except Exception as e:
                    print(f"  ! Error extracting {full_filename}: {e}")
                
                self.f.seek(return_pos)

    def run(self):
        self.parse_header()
        if self.root_offset > 0:
            self.extract_directory(self.root_offset, self.root_size, self.output_dir)
            print(f"\nDone! Extracted to: {self.output_dir}")
        self.f.close()

if __name__ == "__main__":
    print("=======================================================")
    print("  Monolith Productions LithTech Engine .REZ Extractor")
    print("=======================================================")

    if len(sys.argv) < 2:
        print("\nUsage: Drag and drop a .REZ archive onto this script or run via CLI: [python LithTechREZExtractor.py <NOLF.REZ>].")
        input("\nPress Enter to exit...")
        sys.exit(1)
    else:
        for arg in sys.argv[1:]:
            RezExtractor(arg).run()
    input("\nPress Enter to exit...")