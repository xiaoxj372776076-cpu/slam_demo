# ch10 后端（1）：学习总结

[阅读本章总结 PDF](ch10后端总结.pdf)

延续 ch01-02、ch03 的概念主线、公式提示和对比表，以七页整理：状态估计与贝叶斯递推、KF 五个公式、EKF 及交叉协方差、BA 与稀疏结构、Schur 消元、滑窗边缘化与 FEJ，以及具身训练数据的质量验收。

统一采用运动噪声协方差 `Q`、观测噪声协方差 `R`；修正课件中局部混用的符号和时间下标。特别区分递增运行与滤波、BA 线性消元与滑窗边缘化、代价下降与真实精度提升。原空目录 `ch10` 调整为 `ch10后端`；其他章节内容不变。

## 阅读材料记录

于 2026-10-12 逐一阅读本机 `Downloads/ch10后端/` 的全部 29 张 JPG，对应课件页 2-30。目录未发现独立 TXT、Markdown、RTF 等笔记文本，图片中的文字、公式和批注即为学习材料。本仓库不上传课堂原图；PDF 的图示为重新绘制的结构示意。

| JPG 文件 | 课件页 | 阅读内容 |
| --- | --- | --- |
| `20261012-152308.jpg`、`20261012-152312.jpg` | 2-3 | 后端（1）标题；EKF、优化及 Ceres/g2o 学习目标 |
| `20261012-152316.jpg`、`20261012-152319.jpg` | 4-5 | EKF 章节标题；后端、渐进式与批量式 |
| `20261012-152323.jpg` | 6 | 蒙眼行走比喻：预测累积不确定性，路标观测提供约束 |
| `20261012-152328.jpg`、`20261012-152332.jpg` | 7-8 | 运动与观测方程；位姿与路标联合状态 |
| `20261012-152708.jpg`、`20261012-152712.jpg`、`20261012-152715.jpg` | 9-11 | 贝叶斯展开、预测积分、一阶马尔可夫假设与 KF/EKF 分支 |
| `20261012-152719.jpg`、`20261012-152722.jpg` | 12-13 | 线性高斯模型；均值、协方差的预测与似然 |
| `20261012-152725.jpg`、`20261012-152729.jpg`、`20261012-152732.jpg` | 14-16 | 比较高斯二次项与一次项；信息形式、卡尔曼增益及五个公式 |
| `20261012-152735.jpg`、`20261012-152738.jpg`、`20261012-152742.jpg` | 17-19 | EKF 一阶展开、预测和更新；优点与局限 |
| `20261012-152745.jpg`、`20261012-152749.jpg`、`20261012-152751.jpg` | 20-22 | BA 章节标题；重投影目标；变量顶点与观测边 |
| `20261012-152758.jpg`、`20261012-152801.jpg`、`20261012-152806.jpg` | 23-25 | 稀疏雅可比、H 的非零块、变量排序与 B/E/C 结构 |
| `20261012-152809.jpg`、`20261012-152813.jpg` | 26-27 | Schur 消元、先求相机增量再回代路标 |
| `20261012-152816.jpg`、`20261012-152819.jpg` | 28-29 | 边缘化、填充、缩减相机矩阵与共视关系 |
| `20261012-152824.jpg` | 30 | 滑窗一致性、FEJ，以及不同线性化点导致零空间消失的示例 |

## 重新生成 PDF

`generate_summary_pdf.py` 包含全文和矢量示意图，不依赖 Downloads 原图，不需要安装或运行 Ceres/g2o。本次仅整理学习文档，未新增后端算法 demo 或宣称完成视频精度评估。

从仓库根目录运行：

```bash
python3 -m pip install reportlab
python3 'ch10后端/generate_summary_pdf.py'
```

默认使用 macOS 的 `/Library/Fonts/Arial Unicode.ttf`。其他环境可用 `--font /path/to/chinese-font.ttf` 指定兼容中文和数学符号的 TrueType 字体；`--output /path/to/summary.pdf` 可改变输出位置。字体不随仓库分发。

## 核对来源

- [Welch & Bishop：An Introduction to the Kalman Filter](https://www.cs.unc.edu/~welch/media/pdf/kalman_intro.pdf)：KF/EKF 推导与噪声约定。
- [Ceres 官方求解文档](https://ceres-solver.readthedocs.io/latest/nnls_solving.html)：BA 稀疏块、Schur 补和求解器。
- [Ceres 官方教程](https://ceres-solver.readthedocs.io/latest/nnls_tutorial.html)：重投影残差、鲁棒损失和 BA 示例。
- [Huang 团队 FEJ 技术报告](https://udel.edu/~ghuang/papers/tr_fej2.pdf)：可观测性与线性化一致性。
- [g2o 官方仓库](https://github.com/RainerKuemmerle/g2o)、[十四讲作者第十讲代码](https://github.com/gaoxiang12/slambook/tree/master/ch10)：图优化及对应示例入口。
