# ch08 视觉里程计（2）：LK 光流行车 demo

使用 OpenCV 的稀疏金字塔 Lucas-Kanade 光流，跟踪一段真实行车视频中的纹理角点，导出像素轨迹和可播放的对比视频。无需 GPU、相机内参或训练权重。

## 运行

需要 Python 3.10+ 和命令行 `ffmpeg`（macOS 可用 `brew install ffmpeg`）。从仓库根目录运行：

```bash
python3 -m venv /path/to/lk-venv
/path/to/lk-venv/bin/pip install -r 'ch08视觉里程计（2）/requirements.txt'
/path/to/lk-venv/bin/python 'ch08视觉里程计（2）/run_lk_demo.py' --download-demo
```

`--download-demo` 获取 Udacity 官方课程仓库的 `solidWhiteRight.mp4`。固定来源提交和 SHA-256 校验记录在[来源说明](THIRD_PARTY_NOTICES.md)，默认视频缓存为 `.cache/solidWhiteRight.mp4`。不使用 KITTI 下载登录，也不需要下载完整数据集。

也可处理自己的恒定帧率视频：

```bash
/path/to/lk-venv/bin/python 'ch08视觉里程计（2）/run_lk_demo.py' \
  --video /path/to/driving.mp4 \
  --output /path/to/lk-results \
  --max-frames 300 --max-points 180 --trail-frames 35 --fb-threshold 1.0
```

默认输出在本目录 `results/driving_lk/`；`--max-frames 0` 处理全片。现有结果不会默认覆盖；需要重跑时显式指定 `--overwrite`。输入帧最多缩放到 960 像素宽；CSV 使用缩放后图像坐标，原始和处理分辨率均记在摘要中。时间使用 `frame / FPS`，可变帧率视频应先转成恒定帧率再运行。

## 看结果

运行后，浏览器打开 `results/driving_lk/index.html`，或通过本机服务预览：

```bash
/path/to/lk-venv/bin/python 'ch08视觉里程计（2）/serve_results.py'
```

访问 `http://127.0.0.1:8769`。预览服务只绑定本机，并支持 HTTP Range 读取，便于视频进度跳转。网页可慢放视频、选择六条代表性长寿命轨迹、查看 x/y 像素坐标随时间变化，并跳到该点出现的时刻。

| 生成文件 | 内容 |
| --- | --- |
| `lk_tracks.mp4` | H.264 对比视频：左侧原图、右侧 LK 轨迹，保持原片 FPS |
| `preview.jpg` | 单帧对比预览 |
| `contact_sheet.jpg` | 四个时刻的原图 / 轨迹快照 |
| `trajectories.svg` | 六条代表轨迹的图像平面坐标图，y 轴向下 |
| `observations.csv` | 每帧有效点的位置、位移和过滤误差，带独立 track ID |
| `summary.json` | 参数、视频校验、跟踪统计和代表轨迹 |
| `index.html` | 无外部依赖的本地可视化页面 |

输入缓存和生成结果均被 `.gitignore` 排除；运行脚本即可复现，不会自动上传视频或结果。

## 算法主线

1. 转灰度，用 Shi-Tomasi `goodFeaturesToTrack` 选择角点。默认最多 180 点、最小距离 14 px，跳过顶部 25%（此片天空较多）。
2. `calcOpticalFlowPyrLK` 从上一帧跟踪到当前帧：窗口 21×21，`maxLevel=3`（包含第 0 层，共最多四层），最多 30 次迭代，停止阈值 0.01。
3. 反向跟踪到上一帧，要求前后向状态成功、前后向距离 ≤ 1 px、LK 窗口误差 ≤ 25、坐标有限且仍在图像内。
4. 失效点终止；每 10 帧或所有点失效时补点。补点创建新 ID，不会把不同特征拼成同一条轨迹。
5. 右侧视频显示至少连续存活三帧的点及其最近 35 帧尾迹；CSV 保留全部有效观测，代表轨迹图显示完整生命周期。

颜色仅编码 track ID，不编码速度、语义类别或可信度。前后向误差是筛选条件，不是真值跟踪误差。补点属于独立的新轨迹，因此“总 ID 数”可以远大于“单帧活跃点数”。

本机完整运行：221 帧、25 FPS、8.84 秒，960×540；平均活跃点 155.08，共 1164 个 ID，最长轨迹持续 221 帧。这些统计只针对该片段和默认参数，不代表通用性能。

## 不能把像素线当作车辆轨迹

LK 输出图像上的二维运动，包含相机自运动、周围车辆运动和透视效应，**没有输出三维相机位姿或米制车速**。算法假设局部亮度近似不变、邻域运动相近；遮挡、模糊、光照变化、低纹理和大运动仍可能使跟踪失败或漂移。

## 验证

```bash
cd 'ch08视觉里程计（2）'
/path/to/lk-venv/bin/python -m unittest -v test_lk_demo.py
```

测试覆盖已知 3 px / 2 px 平移、无纹理 / 空点集、失效 ID 不复用、短视频编码与 CSV / 页面输出，以及避免误覆盖结果。

参考：[OpenCV 光流教程](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)、[Udacity 行车视频来源](https://github.com/udacity/CarND-LaneLines-P1)。
