# Eigen 和 Pangolin SLAM 基础 Demo

这个目录用于练习《视觉 SLAM 十四讲》前几章常见的数学对象和可视化方式，包括：

- Eigen 矩阵和向量定义
- 矩阵加法、乘法、转置和求逆
- 旋转矩阵
- 欧拉角
- 四元数
- 位姿变换 `Eigen::Isometry3d`
- 使用 Pangolin 展示相机坐标系和运动轨迹

## 目录结构

```text
test/
├── CMakeLists.txt
├── README.md
└── src/
    ├── eigen_math_tests.cpp
    └── eigen_pangolin_demo.cpp
```

## 依赖

Ubuntu / Debian 可以先安装：

```bash
sudo apt update
sudo apt install cmake g++ libeigen3-dev
```

Pangolin 需要单独安装。常见方式是从源码编译安装 Pangolin，安装完成后 CMake 才能找到 `PangolinConfig.cmake`。

## 编译和测试 Eigen 部分

```bash
cd test
mkdir -p build
cd build
cmake ..
cmake --build .
ctest --output-on-failure
```

如果终端输出 `All Eigen math tests passed.`，说明矩阵、欧拉角、四元数和位姿变换的基础测试已经跑通。

## 运行 Pangolin 可视化

安装好 Pangolin 后重新执行上面的编译命令，然后运行：

```bash
./eigen_pangolin_demo
```

窗口中会显示一段简单相机轨迹，每个位姿用 RGB 三轴表示：红色为 x 轴，绿色为 y 轴，蓝色为 z 轴。
