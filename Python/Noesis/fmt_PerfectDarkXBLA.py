#--------------------------------------------------------------------------------------------------------------
#--- Perfect Dark Remastered "PackedSegFile" and "Textures.raw" plugin for Rich Whitehouse's Noesis
#
#      File: fmt_PerfectDarkXBLA.py
#    Author: Dodylectable
#   Version: 1.0
#   Purpose: To import and export files from Perfect Dark Remastered (XBLA Port by 4J Studios)
#   Credits: kholdfuzion, shalashaka, tjoener, neptuwunium
#      Note: You have to rename "PackedSegFile" archive and give it ".psf" at the end so Noesis can see it!
#--------------------------------------------------------------------------------------------------------------

from inc_noesis import *

# ----------------------
# Options:
FLIP_IMAGES_VERTICALLY = True # Switch it to False if you want it to match the originals
# ----------------------

#-----------------------------------------------------------------------------

def registerNoesisTypes():
    handle = noesis.register("Perfect Dark XBLA 'PackedSegFile'", ".psf")
    noesis.setHandlerTypeCheck(handle, pdArchiveCheck)
    noesis.setHandlerExtractArc(handle, pdPSFArchive)

    handle = noesis.register("Perfect Dark XBLA 'Textures.raw'", ".raw")
    noesis.setHandlerTypeCheck(handle, pdArchiveCheck)
    noesis.setHandlerExtractArc(handle, pdTexturesArchive)

    noesis.logPopup()
    return 1

#-----------------------------------------------------------------------------
#---------------
# Format Checks
#---------------

def pdArchiveCheck(data):
    fileName = rapi.getLocalFileName(rapi.getInputName()).lower()
    if "packedsegfile" in fileName or "textures.raw" in fileName: return 1
    return 0

#-----------------------------------------------------------------------------
#---------------
# Helper Functions
#---------------

def lzx_decompression_wrapper(comp_data, uncomp_size):
    try:
        res = rapi.decompXMemLZX(comp_data, uncomp_size)
        if res: return res
    except: pass

    for w in (16, 15, 17):
        try:
            res = rapi.decompLZX(comp_data, uncomp_size, w)
            if res: return res
        except: pass

    if len(comp_data) > 4:
        try:
            res = rapi.decompXMemLZX(comp_data[4:], uncomp_size)
            if res: return res
        except: pass
        try:
            res = rapi.decompLZX(comp_data[4:], uncomp_size, 16)
            if res: return res
        except: pass

    return None

def safe_swap_endian(data, swap_size):
    if not data: return data
        
    rem = len(data) % swap_size
    if rem != 0: data += b'\x00' * (swap_size - rem)

    try:
        swapped = rapi.swapEndianArray(data, swap_size)
        if swapped: return swapped
    except:
        pass

    b = bytearray(data)
    if swap_size == 2:
        for i in range(0, len(b), 2): b[i], b[i+1] = b[i+1], b[i]
    elif swap_size == 4:
        for i in range(0, len(b), 4): b[i], b[i+1], b[i+2], b[i+3] = b[i+3], b[i+2], b[i+1], b[i]

    return bytes(b)

