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

把项目推到 GitHub 后，可以手动触发 `Build binaries` workflow，或打 `v*` tag 自动触发。

- 手动触发：分别在 Linux、macOS、Windows runner 上构建，并上传临时 artifacts。
- 推送 `v*` tag：构建完成后自动创建或更新同名 GitHub Release，并把三端压缩包挂到 Release assets。

发布一个新版本的例子：

```bash
git tag v1.0.0
git push origin v1.0.0
```

tag 推送后，GitHub Actions 会生成类似下面的 Release 文件：

- `fit-analyzer-Linux-X64.tar.gz`
- `fit-analyzer-macOS-ARM64.tar.gz` 或 `fit-analyzer-macOS-X64.tar.gz`
- `fit-analyzer-Windows-X64.zip`

## 首次运行时的系统安全提示

当前 Release 里的二进制是 GitHub Actions 自动构建的开源工具，暂未做商业代码签名或 macOS notarization。因此 macOS Gatekeeper、Windows SmartScreen、浏览器或杀毒软件可能会提示“无法验证开发者”“Windows 已保护你的电脑”或“来自互联网的文件被阻止”。这是未签名小工具常见的提示，不代表文件一定有问题。

建议只对你确认可信的本项目 Release 文件做一次性放行，不要关闭整机的 Gatekeeper、SmartScreen 或杀毒软件。

运行前建议先确认：

- 只从本仓库的 GitHub Releases 下载：<https://github.com/Toothbrush-Lee/Garmin/releases>
- 下载的文件名和版本号符合预期，例如 `v0.1.1`。
- 如果你不信任预构建二进制，可以直接从源码构建：`uv run --group build python scripts/build_binary.py`。

### macOS

解压后先尝试正常运行：

```bash
tar -xzf fit-analyzer-macOS-ARM64.tar.gz
chmod +x ./fit-analyzer
./fit-analyzer --help
```

如果 macOS 拦截未签名文件，可以任选一种方式只放行这个文件：

1. 在 Finder 中找到 `fit-analyzer`，按住 Control 点击，选择“打开”，在确认弹窗中再次选择“打开”。
2. 先运行一次被拦截后，打开“系统设置” -> “隐私与安全性”，在底部找到相关提示，选择“仍要打开”。
3. 如果你确定文件来自本仓库 Release，也可以在终端移除这个文件的 quarantine 标记：

```bash
xattr -d com.apple.quarantine ./fit-analyzer
./fit-analyzer --help
```

Apple 官方说明：<https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac>

### Windows

解压后先尝试正常运行：

```powershell
.\fit-analyzer.exe --help
```

如果 Windows SmartScreen 提示“Windows 已保护你的电脑”，确认文件来自本仓库 Release 后，可以点击“更多信息” -> “仍要运行”。

如果文件属性里显示来自互联网而被阻止，可以任选一种方式只放行这个文件：

1. 右键 `fit-analyzer.exe` -> “属性” -> 勾选“解除锁定” -> “应用”。
2. 在 PowerShell 中运行：

```powershell
Unblock-File -LiteralPath .\fit-analyzer.exe
.\fit-analyzer.exe --help
```

Microsoft 官方 `Unblock-File` 文档也提醒：使用前应先检查文件和来源，确认安全后再解除阻止。文档地址：<https://learn.microsoft.com/powershell/module/microsoft.powershell.utility/unblock-file>

### Linux

解压后给可执行权限即可：

```bash
tar -xzf fit-analyzer-Linux-X64.tar.gz
chmod +x ./fit-analyzer
./fit-analyzer --help
```

如果系统或桌面环境提示文件来自互联网，请确认下载来源后，只对这个文件选择允许运行。

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
