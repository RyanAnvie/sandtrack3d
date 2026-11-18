# -*- coding: utf-8 -*-
"""
Created on Thu Dec 12 10:33:05 2024

@author: rqy19
"""

import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
import os
import glob
from tqdm import tqdm
import time
import pyvista as pv

def read_vtu_as_array(file_path):
    # Create a reader for the .vtu file
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(file_path)
    reader.Update()

    # Get the unstructured grid data
    data = reader.GetOutput()

    # Extract points as a NumPy array
    points_vtk = data.GetPoints()
    points = vtk_to_numpy(points_vtk.GetData())

    # Extract cell connectivity (optional, for element connectivity)
    cells_vtk = data.GetCells()
    cells = vtk_to_numpy(cells_vtk.GetData())

    # Extract point or cell data (optional)
    point_data = {}
    for i in range(data.GetPointData().GetNumberOfArrays()):
        name = data.GetPointData().GetArrayName(i)
        array = vtk_to_numpy(data.GetPointData().GetArray(i))
        point_data[name] = array

    return points, cells, point_data

def filter_points_in_box(points, corner1, corner2):
    """
    Filters points that fall within a rectangular box defined by two corner points.

    Args:
        points (numpy.ndarray): Array of shape (N, 3), where each row is a 3D point (x, y, z).
        corner1 (tuple): Coordinates (x1, y1, z1) of the first corner.
        corner2 (tuple): Coordinates (x2, y2, z2) of the second corner.

    Returns:
        numpy.ndarray: Filtered points within the box.
    """
    # Calculate the bounds of the box
    x_min, x_max = min(corner1[0], corner2[0]), max(corner1[0], corner2[0])
    y_min, y_max = min(corner1[1], corner2[1]), max(corner1[1], corner2[1])
    
    # Filter points within the box
    in_box = (
        (points[:, 0] >= x_min) & (points[:, 0] <= x_max) &
        (points[:, 1] >= y_min) & (points[:, 1] <= y_max))
    
    return points[in_box]

# Example usage
# file_path = r"D:\sand_box_120frame\generated_data0000.vtu"  # Replace with your file path
vtk_data_list = []

# List all .vtk files in the directory
vtk_files = glob.glob(r"D:\Ryan\test\sand_box_120frame\*.vtu")
points_list = []
for file_name in tqdm(vtk_files):
    
    points, _, _ = read_vtu_as_array(file_name)
    points_list.append(points)

output_dir = r"D:\sand_box_colored_output"
os.makedirs(output_dir, exist_ok=True)

corner1 = (-105.6524, 135)  # First corner of the box
corner2 = (205.88, -57.159)  # Second corner of the box

for i, points_raw in enumerate(points_list):
    # Create a PyVista PolyData object
    points = filter_points_in_box(points_raw, corner1, corner2)
    point_cloud = pv.PolyData(points)
    point_cloud["Z-axis"] = points[:, 2]  # Color based on Z-axis

    # Convert PolyData to Unstructured Grid (required for .vtu format)
    unstructured_grid = point_cloud.cast_to_unstructured_grid()

    # Save the unstructured grid as a .vtu file
    output_file = os.path.join(output_dir, f"frame_{i:03d}.vtu")
    unstructured_grid.save(output_file)

    print(f"Saved: {output_file}")

#%%

import numpy as np
from scipy.spatial import KDTree
import pyvista as pv
from joblib import Parallel, delayed

def select_uniform_points(point_cloud, n):
    indices = np.linspace(0, len(point_cloud) - 1, n, dtype=int)
    return point_cloud[indices]

def group_points_by_z_optimized(point_cloud, selected_points, kd_tree, radius):
    return [point_cloud[kd_tree.query_ball_point(center, radius)] for center in selected_points]

def compute_distances_between_columns_parallel(columns_a, columns_b):
    def compute_column_distance(col_a, col_b):
        if len(col_a) == 0 or len(col_b) == 0:
            return []
        kd_tree_b = KDTree(col_b)
        dists, _ = kd_tree_b.query(col_a)
        return dists

    # Use parallel processing for each column
    distances = Parallel(n_jobs=-1)(delayed(compute_column_distance)(col_a, col_b)
                                     for col_a, col_b in zip(columns_a, columns_b))
    return distances

def visualize_distances(columns_a, distances):
    plotter = pv.Plotter()
    for i, (points, dists) in enumerate(zip(columns_a, distances)):
        if len(points) == 0 or len(dists) == 0:
            continue
        point_cloud = pv.PolyData(points)
        point_cloud["Distances"] = dists
        plotter.add_mesh(point_cloud, scalars="Distances", cmap="viridis", point_size=10)
    plotter.add_scalar_bar(title="Distances")
    plotter.show()

# Example Usage
np.random.seed(0)

# Generate two random point clouds
point_cloud_a = points_list[1]
point_cloud_b = points_list[20]

# Step 1: Select uniform points along Z-axis for the first point cloud
n = 60000  # Reduced number of points
selected_points = select_uniform_points(point_cloud_a, n)

# Step 2: Build KDTree once for both point clouds
kd_tree_a = KDTree(point_cloud_a)
kd_tree_b = KDTree(point_cloud_b)

# Step 3: Group points into columns for both point clouds
radius = 1.0
columns_a = group_points_by_z_optimized(point_cloud_a, selected_points, kd_tree_a, radius)
columns_b = group_points_by_z_optimized(point_cloud_b, selected_points, kd_tree_b, radius)

# Step 4: Compute distances in parallel
distances = compute_distances_between_columns_parallel(columns_a, columns_b)

# Step 5: Visualize distances
visualize_distances(columns_a, distances)

#%%

from scipy.spatial import KDTree
import numpy as np

def calculate_local_slope(points, k=5):
    """
    Calculate local slope for each point in a 3D point cloud.
    
    Args:
        points (numpy.ndarray): Array of shape (N, 3) representing x, y, z coordinates.
        k (int): Number of nearest neighbors to consider.
    
    Returns:
        numpy.ndarray: Array of local slope values in degrees.
    """
    kdtree = KDTree(points[:, :2])  # Only consider x and y for neighbors
    slopes = []

    for i, point in enumerate(points):
        # Find k nearest neighbors
        _, indices = kdtree.query(point[:2], k=k+1)  # Include point itself
        neighbors = points[indices]
        
        # Fit a plane to the neighbors (Ax + By + Cz + D = 0)
        A = np.c_[neighbors[:, 0], neighbors[:, 1], np.ones(neighbors.shape[0])]
        C, _, _, _ = np.linalg.lstsq(A, neighbors[:, 2], rcond=None)  # Plane coefficients

        # Normal vector to the plane
        normal = np.array([C[0], C[1], -1])
        normal /= np.linalg.norm(normal)  # Normalize

        # Slope angle (angle between the plane normal and the z-axis)
        slope_angle = np.degrees(np.arccos(np.dot(normal, [0, 0, 1])))
        slopes.append(slope_angle)

    return np.array(slopes)


def calculate_local_slope_optimized(points, k=30):

    # Build KDTree
    kdtree = KDTree(points[:, :2])
    slopes = np.zeros(points.shape[0])  # Initialize slope array

    # Query k+1 nearest neighbors for all points
    _, neighbors_idx = kdtree.query(points[:, :2], k=k+1)

    for i, indices in enumerate(neighbors_idx):
        # Extract neighbors
        neighbors = points[indices]

        # Construct the design matrix A and dependent variable Z
        A = np.c_[neighbors[:, 0], neighbors[:, 1], np.ones(neighbors.shape[0])]
        Z = neighbors[:, 2]

        # Perform least squares fitting
        C, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)

        # Compute the normal vector
        normal = np.array([C[0], C[1], -1])
        normal /= np.linalg.norm(normal)  # Normalize the normal vector

        # Calculate slope as the angle between the normal and the z-axis
        slopes[i] = np.degrees(np.arccos(np.dot(normal, [0, 0, 1])))

    return slopes

