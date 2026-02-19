"""
Create a logo for the Translator agent
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
STATIC_FOLDER = PROJECT_ROOT / "static"

def create_translator_logo(size=400):
    """
    Create a translator logo with language symbols and translation arrows
    """
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors
    primary_color = (33, 150, 243, 255)  # Blue
    secondary_color = (76, 175, 80, 255)  # Green
    accent_color = (255, 152, 0, 255)    # Orange
    
    # Circle background
    circle_margin = size // 10
    draw.ellipse(
        [circle_margin, circle_margin, size - circle_margin, size - circle_margin],
        fill=(255, 255, 255, 255),
        outline=primary_color,
        width=6
    )
    
    # Calculate positions
    center_x = size // 2
    center_y = size // 2
    
    # Draw left text block (representing source language)
    left_x = center_x - size // 4
    left_y = center_y
    draw.rectangle(
        [left_x - 30, left_y - 40, left_x + 30, left_y + 40],
        fill=None,
        outline=secondary_color,
        width=4
    )
    # Draw horizontal lines representing text
    for i in range(-2, 3):
        y = left_y + (i * 12)
        draw.line([(left_x - 20, y), (left_x + 20, y)], fill=secondary_color, width=3)
    
    # Draw right text block (representing target language)
    right_x = center_x + size // 4
    right_y = center_y
    draw.rectangle(
        [right_x - 30, right_y - 40, right_x + 30, right_y + 40],
        fill=None,
        outline=accent_color,
        width=4
    )
    # Draw horizontal lines representing text
    for i in range(-2, 3):
        y = right_y + (i * 12)
        draw.line([(right_x - 20, y), (right_x + 20, y)], fill=accent_color, width=3)
    
    # Draw translation arrows (left to right and right to left)
    arrow_y_top = center_y - 20
    arrow_y_bottom = center_y + 20
    
    # Top arrow (left to right)
    arrow_start = left_x + 40
    arrow_end = right_x - 40
    draw.line([(arrow_start, arrow_y_top), (arrow_end, arrow_y_top)], fill=primary_color, width=5)
    # Arrowhead
    draw.polygon(
        [(arrow_end, arrow_y_top), (arrow_end - 15, arrow_y_top - 8), (arrow_end - 15, arrow_y_top + 8)],
        fill=primary_color
    )
    
    # Bottom arrow (right to left)
    draw.line([(arrow_end, arrow_y_bottom), (arrow_start, arrow_y_bottom)], fill=primary_color, width=5)
    # Arrowhead
    draw.polygon(
        [(arrow_start, arrow_y_bottom), (arrow_start + 15, arrow_y_bottom - 8), (arrow_start + 15, arrow_y_bottom + 8)],
        fill=primary_color
    )
    
    # Add language symbols - "A" on left, "字" style on right
    try:
        # Try to use a system font
        font_size = 60
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("segoeui.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Draw "A" (Latin) on left side
        text_a = "A"
        bbox_a = draw.textbbox((0, 0), text_a, font=font)
        text_width_a = bbox_a[2] - bbox_a[0]
        text_height_a = bbox_a[3] - bbox_a[1]
        draw.text(
            (left_x - text_width_a // 2, left_y - text_height_a // 2 - 10),
            text_a,
            fill=secondary_color,
            font=font
        )
        
        # Draw "字" (Chinese character) on right side
        text_zh = "字"
        bbox_zh = draw.textbbox((0, 0), text_zh, font=font)
        text_width_zh = bbox_zh[2] - bbox_zh[0]
        text_height_zh = bbox_zh[3] - bbox_zh[1]
        draw.text(
            (right_x - text_width_zh // 2, right_y - text_height_zh // 2 - 10),
            text_zh,
            fill=accent_color,
            font=font
        )
    except Exception as e:
        print(f"Font rendering skipped: {e}")
    
    return img

def main():
    print("Creating translator logo...")
    
    # Create logo
    logo = create_translator_logo(400)
    
    # Save as PNG
    output_path = STATIC_FOLDER / "logo-translator.png"
    logo.save(output_path, "PNG")
    print(f"✓ Logo saved to: {output_path}")
    
    # Also create a smaller version for favicon
    small_logo = create_translator_logo(128)
    small_output_path = STATIC_FOLDER / "logo-translator-small.png"
    small_logo.save(small_output_path, "PNG")
    print(f"✓ Small logo saved to: {small_output_path}")

if __name__ == "__main__":
    main()