def process_dxt_blocks(data, width, height, fmt_id, flip):
    if not data or width == 0 or height == 0: return data

    w_blocks = (width + 3) // 4
    h_blocks = (height + 3) // 4
    block_size = 8 if fmt_id == 82 else 16

    # Calculate X360 Pitch padding (often aligns to Power of Two memory bounds)
    pot_w = 1 if width == 0 else 2**(width - 1).bit_length()
    pot_w_blocks = max(w_blocks, (pot_w + 3) // 4)

    read_w_blocks = w_blocks
    if len(data) >= pot_w_blocks * block_size * h_blocks: read_w_blocks = pot_w_blocks

    read_pitch = read_w_blocks * block_size
    if len(data) < read_pitch * h_blocks: return data # Fail-safe for truncated data

    processed_data = bytearray()
    y_range = range(h_blocks - 1, -1, -1) if flip else range(h_blocks)

    for y in y_range:
        start = y * read_pitch
        row_data = data[start : start + read_pitch]

        for x in range(w_blocks): # Only process visible PC blocks, shedding padding
            block_start = x * block_size
            b = row_data[block_start : block_start + block_size]

            if not flip: processed_data.extend(b)
            else:
                if fmt_id == 82: # DXT1: Swap 2-bit color index rows
                    processed_data.extend(b[0:4])
                    processed_data.extend(bytes([b[7], b[6], b[5], b[4]]))

                elif fmt_id == 83: # DXT3: Swap alpha rows then color rows
                    processed_data.extend(bytes([b[6], b[7], b[4], b[5], b[2], b[3], b[0], b[1]]))
                    processed_data.extend(b[8:12])
                    processed_data.extend(bytes([b[15], b[14], b[13], b[12]]))

                elif fmt_id == 84: # DXT5: Bit-shift 3-bit alpha indices then swap color rows
                    processed_data.extend(b[0:2])
                    I = int.from_bytes(b[2:8], 'little')
                    flipped_I = ((I & 0xFFF) << 36) | (((I >> 12) & 0xFFF) << 24) | (((I >> 24) & 0xFFF) << 12) | ((I >> 36) & 0xFFF)
                    processed_data.extend(flipped_I.to_bytes(6, 'little'))
                    processed_data.extend(b[8:12])
                    processed_data.extend(bytes([b[15], b[14], b[13], b[12]]))

    return bytes(processed_data)

def build_dds_header(width, height, data_size, fmt_id):
    header = bytearray(128)
    dwMagic = b'DDS '
    dwSize = 124
    dwFlags = 0x00081007 

    rgb_bitcount = 0
    r_mask = g_mask = b_mask = a_mask = 0

    if fmt_id == 83:
        ddspf_flags = 0x4 
        fourcc = b'DXT3'
    elif fmt_id == 84:
        ddspf_flags = 0x4 
        fourcc = b'DXT5'
    elif fmt_id == 134:
        ddspf_flags = 0x41 
        fourcc = b'\x00\x00\x00\x00' 
        rgb_bitcount = 32
        r_mask = 0x00FF0000
        g_mask = 0x0000FF00
        b_mask = 0x000000FF
        a_mask = 0xFF000000
    else:
        ddspf_flags = 0x4 
        fourcc = b'DXT1'

    struct.pack_into('<4sIIIIIII', header, 0, dwMagic, dwSize, dwFlags, height, width, data_size, 1, 1)
    struct.pack_into('<II4sIIIII', header, 76, 32, ddspf_flags, fourcc, rgb_bitcount, r_mask, g_mask, b_mask, a_mask)
    struct.pack_into('<I', header, 108, 0x1000)

    return bytes(header)

#-----------------------------------------------------------------------------
#---------------
# Extraction Handlers
#---------------

def pdPSFArchive(fileName, fileLen, justChecking):
    if justChecking: return 1

    with open(fileName, "rb") as f:
        bs = NoeBitStream(f.read())
        
    bs.setEndian(NOE_BIGENDIAN)
    fileCount = bs.readUInt()
    entries = []

    for i in range(fileCount):
        entries.append({
            "offset": bs.readUInt(),     
            "size": bs.readUInt(),       
            "sizeOnDisk": bs.readUInt(), 
            "parentID": bs.readUInt()
        })

    for i, entry in enumerate(entries):
        out_data = b''
        read_len = entry["sizeOnDisk"] if entry["sizeOnDisk"] > 0 else entry["size"]
        
        # Only attempt to read if there is actual data 
        if read_len > 0:
            if entry["offset"] < fileLen and entry["offset"] + read_len <= fileLen:
                bs.seek(entry["offset"], NOESEEK_ABS)

                if entry["sizeOnDisk"] == 0: out_data = bs.readBytes(entry["size"])
                else:
                    comp_data = bs.readBytes(entry["sizeOnDisk"])
                    decomp_data = lzx_decompression_wrapper(comp_data, entry["size"])

                    if decomp_data: out_data = decomp_data
                    else:
                        print("[PackedSegFile] Warning: File %d failed LZX decompression. Exporting raw compressed data." % i)
                        out_data = comp_data
            else: print("[PackedSegFile] Warning: File %d offset (0x%08X) out of bounds. Exporting empty file." % (i, entry["offset"]))

        filename_out = "seg_%04d_parent_%d.bin" % (i, entry['parentID'])
        rapi.exportArchiveFile(filename_out, out_data)

    return 1

#-----------------------------------------------------------------------------
    
def pdTexturesArchive(fileName, fileLen, justChecking):
    if justChecking: return 1

    with open(fileName, "rb") as f:
        bs = NoeBitStream(f.read())

    bs.setEndian(NOE_BIGENDIAN)
    fileCount = bs.readUInt()
    entries = []

    # Pass 1: Parse the TexSegment metadata
    for i in range(fileCount):
        entry = {
            "offset": bs.readUInt(),       
            "widthX360": bs.readUInt(),
            "heightX360": bs.readUInt(),
            "widthN64": bs.readUInt(),
            "heightN64": bs.readUInt(),
            "size": bs.readUInt(),         
            "sizeOnDisk": bs.readUInt(),   
            "parentID": bs.readUInt(),
            "unkA": bs.readUInt(),
            "unkB": bs.readUInt(),
            "padA": bs.readUInt(),
            "padB": bs.readUInt(),
            "unkC": bs.readUInt()
        }
        entries.append(entry)

    # Pass 1.5: Parse TexSegment2
    for i in range(fileCount):
        tex2 = {
            "v1": bs.readUInt(), "v2": bs.readUInt(), "v3": bs.readUInt(),
            "v4": bs.readUInt(), "v5": bs.readUInt(), "v6a": bs.readUShort(),
            "v6b": bs.readUShort(), "v7a": bs.readUShort(), "v7b": bs.readUShort(),
            "v8a": bs.readUShort(), "v8b": bs.readUShort(), "v9": bs.readUInt(),
            "v10": bs.readUInt(), "v11": bs.readUInt(), "v12": bs.readUInt(),
            "v13": bs.readUInt()
        }
        entries[i]["tex2"] = tex2

    baseOffset = bs.tell()

    # Pass 2: Extract and format the texture data
    for i, entry in enumerate(entries):
        read_len = entry["sizeOnDisk"] if entry["sizeOnDisk"] > 0 else entry["size"]

        absolute_offset = baseOffset + entry["offset"]
        if absolute_offset >= fileLen or absolute_offset + read_len > fileLen:
            if entry["offset"] + read_len <= fileLen: absolute_offset = entry["offset"]
            else:
                print("[Textures.raw] Skipping texture %d - Offset out of bounds." % i)
                continue

        bs.seek(absolute_offset, NOESEEK_ABS)

        if entry["sizeOnDisk"] == 0: out_data = bs.readBytes(entry["size"])
        else:
            comp_data = bs.readBytes(entry["sizeOnDisk"])
            out_data = lzx_decompression_wrapper(comp_data, entry["size"])

            if not out_data:
                print("[Textures.raw] Failed to decompress texture %d." % i)
                continue

        fmt_id = entry["tex2"]["v9"]
        tex_width = entry['widthX360'] if entry['widthX360'] > 0 else entry['widthN64']
        tex_height = entry['heightX360'] if entry['heightX360'] > 0 else entry['heightN64']

        if tex_width == 0 or tex_height == 0: continue

        # 1. Un-Tiling strictly for RAW formats
        if fmt_id == 134:
            try:
                untiled_data = rapi.imageUntile360Raw(out_data, tex_width, tex_height, 4)
                if untiled_data: out_data = untiled_data
            except: pass

        # 2. Endian Swap
        if fmt_id in (82, 83, 84): out_data = safe_swap_endian(out_data, 2)
        elif fmt_id == 134: out_data = safe_swap_endian(out_data, 4)
        else: out_data = safe_swap_endian(out_data, 2)

        # 3. Flips and NPOT Padding Management
        if fmt_id == 134:
            if FLIP_IMAGES_VERTICALLY:
                try:
                    out_data = rapi.imageFlipRGBA32(out_data, tex_width, tex_height, 0, 1)
                except: pass
        elif fmt_id in (82, 83, 84):
            # Process blocks mathematically to avoid Noesis image encoders altering the dimensions
            out_data = process_dxt_blocks(out_data, tex_width, tex_height, fmt_id, FLIP_IMAGES_VERTICALLY)

        # 4. Header Construction and Export
        dds_header = build_dds_header(tex_width, tex_height, len(out_data), fmt_id)
        final_file_data = dds_header + out_data

        filename_out = "tex_%04d_fmt_%d_%dx%d_parent_%d.dds" % (i, fmt_id, tex_width, tex_height, entry['parentID'])
        rapi.exportArchiveFile(filename_out, final_file_data)

    return 1