# Example usage
points = points_list[1]

slopes = calculate_local_slope_optimized(points)
print("Local slopes (degrees):", slopes)

#%%

import numpy as np
from scipy.spatial import KDTree

def create_grid(points, grid_size):
    """
    Create a grid to segment points in the XY plane.

    Args:
        points (numpy.ndarray): Array of shape (N, 3) representing x, y, z coordinates.
        grid_size (float): Size of each grid cell.

    Returns:
        dict: A dictionary where each key is a grid cell (i, j) and the value is an array of points in that cell.
    """
    # Determine grid bounds
    x_min, x_max = np.min(points[:, 0]), np.max(points[:, 0])
    y_min, y_max = np.min(points[:, 1]), np.max(points[:, 1])

    # Create bins for the grid
    x_bins = np.arange(x_min, x_max + grid_size, grid_size)
    y_bins = np.arange(y_min, y_max + grid_size, grid_size)

    # Assign points to grid cells
    x_indices = np.digitize(points[:, 0], x_bins)
    y_indices = np.digitize(points[:, 1], y_bins)

    # Group points by grid cell
    grid = {}
    for i, (x_idx, y_idx) in enumerate(zip(x_indices, y_indices)):
        cell = (x_idx, y_idx)
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(points[i])

    # Convert lists to numpy arrays
    for cell in grid:
        grid[cell] = np.array(grid[cell])

    return grid

def calculate_slope_per_grid(points, k):
    """
    Calculate a single representative slope for all points in a grid cell.

    Args:
        points (numpy.ndarray): Array of points in the grid cell.
        k (int): Number of nearest neighbors for local plane fitting (not used here directly).

    Returns:
        float: Representative slope (degrees) for the grid.
    """
    # Fit a plane to all points in the grid
    A = np.c_[points[:, 0], points[:, 1], np.ones(points.shape[0])]  # Design matrix
    Z = points[:, 2]  # Elevation values
    C, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)  # Plane coefficients

    # Compute the normal vector to the plane
    normal = np.array([C[0], C[1], -1])
    normal /= np.linalg.norm(normal)  # Normalize the normal vector

    # Calculate slope as the angle between the normal and the z-axis
    slope = np.degrees(np.arccos(np.dot(normal, [0, 0, 1])))

    return slope

def calculate_local_slope_with_grid(points, grid_size, k=30):
    """
    Divide points into grids and calculate a single slope for each grid.

    Args:
        points (numpy.ndarray): Array of shape (N, 3) representing x, y, z coordinates.
        grid_size (float): Size of each grid cell.
        k (int): Number of nearest neighbors for local plane fitting.

    Returns:
        dict: A dictionary where each key is a grid cell (i, j) and the value is the slope (degrees).
    """
    grid = create_grid(points, grid_size)  # Segment points into grids
    grid_slopes = {}

    for cell, cell_points in grid.items():
        if len(cell_points) < k + 1:
            # Skip cells with insufficient points
            grid_slopes[cell] = None
            continue
        grid_slopes[cell] = calculate_slope_per_grid(cell_points, k)

    return grid_slopes

# Example usage
points = points_list[1]
grid_size = 10  # Size of each grid cell in the XY plane

slopes = calculate_local_slope_with_grid(points, grid_size, k=30)
print("Local slopes (degrees):", slopes)

#%%
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import glob
import os


root_dir = r"D:\Ryan\Jetson_orin_nano\image_collection"

image_paths = glob.glob(os.path.join(root_dir, "image_set*", "image_json_000.jpg"), recursive=True)

# Sort the paths for consistent order
image_paths.sort()
images = [cv2.imread(p, cv2.IMREAD_GRAYSCALE) for p in image_paths[0:50]]
#%%
import cv2
import numpy as np
import glob
import os

# Root directory containing your image sets
root_dir = r"D:\Ryan\Jetson_orin_nano\image_collection"

# Gather all image paths
image_paths = glob.glob(os.path.join(root_dir, "image_set*", "image_json_000.jpg"))
image_paths.sort()  # Ensure paths are sorted in order

# Select the images between 300 and 400
image_paths = image_paths[300:400]  # Adjust to your index range

# Parameters for Shi-Tomasi corner detection
feature_params = dict(maxCorners=500, qualityLevel=0.01, minDistance=7, blockSize=7)

# Parameters for Lucas-Kanade optical flow
lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# Process images in the range [300, 400]
for i in range(len(image_paths) - 1):
    # Read consecutive images
    prev_img = cv2.imread(image_paths[i], cv2.IMREAD_GRAYSCALE)
    next_img = cv2.imread(image_paths[i + 1], cv2.IMREAD_GRAYSCALE)

    if prev_img is None or next_img is None:
        print(f"Error loading images: {image_paths[i]} or {image_paths[i+1]}")
        continue

    # Detect good features to track in the first image
    p0 = cv2.goodFeaturesToTrack(prev_img, mask=None, **feature_params)

    # # Limit to the first 50 feature points
    # if p0 is not None and len(p0) > 50:
    #     p0 = p0[:50]

    # Calculate optical flow using Lucas-Kanade method
    p1, st, err = cv2.calcOpticalFlowPyrLK(prev_img, next_img, p0, None, **lk_params)

    # Select good points
    good_old = p0[st == 1]
    good_new = p1[st == 1]

    # Create an image to draw the flow
    output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)

    # Draw the displacement vectors for the first 50 points
    for new, old in zip(good_new, good_old):
        a, b = new.ravel()  # New point coordinates
        c, d = old.ravel()  # Old point coordinates
        cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 2)
        cv2.circle(output_img, (int(a), int(b)), 3, (0, 0, 255), -1)

    # Display the result
    cv2.imshow(f"Optical Flow - Frame {300 + i} to {300 + i + 1}", output_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()


#%%
import cv2
import numpy as np
import glob
import os

# Root directory containing your image sets
root_dir = r"D:\Ryan\Jetson_orin_nano\image_collection"

# Gather all image paths
image_paths = glob.glob(os.path.join(root_dir, "image_set*", "image_json_000.jpg"))
image_paths.sort()  # Ensure paths are sorted in order

# Select the images between 300 and 400
image_paths = image_paths  # Adjust to your index range

# Parameters for Shi-Tomasi corner detection
feature_params = dict(maxCorners=500, qualityLevel=0.01, minDistance=7, blockSize=7)

# Parameters for Lucas-Kanade optical flow
lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# Video writer setup
output_video_path = r"D:\Ryan\Jetson_orin_nano\optical_flow_video.avi"
frame_width, frame_height = None, None  # Initialize frame dimensions

# Define codec and create VideoWriter
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec for AVI file
video_writer = None  # Initialize writer later when frame dimensions are known

# Process images in the range [300, 400]
for i in range(len(image_paths) - 1):
    # Read consecutive images
    prev_img = cv2.imread(image_paths[i], cv2.IMREAD_GRAYSCALE)
    next_img = cv2.imread(image_paths[i + 1], cv2.IMREAD_GRAYSCALE)

    if prev_img is None or next_img is None:
        print(f"Error loading images: {image_paths[i]} or {image_paths[i+1]}")
        continue

    # Set frame dimensions for the video writer
    if frame_width is None or frame_height is None:
        frame_height, frame_width = prev_img.shape
        video_writer = cv2.VideoWriter(output_video_path, fourcc, 10, (frame_width, frame_height))

    # Detect good features to track in the first image
    p0 = cv2.goodFeaturesToTrack(prev_img, mask=None, **feature_params)

    # Calculate optical flow using Lucas-Kanade method
    p1, st, err = cv2.calcOpticalFlowPyrLK(prev_img, next_img, p0, None, **lk_params)

    # Select good points
    good_old = p0[st == 1]
    good_new = p1[st == 1]

    # Create an image to draw the flow
    output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)

    # Draw the displacement vectors for the first 50 points
    for new, old in zip(good_new, good_old):
        a, b = new.ravel()  # New point coordinates
        c, d = old.ravel()  # Old point coordinates
        cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 2)
        cv2.circle(output_img, (int(a), int(b)), 3, (0, 0, 255), -1)

    # Write the frame to the video
    video_writer.write(output_img)

    print(f"Processed frame {i + 1} / {len(image_paths) - 1}")

