# Garmin FIT Analyzer

一个小型 Garmin `.fit` 批量转换工具，基于 Garmin 官方 `garmin-fit-sdk`。

License: MIT

它可以把一个 FIT 文件、多个 FIT 文件，或者整个文件夹里的 FIT 文件批量转换成：

- `*_summary.json`: 结构化摘要
- `*_report.md`: 人类可读报告
- `*_records.csv`: 逐点记录，包含时间、GPS、距离、速度、海拔、心率等
- `*_laps.csv`: 分圈记录

## 直接运行

需要 Python 3.11+ 和 uv。

```bash
uv sync --no-editable
uv run --no-editable fit-analyzer demo/fit --out output/demo --timezone Asia/Shanghai
```

上面的命令会递归查找 `demo/fit` 里的所有 `.fit` 文件。批量转换时，每个 FIT 会输出到一个同名子目录，避免文件互相覆盖。

也可以传单个文件：

```bash
uv run --no-editable fit-analyzer demo/fit/activity.fit --out output/activity
```

或传多个路径：

```bash
uv run --no-editable fit-analyzer demo/fit/activity-1.fit demo/fit/activity-2.fit --out output/two-files
```

常用参数：

```text
--out <目录>          输出目录
--timezone <时区>     本地时间使用的 IANA 时区，默认 Asia/Shanghai
--raw-json           额外输出完整解码 JSON，可能包含隐私信息
--no-recursive       输入是文件夹时，只转换该文件夹第一层的 .fit 文件
```

## 构建二进制

如果希望给不熟悉 Python 的人使用，可以用 PyInstaller 打包成独立可执行文件。

```bash
uv run --group build python scripts/build_binary.py
```

构建完成后会得到：

- macOS/Linux: `dist/fit-analyzer`
- Windows: `dist\fit-analyzer.exe`

默认构建单文件版。如果某些系统安全策略或沙箱环境拦截单文件版启动，可以构建目录版：

```bash
uv run --group build python scripts/build_binary.py --onedir
```

目录版的可执行文件通常位于：

- macOS/Linux: `dist/fit-analyzer/fit-analyzer`
- Windows: `dist\fit-analyzer\fit-analyzer.exe`

然后用户只需要运行可执行文件，传入 FIT 文件或文件夹即可。

macOS/Linux 示例：

```bash
dist/fit-analyzer demo/fit --out output/demo --timezone Asia/Shanghai
```

Windows PowerShell 示例：

```powershell
dist\fit-analyzer.exe demo\fit --out output\demo --timezone Asia/Shanghai
```

如果直接运行二进制但不传参数，它会进入交互模式，提示你输入 FIT 文件或文件夹路径、输出目录和时区。多个输入路径可以用 `|` 分隔。

说明：PyInstaller 通常需要在目标平台上构建对应平台的二进制。也就是说，Windows 版在 Windows 上构建，macOS 版在 macOS 上构建，Linux 版在 Linux 上构建。

## 自动构建多平台二进制

项目里已经包含 GitHub Actions 配置：

```text
.github/workflows/build-binaries.yml
```

把项目推到 GitHub 后，可以手动触发 `Build binaries` workflow，或打 `v*` tag 自动触发。它会分别在 Linux、macOS、Windows runner 上构建并上传 artifacts。

## Demo 文件

`demo/fit/` 是示例输入目录。出于隐私考虑，仓库不包含真实 FIT 活动文件，因为 FIT 文件通常可能包含 GPS 轨迹、设备序列号、用户资料和运动时间等信息。

把你自己的 `.fit` 文件放进 `demo/fit/` 后运行：

```bash
uv run --no-editable fit-analyzer demo/fit --out output/demo --timezone Asia/Shanghai
```

## 项目结构

```text
.
├── .github/workflows/build-binaries.yml
├── demo/
│   ├── README.md
│   └── fit/
│       └── .gitkeep
├── pyproject.toml
├── scripts/
│   ├── analyze_fit.py
│   └── build_binary.py
├── src/garmin_fit_analyzer/
│   ├── __init__.py
│   ├── __main__.py
│   └── cli.py
└── uv.lock
```

## 官方来源

- Garmin FIT SDK overview: https://developer.garmin.com/fit/overview/
- Garmin official FIT Python SDK: https://github.com/garmin/fit-python-sdk
- PyPI package: https://pypi.org/project/garmin-fit-sdk/
- Garmin official FIT SDK tools and FitCSVTool: https://github.com/garmin/fit-sdk-tools
