#!/usr/bin/env python3
"""Rebuild the chapter PDF without the original Downloads materials."""

import argparse
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

ROOT = Path(__file__).resolve().parent
WIDTH = A4[0] - 110
INK, ACCENT, PALE, LINE = [colors.HexColor(c) for c in
                         ("#1C2A3D", "#9B2335", "#FBF0EA", "#E3CEC8")]
STYLES = {
    "title": ParagraphStyle("title", fontName="CN", fontSize=21, leading=28,
                            textColor=ACCENT, spaceAfter=9),
    "sub": ParagraphStyle("sub", fontName="CN", fontSize=10, leading=15,
                          textColor=colors.HexColor("#596B80"), spaceAfter=11),
    "h": ParagraphStyle("h", fontName="CN", fontSize=13, leading=19,
                        textColor=ACCENT, spaceBefore=10, spaceAfter=5, keepWithNext=True),
    "p": ParagraphStyle("p", fontName="CN", fontSize=10, leading=16,
                        textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="CN", fontSize=8.5, leading=13,
                            textColor=INK, spaceAfter=5),
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
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), .5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def grid(rows, widths):
    table = Table([[p(cell, "small") for cell in row] for row in rows],
                  colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), .3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def graph():
    """Original vector schematic: a shared point couples cameras after elimination."""
    d = Drawing(WIDTH, 128)
    left = [(40, 90), (112, 90), (184, 90)]
    center = (112, 28)
    right = [(305, 90), (405, 90), (355, 28)]
    for x, y in left:
        d.add(Line(x, y, *center, strokeColor=ACCENT, strokeWidth=1.2))
    for a, b in [(0, 1), (0, 2), (1, 2)]:
        d.add(Line(*right[a], *right[b], strokeColor=ACCENT, strokeWidth=1.2))
    for nodes in [left, right]:
        for i, (x, y) in enumerate(nodes):
            d.add(Circle(x, y, 15, fillColor=PALE, strokeColor=LINE))
            d.add(String(x, y-3, f"T{i+1}", fontName="CN", fontSize=9, textAnchor="middle"))
    d.add(Circle(*center, 13, fillColor=colors.white, strokeColor=ACCENT))
    d.add(String(center[0], center[1]-3, "P", fontName="CN", fontSize=9, textAnchor="middle"))
    d.add(String(112, 113, "原始 BA 观测图", fontName="CN", fontSize=9, textAnchor="middle"))
    d.add(String(355, 113, "消元后：相机产生耦合", fontName="CN", fontSize=9, textAnchor="middle"))
    d.add(String(238, 62, "→", fontName="CN", fontSize=18, textAnchor="middle"))
    return d


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(55, 42, A4[0]-55, 42)
    canvas.setFont("CN", 8)
    canvas.setFillColor(colors.HexColor("#596B80"))
    canvas.drawString(55, 27, "视觉 SLAM 十四讲 · 第十讲：后端（1）")
    canvas.drawRightString(A4[0]-55, 27, str(doc.page))
    canvas.restoreState()


