# ch07-2 视觉里程计

[阅读本章总结 PDF](ch07视觉里程计2总结.pdf)

本章接续[视觉里程计 1](../ch07-1视觉里程计/ch07视觉里程计1总结.pdf)，整理从已有三维地图定位相机，以及利用深度进行三维配准的方法。

总结共四页：PnP 与 DLT / P3P、重投影误差与 BA / 雅可比、ICP 的去质心和 SVD 解法、具身训练数据中的位姿质量检查。特别区分位姿细化与完整 BA、固定对应配准与迭代 ICP，并补充坐标方向、尺度、旋转行列式修正等容易出错的细节。

## 阅读材料

基于重新整理后的本机 `Downloads/ch07-2视觉里程计/`，逐一阅读全部 18 张图片及 `ch07-2笔记.rtf`；原始材料不上传仓库。

| 图片文件 | 内容 |
| --- | --- |
| `20261009-162440.jpg`、`20261009-162444.jpg` | PnP 标题与问题定义 |
| `20261009-162448.jpg`、`20261009-162451.jpg` | DLT 线性方程与旋转约束 |
| `20261009-162514.jpg`、`20261009-162518.jpg`、`20261009-162522.jpg` | P3P 余弦定理、消元与限制 |
| `20261009-162527.jpg` | 重投影优化目标 |
| `20261009-162620.jpg`、`20261009-162624.jpg`、`20261009-162628.jpg` | 投影、位姿和地图点雅可比 |
| `20261009-162632.jpg`、`20261009-162635.jpg` | 3D-3D ICP 定义与残差 |
| `20261009-205718.jpg`、`20261009-205723.jpg` | 去质心、分离平移与旋转 |
| `20261009-205726.jpg`、`20261009-205729.jpg` | SVD 求解、已知与未知对应的区别 |
| `20261009-210129.jpg` | 第七讲章节小结 |

RTF 笔记补充了 BA 的直觉：重新投影地图点，以整体重投影误差驱动相机位姿和三维点的微小调整。总结保留这一主线，并说明实际常用 GN / LM，而不只笼统称为梯度下降。

## 重新生成 PDF

需要 Python 3、`reportlab` 及支持中文的 TrueType 字体。在本目录执行：

```bash
python3 -m pip install reportlab
python3 generate_summary_pdf.py
```

默认使用 macOS 的 Arial Unicode 字体；其他环境可传入 `--font /path/to/chinese-font.ttf`。生成器包含文档全文，不依赖 Downloads 中的原图或笔记。

## 核对资料

- [OpenCV：Perspective-n-Point pose computation](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html)
- [Ceres：Bundle Adjustment](https://ceres-solver.readthedocs.io/latest/nnls_tutorial.html#bundle-adjustment)
- [Open3D：ICP registration](https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html)
