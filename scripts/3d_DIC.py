# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 12:41:59 2024

@author: Desktop
"""


"""
use all point from the 90th point cloud
"""

import cv2
import numpy as np
import glob
import os
import json
from plyfile import PlyData, PlyElement
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines


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
ply_file_90 = r"E:\Ryan\image_collection_mask\image_set_0130\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_90, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_90 = ply_data['vertex']
points_3d_90 = np.array([vertex_data_90['x'], vertex_data_90['y'], vertex_data_90['z']]).T

ply_file_91 = r"E:\Ryan\image_collection_mask\image_set_0131\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_91, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_91 = ply_data['vertex']
points_3d_91 = np.array([vertex_data_91['x'], vertex_data_91['y'], vertex_data_91['z']]).T
color = np.array([vertex_data_91['red'], vertex_data_91['green'], vertex_data_91['blue']]).T

json_90_path = r"E:\Ryan\image_collection_mask\image_set_0130\reconstruction_global\robust.json"
json_91_path = r"E:\Ryan\image_collection_mask\image_set_0131\reconstruction_global\robust.json"

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
ply_file_90 = r"E:\Ryan\image_collection_mask\image_set_0130\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_90, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_90 = ply_data['vertex']
points_3d_90 = np.array([vertex_data_90['x'], vertex_data_90['y'], vertex_data_90['z']]).T

ply_file_91 = r"E:\Ryan\image_collection_mask\image_set_0131\reconstruction_global\robust_scene_dense.ply"
with open(ply_file_91, 'rb') as f:
    ply_data = PlyData.read(f)
vertex_data_91 = ply_data['vertex']
points_3d_91 = np.array([vertex_data_91['x'], vertex_data_91['y'], vertex_data_91['z']]).T
# color = np.array([vertex_data['red'], vertex_data['green'], vertex_data['blue']]).T

json_90_path = r"E:\Ryan\image_collection_mask\image_set_0130\reconstruction_global\robust.json"
json_91_path = r"E:\Ryan\image_collection_mask\image_set_0131\reconstruction_global\robust.json"

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


#%%


"""
read the 90th frame both point cloud and its image.
using optical flow to track key point movement.