# Release the video writer
video_writer.release()
print(f"Video saved at: {output_video_path}")

#%%
import cv2
import numpy as np
import glob
import os

# Root directory containing your image sets
root_dir = r"D:\Ryan\Jetson_orin_nano\image_collection"

# Gather all image paths
image_paths = glob.glob(os.path.join(root_dir, "image_set*", "image_json_000.jpg"))
image_paths.sort()  # Ensure paths are sorted in order

# Select the images between 300 and 400
image_paths = image_paths

# Parameters for Lucas-Kanade optical flow
lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# SIFT feature detector
sift = cv2.SIFT_create()

# Video writer setup
output_video_path = r"D:\Ryan\Jetson_orin_nano\sift_optical_flow_video.avi"
video_writer = None
frame_width, frame_height = None, None

# Process images in the range [300, 400]
for i in range(len(image_paths) - 1):
    # Read consecutive images
    prev_img = cv2.imread(image_paths[i], cv2.IMREAD_GRAYSCALE)
    next_img = cv2.imread(image_paths[i + 1], cv2.IMREAD_GRAYSCALE)

    if prev_img is None or next_img is None:
        print(f"Error loading images: {image_paths[i]} or {image_paths[i+1]}")
        continue

    # Initialize video writer if not already done
    if video_writer is None:
        frame_height, frame_width = prev_img.shape
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter(output_video_path, fourcc, 10, (frame_width, frame_height))

    # Detect SIFT keypoints and descriptors in the first image
    keypoints, descriptors = sift.detectAndCompute(prev_img, None)

    # Convert keypoints to numpy array of points (x, y) for Lucas-Kanade
    p0 = np.array([kp.pt for kp in keypoints], dtype=np.float32).reshape(-1, 1, 2)

    # Calculate optical flow using Lucas-Kanade method
    p1, st, err = cv2.calcOpticalFlowPyrLK(prev_img, next_img, p0, None, **lk_params)

    # Select good points
    good_old = p0[st == 1]
    good_new = p1[st == 1]

    # Create an image to draw the flow
    output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)

    # Draw the displacement vectors for the SIFT keypoints
    for new, old in zip(good_new, good_old):
        a, b = new.ravel()
        c, d = old.ravel()
        cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 2)
        cv2.circle(output_img, (int(a), int(b)), 3, (0, 0, 255), -1)

    # Write the frame to the video
    video_writer.write(output_img)

    print(f"Processed frame {i + 1} / {len(image_paths) - 1}")

# Release the video writer
if video_writer:
    video_writer.release()

print(f"Video saved at: {output_video_path}")



#%%
import numpy as np
import open3d as o3d

# Generate example 3D point cloud (replace with your actual data)
num_points = 1000
np.random.seed(42)
points = np.random.rand(num_points, 3) * 10  # Random 3D points within a bounding box
displacements = (np.random.rand(num_points, 3) - 0.5) * 2  # Random displacement vectors

# Convert to Open3D point cloud
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)

# Generate arrows (lines to represent displacements)
lines = []
line_colors = []
arrow_vertices = []

for i in range(num_points):
    start = points[i]  # Original point
    end = points[i] + displacements[i]  # Displaced point

    # Add start and end to vertices
    arrow_vertices.append(start)
    arrow_vertices.append(end)

    # Define line segments (index pairs)
    lines.append([2 * i, 2 * i + 1])
    line_colors.append([1, 0, 0])  # Red color for arrows

# Convert to Open3D LineSet
arrow_lines = o3d.geometry.LineSet()
arrow_lines.points = o3d.utility.Vector3dVector(arrow_vertices)
arrow_lines.lines = o3d.utility.Vector2iVector(lines)
arrow_lines.colors = o3d.utility.Vector3dVector(line_colors)

# Visualize point cloud with displacement vectors
o3d.visualization.draw_geometries([pcd, arrow_lines], window_name="3D Displacement Field")

#%%
import os
import glob
import json

# Function to find files matching a pattern in a directory (recursive search)
def find_files_glob(target_path, pattern):
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"The directory {target_path} does not exist.")
    search_pattern = os.path.join(target_path, "**", pattern)
    file_list = glob.glob(search_pattern, recursive=True)
    return file_list

# Function to locate the feature file for a given observation key
def locate_feat_file(feature_files, observation_key):
    for file in feature_files:
        if observation_key in file:
            return file
    raise FileNotFoundError(f"Feature file for {observation_key} not found.")

# Function to read the third column values (assuming .feat files are whitespace-separated)
def read_third_column(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    third_column = [line.split()[2] for line in lines if len(line.split()) > 2]
    return third_column

# File path to robust.json
file_path = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0001\reconstruction_global\robust.json"

# Load the robust.json file
with open(file_path, 'r') as file:
    md_sfm_data = json.load(file)

# Root path and pattern for feature files
json_path = md_sfm_data['root_path']
feature_pattern = '*.feat'
feature_files = find_files_glob(json_path, feature_pattern)

# Structure contains 3D points (X) and their observations
structure = md_sfm_data['structure']

# Results dictionary to hold 3D points (X) and corresponding image coordinates
results = {}

# Process each 3D point in the structure
for item in structure:
    structure_key = item["key"]
    xyz = item["value"]["X"]  # 3D point (X)
    observations = item["value"]["observations"]

    # Initialize results with the 3D point and an empty list for image coordinates
    if structure_key not in results:
        results[structure_key] = {"3D_point": xyz, "image_coordinates": []}

    # Process each observation (association with image key and feature index)
    for observation in observations:
        observation_key = observation["key"]  # Image key
        id_feat = observation["value"]["id_feat"]  # Feature index

        try:
            # Locate the .feat file corresponding to the observation key
            feat_file_path = locate_feat_file(feature_files, observation_key)

            # Read the third column (feature points) from the .feat file
            third_column_values = read_third_column(feat_file_path)
            if id_feat < len(third_column_values):
                x_y = third_column_values[id_feat]
                results[structure_key]["image_coordinates"].append((observation_key, x_y))
            else:
                print(f"Feature index {id_feat} out of bounds in {feat_file_path}")

        except (FileNotFoundError, IndexError) as e:
            print(f"Error processing observation {observation_key}: {e}")

# Print the results: 3D points with corresponding image coordinates
for key, value in results.items():
    print(f"Structure Key: {key}")
    print(f"3D Point (X): {value['3D_point']}")
    print("Image Coordinates (x, y):")
    for obs in value["image_coordinates"]:
        print(f"  Image: {obs[0]}, Coordinates: {obs[1]}")
    print("-" * 40)

#%%
import cv2
import numpy as np
import glob
import os
import json
from plyfile import PlyData, PlyElement
import numpy as np


def find_files_glob(target_path, pattern):
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"The directory {target_path} does not exist.")
    search_pattern = f"{target_path}/**/{pattern}"
    file_list = glob.glob(search_pattern, recursive=True)
    return file_list

