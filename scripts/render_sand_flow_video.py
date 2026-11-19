"""Show synchronized sand point clouds and image-guided 3D displacement."""

from pathlib import Path
import hashlib
import json
import shutil
import subprocess

import cv2
import numpy as np
from matplotlib import colormaps
from plyfile import PlyData
from scipy.spatial import cKDTree


input_folder = Path(r"E:\SynologyDrive\ryan\image_collection_mask")
repository = Path(__file__).resolve().parents[1]
output_folder = repository / "videos"
cache_folder = repository / "outputs" / "sand_flow_cache"
openmvg_converter = Path(r"C:\SfM\openMVG2_build\Windows-AMD64-Release\Release\openMVG_main_ConvertSfM_DataFormat.exe")
first_frame = 1
last_frame = 1001  # Source frames 1..1000 use their successors for displacement.
camera_filename = "image_json_001.jpg"
frames_per_second = 30  # Playback rate, not an inferred acquisition rate.
recalculate_displacements = True

# These analysis/presentation values come from the original 3d_DIC.py.
lk_parameters = dict(winSize=(15, 15), maxLevel=2,
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
matching_quantile = 0.95
reconstruction_to_mm = 966.0  # Original author's scale; not independently recalibrated.
color_gamma = 0.3

video_width = 1920
video_height = 1080
video_crf = 26
video_maxrate = "12M"  # Limit file size for the repository's full-duration demo.
video_buffer_size = "24M"
panel_width = 860
panel_height = 820
panel_top = 145
left_panel_x = 40
right_panel_x = 980
point_size = 2  # Square point footprint in output pixels; no geometric resampling.
background_bgr = (27, 23, 19)
unmatched_bgr = (100, 100, 100)


def read_frame(frame_number, refresh_camera=False):
    folder = input_folder / ("image_set_%04d" % frame_number)
    reconstruction = folder / "reconstruction_global"
    camera_path = reconstruction / "robust.json"
    if not camera_path.exists():
        camera_path = cache_folder / ("cameras_%04d.json" % frame_number)
        if refresh_camera or not camera_path.exists():
            if not openmvg_converter.is_file():
                raise FileNotFoundError("Set openmvg_converter to ConvertSfM_DataFormat.exe.")
            result = subprocess.run([
                str(openmvg_converter), "-i", str(reconstruction / "robust.bin"),
                "-o", str(camera_path), "-V", "-I", "-E",
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stdout)

    camera_data = json.loads(camera_path.read_text(encoding="utf-8"))
    views = {}
    intrinsics = {}
    poses = {}
    for item in camera_data["views"]:
        view = item["value"]["ptr_wrapper"]["data"]
        views[view["filename"]] = view
    for item in camera_data["intrinsics"]:
        intrinsics[item["key"]] = item["value"]["ptr_wrapper"]["data"]
    for item in camera_data["extrinsics"]:
        poses[item["key"]] = item["value"]
    view = views[camera_filename]
    intrinsic = intrinsics[view["id_intrinsic"]]
    pose = poses[view["id_pose"]]
    focal_length = intrinsic["focal_length"]
    cx, cy = intrinsic["principal_point"]
    K = np.array([[focal_length, 0, cx], [0, focal_length, cy], [0, 0, 1]])
    k1, k2, k3 = intrinsic["disto_k3"]
    distortion = np.array([k1, k2, 0, 0, k3])
    R = np.array(pose["rotation"])
    C = np.array(pose["center"])
    t = -R @ C

    ply_path = reconstruction / "robust_scene_dense.ply"
    ply = PlyData.read(str(ply_path))
    vertices = ply["vertex"]
    points = np.column_stack([vertices["x"], vertices["y"], vertices["z"]])
    rgb = np.column_stack([vertices["red"], vertices["green"], vertices["blue"]])
    if not np.isfinite(points).all():
        raise ValueError("Nonfinite XYZ coordinates in " + str(ply_path))
    camera_points = points @ R.T + t.reshape(1, 3)
    depth = camera_points[:, 2]
    homogeneous = camera_points @ K.T
    pixels = homogeneous[:, :2] / homogeneous[:, 2:3]

    image_path = folder / camera_filename
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(str(image_path))
    image = cv2.undistort(image, K, distortion, None, K)
    visible = ((depth > 0) & np.isfinite(pixels).all(axis=1)
               & (pixels[:, 0] >= 0) & (pixels[:, 0] < image.shape[1])
               & (pixels[:, 1] >= 0) & (pixels[:, 1] < image.shape[0]))

    return {"number": frame_number, "points": points, "rgb": rgb,
            "pixels": pixels, "depth": depth, "visible": visible, "image": image,
            "K": K, "distortion": distortion, "R": R, "C": C,
            "source": {
                "frame": frame_number, "point_count": len(points),
                "visible_point_count": int(visible.sum()),
                "ply_attributes": list(vertices.data.dtype.names),
                "ply_sha256": hashlib.sha256(ply_path.read_bytes()).hexdigest(),
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "camera_sha256": hashlib.sha256(camera_path.read_bytes()).hexdigest(),
                "camera_source": "robust.json" if (reconstruction / "robust.json").exists() else "robust.bin exported with OpenMVG -V -I -E",
            }}


def track_frame_pair(previous, current):
    source_ids = np.flatnonzero(previous["visible"])
    p0 = previous["pixels"][source_ids].astype(np.float32).reshape(-1, 1, 2)
    p1, status, error = cv2.calcOpticalFlowPyrLK(
        previous["image"], current["image"], p0, None, **lk_parameters)
    if p1 is None:
        raise ValueError("Optical flow failed at frame %d" % previous["number"])
    new_pixels = p1.reshape(-1, 2)
    good = ((status.ravel() == 1) & np.isfinite(new_pixels).all(axis=1)
            & (new_pixels[:, 0] >= 0) & (new_pixels[:, 0] < current["image"].shape[1])
            & (new_pixels[:, 1] >= 0) & (new_pixels[:, 1] < current["image"].shape[0]))
    source_ids = source_ids[good]
    new_pixels = new_pixels[good]
    # A successful forward LK status can still jump from sand to the pipe.
    # Reject inconsistent round trips using the same 95% residual rule.
    backward, backward_status, backward_error = cv2.calcOpticalFlowPyrLK(
        current["image"], previous["image"], new_pixels.reshape(-1, 1, 2),
        None, **lk_parameters)
    backward = backward.reshape(-1, 2)
    backward_valid = (backward_status.ravel() == 1) & np.isfinite(backward).all(axis=1)
    round_trip_error = np.abs(backward - previous["pixels"][source_ids])
    round_trip_limits = np.quantile(round_trip_error[backward_valid], matching_quantile, axis=0)
    consistent = backward_valid & (round_trip_error <= round_trip_limits).all(axis=1)
    source_ids = source_ids[consistent]
    new_pixels = new_pixels[consistent]
    target_ids = np.flatnonzero(current["visible"])
    tree = cKDTree(current["pixels"][target_ids])
    residual_norm, nearest = tree.query(new_pixels)
    matched_ids = target_ids[nearest]
    residual = np.abs(current["pixels"][matched_ids] - new_pixels)
    limits = np.quantile(residual, matching_quantile, axis=0)
    accepted = (residual <= limits).all(axis=1)

    # Keep each optical-flow seed's source index. Do not query old points with
    # the new image coordinates, which loses the temporal correspondence.
    source_ids = source_ids[accepted]
    matched_ids = matched_ids[accepted]
    delta = current["points"][matched_ids] - previous["points"][source_ids]
    distance_mm = np.linalg.norm(delta, axis=1) * reconstruction_to_mm
    displacement = np.full(len(previous["points"]), np.nan, dtype=np.float32)
    target_index = np.full(len(previous["points"]), -1, dtype=np.int32)
    displacement[source_ids] = distance_mm
    target_index[source_ids] = matched_ids
    statistics = {
        "from_frame": previous["number"], "to_frame": current["number"],
        "seed_count": int(previous["visible"].sum()), "lk_valid_count": int(good.sum()),
        "round_trip_accepted_count": int(consistent.sum()),
        "round_trip_pixel_residual_limits": round_trip_limits.tolist(),
        "accepted_count": int(accepted.sum()),
        "absolute_pixel_residual_limits": limits.tolist(),
        "displacement_mm_quantiles_0_50_90_95_99_100": np.quantile(distance_mm, [0, .5, .9, .95, .99, 1]).tolist(),
    }
    return displacement, target_index, statistics


def rasterize_cloud(frame_data, displacement, view_bounds, color_maximum, palette):
    x_min, y_min, x_max, y_max = view_bounds
    scale = min((panel_width - 30) / (x_max - x_min),
                (panel_height - 30) / (y_max - y_min))
    origin = np.array([x_min, y_min])
    shift = np.array([(panel_width - scale * (x_max - x_min)) / 2,
                      (panel_height - scale * (y_max - y_min)) / 2])
    point_ids = np.flatnonzero(frame_data["visible"])
    locations = np.rint((frame_data["pixels"][point_ids] - origin) * scale + shift).astype(int)
    pixel_ids = []
    vertex_ids = []
    for dy in range(point_size):
        for dx in range(point_size):
            x = locations[:, 0] + dx
            y = locations[:, 1] + dy
            inside = (x >= 0) & (x < panel_width) & (y >= 0) & (y < panel_height)
            pixel_ids.append(y[inside] * panel_width + x[inside])
            vertex_ids.append(point_ids[inside])
    pixel_ids = np.concatenate(pixel_ids)
    vertex_ids = np.concatenate(vertex_ids)
    order = np.lexsort((frame_data["depth"][vertex_ids], pixel_ids))
    sorted_pixels = pixel_ids[order]
    nearest = np.empty(len(sorted_pixels), dtype=bool)
    nearest[0] = True
    nearest[1:] = sorted_pixels[1:] != sorted_pixels[:-1]
    destination = sorted_pixels[nearest]
    selected = vertex_ids[order[nearest]]

    original = np.full((panel_height * panel_width, 3), background_bgr, dtype=np.uint8)
    colored = original.copy()
    original[destination] = frame_data["rgb"][selected, ::-1]
    colored[destination] = unmatched_bgr
    measured = np.isfinite(displacement[selected])
    normalized = displacement[selected[measured]] / color_maximum
    color_ids = np.rint(np.power(normalized, color_gamma) * 255).astype(int)
    colored[destination[measured]] = palette[color_ids]
    return original.reshape(panel_height, panel_width, 3), colored.reshape(panel_height, panel_width, 3)


def render_sand_flow_video():
    cache_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FileNotFoundError("FFmpeg is required on PATH.")
    metadata_path = cache_folder / "analysis.json"

    if recalculate_displacements:
        sources = []
        pairs = []
        view_lower = np.full(2, np.inf)
        view_upper = np.full(2, -np.inf)
        color_maximum = 0.0
        previous = read_frame(first_frame, refresh_camera=True)
        reference_camera = [previous[key].copy() for key in ["K", "distortion", "R", "C"]]
        sources.append(previous["source"])
        for frame_number in range(first_frame + 1, last_frame + 1):
            current = read_frame(frame_number, refresh_camera=True)
            for key, reference in zip(["K", "distortion", "R", "C"], reference_camera):
                if not np.array_equal(current[key], reference):
                    raise ValueError("Camera calibration differs at frame %d: %s" % (frame_number, key))
            sources.append(current["source"])
            displacement, targets, statistics = track_frame_pair(previous, current)
            np.savez_compressed(cache_folder / ("flow_%04d.npz" % previous["number"]),
                                displacement_mm=displacement, target_index=targets)
            color_maximum = max(color_maximum, float(np.nanmax(displacement)))
            visible_pixels = previous["pixels"][previous["visible"]]
            view_lower = np.minimum(view_lower, visible_pixels.min(axis=0))
            view_upper = np.maximum(view_upper, visible_pixels.max(axis=0))
            pairs.append(statistics)
            previous = current
            if len(pairs) % 50 == 0 or frame_number == last_frame:
                print("Calculated %d / %d frame pairs; maximum %.3f mm" %
                      (len(pairs), last_frame - first_frame, color_maximum), flush=True)

        metadata = {
            "input_folder": str(input_folder), "first_frame": first_frame, "last_frame": last_frame,
            "displayed_frames": last_frame - first_frame,
            "playback_fps": frames_per_second,
            "duration_seconds": (last_frame - first_frame) / frames_per_second,
            "acquisition_timing": "Not established; frame numbers are shown instead of experimental timestamps.",
            "video_size_pixels": [video_width, video_height],
            "camera": {key: value.tolist() for key, value in zip(["K", "distortion", "R", "C"], reference_camera)},
            "calibration_check": "All selected frames' camera parameters were read and compared exactly, including exported robust.bin camera data.",
            "displacement_definition": "Euclidean 3D distance from each source PLY point to the next-frame PLY point matched to its Lucas-Kanade image track; rendered at the source point location.",
            "reconstruction_to_mm": reconstruction_to_mm,
            "scale_source": "Original 3d_DIC.py multiplies distances by 966 and labels them mm; this scale was retained, not independently calibrated.",
            "lk_parameters": {"winSize": [15, 15], "maxLevel": 2, "iterations": 10, "epsilon": 0.03},
            "matching_quantile": matching_quantile,
            "selection": "Positive camera depth, inside image, successful finite in-image forward/backward LK tracks; per-axis round-trip residual and target-cloud pixel matching residual each at or below its frame-pair 95th percentile. Unaccepted points are gray, not zero.",
            "correspondence_corrections": "Preserve each seed's original 3D index; use absolute residual quantiles rather than signed residual quantiles; add a forward/backward consistency check using the same 95th-percentile rule to reject observed boundary-to-pipe tracking jumps.",
            "color_mapping": "YlOrRd at (displacement_mm / full_sequence_maximum_mm) ** gamma; fixed limits; no clipping or per-frame renormalization.",
            "color_gamma": color_gamma, "color_maximum_mm": color_maximum,
            "view_bounds_pixels": [*view_lower.tolist(), *view_upper.tolist()],
            "rendering": "Calibrated camera-001 point-cloud projection with nearest-depth rasterization, fixed framing, and a 2x2 pixel point footprint in both panels. No surface interpolation, smoothing, or geometry/attribute edits.",
            "sources": sources, "pairs": pairs,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    else:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["first_frame"] != first_frame or metadata["last_frame"] != last_frame:
            raise ValueError("Cached analysis covers a different frame range.")

    color_maximum = metadata["color_maximum_mm"]
    if color_maximum <= 0:
        raise ValueError("All measured displacements are zero.")
    metadata["video_encoding"] = {"codec": "H.264", "pixel_format": "yuv420p",
                                  "crf": video_crf, "maxrate": video_maxrate,
                                  "buffer_size": video_buffer_size}
    palette_rgb = np.rint(colormaps["YlOrRd"](np.linspace(0, 1, 256))[:, :3] * 255).astype(np.uint8)
    palette = palette_rgb[:, ::-1].copy()
    video_path = output_folder / "sand_flow_displacement.mp4"
    temporary_path = output_folder / "sand_flow_displacement.partial.mp4"
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
               "-pix_fmt", "bgr24", "-s", "%dx%d" % (video_width, video_height),
               "-r", str(frames_per_second), "-i", "pipe:0", "-an", "-c:v", "libx264",
               "-preset", "medium", "-crf", str(video_crf),
               "-maxrate", video_maxrate, "-bufsize", video_buffer_size,
               "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(temporary_path)]
    font = cv2.FONT_HERSHEY_SIMPLEX
    white = (235, 235, 235)
    muted = (170, 170, 170)
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for order, frame_number in enumerate(range(first_frame, last_frame)):
            frame_data = read_frame(frame_number)
            if frame_data["source"] != metadata["sources"][order]:
                raise ValueError("Source files changed after analysis: frame %d" % frame_number)
            flow = np.load(cache_folder / ("flow_%04d.npz" % frame_number))
            displacement = flow["displacement_mm"]
            left, right = rasterize_cloud(frame_data, displacement, metadata["view_bounds_pixels"], color_maximum, palette)
            canvas = np.full((video_height, video_width, 3), background_bgr, dtype=np.uint8)
            canvas[panel_top:panel_top + panel_height, left_panel_x:left_panel_x + panel_width] = left
            canvas[panel_top:panel_top + panel_height, right_panel_x:right_panel_x + panel_width] = right
            cv2.putText(canvas, "SAND FLOW TRACKING", (40, 52), font, 1.05, white, 2, cv2.LINE_AA)
            cv2.putText(canvas, "%04d -> %04d  |  %d fps playback" % (frame_number, frame_number + 1, frames_per_second),
                        (1320, 50), font, .68, white, 1, cv2.LINE_AA)
            cv2.putText(canvas, "A   ORIGINAL POINT CLOUD", (40, 112), font, .78, white, 1, cv2.LINE_AA)
            cv2.putText(canvas, "B   FRAME-TO-FRAME 3D DISPLACEMENT", (980, 112), font, .73, white, 1, cv2.LINE_AA)
            cv2.line(canvas, (940, 140), (940, 970), (65, 60, 55), 1)

            bar_x, bar_y, bar_height = 1850, 240, 580
            bar = palette[np.rint(np.linspace(255, 0, bar_height)).astype(int)]
            canvas[bar_y:bar_y + bar_height, bar_x:bar_x + 18] = bar[:, None, :]
            cv2.putText(canvas, "mm", (1850, 213), font, .55, white, 1, cv2.LINE_AA)
            for fraction in np.linspace(0, 1, 5):
                value = color_maximum * fraction ** (1 / color_gamma)
                y = bar_y + round((1 - fraction) * (bar_height - 1))
                cv2.line(canvas, (bar_x + 18, y), (bar_x + 24, y), muted, 1)
                tick_label = "%.1f" % value if value < 10 else "%.0f" % value
                cv2.putText(canvas, tick_label, (bar_x + 28, y + 5), font, .38, white, 1, cv2.LINE_AA)

            stats = metadata["pairs"][order]
            source_label = "Source frame {:04d}  |  {:,} points".format(frame_number, len(frame_data["points"]))
            cv2.putText(canvas, source_label,
                        (40, 1003), font, .62, muted, 1, cv2.LINE_AA)
            cv2.putText(canvas, "{:,.0f} matched points  |  Gray = no accepted match".format(stats["accepted_count"]),
                        (980, 1003), font, .56, muted, 1, cv2.LINE_AA)
            cv2.putText(canvas, "Fixed view and color range  |  Nonlinear color scale: gamma 0.3  |  mm scale follows source code (x966)",
                        (40, 1047), font, .56, muted, 1, cv2.LINE_AA)
            process.stdin.write(canvas.tobytes())
            if frame_number == 130:
                if not cv2.imwrite(str(output_folder / "sand_flow_poster.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94]):
                    raise OSError("Poster write failed.")
            if (order + 1) % 50 == 0 or frame_number == last_frame - 1:
                print("Rendered %d / %d frames" % (order + 1, last_frame - first_frame), flush=True)
    finally:
        process.stdin.close()
        return_code = process.wait()
    if return_code != 0:
        raise RuntimeError("FFmpeg exited with code %d" % return_code)
    temporary_path.replace(video_path)

    metadata["video_sha256"] = hashlib.sha256(video_path.read_bytes()).hexdigest()
    metadata["preview"] = "Full-duration 640x360 looping GIF at 5 fps; MP4 retains every analyzed frame pair."
    (output_folder / "sand_flow_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    preview_filter = ("fps=5,scale=640:-1:flags=lanczos,split[a][b];"
                      "[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path),
                    "-filter_complex", preview_filter, "-loop", "0",
                    str(output_folder / "sand_flow_preview.gif")], check=True)
    print("Saved synchronized sand-flow video to " + str(video_path), flush=True)


if __name__ == "__main__":
    render_sand_flow_video()