"""


intrinsic_90 = np.array([[2.16519027e+03, 0.00000000e+00, 1.20608529e+03],
                [0.00000000e+00, 2.16519027e+03, 7.56874751e+02],
                [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])

distortion_90 = np.array([-0.0671132 ,  0.05983396, 0,0, -0.47648311])

image_90 = r"E:\Ryan\image_collection_mask\image_set_0130\image_json_001.jpg"
image_91 = r"E:\Ryan\image_collection_mask\image_set_0131\image_json_001.jpg"


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
# region_coords = np.array([[100, 100], [400, 100], [400, 400], [100, 400]])  # Example coordinates

# output_img = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)

# for new, old in zip(good_new, good_old):
#     a, b = new.ravel()
#     c, d = old.ravel()
#     cv2.arrowedLine(output_img, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 1)
#     cv2.circle(output_img, (int(a), int(b)), 2, (0, 0, 255), 1)

# # Save or display the result
# # cv2.putText(output_img, 'Arrows: Motion Direction', (10, 20),
# #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
# # cv2.putText(output_img, 'Red Dots: Key Points', (10, 40),
# #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

# cv2.imshow("Optical Flow - 90th to 91st Image", output_img)
# cv2.imwrite(r"C:\Users\Desktop\Documents\GitHub\ryan\ISGSR_2025\optical_flow_90th_to_91st.png", output_img)  # Save the result
# cv2.waitKey(0)
# cv2.destroyAllWindows()

# print(f"Optical flow computed between the 90th and 91st images with {len(good_new)} points tracked.")

# feature_point_handle = mlines.Line2D([], [], color='red', marker='o', linestyle='None', 
#                                      markersize=8, label='Feature Point')

# # Green Line: Displacement
# displacement_handle = mlines.Line2D([], [], color='lime', linestyle='-', linewidth=2, 
#                                     marker='>', markersize=8, label='Displacement')

# # Add Legend to the Plot

# fig, ax = plt.subplots(figsize=(12, 8))
# ax.imshow(cv2.cvtColor(output_img, cv2.COLOR_BGR2RGB))
# # ax.set_title("Optical Flow - 90th to 91st Image", fontsize=16, fontweight='bold')
# ax.axis('off')

# legend = ax.legend(handles=[feature_point_handle, displacement_handle], 
#                    loc='upper right', 
#                    fontsize=20, 
#                    frameon=True, 
#                    title_fontsize=14)

# # Style the Legend
# legend.get_frame().set_facecolor('white')
# legend.get_frame().set_edgecolor('black')

# # Display the plot
# plt.show()

## Display all points and it path

deltas = good_new - good_old
plt.figure(figsize=(10, 8))
plt.imshow(next_img, cmap='gray')

# Quiver plot of movement vectors
plt.quiver(
    good_old[:, 0], good_old[:, 1], 
    deltas[:, 0], deltas[:, 1],
    angles='xy', scale_units='xy', scale=1, color='b', alpha=0.7
)

# Plot starting points and ending points
plt.scatter(good_new[:, 0], good_new[:, 1], color='r', label='End Points', s=40)
plt.scatter(good_old[:, 0], good_old[:, 1], color='g', label='Start Points', s=40)

# Labels with bigger font
plt.xlabel('X', fontsize=22)
plt.ylabel('Y', fontsize=22)

# Invert Y-axis
# plt.gca().invert_yaxis()

# Increase tick font size
plt.tick_params(axis='both', which='major', labelsize=28)

# Legend with larger font
plt.legend(fontsize=28, loc='upper right')

# Show plot
plt.show()


## Draw a small window to display details

x_min, x_max = 1000, 1050  # X-axis range of the small window
y_min, y_max = 330, 380  # Y-axis range of the small window

combined = np.stack((good_old, good_new), axis=1)  # Shape: (100, 2, 2)

# Create a mask for both points in each row to ensure they are within the window
mask = (
    (combined[:, 0, 0] >= x_min) & (combined[:, 0, 0] <= x_max) &  # good_old x
    (combined[:, 0, 1] >= y_min) & (combined[:, 0, 1] <= y_max) &  # good_old y
    (combined[:, 1, 0] >= x_min) & (combined[:, 1, 0] <= x_max) &  # good_new x
    (combined[:, 1, 1] >= y_min) & (combined[:, 1, 1] <= y_max)    # good_new y
)

# Apply the strict mask to include only valid pairs
filtered_combined = combined[mask]  # Shape: (filtered_count, 2, 2)

# Check if there are any valid pairs
if len(filtered_combined) == 0:
    print("No valid point pairs found in the specified region.")
else:
    # Separate filtered points back into old and new
    filtered_good_old = filtered_combined[:, 0]
    filtered_good_new = filtered_combined[:, 1]

    # Ensure the same size
    assert filtered_good_old.shape == filtered_good_new.shape, "Filtered arrays are not the same size!"

    # Calculate deltas
    deltas = filtered_good_new - filtered_good_old

    # Crop the image to the defined window
    cropped_img = next_img[y_min:y_max, x_min:x_max]

    # Adjust point coordinates to fit the cropped window
    adjusted_good_old = filtered_good_old - [x_min, y_min]
    adjusted_good_new = filtered_good_new - [x_min, y_min]

    # Plot the cropped image with points
    plt.figure(figsize=(6, 6))
    plt.imshow(cropped_img, cmap='gray', extent=[0, x_max-x_min, 0, y_max-y_min])

    # Plot points
    plt.scatter(adjusted_good_old[:, 0], adjusted_good_old[:, 1], color='r', label='Start Points', s=20)
    plt.scatter(adjusted_good_new[:, 0], adjusted_good_new[:, 1], color='g', label='End Points', s=20)

    # Plot arrows between points if they exist
    if len(adjusted_good_old) > 0 and len(adjusted_good_new) > 0:
        plt.quiver(adjusted_good_old[:, 0], adjusted_good_old[:, 1],
                   deltas[:, 0], deltas[:, 1],
                   angles='xy', scale_units='xy', scale=1, color='b', alpha=0.7)

    # Add labels and legend
    plt.title('Strictly Filtered Region with Corresponding Points')
    plt.xlabel('X (Window Region)')
    plt.ylabel('Y (Window Region)')
    plt.legend()
    plt.grid(True)
    plt.axis('equal')  # Maintain equal aspect ratio

    # Save the visualization as PNG
    plt.savefig('strict_filtered_window_with_points.png', dpi=300, bbox_inches='tight')

    # Show the plot
    plt.show()
















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

# cv2.putText(overlayed_image, 'Displacement Magnitude (Low -> High)', (10, 20),
#             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
# cv2.rectangle(overlayed_image, (10, 30), (200, 50), (0, 0, 0), -1)
# for i, color in enumerate(np.linspace(0, 255, 10, dtype=np.uint8)):
#     cv2.rectangle(overlayed_image, (10 + i*19, 30), (29 + i*19, 50),
#                   tuple(int(c) for c in cv2.applyColorMap(np.array([[color]], dtype=np.uint8), cv2.COLORMAP_JET)[0, 0]),
#                   -1)
# cv2.putText(overlayed_image, 'Low', (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
# cv2.putText(overlayed_image, 'High', (160, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)


# Display the DIC-like image
cv2.imshow("DIC Visualization", overlayed_image)
cv2.imwrite("dic_visualization.jpg", overlayed_image)  # Save the result
cv2.waitKey(0)
cv2.destroyAllWindows()


min_disp, max_disp = np.min(displacements), np.max(displacements)
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(cv2.cvtColor(overlayed_image, cv2.COLOR_BGR2RGB))
ax.axis('off')

# Create an accurate color bar using the displacement range
sm = plt.cm.ScalarMappable(cmap='jet', norm=plt.Normalize(vmin=min_disp, vmax=max_disp))
cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Displacement (Pixel)', rotation=270, labelpad=25, fontsize=30)
cbar.ax.set_yticks(np.linspace(min_disp, max_disp, 5))  # Adjust ticks for clarity
cbar.ax.tick_params(labelsize=30)
# Display the plot
# plt.title("Optical Flow with DIC-Based Coloring (Unnormalized Color Bar)")
plt.show()

## if use original point, the number of data set is too large,
## instead, select the point with movement to reduce the data size.
## after filter, use the point to find the 3d point.

# movement_threshold = 0.5
# moving_points_mask  = displacements > movement_threshold
# moving_points_new = good_new[moving_points_mask]
# moving_points_old = good_old[moving_points_mask]

# moving_displacements = displacements[moving_points_mask]

# # Visualize only points with significant movement
# output_img_moving = cv2.cvtColor(next_img, cv2.COLOR_GRAY2BGR)
# for new, old, displacement in zip(moving_points_new, moving_points_old, moving_displacements):
#     a, b = new.ravel()
#     c, d = old.ravel()
#     cv2.arrowedLine(output_img_moving, (int(c), int(d)), (int(a), int(b)), (0, 255, 0), 1)
#     cv2.circle(output_img_moving, (int(a), int(b)), 3, (0, 0, 255), -1)

# # Save or display the result
# cv2.imshow("Significant Movement", output_img_moving)
# cv2.imwrite("significant_movement.jpg", output_img_moving)
# cv2.waitKey(0)
# cv2.destroyAllWindows()





#%%
"""
After we have the tracking path, we can read the next frame sama as the 90th, using the middle camera image
to find the closest point on json file.  find how many pixel it shifted.
"""

"""
This section is working on finding corresponding points from on array to another one.
"""

# import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
import seaborn as sns

# Build KD-Tree for array2
tree = KDTree(points_2d_91)  # Shape: (110638, 2)

# Query the closest points for array1
distances, closest_points = tree.query(good_new, workers=-1)  # Shape: (54688,)

# Get the matched corresponding points
corresponding_points = points_2d_91[closest_points]

print("Closest points computed using KD-Tree!")

x1, y1 = good_new[:, 0], good_new[:, 1]
x2, y2 = corresponding_points[:, 0], corresponding_points[:, 1]

# Plot points
# plt.figure(figsize=(10, 8))
# plt.scatter(x1, y1, color='green', label='Points in Image 1', s=20)
# plt.scatter(x2, y2, color='red', label='Corresponding Points in Image 2', s=20)

# # Draw lines for correspondence
# for i in range(len(good_new)):
#     plt.plot([x1[i], x2[i]], [y1[i], y2[i]], color='blue', linewidth=0.5)

# plt.legend()
# plt.xlabel("X")
# plt.ylabel("Y")
# plt.title("Point Correspondences")
# plt.grid(True)
# plt.show()

original_points = good_new  # Points in image 1
matched_points = corresponding_points  # Matched points in image 2

# Compute errors along x and y axes
errors_x = matched_points[:, 0] - original_points[:, 0]
errors_x_95 = np.quantile(errors_x, 0.95)

errors_y = matched_points[:, 1] - original_points[:, 1]
errors_y_95 = np.quantile(errors_y, 0.95)

# Plot the scatter plot
plt.figure(figsize=(10, 8))
plt.scatter(errors_x, errors_y, color='blue', s=0.1, alpha=0.6, label='Filtered Distance Scatter')

# Add reference lines
plt.axhline(errors_x_95, color='red', linestyle='--', linewidth=1)  # Horizontal reference line
plt.axvline(errors_x_95, color='red', linestyle='--', linewidth=1)  # Vertical reference line

plt.axhline(-errors_x_95, color='red', linestyle='--', linewidth=1)  # Horizontal reference line
plt.axvline(-errors_x_95, color='red', linestyle='--', linewidth=1)  # Vertical reference line

plt.xticks(fontsize=24)
plt.yticks(fontsize=24)

# Plot settings
# plt.title("Scatter Plot of Errors (X vs Y) for Filtered Points")
plt.xlabel("Error in X direction", fontsize=24)
plt.ylabel("Error in Y direction", fontsize=24)

plt.legend()
plt.grid(True)
plt.show()


plt.figure(1)
sns.histplot(errors_x)
plt.xticks(fontsize=24)
plt.yticks(fontsize=24)
plt.xlabel("Error in X direction (Pixel)", fontsize=24)
plt.ylabel("Count", fontsize=24)
plt.axvline(np.quantile(errors_x, 0.95),color="red")
plt.axvline(np.quantile(errors_x, 0.05),color="red")

plt.figure(2)
sns.histplot(errors_x)
plt.xticks(fontsize=24)
plt.yticks(fontsize=24)
plt.xlabel("Error in Y direction (Pixel)", fontsize=24)
plt.ylabel("Count", fontsize=24)
plt.axvline(np.quantile(errors_x, 0.95),color="red")
plt.axvline(np.quantile(errors_x, 0.05),color="red")


#%%

"""
since the 95% of point with in distance around 1 pixel, we only use those point to find 3d point.
"""

valid_indices = (np.abs(errors_x) <= errors_x_95) & (np.abs(errors_y) <= errors_y_95)

# Filter original and matched points based on valid indices
filtered_original_points = original_points[valid_indices]
filtered_matched_points = matched_points[valid_indices]


tree = KDTree(points_2d_91)

# Query the nearest 2D point in mapping_91 for each filtered_matched_point
distances, indices = tree.query(filtered_matched_points)
print("The sum of distance is: ", sum(distances))
# Retrieve corresponding 3D points
filtered_3d_points = points_3d_91[indices]


combined_points_91 = np.hstack((filtered_3d_points, filtered_matched_points))

#%%

tree_good_old = KDTree(good_old)  # Build KDTree with good_old
distances_good_old, indices_good_old = tree_good_old.query(filtered_matched_points)

# Retrieve matching points from good_old
matched_good_old = good_old[indices_good_old]

# Step 2: Map 2D points in good_old to 3D points using mapping_90
# Extract 2D and 3D points from mapping_90
points_3d_90, points_2d_90 = zip(*mapping_90)
points_3d_90 = np.array(points_3d_90)
points_2d_90 = np.array(points_2d_90)

# Build KDTree for points_2d_90
tree_mapping_90 = KDTree(points_2d_90)

# Query KDTree to find corresponding 3D points for matched_good_old
distances_mapping_90, indices_mapping_90 = tree_mapping_90.query(matched_good_old)

# Retrieve corresponding 3D points
corresponding_3d_points = points_3d_90[indices_mapping_90]

# Print the results
print(f"Found {len(corresponding_3d_points)} corresponding 3D points.")

#%%
import numpy as np
import pyvista as pv

# Reference 3D point for distance computation (e.g., the origin)
reference_point = filtered_3d_points

# Step 1: Compute distances between each corresponding_3d_point and the reference point
distances = np.linalg.norm(corresponding_3d_points - reference_point, axis=1)

# Step 2: Normalize distances to [0, 1] for color mapping
normalized_distances = (distances - distances.min()) / (distances.max() - distances.min())

# Step 3: Map normalized distances to colors using a colormap (e.g., 'viridis')
cmap = plt.cm.get_cmap("viridis")
colors = cmap(normalized_distances)[:, :3]  # Extract RGB values

# Step 4: Create a PyVista point cloud
point_cloud = pv.PolyData(corresponding_3d_points)

# Step 5: Add normalized distances as scalar values to the point cloud
point_cloud["Distance"] = normalized_distances
#%%
# Step 6: Visualize with color bar
plotter = pv.Plotter()

# Set scalar range using `clim` (Color Limits)
min_distance = distances.min()*966
max_distance = distances.max()*966

# scalar_bar_args = {
#     "title": "Displacement (mm)",       # Scalar bar title
#     "title_font_size": 35,     # Larger title font size
#     "label_font_size": 35,     # Larger label font size
#     "n_labels": 5,             # Number of labels on the scalar bar
#     "vertical": True,          # Display scalar bar vertically
#     "position_x": 0.2,        # Adjust horizontal position
#     "position_y": 0.1,         # Adjust vertical start position
#     "height": 0.1,             # Scalar bar height (80% of the plot window)
#     "width": 0.7,              # Scalar bar width
#     "fmt": "%.2f"              # Label formatting (2 decimal places)
# }

scalar_bar_args = {
    "title": "Displacement (mm)",       # Scalar bar title
    "title_font_size": 35,     # Larger title font size
    "label_font_size": 35,     # Larger label font size
    "n_labels": 5,             # Number of labels on the scalar bar
    "vertical": True,          # Display scalar bar vertically
    "position_x": 0.85,        # Adjust horizontal position
    "position_y": 0.1,         # Adjust vertical start position
    "height": 0.8,             # Scalar bar height (80% of the plot window)
    "width": 0.1,              # Scalar bar width
    "fmt": "%.2f"              # Label formatting (2 decimal places)
}

plotter.add_mesh(
    point_cloud,
    scalars="Distance",
    cmap="YlOrRd",
    clim=(min_distance, max_distance),  # Set the scalar bar range explicitly
    point_size=5,
    show_scalar_bar=True,
    scalar_bar_args=scalar_bar_args,
    render_points_as_spheres=True
)
plotter.scalar_bars.vertical = True
plotter.scalar_bars.title_font_size = 24
plotter.scalar_bars.label_font_size = 20
plotter.scalar_bars.title = "Distance"
plotter.scalar_bars.title_orientation = "vertical"  # Rotate title manually

# plotter.add_scalar_bar(
#     title="Distance",  # Scalar bar label
#     n_labels=5,                        # Number of labels on the scalar bar
#     fmt="%.2f",                        # Label formatting
#     title_font_size=30,                # Title font size
#     label_font_size=35,                # Label font size
#     vertical=True,                     # Ensures vertical orientation
#     position_x=0.9,                    # Horizontal position (closer to the right edge)
#     position_y=0.1,                    # Vertical start position
#     height=0.8,                        # Scalar bar height (80% of the plot window)
#     width=0.1                         # Scalar bar width
# )
plotter.add_axes()
# plotter.add_title("Corresponding 3D Points Colored by Distance")
plotter.show()

#%%
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv

# Compute distances and normalize
distances = np.linalg.norm(corresponding_3d_points - reference_point, axis=1)
normalized_distances = (distances - distances.min()) / (distances.max() - distances.min())

# Apply exponential scaling
scaled_distances = np.power(normalized_distances, 0.3)

# Create PyVista point cloud
point_cloud = pv.PolyData(corresponding_3d_points)
point_cloud["Distance"] = scaled_distances

# Visualize with adjusted settings
plotter = pv.Plotter()
plotter.add_mesh(point_cloud, scalars="Distance", cmap="YlOrRd", point_size=3, render_points_as_spheres=True, clim=[0, 1])

# plotter.add_scalar_bar(title="Distance (Scaled)", n_labels=5)
plotter.add_axes()
# plotter.add_title("Enhanced Color Visualization")
plotter.show()



#%%
import numpy as np
import pyvista as pv

# Step 1: Compute distances between each corresponding_3d_point and the reference point
distances = np.linalg.norm(corresponding_3d_points - reference_point, axis=1)

# Step 2: Apply exponential scaling for color visualization
scaled_distances = np.power(distances, 0.3)  # Adjust the exponent for desired scaling

# Step 3: Create PyVista point cloud
point_cloud = pv.PolyData(corresponding_3d_points)

# Step 4: Add both scaled and actual distances
point_cloud["Scaled Distance"] = scaled_distances  # Used for coloring
point_cloud["Actual Distance"] = distances  # Used for color bar display

# Step 5: Set Scalar Bar Range using Actual Distance
min_distance = distances.min()
max_distance = distances.max()

# Step 6: Visualization with PyVista
plotter = pv.Plotter()

# Add Mesh with Scaled Distances for Coloring
plotter.add_mesh(
    point_cloud,
    scalars="Scaled Distance",  # Color by scaled distances
    cmap="YlOrRd",              # Perceptually uniform colormap
    point_size=3,
    render_points_as_spheres=True,
    clim=(scaled_distances.min(), scaled_distances.max())  # Use scaled range for coloring
)

# Add Scalar Bar Reflecting Actual Distances
# plotter.add_scalar_bar(
#     title="Distance (Actual Values)",  # Scalar bar label
#     n_labels=5,                        # Number of labels on the scalar bar
#     fmt="%.2f",                        # Label formatting
#     title_font_size=14,                # Title font size
#     label_font_size=12                 # Label font size
# )

# Manually set scalar bar range to actual distances
plotter.update_scalar_bar_range([min_distance, max_distance])

# Add Axes and Title
plotter.add_axes()
plotter.add_title("3D Points Colored by Scaled Distance with True Distance on Color Bar", font_size=14)

# Display the plot
plotter.show()



"Spectral"