def locate_feat_file(observation_key):
    feat_file_path = f"path/to/feat/files/{observation_key}.feat"  # Modify to actual path
    if os.path.exists(feat_file_path):
        return feat_file_path
    else:
        raise FileNotFoundError(f"Feature file {observation_key}.feat not found")

def read_xy_coordinate(feat_file_path):
    third_column_values = []
    with open(feat_file_path, 'r') as f:
        for line in f:
            columns = line.split()  # Split by whitespace
            if len(columns) >= 3:  # Ensure there are at least 3 columns
                third_column_values.append(columns[0:2])
    return third_column_values

file_path = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0090\reconstruction_global\robust.json"


# with open(file_path, 'r') as file:
#     md_sfm_data = json.load(file)
    
#     json_path = md_sfm_data['root_path']
#     feaure_file = '*.feat'
#     feature_path = find_files_glob(json_path, feaure_file)
#     structure = md_sfm_data['structure']

#     results = {}
    
#     for item in structure:
#         structure_key = item["key"]
#         observations = item["value"]["observations"]
#         xyz = item["value"]["X"]
    
#         # Initialize an empty list for each structure_key in results
#         if structure_key not in results:
#             results[structure_key] = [xyz,[]]
    
#         for observation in observations:
#             observation_key = observation["key"]
#             if observation_key == 1:
#                 id_feat = observation["value"]["id_feat"]
        
#                 # Locate the .feat file based on the observation key
#                 try:
#                     feat_file_path = feature_path[observation_key]
#                     # Read all third column values from the feat file
#                     xy_coordinates = read_xy_coordinate(feat_file_path)[id_feat]
        
#                     # Append all third_column_values to the list under the current structure_key
#                     results[structure_key][1].append(xy_coordinates)
        
#                 except (FileNotFoundError, IndexError) as e:
#                     print(f"Error with observation {observation_key}: {e}")

# feature_points = []
# for key, value in results.items():
#     if len(value) > 1 and value[1] and isinstance(value[1][0], list):
#         try:
#             value[1][0] = [float(num) for num in value[1][0]]  # Convert strings to floats
#             feature_points.append(value[1][0])
#         except ValueError as e:
#             print(f"Error converting key {key}: {e}")

# feature_array = np.asarray(feature_points)
#%%

"""
use all point from the 90th point cloud
"""

def project_3d_to_2d(points_3d, intrinsic, extrinsic):
    # Add a column of ones to the 3D points to make them homogeneous
    points_3d_h = np.hstack((points_3d, np.ones((points_3d.shape[0], 1))))
    
    # Transform 3D points to camera coordinates using the extrinsic matrix
    points_camera_h = points_3d_h @ extrinsic.T  # Homogeneous camera coordinates
    
    # Project to 2D using the intrinsic matrix
    points_2d_h = points_camera_h[:, :3] @ intrinsic.T  # Homogeneous 2D points
    
    # Normalize to get pixel coordinates (divide by the third coordinate)
    points_2d = points_2d_h[:, :2] / points_2d_h[:, 2, np.newaxis]
    
    return points_2d

def obtain_info_openmvg(obj_fil_path): 
    """
    Function for obtain camera information from OpenMVG
    The intrinsic and extrinsic view ID order may different.
    
    Argument:
        obj_fil_path: str 
                    target OpenMVG json file path.
        
    output: 
        intrinsic_list: ndarray
                    OpenMVG estimated camera intrinsic.
                    
        rotations_openmvg: list of ndarray
                    OpenMVG estimated camera rotation. 
        
        translation_array_openmvg_reorder: list of ndarray
                    OpenMVG returns center instead of translation, 
                    to calculate translation, using function -R*C
                    
        extrinsic_list: nd array
                    The true extrinsic [R|t].
                    
        distortion_openmvg: nd array
                    OpenMVG estimated camera distortion.
                    
        centers:
                    camera position expressed in world coordinates. 

    """
    json_file = obj_fil_path
    
    # Load the JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Extract intrinsics
    intrinsics = data.get('intrinsics', [])
    intrinsic_idx_openmvg = [intrinsic['key'] for intrinsic in intrinsics]
    distortion = np.array([intrinsic['value']['ptr_wrapper']['data']['disto_k3'] for intrinsic in intrinsics])
    focal_length = np.array([intrinsic['value']['ptr_wrapper']['data']['focal_length'] for intrinsic in intrinsics])
    cxcy = np.array([intrinsic['value']['ptr_wrapper']['data']['principal_point'] for intrinsic in intrinsics])
    
    
    intrinsic_list = [None] * len(intrinsic_idx_openmvg)
    distortion_openmvg = [None] * len(distortion)
    
    for idx, original_index in enumerate(intrinsic_idx_openmvg):
        intrinsic_openmvg = np.zeros((3, 3))
        intrinsic_openmvg[0, 0] = focal_length[idx]
        intrinsic_openmvg[1, 1] = focal_length[idx]
        intrinsic_openmvg[2, 2] = 1
        intrinsic_openmvg[0, 2] = cxcy[idx][0]
        intrinsic_openmvg[1, 2] = cxcy[idx][1]
        
        # Store in the new order
        intrinsic_list[original_index] = intrinsic_openmvg
        distortion_openmvg[original_index] = distortion[idx]
    
    # Extract extrinsics
    extrinsics = data.get('extrinsics', [])
    extrinsic_idx_openmvg = [extrinsic['key'] for extrinsic in extrinsics]
    centers = np.array([extrinsic['value']['center'] for extrinsic in extrinsics])
    rotations_openmvg = np.array([extrinsic['value']['rotation'] for extrinsic in extrinsics])
    
    rotations_openmvg_list = [None] * len(extrinsic_idx_openmvg)
    camera_center = [None] * len(extrinsic_idx_openmvg)

    ## OpenMVG returns center instead of translation, to calculate translation, using function -R*C
    translation_array_openmvg = []
    for i in range(0,len(centers)):
        translation = (-rotations_openmvg[i] @ centers[i].T).reshape(3,1)
        translation_array_openmvg .append(translation)
    
    translation_array_openmvg_reorder = [None] * len(extrinsic_idx_openmvg)
    for idx, original_index in enumerate(extrinsic_idx_openmvg):
        
        rotations_openmvg_list[original_index] = rotations_openmvg[idx]
        camera_center[original_index] = centers[idx]
        translation_array_openmvg_reorder[original_index] = translation_array_openmvg[idx]
    
    extrinsic_list = []
    for R, t in zip(rotations_openmvg_list, translation_array_openmvg_reorder):
        extrinsic_matrix = np.hstack((R, t))  
        extrinsic_list.append(extrinsic_matrix)
    
     

    return intrinsic_list, extrinsic_list, rotations_openmvg_list, translation_array_openmvg_reorder, distortion_openmvg, camera_center

# Path to the PLY file
ply_file_90 = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0090\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_90, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_90 = ply_data['vertex']
points_3d_90 = np.array([vertex_data_90['x'], vertex_data_90['y'], vertex_data_90['z']]).T

ply_file_91 = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_91, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_91 = ply_data['vertex']
points_3d_91 = np.array([vertex_data_91['x'], vertex_data_91['y'], vertex_data_91['z']]).T
# color = np.array([vertex_data['red'], vertex_data['green'], vertex_data['blue']]).T

json_90_path = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0090\reconstruction_global\robust.json"
json_91_path = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\reconstruction_global\robust.json"

# json_file = json_91_path
intrinsic_list_90, extrinsic_list_90, rotations_openmvg_list_90, translation_array_openmvg_reorder_90, distortion_openmvg_90, camera_center_90 = obtain_info_openmvg(json_90_path)

intrinsic_list_91, extrinsic_list_91, rotations_openmvg_list_91, translation_array_openmvg_reorder_91, distortion_openmvg_91, camera_center_91 = obtain_info_openmvg(json_91_path)

