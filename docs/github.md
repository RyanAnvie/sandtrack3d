# 上传到 GitHub

本目录用于建立独立的 `sandtracking` 仓库。整理时只复制项目文件，不继承 `paper` 仓库的历史。论文、海报、审稿文档、Office 临时文件和复制清单保留在 `local_archive/`，由 `.gitignore` 排除。

## 首次提交

在新目录打开 PowerShell，先查看实际提交范围：

```powershell
Set-Location 'D:\Ryan\GitHub\sandtracking'
git status --short
git add .
git diff --cached --stat
git diff --cached --name-only
```

暂存列表应包含代码、图件、说明和依赖文件，不应出现 `local_archive/`。确认列表后创建提交：

```powershell
git commit -m "Organize ISGSR 2025 sand-tracking scripts and figures"
```

## 连接远程仓库

在 GitHub 新建名为 `sandtracking` 的空仓库，不额外初始化 README、`.gitignore` 或许可证。复制 GitHub 提供的仓库地址，将下面的 `YOUR_ACCOUNT` 替换成实际用户名或组织名：

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/sandtracking.git
git push -u origin main
```

此说明不会创建远程仓库或自动上传文件。若已有名为 `origin` 的远程配置，先用 `git remote -v` 检查，避免覆盖其他仓库的地址。

## 后续文件管理

- 原始实验数据放在 `data/` 下，运行结果放在 `outputs/` 下；这两个位置的数据文件默认不纳入 Git。
- `figures/` 保存从原文件夹复制的图件，后续运行结果不要覆盖这些原图。
- `local_archive/file_manifest.json` 记录所有 51 个源文件的原路径、整理后路径、文件大小和 SHA-256，便于核对迁移完整性。
- 保持 `local_archive/` 的忽略规则，除非之后明确决定发布其中的特定文件。

本次整理没有添加许可证，也没有修改脚本中的算法和实验参数。
