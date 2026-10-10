# ch08 后端

目录按学习规划改名为 `ch08后端`；现有总结与行车 demo 仍保留视觉里程计（2）的内容，本次仅调整目录名称和路径引用。

[阅读本章总结 PDF](ch08视觉里程计（2）总结.pdf)

总结共五页：LK 亮度不变假设与最小二乘、迭代 / 金字塔和轨迹检查、SE(3) 直接法的反投影与光度优化、雅可比与可观测性、同一行车视频的两个仓库实验。延续前几章的概念主线、公式提示、对比表与工程边界，并结合具身训练数据的验收需求。

特别澄清：窗口内近似相同的是运动而不是灰度；二维像素尾迹不等于三维位姿；均匀白墙仍缺乏运动约束；位姿更新应包含透视除法中深度的变化；金字塔和误差下降不保证全局最优。

## 阅读材料与文档生成

本机 `Downloads/ch08视觉里程计（2）/` 中全部 19 张 JPG 已逐一阅读；截至此次整理，目录没有独立 TXT、RTF、Markdown 等笔记文本，图片中的文字和公式即为主要学习材料。没有将课堂原图上传仓库。

| 图片文件 | 内容 |
| --- | --- |
| `20261010-115600.jpg`、`20261010-115605.jpg` | 第八讲标题、光流与直接法学习目标 |
| `20261010-115609.jpg`、`20261010-115613.jpg` | 特征点法 VO 的流程、免描述子匹配的两种思路 |
| `20261010-115617.jpg`、`20261010-115621.jpg` | 稀疏 / 稠密光流、像素运动与灰度恒常假设 |
| `20261010-115625.jpg`、`20261010-115628.jpg`、`20261010-115631.jpg` | Taylor 展开、窗口最小二乘、迭代与金字塔 |
| `20261010-115635.jpg` | LK 光流实践章节标题 |
| `20261010-115638.jpg`、`20261010-115642.jpg`、`20261010-115645.jpg` | 直接法标题、相机几何动机、两帧投影关系 |
| `20261010-115649.jpg`、`20261010-115652.jpg`、`20261010-115655.jpg` | 光度残差、位姿扰动、雅可比链式法则 |
| `20261010-115658.jpg` | 图像梯度、稀疏 / 半稠密 / 稠密直接法 |
| `20261010-115702.jpg`、`20261010-115705.jpg` | 局部优化与非凸性、直接法优缺点 |

`generate_summary_pdf.py` 包含全文，`summary_assets/` 保留已有 demo 的两张实验快照。重新生成不依赖 Downloads 材料、视频缓存或 `results/`；快照来源和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

```bash
python3 -m pip install reportlab
python3 'ch08后端/generate_summary_pdf.py'
```

默认使用 macOS 的 Arial Unicode 字体；其他环境传入 `--font /path/to/chinese-font.ttf`，也可用 `--output /path/to/summary.pdf` 指定输出。