intrinsic_90 = intrinsic_list_90[1]
extrinsic_90 = extrinsic_list_90[1]

intrinsic_91 = intrinsic_list_91[1]
extrinsic_91 = extrinsic_list_91[1]

points_2d_90 = project_3d_to_2d(points_3d_90, intrinsic_90, extrinsic_90)
points_2d_91 = project_3d_to_2d(points_3d_91, intrinsic_91, extrinsic_91)

# Save mapping of 3D points to 2D points
mapping_90 = [(tuple(p3d), tuple(p2d)) for p3d, p2d in zip(points_3d_90, points_2d_90)]
mapping_91 = [(tuple(p3d), tuple(p2d)) for p3d, p2d in zip(points_3d_91, points_2d_91)]

points_3d_90, points_2d_90 = zip(*mapping_90)
points_3d_91, points_2d_91 = zip(*mapping_91)


points_3d_90 = np.array(points_3d_90)
points_2d_90 = np.array(points_2d_90)
points_3d_91 = np.array(points_3d_91)
points_2d_91 = np.array(points_2d_91)

# feature_array = points_2d_90

#%%
# root_dir = r"D:\Ryan\Jetson_orin_nano\image_collection_mask"

# # Gather all image paths
# image_paths = glob.glob(os.path.join(root_dir, "image_set*", "image_json_001.jpg"))
# image_paths.sort()  # Ensure paths are sorted in order

# # Lucas-Kanade Optical Flow parameters
# lk_params = dict(winSize=(15, 15), maxLevel=2,
#                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

# # SIFT feature detector
# sift = cv2.SIFT_create()

# # Video writer setup
# output_video_path = r"D:\Ryan\Jetson_orin_nano\consistent_tracking_video.avi"
# frame_width, frame_height = None, None
# video_writer = None

# # Read the first frame and initialize tracking points
# prev_img = cv2.imread(image_paths[1], cv2.IMREAD_GRAYSCALE)


# if prev_img is None:
#     print("Error loading the first image.")
#     exit()

# # Detect SIFT keypoints and descriptors in the first image
# # keypoints, descriptors = sift.detectAndCompute(prev_img, None)

# # initial_points = np.array([kp.pt for kp in keypoints], dtype=np.float32).reshape(-1, 1, 2)
# # print(f"Total initial tracking points: {len(initial_points)}")

# feature_array_init = feature_array.reshape(-1, 1, 2)

# # Keep track of persistent points across all frames
# tracking_points = feature_array_init.copy()


# for i in range(1, len(image_paths)):
#     next_img = cv2.imread(image_paths[i], cv2.IMREAD_GRAYSCALE)
#     if next_img is None:
#         print(f"Error loading image: {image_paths[i]}")
#         break

#     # Validate tracking points
#     if tracking_points is None or len(tracking_points) == 0:
#         print("No points to track. Exiting...")
#         break

#     # Ensure correct format for tracking_points
#     tracking_points = tracking_points.astype(np.float32).reshape(-1, 1, 2)

#     # Calculate optical flow for the current tracking points
#     p1, st, err = cv2.calcOpticalFlowPyrLK(prev_img, next_img, tracking_points, None, **lk_params)

#     # Select only successfully tracked points
#     good_new = p1[st == 1]
#     good_old = tracking_points[st == 1]

#     # Update tracking points for the next frame
#     tracking_points = good_new.reshape(-1, 1, 2)

#     # Draw tracked points and displacement vectors
#     output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)
#     for new, old in zip(good_new, good_old):
#         a, b = new.ravel()
#         c, d = old.ravel()
#         cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 1)
#         cv2.circle(output_img, (int(a), int(b)), 2, (0, 0, 255), -1)

#     # Write the frame to the video
#     video_writer.write(output_img)

#     # Prepare for the next iteration
#     prev_img = next_img.copy()

#     print(f"Processed frame {i} / {len(image_paths)} with {len(tracking_points)} points remaining.")
    
#%%


"""
read the 90th frame both point cloud and its image.
using optical flow to track key point movement.

"""


intrinsic_90 = np.array([[2.16519027e+03, 0.00000000e+00, 1.20608529e+03],
                [0.00000000e+00, 2.16519027e+03, 7.56874751e+02],
                [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])

distortion_90 = np.array([-0.0671132 ,  0.05983396, 0,0, -0.47648311])

image_90 = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0090\image_json_001.jpg"
image_91 = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\image_json_001.jpg"


prev_img = cv2.imread(image_90, cv2.IMREAD_GRAYSCALE)  # 90th image
prev_img = cv2.undistort(prev_img, intrinsic_90, distortion_90, None, intrinsic_90) 

next_img = cv2.imread(image_91, cv2.IMREAD_GRAYSCALE)  # 91st image
next_img = cv2.undistort(next_img, intrinsic_90, distortion_90, None, intrinsic_90) 

feature_array_init = points_2d_90.reshape(-1, 1, 2)

# Keep track of persistent points across all frames
tracking_points = feature_array_init.copy()

if prev_img is None or next_img is None:
    print("Error loading the 90th or 91st image.")
    exit()

# Validate tracking points
if tracking_points is None or len(tracking_points) == 0:
    print("No points to track in the 90th image.")
    exit()

# Ensure correct format for tracking_points
tracking_points = tracking_points.astype(np.float32).reshape(-1, 1, 2)
lk_params = dict(winSize=(15, 15), maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
# Calculate optical flow between the 90th and 91st images
p1, st, err = cv2.calcOpticalFlowPyrLK(prev_img, next_img, tracking_points, None, **lk_params)

# Select only successfully tracked points
"""
In here we have the tracked points.
then we need to use the "good_new" point finding similar point from next frame.
"""
good_new = p1[st == 1]
good_old = tracking_points[st == 1]

# Visualize the optical flow
output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)
for new, old in zip(good_new, good_old):
    a, b = new.ravel()
    c, d = old.ravel()
    cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 1)
    cv2.circle(output_img, (int(a), int(b)), 2, (0, 0, 255), -1)

# Save or display the result
cv2.imshow("Optical Flow - 90th to 91st Image", output_img)
cv2.imwrite("optical_flow_90th_to_91st.jpg", output_img)  # Save the result
cv2.waitKey(0)
cv2.destroyAllWindows()

print(f"Optical flow computed between the 90th and 91st images with {len(good_new)} points tracked.")




displacements = np.linalg.norm(good_new - good_old, axis=1)

# Create an empty image to overlay DIC-like data
dic_visualization = np.zeros_like(next_img, dtype=np.float32)

# Assign displacement values to the image
for (new, displacement) in zip(good_new, displacements):
    x, y = map(int, new.ravel())
    if 0 <= x < dic_visualization.shape[1] and 0 <= y < dic_visualization.shape[0]:
        dic_visualization[y, x] = displacement

# Normalize displacement values for colormap
normalized_dic = cv2.normalize(dic_visualization, None, 0, 255, cv2.NORM_MINMAX)

# Apply colormap
dic_colormap = cv2.applyColorMap(normalized_dic.astype(np.uint8), cv2.COLORMAP_JET)

# Overlay colormap on the grayscale image
overlayed_image = cv2.addWeighted(cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR), 0.5, dic_colormap, 0.5, 0)

# Display the DIC-like image
cv2.imshow("DIC Visualization", overlayed_image)
cv2.imwrite("dic_visualization.jpg", overlayed_image)  # Save the result
cv2.waitKey(0)
cv2.destroyAllWindows()


## if use original point, the number of data set is too large,
## instead, select the point with movement to reduce the data size.
## after filter, use the point to find the 3d point.
movement_threshold = 0.5
moving_points_mask  = displacements > movement_threshold
moving_points_new = good_new[moving_points_mask]
moving_points_old = good_old[moving_points_mask]

