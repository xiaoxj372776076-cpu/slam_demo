#!/usr/bin/env python3
"""Generate the chapter summary. Requires ReportLab and a Chinese TrueType font."""

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ch07视觉里程计2总结.pdf"
WIDTH = A4[0] - 110
INK, BLUE, PALE, LINE = [colors.HexColor(c) for c in ("#172B4D", "#1769AA", "#EDF5FB", "#CCD9E4")]
STYLES = {
    "title": ParagraphStyle("title", fontName="AU", fontSize=21, leading=28, textColor=INK, spaceAfter=10),
    "sub": ParagraphStyle("sub", fontName="AU", fontSize=10, leading=15, textColor=colors.HexColor("#536577"), spaceAfter=12),
    "h": ParagraphStyle("h", fontName="AU", fontSize=13, leading=19, textColor=BLUE, spaceBefore=12, spaceAfter=6),
    "p": ParagraphStyle("p", fontName="AU", fontSize=9.6, leading=15.5, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="AU", fontSize=8.5, leading=13, textColor=INK, spaceAfter=4),
}
for style in STYLES.values():
    style.wordWrap = "CJK"


def p(text, style="p"):
    return Paragraph(text, STYLES[style])


def h(text):
    return p(text, "h")


def box(text):
    table = Table([[p(text)]], colWidths=[WIDTH])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), .5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def grid(rows, widths):
    table = Table([[p(c, "small") for c in row] for row in rows], colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), .3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(55, 42, A4[0] - 55, 42)
    canvas.setFont("AU", 8)
    canvas.setFillColor(INK)
    canvas.drawString(55, 27, "视觉 SLAM 十四讲 · 第七讲：视觉里程计 2")
    canvas.drawRightString(A4[0] - 55, 27, str(doc.page))
    canvas.restoreState()


