# Sandtracking

Research scripts and figures for sand-surface tracking, image displacement analysis, and 3D point-cloud correspondence, collected from the ISGSR 2025 project folder.

[中文说明](README.zh-CN.md) · [Usage and data requirements](docs/usage.md) · [GitHub upload instructions](docs/github.md)

## Project status

This repository preserves the original experimental scripts and their filenames. The scripts contain local Windows paths, dataset-specific parameters, interactive windows, and exploratory sections. They require external experimental data and configuration before use. The two larger scripts are collections of research experiments rather than a single validated end-to-end pipeline.

The raw image sequences, reconstruction files, camera calibration, and VTU datasets are **not included**. The figures are existing illustrations and results, not a runnable example dataset. The video below uses the actual `image_collection_mask` sand-flow experiment referenced by `3d_DIC.py`.

## Sand-flow displacement video

[![Synchronized sand point cloud and frame-to-frame displacement colors](videos/sand_flow_preview.gif)](videos/sand_flow_displacement.mp4)

[Watch or download the MP4](videos/sand_flow_displacement.mp4) · [Method, data, and reproduction instructions](videos/README.md)

The left panel plays the original point cloud. The right panel colors the same source-frame geometry by estimated 3D displacement to the next frame, using image optical flow to establish point correspondence. Gray points have no accepted match; they do not represent zero displacement.

The MP4 covers 1,498 adjacent-frame pairs (0001→0002 through 1498→1499), at 1920 × 1080 and 30 fps playback, about 50 seconds. The camera and color range stay fixed. The original code's ×966 millimeter scale and nonlinear color exponent 0.3 are retained and disclosed; the physical scale has not been independently recalibrated. Playback FPS does not establish experimental timing. The GIF is a smaller 5 fps preview.

## Contents

```text
sandtracking/
├── scripts/
│   ├── manual_mask.py
│   ├── 3d_DIC.py
│   ├── find_point_distance.py
│   └── render_sand_flow_video.py   # Point cloud + tracked displacement video
├── figures/                       # Original images, plots, and SVG artwork
│   └── match_result/              # Original feature-matching figures
├── data/README.md                 # External input-data guidance
├── videos/                        # MP4, animated preview, poster, and provenance
├── docs/
│   ├── usage.md
│   └── github.md
├── requirements.txt
├── requirements-experiments.txt
├── README.zh-CN.md
└── local_archive/                 # Local copy only; excluded from Git
    ├── manuscripts/
    ├── posters/
    ├── reviews/
    ├── temporary/
    └── file_manifest.json
```

| Script | Purpose |
| --- | --- |
| `manual_mask.py` | Select a four-point polygon, mask an image collection, and preserve EXIF metadata when available. |
| `3d_DIC.py` | Project reconstructed 3D points into camera images, track image motion, inspect correspondence errors, and visualize 3D points. |
| `find_point_distance.py` | Explore VTU point-cloud distances, surface slopes, optical flow, OpenMVG reconstruction data, and triangulation. |
| `render_sand_flow_video.py` | Track adjacent sand-flow frames and render synchronized point-cloud/displacement panels. |

## Setup

Create a Python 3 environment from the repository root. For Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For the additional experiments in `find_point_distance.py`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experiments.txt
```

Dependencies were identified from the source imports. Original package versions were not recorded, so these files are dependency lists, not tested environment lockfiles. OpenCV, Matplotlib, and PyVista require a graphical desktop for the interactive parts.

Before running a script, follow [the usage guide](docs/usage.md) to configure the input paths, output paths, frame selections, and experiment-specific settings.

## Example figure

An existing image-displacement visualization from the source folder:

![Image displacement in pixels](figures/2D_DIC.png)

All 37 source image and artwork files are preserved in `figures/`, including the four original `match_result` images. Their filenames and contents are unchanged.

## Preservation and verification

The organization copied all 51 source files without deleting or editing the originals: 3 scripts and 37 figures are included in Git's upload scope; 11 manuscript, poster, review, and temporary files are kept in the ignored local archive. A local manifest records the original and destination paths, sizes, and SHA-256 hashes.

All three original scripts passed Python 3.11 syntax compilation and remain unchanged. The added renderer was run on the external sand-flow dataset. Identity, known-translation, and observed bad-track rejection checks were executed for its correspondence calculation. These checks do not constitute an independent physical validation of the experimental reconstruction or the ×966 scale. Source-file hashes, per-pair match counts, thresholds, and displacement summaries are recorded with the video.
