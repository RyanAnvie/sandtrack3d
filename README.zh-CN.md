# Sandtracking

Sandtracking 结合图像跟踪与三维重建点云，估计砂土表面的运动。项目通过建立相邻帧之间的点对应关系，计算三维位移，并以同步点云播放和位移着色展示沙体流动过程。

[English README](README.md) · [使用说明](docs/usage.md) · [输入数据要求](data/README.md)

## 沙流演示

[![沙流点云与三维位移估计](videos/sand_flow_preview.gif)](videos/sand_flow_displacement.mp4)

[观看或下载 MP4](videos/sand_flow_displacement.mp4) · [计算方法与复现说明](videos/README.md)

左侧播放带有原始 RGB 颜色的点云；右侧在相同点云位置上，以颜色显示到下一帧的三维位移估计。灰色表示没有通过检查的点对应关系。两侧采用固定视角，位移色标在整个序列中保持一致。

演示使用 `image_collection_mask` 沙流实验的前 1,000 组连续相邻帧。MP4 分辨率为 1920 × 1080，以 30 fps 播放，时长约 33.3 秒；GIF 为 5 fps 的缩小预览。播放速度不代表实验采集时间。

## 计算方法

1. 根据相机标定参数，将三维重建点投影到图像，并对对应图像进行畸变校正。
2. 使用 Lucas–Kanade 光流跟踪相邻图像中的投影点，通过前后向一致性检查排除不可靠的跟踪结果。
3. 将跟踪得到的图像位置与下一帧点云的投影点匹配，计算通过检查的对应点之间的三维欧氏距离。
4. 同步显示点云序列和位移颜色，将未匹配的点明确标为灰色。

项目还提供图像掩膜、二维位移可视化，以及点云距离和坡度分析等实验工具。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `scripts/manual_mask.py` | 交互选择多边形区域，并对图像序列应用掩膜。 |
| `scripts/3d_DIC.py` | 三维投影、图像跟踪、点对应关系与位移可视化实验。 |
| `scripts/find_point_distance.py` | 点云距离、坡度、光流和三角化实验。 |
| `scripts/render_sand_flow_video.py` | 计算相邻帧位移并生成同步视频。 |
| `figures/` | 位移图、点云可视化和匹配示例。 |
| `videos/` | 演示视频、动图、封面和计算记录。 |
| `docs/usage.md` | 脚本配置与运行说明。 |
| `data/README.md` | 图像、重建文件和标定数据要求。 |

## 安装与使用

在仓库根目录创建 Python 环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

生成沙流视频前，将 `scripts/render_sand_flow_video.py` 中的 `input_folder` 设置为图像与点云序列所在目录。FFmpeg 需要在 `PATH` 中；如果部分帧仅包含 `robust.bin`，还需将 `openmvg_converter` 设置为 OpenMVG 的 `ConvertSfM_DataFormat` 可执行文件。随后运行：

```powershell
.\.venv\Scripts\python.exe .\scripts\render_sand_flow_video.py
```

视频文件写入 `videos/`，分析缓存写入 `outputs/sand_flow_cache/`。原始图像、PLY/VTU 点云和相机标定数据需要单独准备，具体格式见[数据要求](data/README.md)。

运行 `find_point_distance.py` 中的附加实验还需安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experiments.txt
```

`3d_DIC.py` 和 `find_point_distance.py` 包含多个交互式实验代码段。请根据[使用说明](docs/usage.md)配置路径，并选择相应代码段运行。

## 位移结果说明

视频展示的是相邻帧之间的位移估计，不表示单颗沙粒贯穿整个序列的累计轨迹。重建噪声、遮挡和图像匹配歧义会影响估计结果。演示采用实验脚本中的 ×966 毫米换算系数和 0.3 非线性色阶，物理尺度未经过独立重新标定。[方法文档](videos/README.md)介绍了对应关系检查、颜色映射和计算验证。

## 图像位移示例

![图像位移，单位为像素](figures/2D_DIC.png)