moving_displacements = displacements[moving_points_mask]

# Visualize only points with significant movement
output_img_moving = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)
for new, old, displacement in zip(moving_points_new, moving_points_old, moving_displacements):
    a, b = new.ravel()
    c, d = old.ravel()
    cv2.arrowedLine(output_img_moving, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 1)
    cv2.circle(output_img_moving, (int(a), int(b)), 3, (0, 0, 255), -1)

# Save or display the result
cv2.imshow("Significant Movement", output_img_moving)
cv2.imwrite("significant_movement.jpg", output_img_moving)
cv2.waitKey(0)
cv2.destroyAllWindows()

print(f"Number of points with significant movement: {len(moving_points_new)}")

#%%
"""
After we have the tracking path, we can read the next frame sama as the 90th, using the middle camera image
to find the closest point on json file.  find how many pixel it shifted.
"""

# json_91_path = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\reconstruction_global\robust.json"


# with open(json_91_path, 'r') as file:
#     md_sfm_data = json.load(file)
    
#     json_path = md_sfm_data['root_path']
#     feaure_file = '*.feat'
#     feature_path = find_files_glob(json_path, feaure_file)
#     structure = md_sfm_data['structure']

#     results = {}
    
#     for item in structure:
#         structure_key = item["key"]
#         observations = item["value"]["observations"]
#         xyz = item["value"]["X"]
    
#         # Initialize an empty list for each structure_key in results
#         if structure_key not in results:
#             results[structure_key] = [xyz,[]]
    
#         for observation in observations:
#             observation_key = observation["key"]
#             if observation_key == 1:
#                 id_feat = observation["value"]["id_feat"]
        
#                 # Locate the .feat file based on the observation key
#                 try:
#                     feat_file_path = feature_path[observation_key]
#                     # Read all third column values from the feat file
#                     xy_coordinates = read_xy_coordinate(feat_file_path)[id_feat]
        
#                     # Append all third_column_values to the list under the current structure_key
#                     results[structure_key][1].append(xy_coordinates)
        
#                 except (FileNotFoundError, IndexError) as e:
#                     print(f"Error with observation {observation_key}: {e}")

# feature_points_91 = []
# for key, value in results.items():
#     if len(value) > 1 and value[1] and isinstance(value[1][0], list):
#         try:
#             value[1][0] = [float(num) for num in value[1][0]]  # Convert strings to floats
#             feature_points.append(value[1][0])
#         except ValueError as e:
#             print(f"Error converting key {key}: {e}")

# feature_array_91 = np.asarray(feature_points)


#%%

"""
This section is working on finding corresponding points from on array to another one.
"""

# import numpy as np
# import matplotlib.pyplot as plt

# # Example arrays (replace with your actual data)
# array1 = moving_points_new  
# array2 = points_2d_91  

# # Compute pairwise distances
# distances = np.linalg.norm(array1[:, np.newaxis] - array2, axis=2)

# # Find the index of the closest point in array2 for each point in array1
# closest_points = np.argmin(distances, axis=1)

# # Get the matched corresponding points
# corresponding_points = array2[closest_points]

# plt.figure(figsize=(10, 8))
# plt.imshow(next_img, cmap='gray')

# # Overlay matched points and connect them with lines
# for pt1, pt2 in zip(array1, corresponding_points):
#     # Draw a red point for the first array point
#     plt.scatter(pt1[0], pt1[1], color='red', s=5)
#     # Draw a blue point for the corresponding point in the second array
#     plt.scatter(pt2[0], pt2[1], color='blue', s=5)
#     # Draw a line connecting the points
#     # plt.plot([pt1[0], pt2[0]], [pt1[1], pt2[1]], color='green', linewidth=1)

# # Add legend
# plt.legend(['Matched Pair', 'Array1 (Red)', 'Array2 (Blue)'])

# # Show the plot
# plt.title("Matched Points Display")
# plt.axis('off')  # Turn off axis for better visualization
# plt.show()



from scipy.spatial import KDTree

# Build KD-Tree for array2
tree = KDTree(points_2d_91)  # Shape: (110638, 2)

# Query the closest points for array1
distances, closest_points = tree.query(moving_points_new, workers=-1)  # Shape: (54688,)

# Get the matched corresponding points
corresponding_points = points_2d_91[closest_points]

print("Closest points computed using KD-Tree!")

x1, y1 = moving_points_new[:, 0], moving_points_new[:, 1]
x2, y2 = corresponding_points[:, 0], corresponding_points[:, 1]

# Plot points
plt.figure(figsize=(10, 8))
plt.scatter(x1, y1, color='green', label='Points in Image 1', s=20)
plt.scatter(x2, y2, color='red', label='Corresponding Points in Image 2', s=20)

# Draw lines for correspondence
for i in range(len(moving_points_new)):
    plt.plot([x1[i], x2[i]], [y1[i], y2[i]], color='blue', linewidth=0.5)

plt.legend()
plt.xlabel("X")
plt.ylabel("Y")
plt.title("Point Correspondences")
plt.grid(True)
plt.show()
#%%

from plyfile import PlyData
import numpy as np
import json

def obtain_info_openmvg(obj_fil_path): 

    json_file = obj_fil_path
    
    # Load the JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Extract intrinsics
    intrinsics = data.get('intrinsics', [])
    intrinsic_idx_openmvg = [intrinsic['key'] for intrinsic in intrinsics]
    distortion = np.array([intrinsic['value']['ptr_wrapper']['data']['disto_k3'] for intrinsic in intrinsics])
    focal_length = np.array([intrinsic['value']['ptr_wrapper']['data']['focal_length'] for intrinsic in intrinsics])
    cxcy = np.array([intrinsic['value']['ptr_wrapper']['data']['principal_point'] for intrinsic in intrinsics])
    
    
    intrinsic_list = [None] * len(intrinsic_idx_openmvg)
    distortion_openmvg = [None] * len(distortion)
    
    for idx, original_index in enumerate(intrinsic_idx_openmvg):
        intrinsic_openmvg = np.zeros((3, 3))
        intrinsic_openmvg[0, 0] = focal_length[idx]
        intrinsic_openmvg[1, 1] = focal_length[idx]
        intrinsic_openmvg[2, 2] = 1
        intrinsic_openmvg[0, 2] = cxcy[idx][0]
        intrinsic_openmvg[1, 2] = cxcy[idx][1]
        
        # Store in the new order
        intrinsic_list[original_index] = intrinsic_openmvg
        distortion_openmvg[original_index] = distortion[idx]
    
    # Extract extrinsics
    extrinsics = data.get('extrinsics', [])
    extrinsic_idx_openmvg = [extrinsic['key'] for extrinsic in extrinsics]
    centers = np.array([extrinsic['value']['center'] for extrinsic in extrinsics])
    rotations_openmvg = np.array([extrinsic['value']['rotation'] for extrinsic in extrinsics])
    
    rotations_openmvg_list = [None] * len(extrinsic_idx_openmvg)
    camera_center = [None] * len(extrinsic_idx_openmvg)

    ## OpenMVG returns center instead of translation, to calculate translation, using function -R*C
    translation_array_openmvg = []
    for i in range(0,len(centers)):
        translation = (-rotations_openmvg[i] @ centers[i].T).reshape(3,1)
        translation_array_openmvg .append(translation)
    
    translation_array_openmvg_reorder = [None] * len(extrinsic_idx_openmvg)
    for idx, original_index in enumerate(extrinsic_idx_openmvg):
        
        rotations_openmvg_list[original_index] = rotations_openmvg[idx]
        camera_center[original_index] = centers[idx]
        translation_array_openmvg_reorder[original_index] = translation_array_openmvg[idx]
    
    extrinsic_list = []
    for R, t in zip(rotations_openmvg_list, translation_array_openmvg_reorder):
        extrinsic_matrix = np.hstack((R, t))  
        extrinsic_list.append(extrinsic_matrix)
    
     

    return intrinsic_list, extrinsic_list, rotations_openmvg_list, translation_array_openmvg_reorder, distortion_openmvg, camera_center

