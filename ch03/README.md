# ch03: Eigen 几何运算与 Pangolin 可视化

本目录对应《视觉 SLAM 十四讲》第三讲中常见的三维空间运动表示练习。代码重点不是实现完整 SLAM 系统，而是把后续会频繁用到的数学对象先跑通、看懂。

## 学习目标

- 使用 Eigen 定义矩阵、向量和变换
- 练习矩阵加法、乘法、转置和求逆
- 理解旋转矩阵、欧拉角和四元数之间的转换
- 使用 `Eigen::Isometry3d` 表示相机位姿
- 使用 Pangolin 绘制相机坐标系和一段模拟轨迹

## 目录结构

```text
ch03/
├── CMakeLists.txt
├── README.md
└── src/
    ├── eigen_math_tests.cpp
    └── eigen_pangolin_demo.cpp
```

## 依赖

Eigen 是必须依赖：

```bash
sudo apt update
sudo apt install cmake g++ libeigen3-dev
```

Pangolin 是可视化 demo 的依赖。如果没有安装 Pangolin，`eigen_math_tests` 仍然可以编译和测试，`eigen_pangolin_demo` 会被 CMake 自动跳过。

macOS 上如果从源码安装 Pangolin，常见还需要 GLEW：

```bash
brew install glew
```

## 编译和测试

```bash
cd ch03
mkdir -p build
cd build
cmake ..
cmake --build .
ctest --output-on-failure
```

测试通过时会看到类似输出：

```text
All Eigen math tests passed.
100% tests passed
```

## 运行 Pangolin 可视化

安装好 Pangolin 后重新配置并编译：

```bash
cmake ..
cmake --build .
./eigen_pangolin_demo
```

窗口中会显示一段模拟相机轨迹：

- 黑色折线：相机中心运动轨迹
- 红色轴：当前相机坐标系 x 轴
- 绿色轴：当前相机坐标系 y 轴
- 蓝色轴：当前相机坐标系 z 轴

运行后可以用鼠标拖拽旋转视角，滚轮缩放。终端里还会打印矩阵、向量乘法结果、旋转矩阵、四元数和欧拉角，方便把数值输出和图形显示对应起来。

## 文件说明

`eigen_math_tests.cpp` 是一个无窗口测试程序，用 `assert` 验证基础数学关系是否正确，适合先确认 Eigen 环境可用。

`eigen_pangolin_demo.cpp` 会生成一组模拟相机位姿，用 Pangolin 把轨迹和每个位姿的局部坐标轴画出来，适合直观看旋转和平移的组合效果。
