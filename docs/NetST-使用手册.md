# NetST 使用手册与软件说明

> 🌐 [English](NetST-User-Manual.md) | **中文**

> **NetST — 单倍型网络分析工具 / Haplotype Network Analysis Tool**
> 界面版本：**2.0.0**　·　适用对象：群体遗传学、系统地理学、分子流行病学研究者
>
> 本手册对应 **NetST-py**（基于 PyQt6 的重构版本）。它保留了旧版 VB.NET NetST 的核心工作流，并对数据导入、网络构建、可视化与辅助解读做了重写与增强。

---

## 目录

1. [软件概述](#1-软件概述)
2. [分析流程总览](#2-分析流程总览)
3. [安装与运行](#3-安装与运行)
4. [界面总览](#4-界面总览)
5. [快速开始（示例数据）](#5-快速开始示例数据)
6. [数据导入与预处理](#6-数据导入与预处理)
7. [metadata 管理与可视化配置](#7-metadata-管理与可视化配置)
8. [多序列比对与单倍型识别](#8-多序列比对与单倍型识别)
9. [单倍型网络构建](#9-单倍型网络构建)
10. [网络可视化（tcsBU）](#10-网络可视化tcsbu)
11. [辅助解读分析](#11-辅助解读分析)
12. [数据导出与格式转换](#12-数据导出与格式转换)
13. [输出文件说明](#13-输出文件说明)
14. [方法与算法](#14-方法与算法)
15. [常见问题与已知限制](#15-常见问题与已知限制)
16. [引用与致谢](#16-引用与致谢)
17. [联系方式](#17-联系方式)

---

## 1. 软件概述

**NetST** 是一款面向大规模、多性状单倍型数据集的集成分析软件，覆盖从原始序列到交互式网络可视化的完整链路。它把多个成熟的生物信息学引擎（MAFFT、MUSCLE、fastHaN、McAN）与内置算法（RMST、辅助解读）整合到统一的图形界面中，所有耗时任务都在后台线程运行且可随时取消。

**核心能力**

- **多格式数据导入**：FASTA、NEXUS、PHYLIP、VCF/VCF.GZ；metadata 既可从样本 ID 解析，也可从 CSV/TSV 单独导入。
- **多算法网络构建**：Original TCS、Modified TCS、MSN、MJN（fastHaN），内置 RMST，以及 McAN 最小代价树形网络。
- **多性状同心环可视化**：基于增强版 tcsBU / D3.js，将多个分类型与数值型性状以同心圆环叠加展示，并自动生成对应图例；支持 SVG/PNG/JPG 导出。
- **辅助解读（Interpretation）**：对当前数据与网络给出可视化的质量、多样性、遗传距离/PCoA 与网络拓扑指标，帮助用户直观理解数据与网络结构。
- **中英文双语界面**：菜单、页签、数据表头、日志与结果摘要随语言切换同步刷新。

**设计原则**：拓扑描述与生物学推断严格分离。中心性、桥接、PCoA 聚集等均为**探索性描述**，软件不会把它们自动等同于祖先、起源地、传播源或真实群体。

---

## 2. 分析流程总览

```text
FASTA / NEXUS / PHYLIP / VCF 序列
  │
  ├─ 样本 ID 标准化（可选解析旧式 metadata）/ 模糊碱基过滤
  ├─ 可选：从 CSV/TSV 导入 metadata
  ▼
MAFFT 或 MUSCLE 多序列比对
  ▼
识别唯一单倍型并生成 PHYLIP / CSV / FASTA 文件
  ▼
fastHaN 构建 TCS / MSN / MJN，内置 RMST，或 McAN 构建有向网络
  ▼
统一转换为 GML 并生成 tcsBU 配置
  ▼
在 Qt WebEngine 中交互可视化 ── 可选：辅助解读分析
```

整个流程由以下核心模块组成：

| 阶段 | 模块 | 说明 |
|---|---|---|
| 数据导入与预处理 | File 菜单 + 标准化窗口 | 支持四种序列格式与独立 metadata 表；导入时清理/拆分样本 ID |
| 多序列比对 | MAFFT / MUSCLE | 网络构建时自动执行；也可在 Tools 中单独运行 |
| 单倍型识别 | 内置算法 | 归并完全相同的比对序列为唯一单倍型（H1、H2…） |
| 网络构建 | fastHaN / RMST / McAN | 六种算法，统一输出 GML |
| 可视化 | tcsBU / D3.js | 多性状同心环 + 图例，交互式布局 |
| 辅助解读 | 内置纯计算模块 | 质量/多样性、遗传距离/PCoA、网络拓扑 |

---

## 3. 安装与运行

### 3.1 发布版（推荐给终端用户）

- 从 [NetST GitHub Releases](https://github.com/sculab/NetST/releases) 下载对应平台的发布包。
- 解压后，在解压目录内启动程序（macOS 为 `NetST.app`，Windows 为 `NetST.exe`），无需安装。
- **重要**：请在解压出的 NetST 目录内运行程序。MAFFT、MUSCLE、fastHaN、McAN 等外部依赖已随包内置并按平台链接。

| 平台 | 源码运行 | 内置分析程序 | PyInstaller 配置 |
|---|:---:|---|---|
| macOS Apple Silicon | 是 | MAFFT、MUSCLE 3、fastHaN、McAN | `netst-mac-arm64.spec` |
| Windows x86-64 | 是 | MAFFT、MUSCLE 3、fastHaN、McAN | `netst-win.spec` |
| Linux | 有代码路径 | 需自备 | 未提供 |

> 两个主要平台均已内置 McAN。NetST 会探测二进制并自动选择对应版本的输出参数。

### 3.2 源码运行（开发者 / Linux 用户）

建议使用 Python 3.10 与独立虚拟环境。

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

**Windows PowerShell**

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

主要依赖：`PyQt6`、`PyQt6-WebEngine`、`chardet`、`numpy`（`PyInstaller` 仅在构建发布包时需要）。若内置 MAFFT 不可用，程序会尝试调用系统 `PATH` 中的 `mafft`。

### 3.3 打包发布

```bash
# macOS Apple Silicon → dist/NetST.app
pyinstaller netst-mac-arm64.spec --noconfirm

# Windows → 单文件 dist/NetST.exe
pyinstaller netst-win.spec --noconfirm
```

打包前应在目标系统上验证内置二进制的架构、执行权限与 Qt WebEngine 运行时资源。

---

## 4. 界面总览

NetST 主窗口由**菜单栏**、**页签工作区**和底部**状态栏**组成。

### 4.1 菜单栏

| 菜单 | 功能项 |
|---|---|
| **File 文件** | Import FASTA / NEXUS / PHYLIP / VCF；Load Metadata（CSV/TSV）；Export Sequence Data；Export Metadata；Exit |
| **Analysis 分析** | **Build / Rebuild Haplotype Network**（构建/重新构建单倍型网络）；**Interpretation Analysis 辅助解读** ▸ Sequence Quality and Diversity / Genetic Distance and PCoA / Network Topology Metrics |
| **Tools 工具** | Multiple Sequence Alignment（仅比对）；Calculate Haplotype（比对+单倍型，不构网）；Sequence Format Conversion；Language 语言（中文 / English） |
| **Help 帮助** | About；TCS-BU Help；NetST Help |

### 4.2 页签工作区

| 页签 | 内容 |
|---|---|
| **Home 首页** | 软件定位、核心能力、快速流程、支持算法与输入/输出概览 |
| **Network 网络视图** | tcsBU 交互式单倍型网络（Qt WebEngine 嵌入） |
| **Data 数据** | 序列数据表：ID、名称、序列（只读）、勾选参与分析；样本名/选择/性状可编辑 |
| **Metadata** | 导入 metadata 后出现：逐性状配置类型、Group、是否可视化与颜色 |
| **Haplotype 单倍型** | 单倍型汇总与样本—单倍型映射 |
| **Alignment 序列比对** | 比对矩阵（为保持响应，仅渲染前 500 个位点） |
| **辅助解读 Interpretation** | 结构化辅助分析结果：概览 KPI 卡片、可视化图表、明细表格 |

> Data 与 Info 侧栏在 tcsBU 网络视图中可折叠、可拖拽调宽，为网络腾出空间。

### 4.3 状态栏

分析运行时，窗口底部显示进度条与 **取消** 按钮。取消会请求后台任务停止，并终止当前外部程序的整个进程组；程序关闭或新任务替换旧任务时使用相同的清理流程。

---

## 5. 快速开始（示例数据）

随附两套 SARS-CoV-2 示例数据集：

- **SL-SARS-CoV-2**：130 个代表性单倍型，区分 L / S 谱系（分类型性状）。
- **DP-SARS-CoV-2**：482 条基因组序列（钻石公主号 72 例 + 全球 410 例），带地理位置（分类型）与采集日期（连续型）。

以 DP-SARS-CoV-2 为例的最短路径：

1. **File → Import FASTA**，选择 `DP-SARS-CoV-2.fasta`。
2. 在**标准化窗口**中设置分隔符为 `|`，并把字段位置映射为：`0=样本名`、`1=分类型性状（地区）`、`2=连续型性状（采集日）`。
3. 在 **Data** 页检查数据，勾选需要参与分析的样本（默认全选）。
4. 在右侧填写**项目名称**并选择**输出目录**（默认 `~/HaplotypeOutput`）。
5. **Analysis → Build / Rebuild Haplotype Network**，选择算法（如 Original TCS），点击运行。NetST 会自动完成比对 → 单倍型识别 → 构网 → 可视化。
6. 在 **Network** 页查看交互网络；在 **Alignment / Haplotype** 页查看中间结果。
7. 如需统计解读，运行 **Analysis → Interpretation Analysis** 下的任一分析，结果显示在**辅助解读**页。
8. 用 **File → Export Sequence Data** 或工具栏 **Save Image** 导出结果。

> FASTA 标题形如 `>DP0005|DP|54|1|Human`（样本名 | 地区 | 采集日 | 数量 | 物种）。字段位置从 0 开始计数，可按需选择用到的字段。

---

## 6. 数据导入与预处理

### 6.1 支持的序列格式

| 格式 | 菜单 | 说明 |
|---|---|---|
| **FASTA** | File → Import FASTA | 标题空白会规范化为下划线，避免 PHYLIP/fastHaN 误拆字段 |
| **NEXUS** | File → Import NEXUS | 支持 DATA/CHARACTERS 块的 DNA/RNA MATRIX：顺序、交错、引号名、嵌套注释、`MATCHCHAR` |
| **PHYLIP** | File → Import PHYLIP | 支持顺序与常见交错；首行声明的序列数与长度必须与数据一致 |
| **VCF / VCF.GZ** | File → Import VCF | 见 [§6.3](#63-vcf-导入) |

三种非 VCF 格式导入后均进入相同的**名称标准化窗口**，并作为当前原始数据载入 Data 页。导入失败不会覆盖表格中已有数据。

### 6.2 标准化窗口（样本 ID 处理）

导入对话框可以：

- **清理 / 替换**样本名中的字符；
- 按**分隔符 + 从 0 开始的字段索引**从复合标题中提取**样本名、分类型性状、数值型性状**，兼容旧式标题（如 `sample_01|population_A|12.5`）；
- 也可以只处理样本名，之后再用 **File → Load Metadata** 单独导入多个性状；
- 可选**过滤含 `RYSWKMBDHVN` 模糊碱基**的序列。

数值型性状必须是有效数值。

### 6.3 VCF 导入

**File → Import VCF** 支持含样本基因型列的 VCF / VCF.GZ。当前序列工作流面向**单个序列区域**，因此要求 VCF 仅包含一个 contig，且每条记录含 `GT` 字段。

**metadata 文件（可选）**

| 提供方式 | 效果 |
|---|---|
| 不提供 | metadata 仅从样本 ID 解析 |
| 普通 CSV/TSV | 按样本名匹配，填充离散性状（分组）与连续性状 |
| McAN 六列 TSV | 填充由 Country/State/City 合并的离散性状；**样本名未改动时**启用 McAN 原生 VCF 分析并保留真实采样日期用于网络定向 |

> McAN 六列格式：`SampleName AccessionID SamplingDate Country State City`，缺失值用 `*`，表头可选。若在标准化中重命名/删除样本或之后编辑数据表，程序会自动退回 aligned-FASTA → mutation 适配流程。

**比对重建规则**

- **未提供参考 FASTA**：将每个 VCF 记录转换为等宽变异位点块，生成“仅变异位点比对”。
- **提供参考 FASTA**：校验每条 VCF `REF` 与参考一致，补回不变区域并生成全长比对。
- 多等位基因按 GT 编号解析；杂合单碱基位点用 IUPAC 字符，杂合复杂 indel 用 `N`。
- 符号型 ALT、breakend、多 contig 与相互重叠的记录会被明确拒绝。

---

## 7. metadata 管理与可视化配置

### 7.1 从 CSV/TSV 导入 metadata

**File → Load Metadata** 导入独立 metadata 表。文件首行为表头，至少需要一列能与已导入序列名一一对应：

```csv
sample,population,value
sample_01,population_A,12.5
sample_02,population_B,13.1
```

导入时按首个数据行自动识别分隔符（制表符优先）。每列可设为**样本名 / 忽略 / 分类型性状 / 数值型性状**；一次可选任意多个性状，但**必须至少指定一个分类型性状作为 Group**。程序会检查两侧样本名是否完整匹配并拒绝任一侧的重复名，避免 metadata 被静默覆盖或错配。

每个数值型性状都可点击**连续型转换**并独立设置规则：

| 输入类型 | 可接受的输入与输出 |
|---|---|
| 普通数值 | 严格检查有限数值；空单元格保持为空 |
| 日期 / 时间 | `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY-MM`、`YYYY` 或 ISO 日期时间 → 相对于所选起始日期的天、日历月或日历年；起始日期留空表示本列最早日期 |
| 带单位测量值 | 长度（`mm/cm/m/km/in/ft`）、质量（`mg/g/kg`）或温度（`°C/°F/K`）→ 统一的目标单位；还可为无后缀数值指定原始单位 |

预览会检查整列，而不只是界面显示的前几行。无效值会阻止确认并指出其在 metadata
源文件中的行号。转换不会修改源文件；规范化后的数值写入当前 Data 表，并直接进入普通的连续型可视化流程。日历时间差符合直觉：同日到下月同日恰为 1 个月，同日期到次年恰为 1 年；不足整月/整年的部分仍保留小数，以保持颜色渐变连续。

### 7.2 Metadata 页

导入后出现 **Metadata** 页。每行对应一个性状，可：切换分类型/数值型、选择唯一 Group、控制是否可视化、编辑颜色（类别配色或数值梯度低/高端点，可用色卡或直接输入十六进制）。分类型性状在 2–10 个类别时使用按类别数匹配的预设色板，超过 10 类时生成稳定且不重复的颜色；连续型默认使用灰色（`#BDBDBD`）到黑色（`#000000`）渐变。程序会阻止删除最后一个分类型 Group。

网络节点按 Metadata 表顺序绘制**同心环**：Group 位于最内层，其他已启用性状依次向外。分类型圆环按单倍型成员的类别比例分段；数值型圆环先将成员数值从小到大排序，再按此顺序分段，并用该性状自己的数值范围渐变着色。tcsBU 的 **Legend** 会按相同内外顺序列出全部类别色块与数值梯度范围。

### 7.3 何时重新构建，何时只更新可视化配置

> 网络**拓扑**由输入样本与序列决定；metadata 的类型、分组、圆环与颜色只决定已有拓扑**如何显示**。

| 变化 | 操作 |
|---|---|
| 导入新的 FASTA/NEXUS/PHYLIP/VCF | **重新构建**单倍型网络 |
| 修改样本名、序列、参与分析的样本集合 | **重新构建**单倍型网络 |
| 更换网络算法/参数 | **重新构建**单倍型网络 |
| 导入或修改 metadata 值 | 仅点击 Metadata 页的 **应用可视化配置** |
| 修改性状类型、Group、Visualize 或颜色 | 仅点击 **应用可视化配置** |
| 在 tcsBU 中调整分组名称、颜色或样本所属分组 | 仅更新当前可视化配置 |

轻量刷新只改写 tcsBU 的 `_hapconf.csv`、`_groupconf.csv`、`_traitconf.csv`、内嵌数据的 `.js` 和 `.html`；现有 `.gml`、比对与样本—单倍型映射保持不变（相同序列得到相同的 H1/H2… 标签）。

---

## 8. 多序列比对与单倍型识别

### 8.1 多序列比对（MSA）

NetST 使用 **MAFFT**（含多种模式）或 **MUSCLE** 进行比对：

| MAFFT 模式 | 特点 |
|---|---|
| Auto | 自动选择 |
| FFT-NS-1 | 极快但粗糙 |
| FFT-NS-2 | 快速 |
| G-INS-i | 全局比对，较慢 |
| L-INS-i | 局部比对，最精确 |
| E-INS-i | 含长非比对区域 |

- **完整网络分析**：若输入序列长度不同，先运行 MAFFT，失败后尝试 MUSCLE；长度相同时视为已比对并直接进入单倍型处理。
- **Tools → Multiple Sequence Alignment**：仅运行比对，用于可视化检查或微调，多数用户无需单独使用。

### 8.2 单倍型识别

- **Tools → Calculate Haplotype**：比对并计算单倍型，但不构网。
- 完全相同的比对序列会被归并为唯一单倍型（H1、H2…），以简化后续网络。结果在 **Haplotype** 页展示，并生成 `project_hap.fasta`、`project_seq.meta.csv` 等文件。

---

## 9. 单倍型网络构建

**Analysis → Build / Rebuild Haplotype Network** 打开网络构建对话框，选择算法与参数后一键完成比对 → 单倍型识别 → 构网 → 可视化。

### 9.1 支持的算法与参数

| 算法 | 引擎标识 | 可配置参数 | 适用场景 |
|---|---|---|---|
| **Original TCS**（统计简约网络） | `original_tcs` | 线程、模糊位点、合并中间节点 | 种内系统地理学、浅层分化 |
| **Modified TCS** | `modified_tcs` | 线程 | TCS 的改进变体 |
| **MSN**（最小生成网络） | `msn` | epsilon | 近缘、低分化群体 |
| **MJN**（中位连接网络） | `mjn` | 线程、epsilon | 含重组/缺失、需推断祖先单倍型 |
| **RMST**（随机最小生成树） | `rmst` | 精确/随机模式、重复次数、随机种子、是否排除模糊位点 | 内置实现，见 [§14.1](#141-rmst-内置实现) |
| **McAN**（最小代价树形网络） | `mcan` | 线程、参考序列、是否排除模糊位点 | 有向包含关系网络，见 [§14.2](#142-mcan-适配方式) |

### 9.2 算法选择建议

- **MSN**：结构最简，适合种内/群体级、遗传分化低的数据。
- **MJN**：可容纳网状进化并推断祖先单倍型，适合复杂进化重建、古 DNA、病毒动态。
- **TCS**：使用 95% 连接阈值保证统计可靠的连边，适合种内系统地理学。
- **RMST**：无需外部程序，精确模式结果确定且可复现，推荐作为快速稳健的默认之一。
- **McAN**：给出以参考序列为根的突变包含关系网络；提供真实采样日期时可做时间定向。

---

## 10. 网络可视化（tcsBU）

网络在 **Network** 页以增强版 **tcsBU / D3.js** 渲染，嵌入在 Qt WebEngine 中。

### 10.1 多性状同心环

每个单倍型节点绘制为同心圆环：**Group 最内层**，其他已启用性状依次向外。节点大小按频率缩放。**Legend** 按内外顺序列出全部类别色块与数值梯度范围。

### 10.2 工具栏

网络上方工具栏提供：

- **Save Image**：导出 **SVG（矢量）/ PNG / JPG**，随后由系统保存窗口选择位置。SVG 为标准 `image/svg+xml`，PNG/JPG 默认以 2 倍分辨率导出。
- **Zoom In / Zoom Out**、**Delete Node / Delete Link**（交互编辑）。
- **Legend**：显示/隐藏图例。
- **Haplotype / Distance**：显示单倍型标签 / 连边突变距离标注。
- **Advanced**：打开高级设置对话框（见下）。

### 10.3 Advanced 高级设置对话框

对话框**可拖拽标题栏移动**，分为三个区块：

**Force-Directed Layout Settings（力导向布局）**
Link Distance、Link Strength、Friction、Charge、Gravity，以及 Start / Stop。

**Node and Edge Settings（节点与边）**

| 参数 | 含义 | 默认 |
|---|---|---|
| Node Radius | 频率为 1 的单倍型节点半径（像素），调整时保留不同频率节点间的相对大小 | 5 |
| **Node Line Width** | 节点描边宽度 | 1.5 |
| **Edge Line Width** | 连边（edge）基础线宽 | 1.5 |
| **Edge Weight Scale** | 开启 Edge Weight 时基础线宽的最大倍率 | 4 |
| Text Offset | 节点旁文本偏移 | 5 |

**Metadata Ring Settings（同心环）**

| 参数 | 含义 | 默认 |
|---|---|---|
| **Ring Line Width** | 圆环分段描边宽度 | 0.5 |
| Base Ring Width | 每个非 Group 外环在比例为 1 时的基础厚度（像素）；实际厚度 = 基础宽度 × 对应环比例 | 7 |
| Outer Ring Ratios | 从内到外的逗号分隔比例（缺省按 1） | — |

> 说明：Node/Edge Line Width 为可分别调节的独立参数。Edge Weight 读取数值型 Changes 距离，并以 Edge Line Width 为基础缩放所有连边；变异数越少，连边越粗。

### 10.4 Data 页只读约束

Data 页的 **Sequence 列为只读**，避免误编辑序列导致已有比对、单倍型与网络结果失效；样本名、选择状态与 metadata 性状仍可正常调整。

---

## 11. 辅助解读分析

**Analysis → Interpretation Analysis（辅助解读）** 提供三项纯计算分析。计算层使用**不可变的对齐序列快照**，与界面/文件输出分离，并在后台线程运行，可随时取消。结果显示在**辅助解读**页，并保存为 JSON。

| 菜单功能 | 输入与计算 | 主要结果 |
|---|---|---|
| **序列质量与多样性** | 当前选中的等长对齐序列；可选完整删除 / 成对删除 | 样本/位点缺失率、有效位点、变异位点、简约信息位点、S、Hd、π、θW、分组丰富度与私有单倍型 |
| **遗传距离与 PCoA** | 仅 A/C/G/T 作为确定状态；gap、N、? 与 IUPAC 模糊状态成对删除 | p-distance 矩阵、每对有效比较位点、PCoA 坐标、正/负特征值诊断 |
| **网络拓扑指标** | 当前项目 GML，或用户选择的 tcsBU 兼容 GML | 节点/边数、连通分量、密度、环秩、degree、closeness、betweenness、割点与桥 |

运行前，**序列质量与多样性**和**遗传距离与 PCoA** 会弹出参数窗口：前者可选缺失数据策略（完整删除 / 成对删除）和用于分组的分类型性状；后者可设最小可比较位点数与最低可比较覆盖率。

### 11.1 结果页的可视化

辅助解读页把结果组织为**概览 + 图表 + 明细表格**三部分，让用户更直观地理解数据与网络：

- **概览（Overview）**：一排彩色 **KPI 卡片**，缺失率等指标按 绿/黄/红 分级，配合完整指标表与警告/提示。
- **图表（Visualizations）**：
  - *多样性*：分组多样性对比（N / 单倍型数 / Hd / π / θW 小多图）、样本缺失率条形图（按阈值配色）、**沿比对位置的位点变异与缺失“轨道图”**（深色=简约信息位点，下方=缺失率热带）。
  - *距离/PCoA*：**PCoA 排序散点图**（按分组着色 + 图例 + 解释度轴标）与**遗传距离热图**（灰格=可比位点不足、距离不可用）。
  - *拓扑*：节点度分布直方图，以及枢纽节点介数排名（**割点用红色高亮**）。
- **明细表格**：保留全部精确数值，便于查阅与核对。

> 有 `PyQt6-WebEngine` 时图表在网页视图中渲染并支持悬停查看数值；否则自动回退为静态 SVG，同样完整可用。界面大表格会限制显示行/列数以保持响应，完整结果始终保存为 JSON。

### 11.2 缺失数据与解释约定

- RNA `U` 内部统一为 `T`；`-`/`N`/`?`/IUPAC 模糊状态不作为确定等位基因。
- 低于最小有效位点或覆盖率的序列对，距离记为**缺失**，不补 0，也不使用人为饱和常数。
- PCoA 使用经典多维尺度分析，不把距离矩阵当作普通特征直接跑 PCA。
- McAN 有向 GML 的方向作为来源信息保留；当前中心性、割点与桥指标使用**无向投影**。
- **拓扑中心、桥接节点与 PCoA 聚集均为探索性描述，不自动等同于祖先、起源地、传播源或真实群体。**
- **当前不自动计算 Tajima's D**，因为其稳健解释需要人口史、重组、抽样与零模型假设。

---

## 12. 数据导出与格式转换

### 12.1 导出

**File → Export Sequence Data** 导出 Data 页全部记录：

| 目标格式 | 说明 |
|---|---|
| FASTA | 标题使用 `样本名\|离散性状\|连续性状`，同时保留序列与 metadata |
| NEXUS / PHYLIP | 仅写样本名与序列（不混入 metadata）；要求序列已等长 |
| VCF | 写入序列变异与 `NetSTSampleMetadata` 头，并生成同名 `_metadata.csv`；要求等长且至少一个变异位点 |

**File → Export Metadata** 单独生成 CSV/TSV metadata 表，仅导出 `sample` 与当前 Metadata 页中的性状字段。

### 12.2 序列格式转换

**Tools → Sequence Format Conversion**：

| 输入 | 可转换输出 | 说明 |
|---|---|---|
| FASTA | NEXUS、PHYLIP、VCF | 输出 NEXUS/PHYLIP 要求等长；输出 VCF 可指定参考样本 |
| NEXUS | FASTA、PHYLIP、VCF | 读取 DATA/CHARACTERS 矩阵；支持顺序、交错、MATCHCHAR |
| PHYLIP | FASTA、NEXUS、VCF | 读取顺序或常见交错，要求声明数量与长度正确 |
| VCF / VCF.GZ | FASTA、NEXUS、PHYLIP | 参考 FASTA 可选；未提供时输出变异位点比对 |

> 转 VCF 要求序列已等长比对，会将连续变异列合并为合法等位基因块，并为插入/删除增加参考锚点。完全无变异的比对无法生成只含变异记录的 VCF。输入与输出路径必须不同。

---

## 13. 输出文件说明

所有生成文件统一以“输出目录 + 项目名称”为前缀（下表以 `project` 为例）：

| 文件 | 内容 |
|---|---|
| `project.fasta` | 本次分析的原始输入序列 |
| `project_aln.fasta` | 比对后的序列 |
| `project_seq.fasta` / `project_seq.phy` | 带原始样本名的分析序列 / fastHaN 用 PHYLIP 输入 |
| `project_hap.fasta` | 去冗余的 H1、H2… 单倍型序列 |
| `project_seq.meta.csv` | 样本、单倍型与性状映射 |
| `project_hap_trait.csv` / `project_seq_trait.csv` | 单倍型汇总 / 逐样本性状表 |
| `project_traitconf.csv` | 连续性状配置（仅有有效值时生成） |
| `project.gml` | tcsBU 方言的网络图（fastHaN / RMST / McAN 转换后） |
| `project_rmst.json` / `project_rmst.tsv` | RMST 参数、位点、边表与随机抽样统计（仅 RMST） |
| `project_mcan/` | McAN 输入、样本别名映射及原始 GraphML/JSON（仅 McAN） |
| `project_hapconf.csv` / `project_groupconf.csv` | tcsBU 单倍型 / 分组与颜色配置 |
| `project.js` / `project.html` | 本地交互可视化资源 |
| `project_diversity_analysis.json` | 序列 QC、总体/分组多样性及计算警告 |
| `project_distance_analysis.json` | p-distance、有效比较位点、PCoA 特征值与坐标 |
| `project_topology_analysis.json` | 网络概况、节点/边拓扑指标及方向来源信息 |

> Alignment 与 Haplotype 页为保持响应速度只渲染前 500 个位点；输出文件始终保留完整序列。

---

## 14. 方法与算法

### 14.1 RMST 内置实现

RMST（Randomized Minimum Spanning Tree）直接读取 `project_hap.fasta` 与 `project_seq.meta.csv`，对唯一单倍型计算未校正突变位点数（Hamming 距离），**无需外部可执行程序**。两种模式：

- **精确模式（默认、推荐）**：按距离层确定所有至少能出现在一棵最小生成树中的边；结果确定，不受随机种子影响。
- **随机模式**：多次随机化单倍型顺序并运行稳定 Kruskal，输出每条边的出现次数与频率；固定随机种子可复现，但有限重复不保证找到全部兼容边。

默认排除任何含非 `A/C/G/T/U/-` 字符的比对列，RNA `U` 统一为 `T`，gap 作为一个可比较状态。过滤后变为相同序列的单倍型会与其样本成员合并为一个网络节点，并记录在 JSON 的 `warnings` 与节点 `haplotypes` 字段。规模限制：精确模式 ≤ 1000 个过滤后节点，随机模式 ≤ 500 个节点、≤ 1000 次重复。

> 算法参考：Paradis, E. (2018) *Analysis of haplotype networks: The randomized minimum spanning tree method.* Methods in Ecology and Evolution 9:1308–1317.

### 14.2 McAN 适配方式

McAN 原生接收 VCF 或 mutation + metadata + site mask，输出 GraphML/JSON。`service/mcan_adapter.py` 支持两条路径：

- **原生 VCF 路径**：导入 VCF 且附带 McAN 六列 metadata、样本名未改动时，直接调用 `McAN --vcf`，保留真实采样日期用于网络定向。
- **mutation 适配路径**：FASTA/PHYLIP 来源、无 metadata 的 VCF，或样本被重命名/编辑时：
  1. 读取已比对 FASTA，以所选参考序列计算逐位点差异；
  2. 用 `S0000001` 形式的内部别名生成 mutation/metadata，避免未转义样本名破坏 GraphML；
  3. 生成显式 site mask（可选排除含非 A/C/G/T/U/缺口的列）；
  4. 在独立 `project_mcan/` 目录调用 McAN，保留原始 GraphML/JSON；
  5. 转换为 tcsBU 可读 GML，恢复原始样本名与网络距离。

> NetST 将 McAN 最大序列坐标限制为 30000，并在调用前拒绝更长比对。适配器自动选择 McAN 1.2 的 `--outDir` 或 McAN 1.4.x 的 `--out`，并支持两种 GraphML 格式。FASTA 不含采样日期时，适配器不虚构时间顺序，得到的是以参考序列为根的突变包含关系网络。
> 算法参考：Li, L. et al. (2022) *McAN: an ultrafast haplotype network construction algorithm.* bioRxiv 2022.07.23.501111.

### 14.3 辅助解读的指标定义

- **序列质量**：逐样本/逐位点的缺失、gap、未知、模糊计数与比例；有效位点、变异位点、简约信息位点。
- **多样性**：单倍型丰富度、单倍型多样性 Hd、核苷酸多样性 π、Watterson's θW、分离位点 S、分组私有单倍型。
- **遗传距离**：成对删除的 p-distance，并同时报告每对的有效比较位点数。
- **PCoA**：经典多维尺度分析（无第三方依赖求解器默认限 200 条序列；更大数据集仍输出距离矩阵但跳过 PCoA 并给出警告）。
- **网络拓扑**：连通分量、密度、环秩（独立环数）、degree、closeness、betweenness、割点（articulation point）、桥（bridge）。突变数始终作为距离，不作为更强连接权重。

---

## 15. 常见问题与已知限制

**Q：为什么“辅助解读”里没有 Tajima's D / 社区检测 / 双性状显著性检验？**
A：本版本刻意不提供这些功能。Tajima's D、FST/AMOVA、社区稳定性与人口史零模型的稳健解释需要额外的抽样、重组与零模型假设，超出当前描述性/探索性辅助分析的范围。

**Q：修改了 metadata 或颜色，需要重新构网吗？**
A：不需要。只要序列与样本集合没变，点击 Metadata 页的**应用可视化配置**即可刷新显示（详见 [§7.3](#73-何时重新构建何时只更新可视化配置)）。

**Q：网络视图空白 / 只有文字？**
A：tcsBU 依赖 Qt WebEngine。缺少 `PyQt6-WebEngine` 时网络页会退回降级文本组件；请安装该依赖。

**已知限制**

- 仓库尚未提供完整 Linux 发布包；Linux 需自备兼容的外部程序。
- 内置外部二进制需分平台构建验证，不能跨架构使用；Windows/Linux 的 McAN 需自行编译放置。
- McAN 适配器最多接受 30000 个比对位点。
- 内置 RMST 精确模式 ≤ 1000 节点、随机模式 ≤ 500 节点；更大数据集建议后续接入稀疏/编译型后端。
- VCF 序列转换限定单 contig、非重叠的小变异记录，不支持结构变异、breakend 或符号型 ALT。
- PCoA 无第三方依赖求解器默认限 200 条序列。
- 自动化测试覆盖核心纯逻辑；完整 GUI 交互、平台打包与真实数据端到端流程仍需在目标系统验证。

---

## 16. 引用与致谢

若在研究中使用 NetST，请引用：

> Zhang Z, Yu Y. *NetST: An integrated software for large-scale haplotype network construction, visualization, and automated analytics.*

并请引用相关依赖：

- Chi L, Zhang X, Xue Y, Chen H. 2023. *fastHaN: a fast and scalable program for constructing haplotype network for large-sample sequences.* Mol Ecol Resour. https://doi.org/10.1111/1755-0998.13829
- Múrias Dos Santos A, et al. 2016. *tcsBU: a tool to extend TCS network layout and visualization.* Bioinformatics 32:627–628.
- Nakamura T, et al. 2018. *Parallelization of MAFFT for large-scale multiple sequence alignments.* Bioinformatics 34:2490–2492.
- Paradis E. 2018. *Analysis of haplotype networks: The randomized minimum spanning tree method.* Methods Ecol Evol 9:1308–1317.
- Li L, et al. 2022. *McAN: an ultrafast haplotype network construction algorithm.* bioRxiv 2022.07.23.501111.

示例数据引用：

- DP-SARS-CoV-2：Sekizuka T, et al. 2020. *Haplotype networks of SARS-CoV-2 infections in the Diamond Princess cruise ship outbreak.* PNAS 117:20198–20201.

---

## 17. 联系方式

如对 NetST 有任何问题、建议或意见，请联系：
[yyu@scu.edu.cn](mailto:yyu@scu.edu.cn)　·　[zzhen0302@163.com](mailto:zzhen0302@163.com)

---

*本手册基于 NetST-py 当前源码与 README 编写，随软件更新可能调整。License：MIT。*