def project_3d_to_2d(points_3d, intrinsic, extrinsic):
    # Add a column of ones to the 3D points to make them homogeneous
    points_3d_h = np.hstack((points_3d, np.ones((points_3d.shape[0], 1))))
    
    # Transform 3D points to camera coordinates using the extrinsic matrix
    points_camera_h = points_3d_h @ extrinsic.T  # Homogeneous camera coordinates
    
    # Project to 2D using the intrinsic matrix
    points_2d_h = points_camera_h[:, :3] @ intrinsic.T  # Homogeneous 2D points
    
    # Normalize to get pixel coordinates (divide by the third coordinate)
    points_2d = points_2d_h[:, :2] / points_2d_h[:, 2, np.newaxis]
    
    return points_2d


# Path to the PLY file
ply_file = r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\reconstruction_global\robust_scene_dense.ply"

# Read the PLY file
with open(ply_file, 'rb') as f:
    ply_data = PlyData.read(f)

# Extract point data
vertex_data = ply_data['vertex']
points_3d = np.array([vertex_data['x'], vertex_data['y'], vertex_data['z']]).T
color = np.array([vertex_data['red'], vertex_data['green'], vertex_data['blue']]).T

json_file = json_91_path

intrinsic_list, extrinsic_list, rotations_openmvg_list, translation_array_openmvg_reorder, distortion_openmvg, camera_center = obtain_info_openmvg(json_file)

intrinsic_91 = intrinsic_list[1]
extrinsic_91 = extrinsic_list[1]

points_2d = project_3d_to_2d(points_3d, intrinsic_91, extrinsic_91)

# Save mapping of 3D points to 2D points
mapping = [(tuple(p3d), tuple(p2d)) for p3d, p2d in zip(points_3d, points_2d)]

points_3d, points_2d = zip(*mapping)

points_3d = np.array(points_3d)
points_2d = np.array(points_2d)


array1 = good_new  
array2 = points_2d  

# Compute pairwise distances
distances = np.linalg.norm(array1[:, np.newaxis] - array2, axis=2)

# Find the index of the closest point in array2 for each point in array1
closest_points = np.argmin(distances, axis=1)

# Get the matched corresponding points
corresponding_points = array2[closest_points]

# Calculate the actual distances between array1 and corresponding_points
actual_distances = np.linalg.norm(array1 - corresponding_points, axis=1)

# Filter points where the distance is less than or equal to 3
mask = actual_distances <= 3
filtered_array1 = array1[mask]
filtered_corresponding_points = corresponding_points[mask]

# Visualization: Matched Points with Distances <= 3
plt.figure(figsize=(10, 8))
plt.imshow(next_img, cmap='gray')

# Overlay matched points and connect them with lines
for pt1, pt2 in zip(filtered_array1, filtered_corresponding_points):
    plt.scatter(pt1[0], pt1[1], color='red', s=5)  # Array1 point
    plt.scatter(pt2[0], pt2[1], color='blue', s=5)  # Corresponding point
    plt.plot([pt1[0], pt2[0]], [pt1[1], pt2[1]], color='green', linewidth=1)  # Line connecting points

# Add legend
plt.legend(['Matched Pair', 'Array1 (Red)', 'Array2 (Blue)'])

# Plot settings
plt.title("Filtered Matched Points Display (Distance <= 3)")
plt.axis('off')  # Turn off axis for better visualization
plt.show()

# Calculate X and Y distances for filtered points
distances_x = filtered_corresponding_points[:, 0] - filtered_array1[:, 0]
distances_y = filtered_corresponding_points[:, 1] - filtered_array1[:, 1]

# Scatter plot for distances
plt.figure(figsize=(10, 8))
plt.scatter(distances_x, distances_y, color='blue', s=10, alpha=0.6, label='Filtered Distance Scatter')

# Add reference lines
plt.axhline(0, color='red', linestyle='--', linewidth=1)  # Horizontal reference line
plt.axvline(0, color='red', linestyle='--', linewidth=1)  # Vertical reference line

# Plot settings
plt.title("Scatter Plot of Distances (X vs Y) for Filtered Points")
plt.xlabel("Distance in X direction")
plt.ylabel("Distance in Y direction")
plt.legend()
plt.grid(True)
plt.show()


#%%
import numpy as np
import matplotlib.pyplot as plt

# Compute pairwise distances
distances = np.linalg.norm(array1[:, np.newaxis] - array2, axis=2)

# Find the index of the closest point in array2 for each point in array1
closest_points = np.argmin(distances, axis=1)

# Get the matched corresponding points
corresponding_points = array2[closest_points]

# Calculate the actual distances between array1 and corresponding_points
actual_distances = np.linalg.norm(array1 - corresponding_points, axis=1)

# Filter points where the distance is less than or equal to 3
mask = actual_distances <= 3
filtered_array1 = array1[mask]
filtered_corresponding_points = corresponding_points[mask]

# Visualization: Matched Points with Distances <= 3
plt.figure(figsize=(10, 8))
plt.imshow(next_img, cmap='gray')

# Overlay matched points and connect them with lines
for pt1, pt2 in zip(filtered_array1, filtered_corresponding_points):
    plt.scatter(pt1[0], pt1[1], color='red', s=5)  # Array1 point
    plt.scatter(pt2[0], pt2[1], color='blue', s=5)  # Corresponding point
    plt.plot([pt1[0], pt2[0]], [pt1[1], pt2[1]], color='green', linewidth=1)  # Line connecting points

# Add legend
plt.legend(['Matched Pair', 'Array1 (Red)', 'Array2 (Blue)'])

# Plot settings
plt.title("Filtered Matched Points Display (Distance <= 3)")
plt.axis('off')  # Turn off axis for better visualization
plt.show()

# Calculate X and Y distances for filtered points
distances_x = filtered_corresponding_points[:, 0] - filtered_array1[:, 0]
distances_y = filtered_corresponding_points[:, 1] - filtered_array1[:, 1]

# Scatter plot for distances
plt.figure(figsize=(10, 8))
plt.scatter(distances_x, distances_y, color='blue', s=10, alpha=0.6, label='Filtered Distance Scatter')

# Add reference lines
plt.axhline(0, color='red', linestyle='--', linewidth=1)  # Horizontal reference line
plt.axvline(0, color='red', linestyle='--', linewidth=1)  # Vertical reference line

# Plot settings
plt.title("Scatter Plot of Distances (X vs Y) for Filtered Points")
plt.xlabel("Distance in X direction")
plt.ylabel("Distance in Y direction")
plt.legend()
plt.grid(True)
plt.show()











#%%




#%%




















#%%
"""
After we have the key points from 90th point cloud. In image to find it displacement in 91st image.
since we need to do trangulation, another points from another image is gonna to use.
to find the match point from another image, we need to first apply SIFT find the feature points to calculate its descriptor.
and find the corresponding point from another view's image.
"""

point_image_90 = good_old

sift = cv2.SIFT_create()


the_90_img = prev_img
the_90_img_view_1 = cv2.imread(r"D:\Ryan\Jetson_orin_nano\image_collection_mask\image_set_0091\image_json_000.jpg",0)
# Compute descriptors for the custom keypoints
point_image_90 = good_old
keypoints_90 = [cv2.KeyPoint(x=float(pt[0]), y=float(pt[1]), size=10) for pt in point_image_90]

# keypoints_90, descriptors_90 = sift.compute(the_90_img, keypoints_90)

