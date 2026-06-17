# ==================================================================================
# DEATHLOOP Sound Resource to WWise Encoded Media Conversion Script
# This script converts the game's audio format (*.sr) to WWise audio format (*.wem)
# Then you can use the output result in any program / plugin / utility to convert it
# To OGG Vorbis or any other format it can decode to like vgmstream or ww2ogg etc.
# ==================================================================================

import os, struct, sys
LOG_FILENAME = "soundresource_conversion_log.txt"

def log_message(message):
    """Prints a message to the console and writes it to the log file."""
    print(message)
    with open(LOG_FILENAME, "a", encoding="utf-8") as log_file: log_file.write(message + "\n")

# ====================
# Conversion Pipeline
# ====================

def process_sr_file(sr_path, index, total_files):
    """Process the Sound Resource files."""
    try:
        with open(sr_path, "rb") as f: data = f.read()

        if len(data) < 8:
            log_message(f"[ERROR] {sr_path}: File is too small to process.")
            return
        
        # Read the first 4 bytes as an unsigned integer
        sound_ID = struct.unpack("<I", data[:4])[0]

        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(sr_path))[0]

        # Construct the new filename
        wem_filename = f"{base_name}_ID_{sound_ID}.wem"
        wem_path = os.path.join(os.path.dirname(sr_path), wem_filename)

        # Write the remaining data after the first 8 bytes
        with open(wem_path, "wb") as f: f.write(data[8:])

        log_message(f"\n[INFO] Processing Sound Resource {index} of {total_files}")
        log_message(f"[INFO] Original Sound Resource: {sr_path}")
        log_message(f"[INFO] Sound Resource uses the following ID: {sound_ID}")
        log_message(f"[SUCCESS] Processed WEM: {wem_path}\n")

    except Exception as e: log_message(f"[ERROR] {sr_path}: {e}")

# ==================================================================================

if __name__ == "__main__":
    with open(LOG_FILENAME, "w", encoding="utf-8") as log_file: log_file.write("DEATHLOOP Sound Resource Audio Conversion Script Log\n\n")

    log_message("DEATHLOOP Sound Resource (*.sr) Audio Conversion Script")

    if len(sys.argv) < 2:
        log_message("\nNo Sound Resources were detected!")
        log_message("Drag and drop *.sr files onto this script to process them.\n")
    else:
        sr_files = [file_path for file_path in sys.argv[1:] if file_path.lower().endswith(".sr")]
        total_files = len(sr_files)

        if total_files == 0: log_message("[WARNING] No valid *.sr files detected!\n")
        else:
            for index, file_path in enumerate(sr_files, start=1): process_sr_file(file_path, index, total_files)

    log_message("Processing complete! Press any key to exit...")
    input() # Keep the window open until any key is pressed

# ==================================================================================
