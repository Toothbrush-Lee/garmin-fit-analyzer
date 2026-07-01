# Garmin FIT Analyzer

一个小型 Garmin `.fit` 批量转换工具，基于 Garmin 官方 `garmin-fit-sdk`。

License: MIT

它可以把一个 FIT 文件、多个 FIT 文件，或者整个文件夹里的 FIT 文件批量转换成：

- `*_summary.json`: 结构化摘要
- `*_report.md`: 人类可读报告
- `*_records.csv`: 逐点记录，包含时间、GPS、距离、速度、海拔、心率等
- `*_laps.csv`: 分圈记录

## 最简单用法

普通用户不需要安装 Python，也不需要安装 uv。到 Releases 页面下载自己系统对应的压缩包，解压后运行 `fit-analyzer`，后面加上 FIT 文件或文件夹地址即可。

下载地址：<https://github.com/Toothbrush-Lee/Garmin/releases>

### macOS / Linux

假设你把压缩包下载到了“下载”文件夹：

```bash
cd ~/Downloads
tar -xzf fit-analyzer-macOS-ARM64.tar.gz
chmod +x ./fit-analyzer
./fit-analyzer "/Users/你的用户名/Downloads/activity.fit"
```

如果你下载的是 Linux 版本，把第一行解压命令里的文件名换成：

```bash
tar -xzf fit-analyzer-Linux-X64.tar.gz
```

### Windows

在 PowerShell 里运行：

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive .\fit-analyzer-Windows-X64.zip -DestinationPath .
.\fit-analyzer.exe "C:\Users\你的用户名\Downloads\activity.fit"
```

### 不知道文件地址怎么写？

先在命令行里输入程序名和一个空格：

```bash
./fit-analyzer "<把 .fit 文件拖到这里>"
```

然后把 `.fit` 文件直接拖进终端窗口，系统通常会自动填好完整路径。最后按回车即可。尖括号和里面的提示文字不用手动输入，它们只是这里的占位说明。

Windows PowerShell 里对应的是：

```powershell
.\fit-analyzer.exe "<把 .fit 文件拖到这里>"
```

### 也可以转换整个文件夹

如果一个文件夹里有很多 `.fit` 文件，直接把文件夹地址传进去：

```bash
./fit-analyzer "/Users/你的用户名/Downloads/fit-files"
```

Windows:

```powershell
.\fit-analyzer.exe "C:\Users\你的用户名\Downloads\fit-files"
```

程序会递归查找文件夹里的 `.fit` 文件并批量转换。

### 输出文件在哪里？

默认会输出到当前目录下的 `output/` 文件夹。

单个 FIT 文件会生成：

- `*_summary.json`: 结构化摘要
- `*_report.md`: 人类可读报告
- `*_records.csv`: 逐点记录，包含时间、GPS、距离、速度、海拔、心率等
- `*_laps.csv`: 分圈记录

如果一次转换多个 FIT 文件，程序会在 `output/` 下为每个 FIT 文件创建一个同名子文件夹，避免互相覆盖。

想指定输出位置，可以加 `--out`：

```bash
./fit-analyzer "/Users/你的用户名/Downloads/activity.fit" --out "/Users/你的用户名/Desktop/fit-output"
```

Windows:

```powershell
.\fit-analyzer.exe "C:\Users\你的用户名\Downloads\activity.fit" --out "C:\Users\你的用户名\Desktop\fit-output"
```

### 常用参数

```text
--out <目录>          输出目录，默认 output
--timezone <时区>     本地时间使用的 IANA 时区，默认 Asia/Shanghai
--raw-json           额外输出完整解码 JSON，可能包含隐私信息
--no-recursive       输入是文件夹时，只转换该文件夹第一层的 .fit 文件
```

如果直接运行 `fit-analyzer` 但不传文件地址，它会进入交互模式，提示你输入 FIT 文件或文件夹地址、输出目录和时区。

## 从源码运行

如果你是开发者，或者不想使用预构建二进制，也可以用 Python 3.11+ 和 uv 从源码运行：

```bash
uv sync --no-editable
uv run --no-editable fit-analyzer "/Users/你的用户名/Downloads/activity.fit"
```

## 构建二进制

这一节主要给开发者看。普通用户直接下载 Releases 里的压缩包即可，不需要自己构建。

如果你想自己打包，可以用 PyInstaller 构建独立可执行文件：

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

构建完成后，只需要运行可执行文件，传入 FIT 文件或文件夹即可。

macOS/Linux 示例：

```bash
dist/fit-analyzer "/Users/你的用户名/Downloads/activity.fit"
```

Windows PowerShell 示例：

```powershell
dist\fit-analyzer.exe "C:\Users\你的用户名\Downloads\activity.fit"
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
./fit-analyzer demo/fit --out output/demo
```

如果你是从源码运行，对应命令是：

```bash
uv run --no-editable fit-analyzer demo/fit --out output/demo
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
