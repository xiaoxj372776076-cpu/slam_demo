# ch07 视觉里程计 1：ORB-SLAM3 RGB-D 实验

本讲概念总结：[ch07 视觉里程计 1 总结（PDF）](ch07视觉里程计1总结.pdf)。它结合课堂图片、个人笔记与本目录实验，梳理 ORB、对极几何、五点法/八点法和三角化。

这个 demo 使用 **官方 ORB-SLAM3 的 RGB-D 模式**在 TUM RGB-D `freiburg1_xyz` 上估计相机位置，并从该序列的 RGB 帧生成可播放视频。输出包括逐帧跟踪状态、TUM 格式轨迹、CSV 位置、轨迹与真值对比图、两张 ORB 匹配诊断图，以及一个本地网页总览。

`fr1/xyz` 约 30 秒，运动主要沿 x/y/z 轴，适合作为入门轨迹；RGB-D 提供米制尺度。数据来源：[TUM RGB-D 官方下载页](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download)、[格式说明](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats)。算法源码来自 [UZ-SLAMLab/ORB_SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3)。数据包约 0.47 GB，**不纳入仓库**。

数据及其衍生视频/截图归属 TUM RGB-D Benchmark，按 [CC BY 4.0](https://cvg.cit.tum.de/data/datasets/rgbd-dataset) 署名；建议引用 J. Sturm 等，*A Benchmark for the Evaluation of RGB-D SLAM Systems*, IROS 2012。

## 准备

先按 ORB-SLAM3 官方 README 构建其源码、Pangolin、OpenCV 和 Eigen。构建后需要有 `lib/libORB_SLAM3`、解压后的 `Vocabulary/ORBvoc.txt` 和 `Examples/RGB-D/TUM1.yaml`。本目录的 `CMakeLists.txt` 只编译无界面驱动，不替代 ORB-SLAM3 自身构建。

下载并解压数据（以 `/path/to` 为例）：

```bash
curl -L -o /path/to/rgbd_dataset_freiburg1_xyz.tgz \
  https://webshare.cvg.cit.tum.de/g/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz
tar -xzf /path/to/rgbd_dataset_freiburg1_xyz.tgz -C /path/to
```

编译驱动。若依赖不在系统默认搜索路径，设置 `CMAKE_PREFIX_PATH` 或 `OpenCV_DIR`：

```bash
cmake -S 'ch07视觉里程计1' -B /path/to/ch07-build \
  -DORB_SLAM3_ROOT=/path/to/ORB_SLAM3 \
  -DCMAKE_PREFIX_PATH='/path/to/opencv/install;/path/to/pangolin/install'
cmake --build /path/to/ch07-build -j 4
```

创建 Python 环境并安装绘图依赖；还需命令行 `ffmpeg` 来把 RGB 序列编码为 MP4：

```bash
python3 -m venv /path/to/ch07-venv
/path/to/ch07-venv/bin/pip install -r 'ch07视觉里程计1/requirements.txt'
```

## 运行

```bash
/path/to/ch07-venv/bin/python 'ch07视觉里程计1/run_demo.py' \
  --dataset /path/to/rgbd_dataset_freiburg1_xyz \
  --orb-root /path/to/ORB_SLAM3 \
  --binary /path/to/ch07-build/rgbd_tum_headless
```

默认输出在 `ch07视觉里程计1/results/fr1_xyz/`。浏览器打开其中 `index.html`，或分别查看：

| 文件 | 内容 |
| --- | --- |
| `rgb_preview.mp4` | 从 798 张 RGB 图像按实际时间戳跨度编码的视频（本次约 26.6 秒） |
| `position_estimates.csv` | ORB-SLAM3 估计的时间戳、位置和姿态四元数 |
| `trajectory.png` | 相机轨迹（俯视和正视）及 TUM 真值 |
| `orb_matches_early.png`, `orb_matches_late.png` | 前、后两个时段的 ORB 图像匹配 |
| `CameraTrajectory.txt`, `KeyFrameTrajectory.txt` | ORB-SLAM3 自身输出的 TUM 格式轨迹 |
| `tracking_states.csv` | 每帧状态，`2` 表示跟踪成功；失效帧位置留空 |
| `summary.json` | 帧数、匹配数和 ATE RMSE 等摘要 |

两张匹配图由**独立的 OpenCV ORB + Hamming 比值筛选 + RANSAC**计算，方便观察图像特征；它们并非 ORB-SLAM3 内部关联结果的导出。轨迹采用 ORB-SLAM3 的真实运行输出，不由匹配图推算。绘图对估计轨迹和真值做了仅旋转、平移的 SE(3) 对齐，**未缩放**；ATE RMSE 是对齐后的平移误差，不代表无初值或其他序列下的算法精度。

`rgb_preview.mp4` 只包含 RGB 图像，不带相机内参。运行脚本使用 ORB-SLAM3 的 `Examples/RGB-D/TUM1.yaml` 配置相机模型，并与 TUM 深度图配合运行；因此这是 **RGB-D** 实验，不是仅凭该视频运行的单目实验。

首次加载 ORB 词袋可能耗时数十秒。运行时 GUI 关闭，适合无显示器的环境。`run_demo.py --help` 可查看自定义输出路径等参数。

## 本机构建记录

本例在 macOS 14 arm64 上使用 ORB-SLAM3 `4452a3c`、OpenCV 4.10.0、Pangolin `3667bb7`、Eigen 3.4、Boost 1.92 编译。旧版上游代码在新版 Apple Clang 上需把两处 `stdint-gcc.h` 改为 `<cstdint>`，把内置 g2o 的 `std::tr1` 容器/智能指针改为 `std`，并将上游 CMake 的 Linux `.so` 链接路径改为 macOS `.dylib`。这些兼容性改动只在外部 ORB-SLAM3 构建目录进行，**没有复制或修改本仓库以外的上游代码进本仓库**。Linux 用户一般无需上述 macOS 改动。
