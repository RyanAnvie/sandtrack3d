# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 23:20:53 2024

@author: Desktop
"""

import cv2
import numpy as np
import glob
import os
import piexif

# Global variables
points = []  # Store the selected points
window_name = "Select 4 Points"

# Mouse callback function to capture points
def select_points(event, x, y, flags, param):
    global points, img_display
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))
        cv2.circle(img_display, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow(window_name, img_display)
        if len(points) == 4:
            print("4 points selected:", points)

# Mask outside the selected region
def mask_outside_area(img, points):
    mask = np.zeros_like(img, dtype=np.uint8)
    pts = np.array(points, dtype=np.int32)
    cv2.fillPoly(mask, [pts], (255, 255, 255))  # Fill the polygon with white
    masked_img = cv2.bitwise_and(img, mask)
    return masked_img

# Read EXIF data from an image
def read_exif(image_path):
    try:
        exif_data = piexif.load(image_path)
        return exif_data
    except Exception as e:
        print(f"Could not read EXIF data: {e}")
        return None

# Write EXIF data to a new image
def write_exif(image_path, exif_data):
    try:
        exif_bytes = piexif.dump(exif_data)
        piexif.insert(exif_bytes, image_path)
    except Exception as e:
        print(f"Could not write EXIF data: {e}")

# --- Execution starts here ---
# Folder containing 1500 images
input_folder = r"D:\Ryan\Jetson_orin_nano\image_collection"
output_root_folder = r"D:\Ryan\Jetson_orin_nano\image_collection_mask"
os.makedirs(output_root_folder, exist_ok=True)

# Load all image paths
image_paths = glob.glob(os.path.join(input_folder, "**", "*002.jpg"), recursive=True)
image_paths = image_paths[:1500]  # Process first 1500 images
image_paths.sort()

if len(image_paths) == 0:
    print("No images found!")
    exit()

print(f"Total images to process: {len(image_paths)}")

# Load the first image for point selection
img = cv2.imread(image_paths[0])
if img is None:
    print("Error: Could not load the first image!")
    exit()

img_display = img.copy()

# Display the first image and set mouse callback
cv2.imshow(window_name, img_display)
cv2.setMouseCallback(window_name, select_points)

print("Please click 4 points on the first image to define the mask...")
while True:
    if len(points) == 4:
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Program terminated by user.")
        cv2.destroyAllWindows()
        exit()

cv2.destroyAllWindows()

# Create the mask using the 4 selected points
mask = np.zeros_like(img, dtype=np.uint8)
pts = np.array(points, dtype=np.int32)
cv2.fillPoly(mask, [pts], (255, 255, 255))

# Process all images
for idx, img_path in enumerate(image_paths):
    print(f"Processing {idx + 1}/{len(image_paths)}: {img_path}")

    # Read the image
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error reading {img_path}")
        continue

    # Read EXIF data
    exif_data = read_exif(img_path)

    # Apply the mask
    masked_img = cv2.bitwise_and(img, mask)

    # Generate new output path dynamically
    output_subfolder = os.path.join(output_root_folder, f"image_set_{str(idx + 1).zfill(4)}")
    os.makedirs(output_subfolder, exist_ok=True)  # Ensure subfolder exists
    output_path = os.path.join(output_subfolder, "image_json_002.jpg")

    # Save the masked image
    cv2.imwrite(output_path, masked_img)

    # Write EXIF data to the output image
    if exif_data:
        write_exif(output_path, exif_data)

print("Processing completed. Masked images saved with EXIF data intact.")