核对资料：[OpenCV 光流教程](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)、[Baker & Matthews 图像对齐](https://www.ri.cmu.edu/pub_files/pub3/baker_simon_2004_1/baker_simon_2004_1.pdf)、[十四讲作者的 RGB-D 直接法示例](https://github.com/gaoxiang12/slambook/blob/master/ch8/directMethod/direct_sparse.cpp)、[DSO 作者说明](https://cvg.cit.tum.de/research/vslam/dso)。

## 行车 demo 概览

使用 OpenCV 的稀疏金字塔 Lucas-Kanade 光流，跟踪一段真实行车视频中的纹理角点，导出像素轨迹和可播放的对比视频。无需 GPU、相机内参或训练权重。

本章另包含[直接法 demo](#直接法-demo道路平面光度对齐)：复用同一段行车视频，自行实现光度误差、雅可比与阻尼高斯牛顿，联合估计道路平面的单应变换，再可视化道路像素的模型投影轨迹。两种 demo 都是二维像素实验，不是三维车辆轨迹估计。

## 运行

需要 Python 3.10+ 和命令行 `ffmpeg`（macOS 可用 `brew install ffmpeg`）。从仓库根目录运行：

```bash
python3 -m venv /path/to/lk-venv
/path/to/lk-venv/bin/pip install -r 'ch08后端/requirements.txt'
/path/to/lk-venv/bin/python 'ch08后端/run_lk_demo.py' --download-demo
```

`--download-demo` 获取 Udacity 官方课程仓库的 `solidWhiteRight.mp4`。固定来源提交和 SHA-256 校验记录在[来源说明](THIRD_PARTY_NOTICES.md)，默认视频缓存为 `.cache/solidWhiteRight.mp4`。不使用 KITTI 下载登录，也不需要下载完整数据集。

也可处理自己的恒定帧率视频：

```bash
/path/to/lk-venv/bin/python 'ch08后端/run_lk_demo.py' \
  --video /path/to/driving.mp4 \
  --output /path/to/lk-results \
  --max-frames 300 --max-points 180 --trail-frames 35 --fb-threshold 1.0
```

默认输出在本目录 `results/driving_lk/`；`--max-frames 0` 处理全片。现有结果不会默认覆盖；需要重跑时显式指定 `--overwrite`。输入帧最多缩放到 960 像素宽；CSV 使用缩放后图像坐标，原始和处理分辨率均记在摘要中。时间使用 `frame / FPS`，可变帧率视频应先转成恒定帧率再运行。

## 看结果

运行后，浏览器打开 `results/driving_lk/index.html`，或通过本机服务预览：

```bash
/path/to/lk-venv/bin/python 'ch08后端/serve_results.py'
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

输入缓存和 `results/` 生成结果均被 `.gitignore` 排除；运行脚本即可复现，不会自动上传视频或结果。仅本章总结选用的两张静态实验快照保存在 `summary_assets/`，随 PDF 和生成器提交。

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
cd 'ch08后端'
/path/to/lk-venv/bin/python -m unittest -v test_lk_demo.py
```

测试覆盖已知 3 px / 2 px 平移、无纹理 / 空点集、失效 ID 不复用、短视频编码与 CSV / 页面输出，以及避免误覆盖结果。

参考：[OpenCV 光流教程](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html)、[Udacity 行车视频来源](https://github.com/udacity/CarND-LaneLines-P1)。

## 直接法 demo：道路平面光度对齐

### 运行与预览

复用上面的依赖、`ffmpeg` 和 `.cache/solidWhiteRight.mp4`；不需要额外权重。仓库根目录运行：

```bash
/path/to/lk-venv/bin/python 'ch08后端/run_direct_demo.py' --download-demo
/path/to/lk-venv/bin/python 'ch08后端/serve_results.py' \
  --directory 'ch08后端/results/driving_direct' --port 8770
```

打开 `http://127.0.0.1:8770`，可慢放对比视频、切换代表道路探针、查看图像平面轨迹与 x/y 时间曲线、跳到该点起始时刻。输出在 `results/driving_direct/`，同样不纳入 Git。使用自己的恒定帧率视频时传入 `--video /path/to/video.mp4`，但必须检查/调整 `direct_alignment.py` 中的人工道路 ROI，不能直接把此道路模型用于任意视频。

```bash
/path/to/lk-venv/bin/python 'ch08后端/run_direct_demo.py' \
  --video /path/to/driving.mp4 --output /path/to/direct-results \
  --max-frames 300 --max-width 960 --max-points 100
```

`--max-frames 0` 处理全片；重跑同一输出目录须传 `--overwrite`。CSV 坐标与单应矩阵均属于缩放后的处理图像。

| 文件 | 内容 |
| --- | --- |
| `direct_tracks.mp4` | 左原图、右道路探针投影及近期尾迹；空心点表示尚未存活三帧的新探针 |
| `preview.jpg`、`contact_sheet.jpg` | 轨迹预览和带时间标注的快照；预览选择实际累计尾迹较长的帧 |
| `index.html`、`trajectories.svg` | 交互报告及六条空间分散的代表轨迹 |
| `photometric_alignment.jpg` | 参考图、当前图、对齐图与同尺度光度误差图；黄色道路 ROI、重叠区域 MAE |
| `observations.csv` | 独立 track ID、位置、逐帧位移、正反向一致性和 7×7 光度 MAE |
| `frame_homographies.csv` | 上一帧 → 当前帧的 3×3 单应矩阵与质量门限状态 |
| `alignment_diagnostics.json` | 正反向各金字塔层的 Huber 目标值迭代日志及质量检查 |
| `summary.json` | 来源校验、参数、统计和代表轨迹 |

### 直接优化了什么

在人工指定的静态、近似平面道路区域，上一帧像素 `p` 经一个共享单应矩阵 `H` 映射到当前帧，齐次坐标需除以第三分量。目标是：

```text
H* = argmin_H Σ_p ρ( I_current(W_H(p)) - I_previous(p) )
p_current = W_H(p_previous)
```

`ρ` 为 Huber 损失；灰度归一化到 `[0,1]`，阈值 0.03。优化器在道路 ROI 的高梯度像素上采样，不需要先匹配两帧特征点。

1. 灰度图、道路梯形 ROI，图像金字塔默认 `levels=3`（含原图，共最多四层）。
2. 用上一帧变换和少量向内/向外的透视扩张候选做光度初始化，降低车道线沿线方向的局部极小问题。候选中心为图像宽的 0.5、高的 0.55，**只是本视频的初始化启发式，不是相机内参或测得的消失点**。
3. 每层计算当前图像的梯度、双线性采样及光度残差。单应矩阵固定 `h22=1`，优化其余 8 个参数；图像坐标归一化以改善数值条件。
4. 链式法则构造 `J = 图像梯度 × 单应投影雅可比`，Huber 加权，解阻尼法方程求增量。候选步须降低同一批有效样本的目标值，再更新矩阵；从粗到细迭代。优化采样留有边界余量，避免即将出图的道路像素阻止正确的外扩步骤。
5. 正反向各直接对齐一次，反向 ROI 为正向道路区域的投影。质量检查要求至少 65% 道路网格可见、至少 65% 可见点光度误差 <25，以及第 95 百分位帧间位移 <90 px；欠纹理/秩不足时拒绝对齐。
6. 用 Shi-Tomasi 只选择显示用的道路探针，不做跨帧特征匹配。将探针共同通过 `H` 投影；前后向距离 ≤1.5 px、7×7 完整投影图像块 MAE ≤25 且在图内才保留。每 10 帧或全部失效时补点，旧 ID 不复用。探针的数量不决定用于优化的光度采样数量（默认最多 3500 个）。

核心求解器在 `direct_alignment.py`，入口为 `run_direct_demo.py`；下载、视频编码和通用可视化复用 `run_lk_demo.py` 的输出管线。**直接求解没有调用 `calcOpticalFlowPyrLK`、`findTransformECC`、特征匹配或 `findHomography`。**

### 和 LK、书中的直接法有何区别

LK 和直接对齐都可以基于亮度残差与局部线性化，不能仅靠“用了光度误差”区分它们。这里与之前 LK demo 的差异在于：之前逐个点求局部二维位移；这里联合求一个全局道路单应，所有探针服从同一模型，**不是互相独立测量出的像素运动**。

这段原视频没有随附标定和深度。书中基于 3D 点、相机内参、`SE(3)` 位姿的直接法无法仅凭这些帧原样运行，所以本实验明确选用二维平面直接图像对齐；不伪造内参/深度，不输出三维位姿、米制距离或车速。前车、护栏、树木、坡道及非平面路面并不满足同一个道路模型。

### 本机实测与限制

默认参数、原片 221 帧 / 25 FPS / 8.84 秒 / 960×540：220 个帧间对齐通过质量门限，平均活跃探针 13.21，累计 2032 个 ID，最长连续轨迹 31 帧（首尾跨度 1.20 秒）。门限通过不等于几何真值准确；平坦路面使全 ROI 平均光度误差容易较低。新点和短轨迹较多，不应将它们拼接为长轨迹或据此声称精确的视觉里程计。

第 99→100 帧诊断图，在同一可见重叠道路 ROI 上，灰度绝对误差 MAE 从 2.55 降到 1.99（范围 0–255）。这只是该帧对的光度改进，不是像素跟踪真值误差。完整迭代日志可复查实际目标值变化。

低纹理、车道线的孔径歧义、遮挡、光照变化、曝光变化及模型偏差都会让直接法不稳定；需要靠谱的初始化和失败检查。特定道路 ROI 与初始化候选使本脚本是学习 demo，不是通用直接 SLAM 系统。

### 验证

```bash
cd 'ch08后端'
/path/to/lk-venv/bin/python -m unittest -v test_lk_demo.py test_direct_demo.py
```

共 11 项测试，包括已知平移/单应运动、真实双线性采样、各层目标值不增加、无纹理和单方向纹理退化拒绝、输入尺寸检查、丢失 ID 不复用、视频/CSV/页面/迭代日志输出和防止误覆盖。直接法端到端测试将 OpenCV LK、ECC、几何单应估计接口替换为会报错的桩，确认没有走这些求解捷径。

参考：[Baker & Matthews，参数化图像对齐与高斯牛顿](https://www.ri.cmu.edu/pub_files/pub3/baker_simon_2004_1/baker_simon_2004_1.pdf)、[十四讲作者的 RGB-D 直接法示例](https://github.com/gaoxiang12/slambook/blob/master/ch8/directMethod/direct_sparse.cpp)。
