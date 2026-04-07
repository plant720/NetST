# NetST 帮助文档 / NetST Help Documentation

---

## 1. 软件简介 / Overview

**NetST**（Haplotype Network Analysis Tool）是一款基于 PyQt6 开发的单倍型网络分析工具，支持多序列比对、单倍型计算与可视化，广泛适用于种群遗传学、系统发育学及分子生态学研究。

**NetST** is a haplotype network analysis tool built with PyQt6. It supports multiple sequence alignment, haplotype calculation, and interactive visualization, suitable for population genetics, phylogenetics, and molecular ecology research.

---

## 2. 界面布局 / Interface Layout

主界面由以下区域组成：

- **菜单栏 (Menu Bar)**：提供文件、分析、工具、帮助等功能入口。
- **标签页区域 (Tab Area)**：依次包含 Home、Data、Network、Haplotype、Alignment 等标签页。
- **输出面板 (Output Panel)**：位于右侧，显示输出目录、项目名称、日志信息，可通过右侧箭头按钮折叠/展开。
- **状态栏 (Status Bar)**：底部显示当前状态与进度条。

---

## 3. 快速上手 / Quick Start

### 3.1 载入序列 / Load Sequences

1. 点击菜单 **File → Load Sequence...**，选择 FASTA 格式文件（`.fas / .fasta / .fa`）。
2. 在弹出的**标准化对话框**中，根据序列头部格式选择分隔符及字段顺序（名称、离散性状、连续性状）。
3. 点击确定后，数据显示在 **Data** 标签页中。

### 3.2 设置输出目录与项目名 / Set Output Directory and Project Name

在右侧**输出面板**中：

- 点击 **Change** 按钮选择输出目录。
- 在项目名称输入框中填写项目前缀（默认 `project`）。

### 3.3 选择序列 / Select Sequences

在 **Data** 标签页中，勾选需要参与分析的序列。可使用 **Select All / Deselect All** 按钮批量操作。

---

## 4. 功能说明 / Features

### 4.1 多序列比对 / Multiple Sequence Alignment (MSA)

**菜单入口：Analysis → Multiple Sequence Alignment...**

支持两种比对工具：

- **MAFFT**：提供多种算法预设（Auto、FFT-NS-1、FFT-NS-2、G-INS-i、L-INS-i、E-INS-i），适用于不同规模与精度需求。
- **MUSCLE**：支持 PPP 算法，适用于大规模序列比对。

比对完成后，结果显示在 **Alignment** 标签页中，对齐序列以不同颜色高亮碱基（A=绿色, T=红色, C=蓝色, G=紫色）。

### 4.2 计算单倍型 / Calculate Haplotype

**菜单入口：Analysis → Calculate Haplotype...**

本功能执行以下步骤：

1. **多序列比对**：弹出比对参数对话框（MAFFT 或 MUSCLE），自动对所选序列进行比对。若序列长度已一致则跳过比对步骤。
2. **单倍型计算**：识别所有独特序列，分配单倍型编号（H1、H2、…），统计每个单倍型的样本数及性状信息。
3. **结果展示**：
   - **Haplotype 标签页**（单倍型结果）自动打开，显示单倍型汇总、序列可视化及样本映射。
   - **Alignment 标签页** 显示比对后的序列。

**输出文件：**

- `{prefix}_hap.fasta` — 各单倍型的代表序列
- `{prefix}_hap_trait.csv` — 每个单倍型的数量及性状汇总
- `{prefix}_seq.meta.csv` — 每条序列对应的单倍型及性状信息
- `{prefix}_aln.fasta` — 多序列比对结果

### 4.3 构建单倍型网络 / Build Haplotype Network

**菜单入口：Analysis → Build Haplotype Network...**

在完成单倍型计算的基础上，进一步调用 **fastHaN** 构建网络，支持以下算法：

- **Original TCS** — 经典 TCS 网络算法
- **Modified TCS** — 改进版 TCS 算法
- **MJN** — 中值连接网络 (Median Joining Network)
- **MSN** — 最小生成网络 (Minimum Spanning Network)

**参数设置：**

- **线程数 (-t)**：并行线程数，默认 8
- **屏蔽模糊碱基 (-a)**：标记含模糊碱基的位点
- **合并中间顶点 (-m)**：合并过渡顶点以简化网络
- **Epsilon (-e)**：网络构建的松弛值，默认 0

网络构建完成后，结果在 **Network** 标签页中以 D3.js 交互式图形显示（TCS-BU 可视化界面）。

### 4.4 TCS-BU 网络可视化 / Network Visualization

**Network** 标签页使用 TCS-BU 组件进行交互式可视化，主要功能包括：

