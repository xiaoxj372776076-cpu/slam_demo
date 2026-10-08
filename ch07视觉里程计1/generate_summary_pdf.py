#!/usr/bin/env python3
"""Rebuild the chapter-7 PDF summary from local demo results."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "fr1_xyz"
OUT = ROOT / "ch07视觉里程计1总结.pdf"
pdfmetrics.registerFont(TTFont("AU", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"))
INK, BLUE, PALE, LINE = [colors.HexColor(c) for c in ("#172B4D", "#1769AA", "#EDF5FB", "#CCD9E4")]

styles = {
    "title": ParagraphStyle("title", fontName="AU", fontSize=22, leading=29, textColor=INK, spaceAfter=10),
    "sub": ParagraphStyle("sub", fontName="AU", fontSize=10, leading=15, textColor=colors.HexColor("#536577"), spaceAfter=12),
    "h": ParagraphStyle("h", fontName="AU", fontSize=13, leading=19, textColor=BLUE, spaceBefore=10, spaceAfter=5),
    "p": ParagraphStyle("p", fontName="AU", fontSize=9.4, leading=15.2, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="AU", fontSize=8.2, leading=12.3, textColor=INK, spaceAfter=4),
    "cap": ParagraphStyle("cap", fontName="AU", fontSize=8, leading=12, textColor=colors.HexColor("#536577"), alignment=TA_CENTER, spaceAfter=6),
}


def p(text, style="p"):
    return Paragraph(text, styles[style])


def h(text):
    return p(text, "h")


def box(text):
    table = Table([[p(text)]], colWidths=[485])
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
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def image(name, width, height):
    path = RESULTS / name
    w, h0 = ImageReader(str(path)).getSize()
    ratio = min(width / w, height / h0)
    return Image(str(path), width=w * ratio, height=h0 * ratio)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(55, 42, A4[0] - 55, 42)
    canvas.setFont("AU", 8)
    canvas.setFillColor(INK)
    canvas.drawString(55, 27, "视觉 SLAM 十四讲 · 第七讲：视觉里程计 1")
    canvas.drawRightString(A4[0] - 55, 27, str(doc.page))
    canvas.restoreState()


story = [
    p("ch07 视觉里程计 1", "title"),
    p("从 ORB 特征到两视图位姿｜课堂图片、个人笔记与仓库实验", "sub"),
    box("<b>学习主线：</b>图像特征 → 跨帧匹配 → 对极约束与相对位姿 → 有基线和视差时三角化。匹配点本身不能直接给出带米制尺度的三维坐标。"),
    h("1 · 视觉里程计与三类对应关系"),
    p("视觉里程计（VO）根据连续图像估计相机运动，为 SLAM 后端提供位姿初值。稳定、可重复、可区分的视觉特征可作为路标；关键点记录位置、尺度和方向，描述子便于跨帧识别。"),
    grid([
        ["对应关系", "典型方法", "用途"],
        ["2D–2D：两帧像素", "对极几何 E / F", "单目相对旋转与平移方向"],
        ["3D–2D：地图点与像素", "PnP", "用已有三维路标估计相机位姿"],
        ["3D–3D：两组三维点", "ICP / 三维配准", "有深度时估计两帧变换"],
    ], [134, 130, 221]),
    h("2 · ORB：从角点到二进制匹配"),
    p("<b>FAST：</b>以候选像素为中心，在周围 16 像素圆上寻找连续 N 个比中心亮度高/低超过阈值的像素。原始 FAST 很快，但没有方向；ORB 用邻域图像矩 m<sub>pq</sub>=Σx<sup>p</sup>y<sup>q</sup>I(x,y) 的质心方向 θ=atan2(m<sub>01</sub>,m<sub>10</sub>) 赋予方向，并通过图像金字塔处理尺度变化。"),
    p("<b>旋转 BRIEF：</b>在关键点邻域按固定点对比较亮度，每对产生 1 位，再依角点方向旋转采样模式。笔记中的 128 位可作示意；常见 ORB 描述子为 256 位。注意每一位比较的是<b>两个采样点</b>，不一定与中心像素比较。"),
    p("<b>匹配：</b>汉明距离为两个二进制串异或后 1 的个数。最近邻和比值/交叉检验给出候选对应，再用 RANSAC 和几何约束排除误匹配；描述子相似并不能保证来自同一三维点。"),
    PageBreak(),
    p("两视图几何：从匹配到位姿", "title"),
    h("3 · 对极约束在约束什么"),
    p("同一空间点 P 在两帧的齐次像素坐标为 p<sub>1</sub>、p<sub>2</sub>；相机内参 K<sub>1</sub>、K<sub>2</sub> 将它们变为归一化坐标 x<sub>i</sub>=K<sub>i</sub><sup>−1</sup>p<sub>i</sub>。若两相机相对运动为 (R,t)，则 s<sub>1</sub>x<sub>1</sub>=P，s<sub>2</sub>x<sub>2</sub>=RP+t。消去未知深度得到对极约束："),
    box("<b>x<sub>2</sub><sup>T</sup>E x<sub>1</sub>=0，E=[t]<sub>×</sub>R</b>（本质矩阵）；<b>p<sub>2</sub><sup>T</sup>F p<sub>1</sub>=0，F=K<sub>2</sub><sup>−T</sup>E K<sub>1</sub><sup>−1</sup></b>（基础矩阵）。给定第一帧点，第二帧对应点应落在其对极线上。"),
    p("两相机光心和 P 定义对极平面，与像平面相交成对极线。观测有噪声，实际只要求点靠近线，并用 RANSAC 抵抗外点。"),
    h("4 · 笔记疑问：五点法与八点法为何不同"),
    grid([
        ["方法", "输入与对象", "点数缘由"],
        ["五点法", "已标定相机的归一化点 → E", "E 有 5 个有效自由度：旋转 3、平移方向 2；用其非线性约束从 5 对点求候选解。"],
        ["八点法", "像素点 → F；或归一化点 → E", "3×3 矩阵去掉整体尺度后有 8 个线性未知；每对点给 1 条方程，之后施加秩约束。"],
    ], [80, 170, 235]),
    p("五点法不是用五条线性方程直接求九个元素；八点法则是简明的线性初解，常配坐标归一化。实际用更多匹配点 + RANSAC 选内点，再重估。E 分解会产生多组 (R,t) 候选，用正深度条件选解，但 t 的长度仍未知。"),
    h("5 · 何时三角化，何时不能"),
    p("先估计相机间 (R,t)，再由同一空间点在两帧的观测射线求交；噪声下求最接近解。可选第一帧为世界坐标系，但单目两视图的地图仍只有相似变换意义上的尺度，不能凭自身恢复米制距离。纯旋转时 t=0，没有三角化基线；小视差时深度不稳定。RGB-D、双目或其他尺度信息可提供米制约束。"),
    box("<b>关键区分：</b>ORB 提供候选像素对应；E/F 约束两视图几何；相对位姿 + 非零视差才让三角化有意义。地图点建立后，PnP 可继续利用 3D–2D 对应跟踪。"),
    PageBreak(),
    p("回到本仓库的 ORB-SLAM3 实验", "title"),
    p("本目录在 TUM RGB-D <i>freiburg1_xyz</i> 的 798 帧 RGB + 深度图上运行 ORB-SLAM3。相机内参由 <i>Examples/RGB-D/TUM1.yaml</i> 提供；<i>rgb_preview.mp4</i> 只是 RGB 预览，不含内参。RGB-D 深度提供米制尺度。两张匹配图来自独立 OpenCV ORB 诊断，不是 ORB-SLAM3 内部关联的导出。"),
    image("trajectory.png", 440, 183),
    p("图 1：估计轨迹与 TUM 真值。798 帧均跟踪成功，796 个估计位姿匹配真值；仅 SE(3) 对齐、无尺度缩放后的 ATE RMSE ≈ 0.0102 m。这只是该序列的结果。", "cap"),
    image("orb_matches_early.png", 425, 112),
    p("图 2：早期帧 79 ↔ 87，670 个比值筛选匹配、527 个 RANSAC 内点；图中只显示 80 条。", "cap"),
    image("orb_matches_late.png", 425, 112),
    p("图 3：后期帧 558 ↔ 566，512 个比值筛选匹配、416 个 RANSAC 内点；图中只显示 80 条。", "cap"),
    h("复习时自问"),
    p("FAST 为什么看连续圆弧？ORB 如何获得方向？BRIEF 的每一位比较谁？E 与 F 使用什么坐标？五点法和八点法各求什么？为什么单目有尺度不定、纯旋转不能三角化，而 RGB-D 可以？", "small"),
    p("资料：本机 Downloads/ch07-1视觉里程计中的 15 张课堂图片与 RTF 笔记；Rublee et al., ORB (ICCV 2011)；Hartley, In Defense of the Eight-Point Algorithm (PAMI 1997)；OpenCV calib3d 文档；TUM RGB-D Benchmark；本仓库 ch07 实验结果。", "small"),
]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=55, rightMargin=55, topMargin=50, bottomMargin=55, title="ch07视觉里程计1总结", author="slam_demo")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
