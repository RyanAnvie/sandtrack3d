# Sandtracking

从 ISGSR 2025 项目文件夹整理的砂土表面跟踪、图像位移分析和三维点云对应研究脚本。

[English README](README.md) · [运行和数据说明](docs/usage.md) · [上传 GitHub](docs/github.md)

## 文件安排

| 目录或文件 | 内容 | 是否纳入 Git |
| --- | --- | --- |
| `scripts/` | 3 个原始 Python 脚本 | 是 |
| `figures/` | 37 个原始图件，包含 `match_result/` | 是 |
| `docs/`、`data/README.md` | 使用、数据和上传说明 | 是 |
| `requirements*.txt` | 从脚本导入语句整理的依赖 | 是 |
| `local_archive/manuscripts/` | 7 个论文文档/PDF | 否 |
| `local_archive/posters/` | 2 个海报 PPTX | 否 |
| `local_archive/reviews/` | 1 个审稿文档 | 否 |
| `local_archive/temporary/` | 1 个 Office 临时锁文件 | 否 |
| `local_archive/file_manifest.json` | 全部原文件的路径映射、大小和 SHA-256 | 否 |

原文件夹完整保留；51 个文件均采用复制方式迁入，原始文件名和文件内容未修改。`local_archive/` 已写入 `.gitignore`，普通 `git add .` 不会包含其中的内容。

## 脚本用途

- `manual_mask.py`：手动选择四点多边形，对图像序列进行掩膜，并在可读取时保留 EXIF 信息。
- `3d_DIC.py`：三维点投影、图像光流跟踪、点对应误差分析及三维可视化。
- `find_point_distance.py`：包含 VTU 点云距离、坡度、光流、OpenMVG 数据读取和三角化等探索性代码段。

## 安装与使用

在仓库根目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

运行 `find_point_distance.py` 中的附加实验还需要：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experiments.txt
```

脚本保留了原有的 Windows 绝对路径、帧号、阈值和交互窗口。运行前必须按 [使用说明](docs/usage.md) 修改输入输出路径并准备对应数据。两个较大的脚本包含多个实验代码段，不能当作已验证的一键运行流程。

原始图像序列、PLY/VTU 点云、OpenMVG JSON 和标定数据不在本仓库中；`figures/` 中的图件不能代替完整实验数据。依赖版本在原文件夹中没有记录，因此没有编造版本锁定。

## 验证范围

已核对全部复制文件的 SHA-256，并对 3 个 Python 脚本执行 Python 3.11 语法编译检查。未运行完整实验，也未重新生成图表或验证数值结果。此次整理没有修改算法、坐标约定、单位、阈值或实验数据。
