# Usage and data requirements

## Before running

The three original scripts were copied without changing their contents. They execute work at module level, open graphical windows, and retain the original absolute Windows paths. Importing them is not a safe way to inspect their functions without also executing the surrounding code.

Install the dependencies described in the [README](../README.md), provide the [external data](../data/README.md), and edit the relevant paths directly in the scripts. No command-line interface or automatic dataset setup was added.

Keep derived output separate from input data. You can create an ignored `outputs/` directory at the repository root and use it as the working directory for relative output filenames. Absolute output paths inside each script must also be edited; changing the working directory does not redirect them.

## `manual_mask.py`

Edit `input_folder` and `output_root_folder` in the execution section. The script searches recursively for `*002.jpg`, takes the first 1500 matches, and then sorts that subset lexicographically. Verify the selected sequence; this is not a guaranteed numeric or chronological sort for arbitrary filenames.

After configuring the paths:

```powershell
.\.venv\Scripts\python.exe .\scripts\manual_mask.py
```

Click four polygon corners on the first image in boundary order. Press `q` before completing the selection to exit. The same mask is applied to all selected images, so the image dimensions and region must be appropriate for the whole sequence.

The original output pattern is `image_set_0001/image_json_002.jpg`, with subsequent folders numbered from the selected sequence order. Choose a new output folder to avoid overwriting earlier results. The script attempts to copy EXIF metadata and prints failures when metadata cannot be read or written.

## `3d_DIC.py`

The script contains multiple `#%%` research sections, repeated setup code, image tracking, correspondence analysis, and plotting. Inspect and run the intended sections in a scientific Python editor after their required variables have been initialized.

| Setting | Meaning |
| --- | --- |
| `ply_file_90`, `ply_file_91` | Paths to the two dense PLY point clouds; assigned in both setup sections. |
| `json_90_path`, `json_91_path` | Corresponding OpenMVG camera/reconstruction JSON paths; also repeated. |
| `image_90`, `image_91` | The matching camera images for the two frames. |
| Camera/view indexes, ROI and tracking parameters | Existing experiment-specific selections that must agree with the supplied data. |

The variable suffixes refer to an earlier experiment: the preserved paths actually select frames 0130 and 0131. Verify the paths themselves when selecting a frame pair. Both setup sections must be updated consistently.

This script reads `image_json_001.jpg`, whereas `manual_mask.py` currently selects and writes the `002` camera images. The supplied scripts do not establish an automatic sequence from masking to reconstruction to tracking. Prepare all required views and reconstruction products separately.

The code reads OpenMVG camera centers and computes translation as `t = -R @ C`; projection uses the camera matrix and homogeneous normalization. Existing geometry, view indexing, distortion handling, filtering, and visualization settings were left unchanged and have not been revalidated for another dataset.

Relative output names include `strict_filtered_window_with_points.png` and `dic_visualization.jpg`. Set the working directory to `outputs/` when evaluating sections so that generated files remain separate from the preserved figures. GUI displays require an interactive desktop.

## `find_point_distance.py`

This file combines several exploratory workflows, including VTU loading, nearest-neighbor distances, local slopes, optical flow, camera data inspection, triangulation, and PLY export. Sections share variables and repeat definitions. Select the relevant sections and inspect their dependencies before execution; a successful syntax check does not establish that running the entire file will work.

Review `vtk_files`, `output_dir`, every `root_dir`, `output_video_path`, the PLY/JSON/image paths, `json_file`, and `ply_filename`. Search the entire file for drive-letter paths because some paths occur directly inside function calls. Configure output destinations before running sections that save VTU, AVI, JPEG, or PLY files.

This file already uses `joblib` parallel computation and several visualization backends. These choices, the original frame selections, and the numerical parameters were preserved.

## `render_sand_flow_video.py`

This added script uses the original sand-flow image/PLY sequence in `image_collection_mask`. It computes image-guided 3D displacement between adjacent frames, then renders the point cloud on the left and displacement colors on the right. Configure `input_folder` and, when needed, `openmvg_converter` near the top of the script, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe .\scripts\render_sand_flow_video.py
```

The script uses NumPy, OpenCV, SciPy, plyfile, and Matplotlib's colormap table from the existing requirements. It does not require VTK/PyVista for rendering. FFmpeg must be on `PATH`. OpenMVG's `ConvertSfM_DataFormat` executable exports camera data from `robust.bin` where `robust.json` is absent; exports are written to the ignored `outputs/sand_flow_cache/`, never to the input folders.

The default range is source frames 1 through 1499. Frame 0 has no matching camera image and frame 1500 has no dense reconstruction in the supplied dataset. Each output image uses a source frame and its successor, so the full video has 1498 frames. Keep `recalculate_displacements = True` for normal use. Setting it to `False` reuses the analysis cache for rerendering the same data and settings; do not use stale caches after changing analysis parameters. Reruns replace this script's generated video assets.

Read [the video method and limitations](../videos/README.md), especially the retained ×966 scale, gray unmatched points, forward/backward validation, and nonlinear fixed color range.

## Validation limits

File-copy integrity and Python syntax were checked during organization. Complete execution and scientific results of the three original scripts were not validated. No original figures were regenerated. The added sand-flow renderer was executed separately on the actual image/PLY sequence; numerical correspondence checks are described in the video README.
