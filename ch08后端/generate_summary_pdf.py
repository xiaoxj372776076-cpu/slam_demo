#!/usr/bin/env python3
"""Rebuild the chapter summary; no Downloads files or runtime results required."""

import argparse
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
OUTPUT = ROOT / "ch08视觉里程计（2）总结.pdf"
WIDTH = A4[0] - 110
INK, ACCENT, PALE, LINE = [colors.HexColor(c) for c in ("#1C2A3D", "#9B2335", "#FBF0EA", "#E3CEC8")]
STYLES = {
    "title": ParagraphStyle("title", fontName="CN", fontSize=21, leading=28, textColor=ACCENT, spaceAfter=9),
    "sub": ParagraphStyle("sub", fontName="CN", fontSize=10, leading=15, textColor=colors.HexColor("#596B80"), spaceAfter=11),
    "h": ParagraphStyle("h", fontName="CN", fontSize=13, leading=19, textColor=ACCENT, spaceBefore=10, spaceAfter=5, keepWithNext=True),
    "p": ParagraphStyle("p", fontName="CN", fontSize=9.8, leading=15.7, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="CN", fontSize=8.5, leading=13, textColor=INK, spaceAfter=4),
    "cap": ParagraphStyle("cap", fontName="CN", fontSize=8.3, leading=12.5, textColor=colors.HexColor("#596B80"), alignment=TA_CENTER, spaceAfter=6),
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
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def grid(rows, widths):
    table = Table([[p(cell, "small") for cell in row] for row in rows], colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), .3, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def image(name):
    path = ROOT / "summary_assets" / name
    width, height = ImageReader(str(path)).getSize()
    return Image(str(path), width=WIDTH, height=WIDTH * height / width)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(55, 42, A4[0]-55, 42)
    canvas.setFont("CN", 8)
    canvas.setFillColor(colors.HexColor("#596B80"))
    canvas.drawString(55, 27, "视觉 SLAM 十四讲 · 第八讲：视觉里程计（2）")
    canvas.drawRightString(A4[0]-55, 27, str(doc.page))
    canvas.restoreState()


def build(font, output):
    pdfmetrics.registerFont(TTFont("CN", str(font)))
    pdfmetrics.registerFontFamily("CN", normal="CN", bold="CN", italic="CN", boldItalic="CN")
    story = [
        p("第八讲：视觉里程计（2）总结", "title"),
        p("从像素运动到光度对齐：LK 光流、直接法与结果可信度", "sub"),
        box("<b>本讲主线：</b>不必总是“提取描述子、匹配特征、再求位姿”。可以先用光流跟踪像素，再做几何估计；也可以用几何模型投影像素，直接让两帧灰度尽量一致。共同基础是光度残差，但优化变量不同。"),
        h("一、先分清三种问题"),
        grid([
            ["方法", "主要约束 / 输入", "首先求什么"],
            ["特征点法", "关键点与描述子关联；几何残差", "对应关系，再估计位姿 / 地图"],
            ["局部 LK 光流", "图像块亮度；邻域近似同一运动", "各个点的二维像素位移"],
            ["直接法 VO", "内参、三维结构及图像光度残差", "由共享相机运动解释多个像素"],
        ], [89, 208, WIDTH-297]),
        p("光流跟踪可以免去描述子匹配，但并不意味着完全不选点。直接法也可以选角点或高梯度像素；“直接”强调用原始亮度作为优化残差，而不是一律使用全部像素。课件中的耗时只是示意，不能当成通用性能结论。", "small"),
        h("二、光流：同一场景点在图像里移动多少"),
        p("设图像为 I(x,y,t)，场景点在 dt 内从 (x,y) 移到 (x+dx,y+dy)。假设亮度不变，并在小运动附近一阶展开："),
        box("I(x+dx,y+dy,t+dt)=I(x,y,t)<br/>I<sub>x</sub>dx+I<sub>y</sub>dy+I<sub>t</sub>dt≈0<br/><b>I<sub>x</sub>u+I<sub>y</sub>v=-I<sub>t</sub>，u=dx/dt，v=dy/dt。</b>"),
        p("I<sub>x</sub>、I<sub>y</sub> 是空间梯度，I<sub>t</sub> 是时间变化。此处 (u,v) 是图像速度；两帧实现通常输出位移 (dx,dy)，单位为像素 / 帧间隔，不是米 / 秒。[1]"),
        h("三、LK：一条方程不够，就用整个小窗口"),
        p("一个像素只有一条约束，却有两个未知量。LK 在 w×w 邻域中假设各像素具有近似相同的位移 / 速度；每个像素仍需满足自身的亮度不变，<b>不是假设窗口内所有像素灰度相同</b>。将这些约束堆叠成最小二乘问题："),
        box("A 的第 k 行为 [I<sub>x,k</sub>, I<sub>y,k</sub>]，b<sub>k</sub>=I<sub>t,k</sub>。<br/>min ||A d+b||²，d=(u,v)<sup>T</sup>；法方程：<b>(A<sup>T</sup>A)d=-A<sup>T</sup>b。</b><br/>仅在可逆时才可写 d=-(A<sup>T</sup>A)<sup>-1</sup>A<sup>T</sup>b；实现宜解线性方程。"),
        p("平坦块几乎没有梯度，两个方向都难估；单条边缘只能较好约束垂直边缘的运动，沿边缘方向不确定，即孔径问题。角点包含多个方向的梯度，通常更适合跟踪。A<sup>T</sup>A 的两个特征值都足够大，才有较好的二维可观测性。", "small"),
        PageBreak(),
        p("LK 的迭代、金字塔与轨迹", "title"),
        p("一次线性化只在初值附近有效；真正的跟踪要反复采样和更新。", "sub"),
        h("四、把 LK 写成光度误差最小化"),
        p("对参考窗口 Ω，待估计二维位移 d：r<sub>k</sub>(d)=I<sub>2</sub>(p<sub>k</sub>+d)-I<sub>1</sub>(p<sub>k</sub>)。最小化 ½Σr<sub>k</sub>²；在当前估计附近 r(d+δd)≈r(d)+Jδd。对于前向加法形式，J<sub>k</sub>=∇I<sub>2</sub>(p<sub>k</sub>+d)，这是一个 1×2 行向量。"),
        box("当前 d → 在 I<sub>2</sub> 中采样 → 计算 r 与 J → 解 (J<sup>T</sup>J)δd=-J<sup>T</sup>r → d←d+δd → 重算残差。<br/>坐标通常不是整数，需双线性插值；反向合成等形式会采用不同梯度 / 更新约定。[2]"),
        p("所以 LK 与直接图像对齐具有共同的光度优化基础。不能把 OpenCV LK 换一个函数名就宣称成了另一种直接法；关键要看残差、运动模型与共享的优化变量。"),
        h("五、金字塔：先粗后细，扩大小运动假设的范围"),
        p("将图像逐级降采样，在粗层求位移，再乘尺度传到细层继续优化。例如原图 16 px 的运动，在缩小 4 倍的一层约为 4 px。位移和像素坐标都必须同步缩放。金字塔只是降低局部优化难度，不能消除重复纹理、遮挡或保证全局最优。"),
        p("OpenCV 的 maxLevel=3 表示第 0 至第 3 层，最多四层；不是总共三层。窗口过小缺少约束，过大容易混入不同深度或不同物体的运动。LK 的局部平移模型虽不显式求相机旋转，仍可追踪由旋转产生的像素运动；只是大旋转 / 缩放时近似可能变差。", "small"),
        h("六、把每帧位移连成轨迹时，先做失败检查"),
        grid([
            ["检查", "做法", "边界"],
            ["状态与边界", "求解成功、坐标有限、窗口仍在图内", "成功标记本身并非真值正确"],
            ["正反向一致性", "p→p′→p″，检查 ||p″-p||", "重复纹理可能正反都错"],
            ["光度质量", "查看图像块误差、光照 / 模糊变化", "低误差也可能是平坦区域"],
            ["轨迹身份", "失效 ID 终止，补点建立新 ID", "不能把不同场景点拼成长轨迹"],
            ["覆盖与动态区域", "多方向、分布均匀；按需求屏蔽动态物体", "车辆自身运动不是相机运动"],
        ], [91, 238, WIDTH-329]),
        h("七、光流之后还缺什么，才能得到位姿"),
        box("二维像素对应 → 静态场景筛选 / 几何验证 → 有标定时用对极几何求相对运动；若已有三维地图则可用 PnP → 后续优化。<b>二维尾迹本身不等于三维相机轨迹。</b>"),
        p("纯单目两视图通常只能恢复平移方向，米制尺度需额外信息。像素位移同时包含相机运动、物体运动和透视效应；远近物体即使静止，也会产生不同的图像运动。", "small"),
        PageBreak(),
        p("直接法：让几何预测的像素亮度一致", "title"),
        p("不先寻找独立的跨帧匹配点，而是用位姿模型预测该到哪里取亮度。", "sub"),
        h("八、从像素反投影，再变换和投影"),
        p("设参考像素 p<sub>1</sub>=(a,b)，其齐次坐标 p̃<sub>1</sub>=(a,b,1)<sup>T</sup>；内参 K 已知，深度 z<sub>1</sub> 表示参考相机坐标系的 Z 分量。以下为固定三维点、只优化相对位姿的直接跟踪模型。"),
        box("P<sub>1</sub>=z<sub>1</sub>K<sup>-1</sup>p̃<sub>1</sub><br/>P<sub>2</sub>=R<sub>21</sub>P<sub>1</sub>+t<sub>21</sub>，T<sub>21</sub>：参考相机 → 当前相机<br/>p<sub>2</sub>=π(P<sub>2</sub>)=(f<sub>x</sub>X/Z+c<sub>x</sub>, f<sub>y</sub>Y/Z+c<sub>y</sub>)<sup>T</sup>"),
        p("π 在此包含内参。必须检查 Z&gt;0、可见性、投影边界与畸变处理。一般单目像素只有射线，没有已知深度；深度来自 RGB-D / 双目、已有地图，或在多帧系统中初始化并联合估计。书中示例使用 RGB-D 构造三维点。[3]"),
        h("九、光度残差与重投影残差不同"),
        grid([
            ["残差", "计算方式", "维度 / 单位"],
            ["重投影残差", "观测像素 - 几何预测像素", "2 维，像素"],
            ["光度残差", "e<sub>i</sub>=I<sub>1</sub>(p<sub>1,i</sub>)-I<sub>2</sub>(π(T<sub>21</sub>P<sub>1,i</sub>))", "每个亮度样本 1 维，灰度"],
        ], [99, 291, WIDTH-390]),
        p("直接法假设几何对应点的亮度近似一致；灰度相似并不等于唯一对应。单个像素区分性差，通常联合许多分散样本或小图像块约束同一个相机运动；每个样本不是各自求一个独立位姿。"),
        h("十、用第六讲的 GN / LM 调整六维位姿"),
        box("min<sub>T</sub> ½Σ<sub>i</sub> e<sub>i</sub>(T)²；或加入鲁棒损失与权重。<br/>e(T⊕δξ)≈e(T)+Jδξ；(J<sup>T</sup>WJ)δξ=-J<sup>T</sup>We。<br/>LM / 阻尼形式加 λD；采用左扰动更新 <b>T←exp(hat(δξ))T</b>。"),
        p("δξ=(δρ,δφ) 为六维局部增量，先平移后旋转；D 可取单位阵或正对角矩阵。逐层计算残差 → 雅可比 → 增量 → 试更新 → 检查目标值 → 接受或加阻尼重试。不能把旋转矩阵元素当普通向量随意相加。"),
        p("好的初值仍然重要。需要关注的是候选步后的<b>目标函数是否合理下降</b>，不是要求“从初值到最优值的图像梯度一直下降”。图像亮度函数通常非凸；线性化和金字塔都不能保证得到真实运动。", "small"),
        h("十一、固定深度跟踪，不等于完整直接 VO"),
        p("上述模型固定参考三维点，只求位姿。完整单目直接 VO 还需要初始化、深度 / 逆深度估计、关键帧管理及退化处理；例如 DSO 联合优化相机运动和逆深度，并建模曝光及光度标定。[4] 直接法并不会仅凭一帧、在完全没有纹理和几何信息时恢复米制位姿。", "small"),
        PageBreak(),
        p("雅可比、纹理与失败边界", "title"),
        p("记住链式法则与可观测性，比背一个不注明约定的长矩阵更有价值。", "sub"),
        h("十二、光度雅可比的三段链路"),
        p("令当前相机坐标 P<sub>2</sub>=(X,Y,Z)<sup>T</sup>，固定参考深度和内参，采用上页的左扰动与 e=参考亮度-当前亮度。则："),
        box("<b>J<sub>e</sub>=-∇I<sub>2</sub>(p<sub>2</sub>) · J<sub>π</sub> · [ I, -[P<sub>2</sub>]<sub>×</sub> ]</b><br/>尺寸链路： (1×2) · (2×3) · (3×6) = 1×6。<br/>J<sub>π</sub> = [ f<sub>x</sub>/Z, 0, -f<sub>x</sub>X/Z² ; 0, f<sub>y</sub>/Z, -f<sub>y</sub>Y/Z² ]。<br/>[P]<sub>×</sub>a=P×a；左扰动下 ∂P<sub>2</sub>/∂δξ=[I,-[P<sub>2</sub>]<sub>×</sub>]。"),
        p("第一项：移动像素会怎样改变灰度；第二项：移动三维点会怎样改变投影；第三项：改变位姿会怎样移动三维点。负号来自残差定义。右扰动、残差反号或交换平移 / 旋转顺序时，需要同步修改雅可比；不能照抄。", "small"),
        p("透视除法的 Z 随位姿更新而变化，必须包含导数 -f<sub>x</sub>X/Z²、-f<sub>y</sub>Y/Z²；不能把投影式里的 1/Z 当常数一路展开。课件的链式法则比中间简写更可靠。", "small"),
        h("十三、梯度大，不等于所有运动都可估计"),
        p("∇I≈0 时，雅可比接近零，对运动约束很弱。单一方向的边缘仍会产生孔径歧义；多个方向、空间上分散的梯度与合适的几何结构，才有助于约束六自由度。直接法能利用边缘和缓慢亮度变化，不必只选角点，但<b>完全均匀的白墙依然没有足够信息</b>。"),
        grid([
            ["采样方式", "使用的图像信息", "注意"],
            ["稀疏", "少量选定像素 / 小图像块", "不一定依赖角点检测或描述子"],
            ["半稠密", "较多梯度明显的区域", "梯度阈值与空间覆盖均重要"],
            ["稠密", "广泛使用有效像素", "仍需排除不可见 / 无效区域；计算更多"],
        ], [75, 218, WIDTH-293]),
        h("十四、直接法的优点与真实代价"),
        p("可省掉描述子匹配，利用更多图像信息，并由统一运动模型约束投影；但图像采样、梯度和迭代也有成本，不能保证总比特征法快。亮度恒常易受自动曝光、阴影、高光、反射和模糊破坏；动态物体、遮挡、错误深度和标定误差也会让模型不成立。"),
        p("工程上可使用鲁棒损失、可见性检查、动态区域屏蔽、曝光 / 增益偏置模型与光度标定，但这些不等于自动修复所有错误。低纹理下，平均光度误差小也可能只是“怎么移动都差不多”。"),
        h("十五、具身训练数据的最低验收清单"),
        grid([
            ["检查对象", "必须确认"],
            ["图像与标定", "时间戳 / 帧率、缩放裁剪后的 K、畸变、曝光和模糊。"],
            ["对应与可观测性", "静态有效区域、梯度方向与覆盖；正反向检查、遮挡和断点。"],
            ["输出约定", "二维轨迹还是 SE(3)；T 的方向、相机中心、尺度与单位。"],
            ["质量结论", "同时看误差分布、轨迹突跳与可视化；有真值再做几何评价。"],
        ], [112, WIDTH-112]),
        p("坐标轴矫正不能恢复单目米制尺度，也不能证明上游位姿准确。用于训练时保留算法、参数、帧索引与失效状态，避免把插值、重建和真正观测混为一谈。", "small"),
        PageBreak(),
        p("回到仓库：同一行车视频的两个实验", "title"),
        p("solidWhiteRight.mp4：221 帧、25 FPS、8.84 秒、960×540。两者均为二维学习 demo。", "sub"),
        image("lk_preview.jpg"),
        p("图 1 · LK，t=8.00 s。左侧原图，右侧角点的二维跟踪尾迹；不同物体可有不同运动。", "cap"),
        image("direct_preview.jpg"),
        p("图 2 · 道路平面直接对齐，t=3.00 s。先联合优化一个单应 H，再投影道路探针；不是书中的 SE(3) 直接 VO。", "cap"),
        grid([
            ["默认参数的本机统计", "LK", "道路平面直接对齐"],
            ["平均活跃点 / 总 ID", "155.08 / 1164", "13.21 / 2032"],
            ["最长连续轨迹", "221 帧", "31 帧，首尾跨度 1.20 s"],
            ["结果含义", "局部图像块的独立二维位移", "探针共同服从 H 的模型投影"],
        ], [144, 165, WIDTH-309]),
        p("两者 ROI、选点数量与过滤条件不同，不能据此排名优劣。直接 demo 通过 220/220 个帧间质量门限；第 99→100 帧的重叠道路区域灰度 MAE 从 2.55 降至 1.99（0-255）。这些指标不是几何真值精度，且道路纹理少，短轨迹较多。", "small"),
        p("现有脚本：run_lk_demo.py、run_direct_demo.py；可视化含原图 / 尾迹视频、代表点的 x/y 曲线和 CSV，直接 demo 另含单应矩阵及光度迭代日志。后者不调用 LK、ECC 或几何单应拟合，只优化光度误差；原视频无随附深度与标定，因此采用人工道路 ROI 和二维平面模型。", "small"),
        h("整理范围与核对资料"),
        p("已逐一阅读 Downloads/ch08视觉里程计（2）中的全部 19 张 JPG（20261010-115600 至 20261010-115705）。目录未发现独立笔记文本；总结基于图片中文字 / 公式、现有 demo 与以下核对资料。课堂截图不上传；本页仅保留实验快照，来源许可见 THIRD_PARTY_NOTICES.md。", "small"),
        p('[1] <link href="https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html" color="#9B2335">OpenCV：光流与 LK</link>；[2] <link href="https://www.ri.cmu.edu/pub_files/pub3/baker_simon_2004_1/baker_simon_2004_1.pdf" color="#9B2335">Baker &amp; Matthews：图像对齐</link>；[3] <link href="https://github.com/gaoxiang12/slambook/blob/master/ch8/directMethod/direct_sparse.cpp" color="#9B2335">十四讲作者：RGB-D 直接法示例</link>；[4] <link href="https://cvg.cit.tum.de/research/vslam/dso" color="#9B2335">DSO：直接稀疏里程计</link>。概念与公式经统一坐标 / 残差约定整理；课堂材料的简化表述在正文中已澄清。', "small"),
    ]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=55, rightMargin=55,
                            topMargin=50, bottomMargin=55, title="ch08视觉里程计（2）总结", author="slam_demo")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
                        help="Chinese-capable TrueType font")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.font, args.output)