- 调整节点大小、连接线粗细
- 按离散性状分组着色
- 双性状可视化（离散 + 连续性状）
- 导出图像（SVG / PNG）

详细使用方法请参阅 **Help → TCS-BU Help**。

---

## 5. 标签页说明 / Tab Descriptions

### 5.1 Home 标签页

欢迎页面，简要介绍软件功能与使用流程。

### 5.2 Data 标签页

显示已载入的所有序列数据，列包括：

- **ID** — 序列编号
- **Name** — 序列名称
- **Sequence** — 核苷酸序列（前 50 bp 预览）
- **Length** — 序列长度
- **Discrete Traits** — 离散性状标签
- **Continuous Traits** — 连续性状数值
- **Selected** — 是否参与分析（可点击勾选）

### 5.3 Network 标签页

显示 TCS-BU 交互式网络图，分析完成后自动加载结果。

### 5.4 Haplotype 标签页

分析完成后自动显示，包含三个区域：

- **左上：单倍型汇总表** — 显示每个单倍型的编号、样本数、所含样本名称
- **右上：序列可视化** — 碱基颜色编码，超过 500 个位点时仅显示变异位点
- **下方：序列-单倍型映射表** — 每条序列对应的单倍型及性状信息

### 5.5 Alignment 标签页

显示多序列比对结果，碱基颜色编码与 Haplotype 标签页一致。

---

## 6. 数据格式 / Data Formats

### 6.1 输入格式 / Input Format

支持标准 **FASTA** 格式（`.fas / .fasta / .fa`）。序列头部可包含多字段信息，字段间以分隔符（如 `|`）分隔，例如：

```
>SampleA|Population1|5.2
ATCGATCGATCG...
>SampleB|Population2|3.8
ATCGATCGATCG...
```

在标准化对话框中指定：分隔符 `|`，字段顺序（名称 / 离散性状 / 连续性状）。

### 6.2 输出文件 / Output Files

| 文件名 | 说明 |
| --- | --- |
| `{prefix}.fasta` | 原始输入序列 |
| `{prefix}_aln.fasta` | 多序列比对结果 |
| `{prefix}_hap.fasta` | 各单倍型代表序列 |
| `{prefix}_hap_trait.csv` | 单倍型汇总（数量、性状、样本） |
| `{prefix}_seq.meta.csv` | 序列元数据（单倍型归属、性状） |
| `{prefix}_seq.phy` | PHYLIP 格式序列（fastHaN 输入） |
| `{prefix}.gml` | 网络图文件（GML 格式） |
| `{prefix}.js` | 可视化数据脚本 |

---

## 7. 工具菜单 / Tools Menu

### 语言切换 / Language Switch

**Tools → Language** 支持中文和英文界面切换，切换后菜单、按钮及提示信息即时更新。

---

## 8. 文件菜单 / File Menu

- **Load Sequence...** — 从 FASTA 文件载入序列（清空已有数据）
- **Add Sequence...** — 追加序列到当前数据集
- **Export Sequence...** — 将当前所有序列导出为 FASTA 文件
- **Exit** — 退出程序

---

## 9. 常见问题 / FAQ

**Q: 序列比对失败怎么办？**
A: 检查 MAFFT 或 MUSCLE 可执行文件是否位于 `lib/` 目录下，或系统 PATH 中已安装。

**Q: 网络图没有显示？**
A: 确认 fastHaN 可执行文件存在于 `lib/` 目录，且输出目录有写入权限。

**Q: 单倍型只有 H1 一个？**
A: 所选序列可能完全相同，或比对后序列差异为零。请检查输入序列是否存在多态性。

**Q: 如何可视化离散性状分组？**
A: 载入序列时，在标准化对话框中指定包含分组信息的字段为"Discrete Traits"，分析完成后网络图将自动启用分组着色。

**Q: 连续性状可视化不生效？**
A: 确认离散性状字段包含有效数值（非空、非 0），并在标准化时正确映射为"Continuous Traits"字段。

---

## 10. 技术依赖 / Technical Dependencies

- **PyQt6** — GUI 框架
- **PyQt6-WebEngine** — 网络图 HTML/JS 渲染
- **MAFFT** — 多序列比对工具（[https://mafft.cbrc.jp](https://mafft.cbrc.jp)）
- **MUSCLE** — 多序列比对工具（[https://www.drive5.com/muscle](https://www.drive5.com/muscle)）
- **fastHaN** — 单倍型网络构建工具
- **TCS-BU** — 网络可视化组件（[https://github.com/stelmo/TCS-Beautifier-GUI](https://github.com/stelmo/TCS-Beautifier-GUI)）
- **D3.js** — 交互式数据可视化库

---

*NetST v2.0 — Haplotype Network Analysis Tool*
