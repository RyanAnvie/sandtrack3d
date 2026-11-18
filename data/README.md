# External experimental data

The source folder did not contain the raw image sequences, reconstruction inputs, or point-cloud datasets referenced by the scripts. Add your own data here or configure the scripts to read another local directory. Everything below `data/` except this README is ignored by Git.

Required inputs depend on the selected experiment:

| Script | Inputs referenced by the original code |
| --- | --- |
| `manual_mask.py` | JPEG images matching `**/*002.jpg` beneath `input_folder`. |
| `3d_DIC.py` | Two frame folders containing `image_json_001.jpg`, `reconstruction_global/robust_scene_dense.ply`, and `reconstruction_global/robust.json`. The original paths select frames 0130 and 0131. |
| `find_point_distance.py` | Depending on the code section: VTU sequences, image sequences, reconstructed PLY files, OpenMVG JSON/feature files, or `known_pose0000.json`. |

The dense PLY inputs in the DIC experiments include XYZ coordinates, and the next-frame cloud is also read for red, green, and blue attributes. OpenMVG JSON is expected to contain the camera fields accessed by the scripts. Preserve frame/view identifiers and use mutually consistent images, calibration, and point clouds.

No dataset download URL, complete calibration package, or general physical scale was supplied with these files. Use the units and coordinate conventions of your own reconstruction; do not infer physical units from the image-displacement figure.

See [the usage guide](../docs/usage.md) before execution.