# the reason here not use the point coordinate from OpenMVG directly is that 
# some point in previous step has been filtered out because it is not show in multiple frames.
# since we don't know which on is filted out, instead use SIFT method to find corresponding
# point from another view. 
keypoints_90, descriptors_90 = sift.detectAndCompute(the_90_img, None)
keypoints_90_view1, descriptors_90_view1 = sift.detectAndCompute(the_90_img_view_1, None)

index_params = dict(algorithm=1, trees=5)  # FLANN parameters for SIFT
search_params = dict(checks=50)
# flann = cv2.FlannBasedMatcher(index_params, search_params)
# matches = flann.knnMatch(descriptors_90, descriptors_90_view1, k=2)


bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
matches = bf.knnMatch(descriptors_90, descriptors_90_view1, k=2)
# Apply Lowe's ratio test to filter good matches
good_matches = []
pts_90 = []
pts_90_view1 = []


for match in matches:
    m = match[0]  # Best match
    good_matches.append(m)
    pts_90.append(keypoints_90[m.queryIdx].pt)
    pts_90_view1.append(keypoints_90_view1[m.trainIdx].pt)

# Convert points to numpy arrays
pts_90 = np.float32(pts_90)
pts_90_view1 = np.float32(pts_90_view1)

# Apply RANSAC to find inliers
F, inliers = cv2.findFundamentalMat(pts_90, pts_90_view1, cv2.FM_RANSAC)

# Filter inliers based on the RANSAC mask
inlier_pts_90 = pts_90[inliers.ravel() == 1]
inlier_pts_90_view1 = pts_90_view1[inliers.ravel() == 1]

# Filter good matches to include only inliers
inlier_matches = [good_matches[i] for i in range(len(good_matches)) if inliers[i]]

# Print results
print(f"Number of original matches: {len(good_matches)}")
print(f"Number of inlier matches after RANSAC: {len(inlier_matches)}")

# Visualize inlier matches
output_img = cv2.drawMatches(the_90_img, keypoints_90, the_90_img_view_1, keypoints_90_view1, inlier_matches, None,
                              flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
cv2.imshow("Inlier Matches after RANSAC", output_img)
cv2.waitKey(0)
cv2.destroyAllWindows()


#%%
import json
def obtain_info_openmvg(obj_fil_path): 
    """
    Function for obtain camera information from OpenMVG
    The intrinsic and extrinsic view ID order may different.
    
    Argument:
        obj_fil_path: str 
                    target OpenMVG json file path.
        
    output: 
        intrinsic_list: ndarray
                    OpenMVG estimated camera intrinsic.
                    
        rotations_openmvg: list of ndarray
                    OpenMVG estimated camera rotation. 
        
        translation_array_openmvg_reorder: list of ndarray
                    OpenMVG returns center instead of translation, 
                    to calculate translation, using function -R*C
                    
        extrinsic_list: nd array
                    The true extrinsic [R|t].
                    
        distortion_openmvg: nd array
                    OpenMVG estimated camera distortion.
                    
        centers:
                    camera position expressed in world coordinates. 

    """
    json_file = obj_fil_path
    
    # Load the JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Extract intrinsics
    intrinsics = data.get('intrinsics', [])
    intrinsic_idx_openmvg = [intrinsic['key'] for intrinsic in intrinsics]
    distortion = np.array([intrinsic['value']['ptr_wrapper']['data']['disto_k3'] for intrinsic in intrinsics])
    focal_length = np.array([intrinsic['value']['ptr_wrapper']['data']['focal_length'] for intrinsic in intrinsics])
    cxcy = np.array([intrinsic['value']['ptr_wrapper']['data']['principal_point'] for intrinsic in intrinsics])
    
    
    intrinsic_list = [None] * len(intrinsic_idx_openmvg)
    distortion_openmvg = [None] * len(distortion)
    
    for idx, original_index in enumerate(intrinsic_idx_openmvg):
        intrinsic_openmvg = np.zeros((3, 3))
        intrinsic_openmvg[0, 0] = focal_length[idx]
        intrinsic_openmvg[1, 1] = focal_length[idx]
        intrinsic_openmvg[2, 2] = 1
        intrinsic_openmvg[0, 2] = cxcy[idx][0]
        intrinsic_openmvg[1, 2] = cxcy[idx][1]
        
        # Store in the new order
        intrinsic_list[original_index] = intrinsic_openmvg
        distortion_openmvg[original_index] = distortion[idx]
    
    # Extract extrinsics
    extrinsics = data.get('extrinsics', [])
    extrinsic_idx_openmvg = [extrinsic['key'] for extrinsic in extrinsics]
    centers = np.array([extrinsic['value']['center'] for extrinsic in extrinsics])
    rotations_openmvg = np.array([extrinsic['value']['rotation'] for extrinsic in extrinsics])
    
    rotations_openmvg_list = [None] * len(extrinsic_idx_openmvg)
    camera_center = [None] * len(extrinsic_idx_openmvg)

    ## OpenMVG returns center instead of translation, to calculate translation, using function -R*C
    translation_array_openmvg = []
    for i in range(0,len(centers)):
        translation = (-rotations_openmvg[i] @ centers[i].T).reshape(3,1)
        translation_array_openmvg .append(translation)
    
    translation_array_openmvg_reorder = [None] * len(extrinsic_idx_openmvg)
    for idx, original_index in enumerate(extrinsic_idx_openmvg):
        
        rotations_openmvg_list[original_index] = rotations_openmvg[idx]
        camera_center[original_index] = centers[idx]
        translation_array_openmvg_reorder[original_index] = translation_array_openmvg[idx]
    
    extrinsic_list = []
    for R, t in zip(rotations_openmvg_list, translation_array_openmvg_reorder):
        extrinsic_matrix = np.hstack((R, t))  
        extrinsic_list.append(extrinsic_matrix)
    
     

    return intrinsic_list, extrinsic_list, rotations_openmvg_list, translation_array_openmvg_reorder, distortion_openmvg, camera_center

json_file = r"D:\Ryan\Jetson_orin_nano\json_file\known_pose0000.json"

intrinsic_list, extrinsic_list, rotations_openmvg_list, translation_array_openmvg_reorder, distortion_openmvg, camera_center = obtain_info_openmvg(json_file)


inlier_pts_90 = pts_90[inliers.ravel() == 1]
inlier_pts_90_view1 = pts_90_view1[inliers.ravel() == 1]

P1 = intrinsic_list[1] @ extrinsic_list[1]  # Projection matrix for camera 1
P2 = intrinsic_list[0] @ extrinsic_list[0]  # Projection matrix for camera 2

# Convert points to homogeneous coordinates
pts_90_h = inlier_pts_90.T  # Shape (2, n)
pts_90_v1 = inlier_pts_90_view1.T  # Shape (2, n)

points_4d_h = cv2.triangulatePoints(P1, P2, pts_90_h, pts_90_v1)

points_3d = points_4d_h[:3] / points_4d_h[3]
#%%
import numpy as np
from plyfile import PlyData, PlyElement

# Assuming points_3d is a numpy array of shape (3, n) or (n, 3)
# Convert to shape (n, 3) for easier handling
points_3d = points_3d.T if points_3d.shape[0] == 3 else points_3d  # Ensure shape (n, 3)

# Create a structured numpy array for PLY
vertex = np.array(
    [(x, y, z) for x, y, z in points_3d],
    dtype=[("x", "f4"), ("y", "f4"), ("z", "f4")]
)

# Create a PlyElement
vertex_element = PlyElement.describe(vertex, "vertex")

# Write to a PLY file
ply_filename = r"D:\Ryan\Jetson_orin_nano\output_points.ply"
PlyData([vertex_element]).write(ply_filename)

print(f"3D points saved to {ply_filename}")







