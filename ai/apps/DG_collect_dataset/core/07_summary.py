#!/usr/bin/env python3
"""
07_summary.py - Generate contact sheet and caption summary for dataset
Creates a visual overview of all images with their captions
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import math

# --- CONFIGURATION ---
SCRIPT_VERSION = "v4.0-dynamic-text-height"
PADDING = 15 
BACKGROUND_COLOR = (255, 255, 255)
FONT_COLOR = (0, 0, 0)
FONT_SIZE = 20 
MAX_IMAGE_DIMENSION = 2048 

# --- FONT CONFIGURATION ---
FONT_NAME = "Roboto"
FONT_FILENAME = "Roboto-Regular.ttf" 
# NOTE: Line spacing can be adjusted for tighter or looser text
LINE_SPACING_FACTOR = 1.1 

# --- UTILITY FUNCTION FOR TEXT WRAPPING ---
def get_wrapped_text_and_height(draw, text, font, max_width):
    """
    Wraps text to a max width and calculates the total required height.
    Returns: list of lines (str), total height (int)
    """
    if not text:
        return [], 0
    
    # Text is usually too wide, so we force wrap
    line_spacing = font.getbbox("Tg")[3] * LINE_SPACING_FACTOR
    
    lines = []
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        lines.append(text)
    else:
        words = text.split(' ')
        current_line = ""
        for word in words:
            # Check if adding the next word exceeds max width
            test_line = (current_line + " " + word).strip()
            
            # Using getsize or getbbox for PIL text width check
            if draw.textbbox((0, 0), test_line, font=font)[2] <= max_width:
                current_line = test_line
            else:
                # Start a new line
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)

    total_height = len(lines) * line_spacing
    return lines, int(total_height)


# --- IMAGE AND CAPTION LOADING ---
def load_image_and_caption(img_path, max_size):
    """Loads, resizes the image, and reads the corresponding caption text."""
    try:
        img = Image.open(img_path)
        original_width, original_height = img.size
        
        if original_width > max_size or original_height > max_size:
            ratio = min(max_size / original_width, max_size / original_height)
            new_size = (int(original_width * ratio), int(original_height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        base_name_no_ext = os.path.splitext(os.path.basename(img_path))[0]
        txt_filename = base_name_no_ext + ".txt"
        txt_path = os.path.join(os.path.dirname(img_path), txt_filename)
        
        caption_content = ""
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                caption_content = f.read().strip()
        
        image_label = os.path.basename(img_path)

        return img, image_label, txt_filename, caption_content

    except Exception as e:
        print(f"Warning: Could not process {img_path}. Skipping. Error: {e}")
        return None, None, None, None

# --- TEXT SUMMARY GENERATION ---
def generate_text_summary(file_data, dataset_folder_name, output_dir):
    """Creates the long combined text file, saving it to the output_dir."""
    
    output_text_path = os.path.join(output_dir, f"{dataset_folder_name}_caption_summary.txt")
    print(f"\nGenerating caption summary to: {output_text_path}")
    
    with open(output_text_path, 'w', encoding='utf-8') as outfile:
        outfile.write(f"--- CAPTION SUMMARY FOR DATASET: {dataset_folder_name} ---\n\n")
        
        for item in file_data:
            outfile.write(f"{item['txt_filename']}\n")
            outfile.write(f"{item['caption_content']}\n\n")
        
    print("Caption summary generation complete.")
    return output_text_path

# --- MAIN CONTACT SHEET LOGIC (DYNAMIC HEIGHTS) ---
def create_contact_sheet(folder_path, output_dir, max_image_dimension, dataset_name_override=None):
    """Generates the contact sheet, saving it to the output_dir."""
    # Use override name if provided, otherwise use folder name
    dataset_folder_name = dataset_name_override or os.path.basename(os.path.normpath(folder_path))
    
    print(f"--- Running Dataset Summarizer {SCRIPT_VERSION} ---")
    print(f"Processing dataset folder: {folder_path}")
    
    # Find and Sort Image Files
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']
    image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in image_extensions]

    if not image_paths:
        print("Error: No image files found in the selected directory.")
        return
    image_paths.sort()
    
    # --- Initialize Font for layout calculations ---
    try:
        font = ImageFont.truetype(FONT_FILENAME, FONT_SIZE) 
    except IOError:
        try:
            font = ImageFont.truetype(FONT_NAME, FONT_SIZE) 
        except IOError:
            print(f"Warning: Could not load '{FONT_NAME}' or '{FONT_FILENAME}'. Falling back to default font.")
            font = ImageFont.load_default()
    
    # Need a temporary ImageDraw object for text measurements
    temp_img = Image.new('RGB', (1, 1), 'white')
    draw = ImageDraw.Draw(temp_img)

    # --- 2. Load Images and Calculate Average Dimensions ---
    file_data = []
    total_image_width, total_image_height = 0, 0
    for img_path in image_paths:
        img, label, txt_file, content = load_image_and_caption(img_path, max_image_dimension)
        if img:
            total_image_width += img.width
            total_image_height += img.height
            
            # Temporarily store the label, will calculate height later
            file_data.append({'image': img, 'image_label': label, 'txt_filename': txt_file, 'caption_content': content, 'text_height': 0, 'wrapped_lines': []})

    if not file_data:
        print("Error: No images successfully loaded.")
        return
    
    num_images = len(file_data)
    
    # --- 3. Determine Optimal Layout (Square-seeking logic) ---
    # The complexity here is that the image widths *depend* on the column layout.
    
    # We will use the simple sqrt approach for a starting point for columns
    num_columns = math.ceil(math.sqrt(num_images))
    print(f"Using initial layout: {num_columns} columns.")


    # --- 4. Final Layout Calculation (Calculate real dimensions and dynamic heights) ---
    
    # Initialize structures for dimensions
    num_rows = math.ceil(num_images / num_columns)
    max_image_widths_per_column = [0] * num_columns
    row_heights = [] # Max image height in that row
    row_text_heights = [0] * num_rows # Max required text height in that row
    
    # Pass 1: Determine Max Image Widths and Max Image Heights per Row
    for i, item in enumerate(file_data):
        img = item['image']
        col_index = i % num_columns
        row_index = i // num_columns
        
        if img.width > max_image_widths_per_column[col_index]:
            max_image_widths_per_column[col_index] = img.width
        
        if row_index == len(row_heights):
            row_heights.append(img.height)
        elif img.height > row_heights[row_index]:
            row_heights[row_index] = img.height
            
    # Pass 2: Calculate Dynamic Text Height based on determined Column Widths
    for i, item in enumerate(file_data):
        col_index = i % num_columns
        row_index = i // num_columns
        
        # Max width the text can occupy is the widest image in its column
        max_text_width = max_image_widths_per_column[col_index]
        
        # Calculate wrapping and height
        lines, height = get_wrapped_text_and_height(draw, item['image_label'], font, max_text_width)
        
        # Update the item data and the max height required for the row
        item['text_height'] = height
        item['wrapped_lines'] = lines
        
        if height > row_text_heights[row_index]:
            row_text_heights[row_index] = height


    # Calculate Final Sheet Dimensions
    total_width = sum(max_image_widths_per_column) + PADDING * (num_columns + 1)
    
    # Total Height: Sum of row heights + Sum of max required text heights + (row count + 1 * PADDING)
    # Each row contributes: max(image_height) + max(text_height) + (2 * PADDING, one above image, one below text)
    total_height = sum(
        row_heights[r] + row_text_heights[r] + PADDING * 2
        for r in range(num_rows)
    ) + PADDING # Add one extra padding for the bottom edge of the sheet

    print(f"Final grid: {num_rows} rows x {num_columns} columns.")
    print(f"Final image size: {int(total_width)}x{int(total_height)} pixels.")

    # --- 5. Create Contact Sheet Image ---
    try:
        contact_sheet = Image.new('RGB', (int(total_width), int(total_height)), BACKGROUND_COLOR)
    except MemoryError:
        print(f"ERROR: MemoryError trying to create an image of size {int(total_width)}x{int(total_height)}. Try reducing MAX_IMAGE_DIMENSION.")
        return

    draw = ImageDraw.Draw(contact_sheet)
    # Font is already loaded from Step 3, but load again for drawing on the new image
    try:
        font = ImageFont.truetype(FONT_FILENAME, FONT_SIZE) 
    except IOError:
        try:
            font = ImageFont.truetype(FONT_NAME, FONT_SIZE) 
        except IOError:
            font = ImageFont.load_default()
    
    
    # Image drawing loop
    current_y, img_counter = PADDING, 0
    line_spacing = font.getbbox("Tg")[3] * LINE_SPACING_FACTOR

    for r in range(num_rows):
        current_x = PADDING
        
        # Vertical space needed for this specific row (Image + Text + Padding)
        row_vertical_space = row_heights[r] + row_text_heights[r] + PADDING * 2

        for c in range(num_columns):
            if img_counter < num_images:
                item = file_data[img_counter]
                img = item['image']
                
                # Paste the image (starts after top PADDING for the row)
                contact_sheet.paste(img, (current_x, current_y))

                # Draw the wrapped filename
                text_start_y = current_y + row_heights[r] + PADDING
                
                for line_num, line in enumerate(item['wrapped_lines']):
                    text_y_pos = text_start_y + (line_num * line_spacing)
                    draw.text((current_x, text_y_pos), line, fill=FONT_COLOR, font=font)

                current_x += max_image_widths_per_column[c] + PADDING
                img_counter += 1
        
        # Advance Y position to the start of the next row's top PADDING
        current_y += row_vertical_space

    # --- 6. Save Files (Overwrites by default) ---
    output_image_path = os.path.join(output_dir, f"{dataset_folder_name}_contact_sheet_summary.png")
    try:
        contact_sheet.save(output_image_path)
        print(f"\n--- Success! ---\nContact sheet saved to: {output_image_path}")
        
        generate_text_summary(file_data, dataset_folder_name, output_dir)
        
    except Exception as e:
        print(f"\nERROR: Failed to save contact sheet. Reason: {e}")


def run(slug):
    """
    Pipeline entry point - generates summary for the published dataset.
    """
    from pathlib import Path
    import utils
    
    config = utils.load_config(slug)
    if not config:
        print(f"⚠️ No config found for {slug}")
        return
    
    # Get the Windows destination path where 256 images were published
    DEST_APP_ROOT = Path("/mnt/c/AI/apps/musubi-tuner")
    DEST_DATASETS = DEST_APP_ROOT / "files" / "datasets"
    
    name = config.get('name', slug)
    
    # The 256 folder contains the final dataset
    dataset_folder = DEST_DATASETS / name / "256"
    output_dir = DEST_DATASETS  # Save summary files alongside the dataset folder
    
    if not dataset_folder.exists():
        print(f"⚠️ Dataset folder not found: {dataset_folder}")
        print("Skipping summary generation.")
        return
    
    print(f"\n--> [07_summary] Generating contact sheet and caption summary...")
    # Pass the person's name as the dataset_name override
    create_contact_sheet(str(dataset_folder), str(output_dir), MAX_IMAGE_DIMENSION, dataset_name_override=name)
    print(f"✅ Summary complete for: {name}")


def main():
    """Parses command-line arguments and runs the main function."""
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(__file__)} <dataset_folder_path>")
        print(f"Example: python {os.path.basename(__file__)} \"C:\\AI\\apps\\musubi-tuner\\files\\datasets\\Ed Milliband\"")
        sys.exit(1)

    folder_path = sys.argv[1]
    
    output_dir = os.path.abspath(os.path.join(folder_path, os.pardir))
    
    create_contact_sheet(folder_path, output_dir, MAX_IMAGE_DIMENSION)


if __name__ == '__main__':
    main()
