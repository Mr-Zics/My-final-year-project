"""
Helper script to convert all report screenshots (PNG/JPG) in a directory
to greyscale using Pillow, saving them into a 'grayscale' subfolder.
Required by Specification Section 9.6.
"""

import os
import sys
from pathlib import Path
from PIL import Image

def convert_to_grayscale(folder_path="."):
    target_dir = Path(folder_path).resolve()
    if not target_dir.exists():
        print(f"Error: Target directory '{target_dir}' does not exist.")
        return

    output_dir = target_dir / "grayscale"
    output_dir.mkdir(exist_ok=True)

    extensions = {".png", ".jpg", ".jpeg"}
    processed = 0

    for item in target_dir.iterdir():
        if item.is_file() and item.suffix.lower() in extensions:
            try:
                with Image.open(item) as img:
                    gray_img = img.convert("L")
                    out_path = output_dir / item.name
                    gray_img.save(out_path)
                    print(f"Converted: {item.name} -> grayscale/{item.name}")
                    processed += 1
            except Exception as e:
                print(f"Failed to convert {item.name}: {e}")

    print(f"\nCompleted! {processed} screenshot(s) converted to greyscale in: {output_dir}")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    convert_to_grayscale(folder)