def build(font_path):
    pdfmetrics.registerFont(TTFont("AU", str(font_path)))
    pdfmetrics.registerFontFamily("AU", normal="AU", bold="AU", italic="AU", boldItalic="AU")
    story = [
        p("ch07 视觉里程计 2", "title"),
        p("从 3D-2D PnP 到重投影优化，再到 3D-3D ICP", "sub"),
        box("<b>学习主线：</b>已有地图点 + 当前图像 → PnP 位姿初值 → 重投影优化；两帧都有三维点 → 三维配准 / ICP。本讲把第六讲的非线性优化落到具体几何残差上。"),
        h("1 · PnP：已知三维点，求相机位姿"),
        p("输入是空间点 P<sub>w,i</sub> 与其图像观测 z<sub>i</sub>=(u<sub>i</sub>,v<sub>i</sub>) 的对应关系，以及相机内参 K 和畸变模型。输出 R、t，使点从世界坐标变到相机坐标，再投影后尽量贴近观测。PnP 不是从单张图像凭空恢复所有三维点。"),
        box("P<sub>c</sub>=RP<sub>w</sub>+t，T<sub>cw</sub>：世界 → 相机。<br/>u=f<sub>x</sub>X<sub>c</sub>/Z<sub>c</sub>+c<sub>x</sub>，v=f<sub>y</sub>Y<sub>c</sub>/Z<sub>c</sub>+c<sub>y</sub>。<br/>相机在世界中的位置 C<sub>w</sub>=-R<sup>T</sup>t；<b>t 并不是相机的世界坐标</b>。"),
        h("2 · DLT：先放松约束，求线性初值"),
        p("对去畸变后的归一化坐标 x=(u<sub>n</sub>,v<sub>n</sub>,1)<sup>T</sup>，写 s x=M P̃，其中 P̃=(X,Y,Z,1)<sup>T</sup>、M=[R|t]。若 m<sub>1</sub>、m<sub>2</sub>、m<sub>3</sub> 是 M 的三行，消去 s 后，每对点给出两条方程："),
        p("(m<sub>1</sub>-u<sub>n</sub>m<sub>3</sub>)P̃=0；(m<sub>2</sub>-v<sub>n</sub>m<sub>3</sub>)P̃=0。"),
        p("把 M 的 12 个元素当独立未知量；整体尺度不定，因此有 11 个有效自由度。一般非退化配置下至少 6 对点可构造线性解，多点用齐次最小二乘。共面点需使用适合平面配置的方法，不能机械套用通用 DLT。"),
        p("线性解没有自动满足 R<sup>T</sup>R=I、det(R)=+1；必须恢复统一尺度（包含 t），再将旋转投影到 SO(3)，常用 SVD / 极分解。课件的 QR 表述可帮助理解正交化，但不等同于最近旋转矩阵的投影。随后用重投影误差细化。", "small"),
        h("3 · P3P：三个点为何还会有多个答案"),
        p("三维三角形 ABC 的边长已知；像素经 K<sup>-1</sup> 得到三条观测射线，其夹角已知。余弦定理如 AB²=OA²+OB²-2·OA·OB·cos∠AOB，可求光心到三点的距离，再恢复刚体变换。"),
        p("P3P 最多有 4 个候选解，通常用额外观测、正深度和重投影误差选解。三点是最小求解模型，不代表不能利用更多点：工程上可在 RANSAC 中抽样求候选，用全部数据评分，再用内点细化。[1]", "small"),
        PageBreak(),
        p("重投影优化与 Bundle Adjustment", "title"),
        p("个人笔记的核心：将三维点重新投影到图像，用预测与观测的差反复调整状态。", "sub"),
        h("4 · 先分清残差、目标与优化变量"),
        box("e<sub>ij</sub>=z<sub>ij</sub>-π(K,T<sub>cw,i</sub>P<sub>w,j</sub>)。<br/>最简单的目标：min ½ Σ<sub>(i,j)∈观测集合</sub> ||e<sub>ij</sub>||²。<br/>例如观测 (100,200)，预测 (103,198)，则 e=(-3,2)，平方误差为 13 像素²。"),
        grid([
            ["问题", "固定什么", "调整什么"],
            ["PnP 位姿细化 / pose-only BA", "地图点、内参与对应关系", "当前相机位姿 T"],
            ["完整 BA", "观测、对应关系；本例内参固定", "多帧位姿 T 与地图点 P"],
        ], [154, 177, WIDTH - 331]),
        p("完整 BA 让同一地图点在多帧中都解释得通，通常是大型稀疏非线性最小二乘问题。[2] 还需固定参考坐标系；纯单目系统若没有额外尺度约束，优化本身也不能凭空产生米制尺度。"),
        h("5 · 第六讲的 GN / LM 在这里做什么"),
        p("透视除法 X/Z 和旋转使残差对状态呈非线性。当前状态附近线性化 e(x+δx)≈e(x)+Jδx；高斯牛顿解 (J<sup>T</sup>J)δx=-J<sup>T</sup>e。LM 加阻尼，如 (J<sup>T</sup>J+λI)δx=-J<sup>T</sup>e，并根据实际误差下降调整步长。"),
        p("计算残差与雅可比 → 解增量 → 更新状态 → 重算误差 → 判断是否接受与停止。笔记中的“梯度下降”可表达逐步调整的直觉，但 SLAM 的这类最小二乘更常用 GN / LM；优化收敛不等于一定找到了真实位姿。"),
        h("6 · 课件雅可比：记住链式法则即可"),
        p("以下假设固定内参、已去畸变，P<sub>c</sub>=(X,Y,Z)<sup>T</sup>。投影对相机坐标的导数 J<sub>π</sub> 为 2×3 矩阵："),
        box("J<sub>π</sub> = [ f<sub>x</sub>/Z, 0, -f<sub>x</sub>X/Z² ; 0, f<sub>y</sub>/Z, -f<sub>y</sub>Y/Z² ]<br/>采用左扰动 T ← exp(δξ̂)T，δξ=(δρ,δφ)，先平移后旋转：<br/>∂P<sub>c</sub>/∂δξ = [ I, -[P<sub>c</sub>]<sub>×</sub> ]<br/><b>J<sub>位姿</sub>=-J<sub>π</sub>[ I, -[P<sub>c</sub>]<sub>×</sub> ]（2×6）</b><br/><b>J<sub>地图点</sub>=-J<sub>π</sub>R（2×3）</b>"),
        p("[P]<sub>×</sub>a=P×a；ξ̂ 是将六维增量映射到 se(3) 矩阵的算子。负号来自 e=观测-预测。若改为右扰动、交换平移旋转顺序、反转残差定义，雅可比也要对应变化，不能只复制公式。", "small"),
        p("对误匹配先做 RANSAC / 几何筛选，再用 Huber 等鲁棒损失限制外点影响；不同观测精度可用信息矩阵加权。鲁棒损失不是错误关联或错误标定的万能修复器。", "small"),
        PageBreak(),
        p("ICP：让两组三维点对齐", "title"),
        p("先理解“已知对应的刚体配准”，再理解 ICP 中重复寻找对应的迭代。", "sub"),
        h("7 · 固定对应：去质心，把平移与旋转分开"),
        p("设 p′<sub>i</sub> 是源点，p<sub>i</sub> 是目标点；求源 → 目标的 R、t，最小化 ½Σ||p<sub>i</sub>-(Rp′<sub>i</sub>+t)||²。两点集必须单位和尺度一致，刚体变换不会调整尺度。"),
        box("p̄=(1/n)Σp<sub>i</sub>，p̄′=(1/n)Σp′<sub>i</sub>；q<sub>i</sub>=p<sub>i</sub>-p̄，q′<sub>i</sub>=p′<sub>i</sub>-p̄′。<br/>目标 = ½Σ||q<sub>i</sub>-Rq′<sub>i</sub>||² + (n/2)||p̄-Rp̄′-t||²。<br/>去质心后 Σq<sub>i</sub>=Σq′<sub>i</sub>=0，交叉项消失；给定 R，最优 t=p̄-Rp̄′。"),
        h("8 · SVD：在旋转约束下求解"),
        p("旋转不改变向量长度，因此旋转相关目标等价于最大化 Σq<sub>i</sub><sup>T</sup>Rq′<sub>i</sub>。采用与课件相同的 W 定义："),
        box("W=Σq<sub>i</sub>q′<sub>i</sub><sup>T</sup>=UΣV<sup>T</sup><br/><b>R=U diag(1,1,det(UV<sup>T</sup>)) V<sup>T</sup>，t=p̄-Rp̄′。</b>"),
        p("课件的 R=UV<sup>T</sup> 适用于 det(UV<sup>T</sup>)=+1；一般实现应加行列式修正，避免得到镜像反射。如果把 W 定义成 Σq′q<sup>T</sup>，U、V 的乘法顺序也要反过来。"),
        p("固定正确对应、无尺度变化的点到点刚体最小二乘，可由 SVD 给出全局最优配准；退化配置（如共线点）可能无法唯一确定旋转。也可用非线性优化表示同一残差，但不能据此保证任意 ICP 或鲁棒版本都有全局解。", "small"),
        h("9 · 真正的 ICP：对应关系也在变"),
        grid([
            ["迭代环节", "操作", "注意"],
            ["初始化", "提供源 → 目标的初始变换", "通常需要足够接近且有重叠"],
            ["找对应", "变换源点，搜索目标中的近邻", "限制距离，拒绝不合理对应"],
            ["估计更新", "固定本轮对应，求刚体配准", "点到点可用 SVD；也有点到面模型"],
            ["重新匹配与停止", "更新变换，重复以上过程", "检查误差、增量、迭代上限"],
        ], [94, 199, WIDTH - 293]),
        p("最近邻会随变换改变，整体问题通常只能局部收敛。[3] 重复结构、重叠不足、初值过差、动态物体或深度噪声，都可能让它对齐到错误位置。点更多不代表对应更正确。"),
        p("课件把三维配准的非线性解也称作 BA；更严格的命名是“三维配准优化”，经典 BA 指图像重投影优化。两种残差可以放进同一优化问题，但像素误差与米制误差必须按不确定性归一化 / 加权。", "small"),
        PageBreak(),
        p("把本讲用于具身训练数据建设", "title"),
        p("知道输入、输出、失败条件与验收方法，比先背完所有推导更实用。", "sub"),
        h("10 · 三类几何关系，串起第七讲"),
        grid([
            ["对应", "解决什么", "尺度来自哪里"],
            ["2D-2D", "对极几何估计相对旋转 / 平移方向；有视差再三角化", "单目两视图不能确定米制尺度"],
            ["3D-2D", "PnP 用既有地图点定位当前相机", "继承三维地图的尺度"],
            ["3D-3D", "配准 / ICP 估计两点集的刚体变换", "继承深度 / 点云尺度，且两者须一致"],
        ], [69, 255, WIDTH - 324]),
        p("第七讲 1：特征提取与匹配 → 对极几何 → 三角化。第七讲 2：地图建立后用 PnP 跟踪；有双目 / RGB-D 深度时还可做三维配准。第六讲的残差、雅可比、GN / LM 提供细化工具；后续 BA 将多帧与地图点联系起来。"),
        h("11 · 输出轨迹前，至少检查这些"),
        grid([
            ["检查项", "验收动作 / 常见问题"],
            ["标定与图像处理", "核对 K、畸变、分辨率；缩放 / 裁剪图像时同步更新焦距与主点。"],
            ["数据与关联", "检查帧 / 深度时间戳、同步、内点数量及空间覆盖，剔除动态物体和明显误匹配。"],
            ["位姿约定", "明确 Tcw 或 Twc、源与目标；核对逆变换、轴向、四元数顺序和相机中心公式。"],
            ["尺度与单位", "区分米、毫米和任意单目尺度；不要把坐标轴矫正误认为尺度恢复。"],
            ["重投影质量", "可视化观测点与预测点；统计内点误差分布、正深度比例及轨迹突跳，而非只看总损失。"],
            ["点云配准质量", "同时看重叠 / fitness、内点 RMSE 和对齐图；指标依赖对应距离阈值，不宜跨设置直接比较。"],
        ], [99, WIDTH - 99]),
        box("<b>学习优先级：</b>先掌握 PnP / ICP 的数据接口、坐标约定、尺度和失败诊断；DLT / P3P 的长篇消元可后学。对做训练数据的人，不能跳过结果是否可信的判断。"),
        h("复习自问"),
        p("为什么 PnP 的 t 不是相机位置？P3P 三点为何可能多解？哪些变量被优化才算完整 BA？雅可比的负号从哪里来？去质心为何能分离平移？为何 SVD 的配准最优性不等于 ICP 的全局最优性？", "small"),
        h("资料与整理范围"),
        p("本机 Downloads/ch07-2视觉里程计中重新整理的 18 张 JPG（20261009-162440 至 20261009-210129）及 ch07-2笔记.rtf，已逐一阅读。图片涵盖 PnP、DLT、P3P、重投影残差与雅可比、ICP 去质心 / SVD 和章节小结；未将课堂原图上传仓库。", "small"),
        p('[1] <link href="https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html" color="#1769AA">OpenCV：PnP pose computation</link>；[2] <link href="https://ceres-solver.readthedocs.io/latest/nnls_tutorial.html#bundle-adjustment" color="#1769AA">Ceres：Bundle Adjustment</link>；[3] <link href="https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html" color="#1769AA">Open3D：ICP registration</link>。官方资料用于核对接口、BA 定义及迭代配准边界；其余为课堂材料整理与工程补充。', "small"),
    ]
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=55, rightMargin=55, topMargin=50,
                            bottomMargin=55, title="ch07视觉里程计2总结", author="slam_demo")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
                        help="Path to a Chinese-capable TrueType font (default: macOS Arial Unicode)")
    args = parser.parse_args()
    build(args.font)
