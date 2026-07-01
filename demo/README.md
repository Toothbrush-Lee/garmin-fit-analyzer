# Demo FIT Files

`fit/` 目录用于放演示或待转换的 Garmin FIT 文件。

出于隐私考虑，仓库不包含真实 FIT 活动文件。真实 FIT 文件通常可能包含 GPS 轨迹、设备序列号、用户资料和运动时间等信息。

你可以把自己的 `.fit` 文件复制到 `demo/fit/`，然后从项目根目录批量转换：

```bash
uv run --no-editable fit-analyzer demo/fit --out output/demo --timezone Asia/Shanghai
```

如果已经构建了二进制：

```bash
dist/fit-analyzer demo/fit --out output/demo --timezone Asia/Shanghai
```
