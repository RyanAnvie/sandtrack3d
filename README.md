# Sandtracking

Sandtracking estimates sand-surface motion by combining image tracking with reconstructed 3D point clouds. It establishes correspondences between consecutive frames and visualizes sand flow through synchronized point-cloud playback and displacement colors.

[中文说明](README.zh-CN.md) · [Usage guide](docs/usage.md) · [Input data](data/README.md)

## Sand-flow demonstration

[![Sand-flow point cloud and estimated 3D displacement](videos/sand_flow_preview.gif)](videos/sand_flow_displacement.mp4)

[Watch or download the MP4](videos/sand_flow_displacement.mp4) · [Method and reproduction details](videos/README.md)

The left panel displays the point cloud with its recorded RGB colors. The right panel shows the same geometry colored by estimated 3D displacement to the next frame. Gray indicates points without an accepted correspondence. Both panels use a fixed view, and the displacement color scale stays fixed throughout the sequence.

The demonstration contains the first 1,000 consecutive frame pairs from the `image_collection_mask` sand-flow experiment. The MP4 is 1920 × 1080 at 30 fps, approximately 33.3 seconds long; the GIF is a 5 fps preview. Playback speed is independent of experimental acquisition timing.

## Method

1. Project reconstructed 3D points into a calibrated camera view and undistort the corresponding images.
2. Track projected points between consecutive images using Lucas–Kanade optical flow. Check forward/backward consistency to reject unreliable tracks.
3. Match tracked image locations to projected points in the next point cloud. Compute the Euclidean 3D distance between each accepted source–destination pair.
4. Display the point-cloud sequence alongside the estimated displacement field, with unmatched points shown explicitly in gray.

The project also includes image masking, 2D displacement visualization, and experimental tools for point-cloud distance and slope analysis.

## Project structure

| Path | Purpose |
| --- | --- |
| `scripts/manual_mask.py` | Apply an interactively selected polygon mask to an image sequence. |
| `scripts/3d_DIC.py` | Explore 3D projection, image tracking, point correspondence, and displacement visualization. |
| `scripts/find_point_distance.py` | Explore point-cloud distances, slopes, optical flow, and triangulation. |
| `scripts/render_sand_flow_video.py` | Calculate adjacent-frame displacement and generate the synchronized video. |
| `figures/` | Displacement plots, point-cloud visualizations, and matching examples. |
| `videos/` | Demonstration video, animated preview, poster, and calculation metadata. |
| `docs/usage.md` | Script configuration and execution guidance. |
| `data/README.md` | Required images, reconstruction files, and calibration data. |

## Installation and use

Create a Python environment and install the dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

To generate the sand-flow video, set `input_folder` in `scripts/render_sand_flow_video.py` to your image/point-cloud sequence. FFmpeg must be available on `PATH`. For frames that contain only `robust.bin`, also set `openmvg_converter` to OpenMVG's `ConvertSfM_DataFormat` executable. Then run:

```powershell
.\.venv\Scripts\python.exe .\scripts\render_sand_flow_video.py
```

The renderer writes video assets to `videos/` and analysis caches to `outputs/sand_flow_cache/`. Raw images, PLY/VTU point clouds, and camera calibration are supplied separately; see the [data requirements](data/README.md).

Additional experiments in `find_point_distance.py` require:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experiments.txt
```

`3d_DIC.py` and `find_point_distance.py` contain interactive experiment sections. Configure their paths and run the relevant sections as described in the [usage guide](docs/usage.md).

## Displacement interpretation

The video shows pairwise displacement estimates, rather than cumulative trajectories of individual grains. Reconstruction noise, occlusion, and ambiguous image matches affect the estimates. The demonstration uses the experiment script's ×966 conversion to millimeters and a nonlinear color exponent of 0.3; the physical scale has not been independently recalibrated. The [method documentation](videos/README.md) explains correspondence checks, color mapping, and computational validation.

## Image-displacement example

![Image displacement in pixels](figures/2D_DIC.png)