def build(font, output):
    pdfmetrics.registerFont(TTFont("CN", str(font)))
    pdfmetrics.registerFontFamily("CN", normal="CN", bold="CN", italic="CN", boldItalic="CN")
    story = [
        p("第十讲：后端总结", "title"),
        p("从带噪声观测到一致的轨迹与地图：滤波、BA、消元与边缘化", "sub"),
        box("<b>一句话：</b>前端建立观测关联并给出初值；后端把这些带噪声的约束放在一起，估计状态及其不确定性。它不是把轨迹画得更平滑，而是让预测与观测在可信度加权后尽可能一致。"),
        h("一、这一讲怎样连接前面的内容"),
        p("第 3 讲解决“用什么表示位姿”，第 6 讲解决“怎样迭代调整状态”，第 7-8 讲提供匹配、几何或光度约束。第 10 讲把这些约束组织成状态估计问题，并利用结构降低计算量。后端并不限于独立线程；前端跟踪中也可能执行小规模优化。"),
        h("二、状态、输入、观测和噪声"),
        box("运动：s<sub>k</sub>=f(s<sub>k-1</sub>,u<sub>k</sub>)+w<sub>k</sub><br/>观测：z<sub>kj</sub>=h(T<sub>k</sub>,P<sub>j</sub>)+v<sub>kj</sub><br/>滤波联合状态可写成 s<sub>k</sub>=(当前位姿、路标、必要的速度 / 偏置等)。"),
        p("T 是位姿，P 是地图点，u 是 IMU、轮速等输入，z 是像素或距离观测。纯视觉系统可以不显式加入独立运动因子，但仍需要多帧观测与初始化。用 s 表示完整状态，避免课件把“位姿”和“位姿加地图”都记成 x 的冲突。"),
        h("三、滤波与优化：保留哪些状态，何时更新"),
        grid([
            ["方式", "主要保留什么", "新数据到来时"],
            ["滤波（KF / EKF）", "当前联合状态的均值、协方差；历史压缩为后验", "递推预测和观测更新"],
            ["批量 / 平滑优化", "一组历史位姿、路标及对应约束", "对保留的变量联合求解，可重新线性化"],
            ["滑动窗口优化", "有限窗口变量及旧信息形成的先验", "加入新帧，优化，再边缘化旧变量"],
        ], [98, 240, WIDTH-338]),
        p("“递增运行”不等于“必然采用滤波”：优化也可以增量执行。批量 BA 也不一定一次处理整段视频，局部 BA 可以在运行过程中反复调用。二者不是单纯的在线 / 离线划分。", "small"),
        h("四、概率主线：预测是先验，观测用于修正"),
        p("在状态满足一阶马尔可夫性、观测按状态条件独立的模型下，先对上一时刻的后验做状态转移，再用新观测似然相乘并归一化。历史并没有消失，而是通过后验继续影响当前估计。"),
        box("预测：p(s<sub>k</sub>|历史)=∫p(s<sub>k</sub>|s<sub>k-1</sub>,u<sub>k</sub>)p(s<sub>k-1</sub>|历史)ds<sub>k-1</sub><br/>更新：p(s<sub>k</sub>|历史,z<sub>k</sub>) ∝ p(z<sub>k</sub>|s<sub>k</sub>)p(s<sub>k</sub>|历史)"),
        PageBreak(),
        p("KF：五个公式背后的直觉", "title"),
        p("线性模型 + 高斯噪声：用均值和协方差完整描述后验。", "sub"),
        h("五、先统一符号，不要只背 Q / R 的名字"),
        p("本总结采用常见约定：运动噪声 Cov(w)=Q，观测噪声 Cov(v)=R。课件主体采用相反命名，且小结中有局部混用；判断时必须看噪声属于哪条方程。下标 k 可随时间变化。[1]"),
        box("线性模型：s<sub>k</sub>=A<sub>k</sub>s<sub>k-1</sub>+B<sub>k</sub>u<sub>k</sub>+w<sub>k</sub>，z<sub>k</sub>=C<sub>k</sub>s<sub>k</sub>+v<sub>k</sub><br/>m 为均值，P 为状态协方差；“-”表示当前观测前，“+”表示当前观测后。"),
        h("六、预测两步，更新三步"),
        box("1. m<sub>k</sub><sup>-</sup>=A<sub>k</sub>m<sub>k-1</sub><sup>+</sup>+B<sub>k</sub>u<sub>k</sub><br/>2. P<sub>k</sub><sup>-</sup>=A<sub>k</sub>P<sub>k-1</sub><sup>+</sup>A<sub>k</sub><sup>T</sup>+Q<sub>k</sub><br/>3. K<sub>k</sub>=P<sub>k</sub><sup>-</sup>C<sub>k</sub><sup>T</sup>(C<sub>k</sub>P<sub>k</sub><sup>-</sup>C<sub>k</sub><sup>T</sup>+R<sub>k</sub>)<sup>-1</sup><br/>4. m<sub>k</sub><sup>+</sup>=m<sub>k</sub><sup>-</sup>+K<sub>k</sub>(z<sub>k</sub>-C<sub>k</sub>m<sub>k</sub><sup>-</sup>)<br/>5. P<sub>k</sub><sup>+</sup>=(I-K<sub>k</sub>C<sub>k</sub>)P<sub>k</sub><sup>-</sup>"),
        p("运动模型把位置往前推，Q 描述额外的不确定性。创新 ν=z-Cm<sup>-</sup> 是“真实观测减去预测观测”，K 把创新转换为状态修正。观测提供的约束只降低可观测方向的不确定性，不能凭空确定所有自由度。"),
        h("七、一个一维例子：到底信谁多一些"),
        p("预测位置 m<sup>-</sup>=10 m，方差 P<sup>-</sup>=4 m²；传感器读数 z=12 m，方差 R=1 m²，C=1。则 K=4/(4+1)=0.8，更新后 m<sup>+</sup>=11.6 m，P<sup>+</sup>=0.8 m²。读数较可靠，所以向读数移动较多。若 R=16 m²，则 K=0.2，位置只更新到 10.4 m。"),
        box("不是简单取平均，而是按不确定性融合。矩阵情形的 K 同时处理方向和状态相关性，不能笼统理解成一个固定百分比。"),
        h("八、信息形式：与最小二乘建立联系"),
        p("高斯先验与高斯似然相乘，等价于相加负对数中的二次型。在线性情况下，其后验均值也可由加权最小二乘求得："),
        box("min<sub>s</sub> ½(s-m<sup>-</sup>)<sup>T</sup>(P<sup>-</sup>)<sup>-1</sup>(s-m<sup>-</sup>)<br/>　　　 +½(z-Cs)<sup>T</sup>R<sup>-1</sup>(z-Cs)<br/>(P<sup>+</sup>)<sup>-1</sup>=(P<sup>-</sup>)<sup>-1</sup>+C<sup>T</sup>R<sup>-1</sup>C"),
        p("实际程序应通过矩阵分解解方程，避免显式求逆。协方差更新可用 Joseph 形式：(I-KC)P<sup>-</sup>(I-KC)<sup>T</sup>+KRK<sup>T</sup>，减轻浮点误差造成的非对称或非正定问题。以上“最优”依赖正确的线性高斯模型，不可直接推广为 EKF 的全局最优保证。", "small"),
        PageBreak(),
        p("EKF：非线性系统的局部近似", "title"),
        p("用非线性函数算预测值，用雅可比传播局部不确定性。", "sub"),
        h("九、为什么视觉 SLAM 不能直接套线性 KF"),
        p("旋转组合、透视投影 X/Z、畸变等使 f、h 为非线性函数。高斯随机变量经过非线性函数后，通常不再严格为高斯；EKF 在估计附近一阶展开，继续用均值与协方差近似后验。"),
        box("F<sub>k</sub>=∂f/∂s，取值点为上一时刻后验均值 m<sub>k-1</sub><sup>+</sup><br/>H<sub>k</sub>=∂h/∂s，取值点为当前预测均值 m<sub>k</sub><sup>-</sup><br/>m<sub>k</sub><sup>-</sup>=f(m<sub>k-1</sub><sup>+</sup>,u<sub>k</sub>)<br/>P<sub>k</sub><sup>-</sup>=F<sub>k</sub>P<sub>k-1</sub><sup>+</sup>F<sub>k</sub><sup>T</sup>+Q<sub>k</sub><br/>K<sub>k</sub>=P<sub>k</sub><sup>-</sup>H<sub>k</sub><sup>T</sup>(H<sub>k</sub>P<sub>k</sub><sup>-</sup>H<sub>k</sub><sup>T</sup>+R<sub>k</sub>)<sup>-1</sup><br/>m<sub>k</sub><sup>+</sup>=m<sub>k</sub><sup>-</sup>+K<sub>k</sub>[z<sub>k</sub>-h(m<sub>k</sub><sup>-</sup>)]<br/>P<sub>k</sub><sup>+</sup>=(I-K<sub>k</sub>H<sub>k</sub>)P<sub>k</sub><sup>-</sup>"),
        p("这里假设加性、独立、零均值噪声。噪声若通过非线性函数进入，应另用噪声雅可比传播协方差。公式中的普通加法适用于欧氏状态；旋转 / SE(3) 实现需使用误差状态或流形更新，不能直接给旋转矩阵加一个向量。", "small"),
        h("十、EKF-SLAM 为什么要保存交叉协方差"),
        p("状态包含当前机器人和地图路标，P 的非对角块描述“机器人误差与路标误差如何共同变化”。再次看到旧路标时，创新不只修正该路标，还会通过这些相关性修正机器人及其他路标。不能把 P 简化成互不相关的一串方差。"),
        p("若联合状态维度为 d，完整协方差存储约为 O(d²)。地图路标不断增加时，经典 EKF-SLAM 的存储和更新成本变高；这不意味着所有滤波器都必须保存完整历史轨迹。固定维度的传感器融合滤波是另一种设置。"),
        h("十一、优势与边界"),
        grid([
            ["优势", "风险", "工程应对"],
            ["递推清楚，便于多传感器融合", "初始化差、强非线性会放大近似误差", "正确初始化；必要时迭代更新"],
            ["显式维护不确定性", "噪声估错、错误匹配会导致过度自信或发散", "创新门限、离群检查、噪声建模"],
            ["历史压缩，不必反复处理原始数据", "旧线性化信息难以完整重新计算", "关注一致性、可观测性及 FEJ"],
        ], [160, 177, WIDTH-337]),
        p("澄清：采用马尔可夫运动模型，不等于 BA 必须使用非马尔可夫运动模型；平滑优化同样可使用相邻状态的马尔可夫因子。EKF 的问题是模型、线性化与历史压缩等共同作用，而不是“一阶马尔可夫假设必然错误”。"),
        PageBreak(),
        p("BA：把观测组织成稀疏问题", "title"),
        p("不只调一帧相机，而是联合调整保留的相机和三维点。", "sub"),
        h("十二、重投影残差与目标函数"),
        p("约定 T<sub>i</sub> 把世界点转换到第 i 帧相机系。固定内参时，预测像素为 h(T<sub>i</sub>,P<sub>j</sub>)=π(KT<sub>i</sub>P<sub>j</sub>)，π 包含透视除法。只对实际存在且通过筛选的观测集合 O 求和，不是所有相机与点的笛卡尔积。"),
        box("e<sub>ij</sub>=z<sub>ij</sub>-h(T<sub>i</sub>,P<sub>j</sub>)<br/>min<sub>{T,P}</sub> ½Σ<sub>(i,j)∈O</sub> ρ(e<sub>ij</sub><sup>T</sup>Ω<sub>ij</sub>e<sub>ij</sub>)，Ω<sub>ij</sub>=Σ<sub>ij</sub><sup>-1</sup>"),
        p("Σ 是观测协方差，Ω 是信息矩阵。独立高斯噪声且无鲁棒核时得到加权最小二乘；加入先验则对应 MAP 估计。鲁棒核降低异常残差影响，但不能代替正确匹配。先白化残差，再设置合理阈值，避免混用像素与米。"),
        h("十三、图结构就是计算结构"),
        p("位姿、路标是变量节点，每条观测是连接一个相机和一个路标的残差因子。一个点被多帧看到，就把这些帧联系起来。图优化是组织非线性最小二乘问题的方式；BA 是其中一种问题，位姿图不是 BA 的同义词。"),
        graph(),
        p("示意图仅表达连接关系，不是实测轨迹；右图为线性消元后的耦合，不表示已把 BA 近似成若干独立的位姿图边。" , "small"),
        h("十四、雅可比为什么稀疏"),
        p("固定内参时，一个二维像素残差只对 T<sub>i</sub> 的局部 6 维扰动和 P<sub>j</sub> 的 3 维坐标有导数，其余列为零。共有 m 帧、n 点，则增量维度为 6m+3n。纯重投影 BA 的相机块和路标块分别块对角，交叉块由可见关系决定。"),
        box("e(x⊞δ)≈e(x)+Jδ<br/>H=ΣJ<sub>ij</sub><sup>T</sup>Ω<sub>ij</sub>J<sub>ij</sub>，g=ΣJ<sub>ij</sub><sup>T</sup>Ω<sub>ij</sub>e<sub>ij</sub><br/>GN 解 Hδ=-g；LM 解 (H+λD)δ=-g，并检查候选步。"),
        p("⊞ 表示流形上的状态更新。H 是 GN 近似 Hessian，不是一般非线性目标的精确二阶导数。加入 IMU、相机运动因子、共享内参或边缘化先验后，块结构会改变，不能一概声称所有 BA 的相机块都对角。", "small"),
        PageBreak(),
        p("Schur 消元：先求相机，再回代点", "title"),
        p("利用地图点多、点块互不直接关联的结构，缩小每次线性求解。", "sub"),
        h("十五、将变量排成“相机在前，路标在后”"),
        box("H = [ B　E ; E<sup>T</sup>　C ]，δ=(δc,δp)<sup>T</sup>，右端 q=-g<br/>Bδc+Eδp=q<sub>c</sub><br/>E<sup>T</sup>δc+Cδp=q<sub>p</sub>"),
        grid([
            ["块", "尺寸（固定内参）", "含义"],
            ["B", "6m × 6m", "相机变量之间的局部信息"],
            ["C", "3n × 3n", "路标块；标准 BA 为各点的 3×3 块对角"],
            ["E", "6m × 3n", "相机和点的观测耦合，通常块稀疏"],
        ], [46, 143, WIDTH-189]),
        h("十六、由第二行消去路标增量"),
        box("δp=C<sup>-1</sup>(q<sub>p</sub>-E<sup>T</sup>δc)<br/>S=B-EC<sup>-1</sup>E<sup>T</sup> （Schur 补）<br/><b>Sδc=q<sub>c</sub>-EC<sup>-1</sup>q<sub>p</sub></b><br/>先解 δc，再回代求 δp，最后更新相机与点。"),
        p("C 为块对角时，可分别解各点的小方程，而不构造巨大的 C 逆矩阵。上式要求被消元块可解；低视差、单次观测或退化点可能导致奇异，应筛点、加合理约束或在 LM 阻尼后的系统上求解。全局规范自由度也要单独处理。"),
        h("十七、消元以后为什么出现相机间非零块"),
        p("同一个点连接多帧时，EC<sup>-1</sup>E<sup>T</sup> 将这些相机耦合起来，S 反映共视关系。消去一个共享节点，通常会在其邻居间产生新连接，这叫 fill-in（填充）。消元会降低稀疏度，但并不必然令 S 完全稠密。"),
        box("标准 BA：原始相机块可为块对角 → 消去共同路标 → 共视相机产生耦合 → 解更小的相机系统 → 恢复路标增量。"),
        h("十八、不要把“先消元”理解成“不优化路标”"),
        p("Schur 消元在当前线性化系统上进行代数重排；精确求解和回代得到与完整线性系统一致的增量。路标仍参与原始非线性问题，下次迭代仍可以重算其残差和雅可比。这也不同于固定路标只调相机的 pose-only 优化。[2]"),
        p("Ceres 提供 DENSE_SCHUR、SPARSE_SCHUR、ITERATIVE_SCHUR；它们处理缩减系统的方式不同。选择应依据规模、稀疏性、内存和编译后端，而非看到“Schur”就认定某一种必然最快。[2]", "small"),
        PageBreak(),
        p("边缘化与 FEJ：不能凭空增加信息", "title"),
        p("减小状态规模时，保留信息，也保留线性化带来的限制。", "sub"),
        h("十九、同一个消元公式，两种不同用途"),
        grid([
            ["用途", "被消去的变量", "以后还能否重新线性化"],
            ["BA 线性求解加速", "本轮暂时消去点，随后回代", "原变量 / 因子保留，可在下一轮重算"],
            ["滑窗边缘化", "从活动集合移除旧相机 / 点", "相关旧因子压缩为局部先验，通常无法原样重算"],
        ], [115, 166, WIDTH-281]),
        p("在线性高斯信息形式中，积分掉部分变量可用 Schur 补得到剩余变量的信息。非线性滑窗通常先线性化，再形成二次先验：它保留局部近似信息，不等于保留完整非线性后验。不能把“信息都跑到相机里”理解成无损恢复所有旧原始数据。"),
        h("二十、可观测性：哪些东西本来就不知道"),
        p("无绝对定位先验时，视觉重建通常无法确定世界坐标原点和朝向；单目还缺少绝对尺度。这些规范自由度形成零空间。固定参考位姿、约束尺度或加真实先验是选坐标 / 提供信息，不是算法从图像里自动测出绝对位置。"),
        box("不一致的线性化可能把本不可观测的方向伪装成可观测：协方差看起来变小，但真实误差未相应下降，即过度自信。边缘化先验固定在旧线性化点，而新因子不断重线性化时，要特别关注这一问题。"),
        h("二十一、课件 xy 示例：为什么零空间会消失"),
        p("令两个相同残差都为 r(x,y)=xy-1，则 E=2(xy-1)²。xy=1 是一条等代价曲线。若两个残差在同一点线性化，两行雅可比相同，J 的秩为 1，保留一个局部零方向。"),
        box("分别在 (0.5,1.4) 和 (1.2,0.5) 线性化：<br/>J<sub>1</sub>=[1.4,0.5]，J<sub>2</sub>=[0.5,1.2]<br/>堆叠矩阵的行列式 = 1.4×1.2-0.5×0.5 = 1.43 ≠ 0。<br/>两行不再平行，局部零空间被人为消除；这是课件的一致性警示，不是新增了真实观测。"),
        h("二十二、FEJ 的作用与边界"),
        p("FEJ（First-Estimates Jacobian）对特定状态的相关雅可比使用一致的首次估计参考，以维护正确的不可观测子空间。它不是“所有量永远不更新”，也不是所有边缘化都必须机械地套同一个 FEJ 实现；具体规则取决于滤波 / 滑窗模型、误差状态和先验处理。[4]"),
        p("工程上至少记录：先验参考点、残差重线性化规则、位姿扰动方向与规范约束。FEJ 解决的是一致性问题，不能修复错误匹配、失效标定或缺失的米制尺度。", "small"),
        PageBreak(),
        p("落地理解：工具与训练数据验收", "title"),
        p("下面是工程补充；不把课件概念说明写成已经完成的程序实验。", "sub"),
        h("二十三、Ceres / g2o 都要先把问题定义对"),
        p("Ceres 用参数块与残差块表达问题，支持自动求导、鲁棒损失和流形；g2o 以变量顶点、约束边及信息矩阵表达图优化。它们负责数值求解，不负责替你发现正确对应关系、选择坐标系或补齐尺度。[3][5]"),
        box("检查输入与关联 → 明确位姿方向 / 单位 → 建立残差和权重 → 约束规范自由度 → 核对雅可比 → GN / LM 求解 → 查看收敛与异常 → 导出轨迹及质量指标"),
        p("实现核对：① 用有限差分检查解析雅可比；② 用小问题比较 Schur 与完整求解增量；③ 注入离群点验证鲁棒机制；④ 检查相机前方深度、矩阵秩和参考约束；⑤ 保留 cost、停止原因和失败片段，不能只看一条漂亮曲线。", "small"),
        h("二十四、对具身训练数据建设，优先检查什么"),
        grid([
            ["质量维度", "需要记录 / 验收", "不能误认为什么"],
            ["坐标与尺度", "Tcw / Twc、轴方向、单位、时间戳与有效帧", "z 轴矫正或平滑不等于恢复米制尺度"],
            ["观测支持", "有效关联数、空间覆盖、视差、遮挡和动态物体", "匹配点多不等于约束充分"],
            ["局部一致性", "重投影残差的中位数 / 尾部、正深度、优化前后变化", "代价下降不等于真值误差下降"],
            ["长期漂移", "回环几何验证；有真值时测 ATE / RPE 并注明对齐方式", "轨迹平滑不等于全局一致"],
            ["不确定性与可用性", "噪声模型、先验、失败标记及片段筛选策略", "置信度分数不必然是统计协方差"],
        ], [90, 228, WIDTH-318]),
        p("这些是工程验收建议，不声称本次已评估某个视频或重跑 SLAM。即使以学习模型提供初值，后端仍只能在模型与观测支持的范围内改善结果；内参偏差、运动物体和错误回环都可能被优化成一组错误但低残差的状态。"),
        h("二十五、学习时抓住这五句话"),
        box("1. 后端估计的是状态及不确定性，不只是曲线。<br/>2. KF / EKF 递推先验与观测；EKF 是局部近似。<br/>3. BA 联合调相机和路标，图连接决定雅可比稀疏性。<br/>4. Schur 缩小线性系统，路标增量仍要回代。<br/>5. 滑窗边缘化留下局部先验，需警惕填充与一致性。"),
        h("材料与核对来源"),
        p("本机 Downloads/ch10后端 全部 29 张 JPG 已逐一阅读（20261012-152308 至 20261012-152824，课件页 2-30）。未发现独立笔记文本；全文基于图片文字、公式与示意。课堂原图不上传。逐文件内容索引见本目录 README。整理日期：2026-10-12。", "small"),
        p('[1] Welch &amp; Bishop，<link href="https://www.cs.unc.edu/~welch/media/pdf/kalman_intro.pdf" color="#9B2335">An Introduction to the Kalman Filter</link>：KF / EKF 基本推导。', "small"),
        p('[2] <link href="https://ceres-solver.readthedocs.io/latest/nnls_solving.html" color="#9B2335">Ceres 官方求解文档</link>：BA 块结构、Schur 补与求解器。', "small"),
        p('[3] <link href="https://ceres-solver.readthedocs.io/latest/nnls_tutorial.html" color="#9B2335">Ceres 官方教程</link>：重投影残差、鲁棒损失与 BA 示例。', "small"),
        p('[4] <link href="https://udel.edu/~ghuang/papers/tr_fej2.pdf" color="#9B2335">Huang 团队 FEJ 技术报告</link>：线性化、可观测性与估计一致性。', "small"),
        p('[5] <link href="https://github.com/RainerKuemmerle/g2o" color="#9B2335">g2o 官方仓库</link>；<link href="https://github.com/gaoxiang12/slambook/tree/master/ch10" color="#9B2335">十四讲作者第十讲示例</link>。', "small"),
    ]
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=55, rightMargin=55,
                            topMargin=50, bottomMargin=55, title="ch10后端总结", author="slam_demo")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("/Library/Fonts/Arial Unicode.ttf"))
    parser.add_argument("--output", type=Path, default=ROOT / "ch10后端总结.pdf")
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("请用 --font 指定支持中文、希腊字母及数学符号的 TrueType 字体。")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build(args.font, args.output)
    print(args.output)
