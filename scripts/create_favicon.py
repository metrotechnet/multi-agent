#!/usr/bin/env python3
"""
Utility script to generate favicon for Dok2u Multi-Agent
Generates favicon.ico with 'Ben' text on blue background
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_favicon():
    """Generate favicon with Ben branding"""
    output_path = Path(__file__).parent.parent / "static" / "favicon.ico"

    
    # Create high-quality base image
    size = 256
    img = Image.new('RGB', (size, size), color='#6366f1')
    draw = ImageDraw.Draw(img)
    
    # Load font with fallback
    try:
        font = ImageFont.truetype("arial.ttf", 140)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 140)
        except OSError:
            font = ImageFont.load_default()
    
    # Center text
    text = "Ben"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
    
    draw.text((x, y), text, fill='white', font=font)
    
    # Save multi-size favicon
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format='ICO', sizes=sizes)
    
    print(f"✅ Favicon created: {output_path}")
    return output_path

if __name__ == "__main__":
    create_favicon()
