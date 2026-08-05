# NetST

> 🌐 [English](README.md) | **中文**

**单倍型网络分析工具 / Haplotype Network Analysis Tool**

NetST 是一个基于 PyQt6 的桌面科研软件，用于从 DNA/RNA 序列完成多序列比对、单倍型识别、单倍型网络构建与交互式可视化。本项目由旧版 VB.NET 程序重构而来，面向群体遗传学、系统地理学与分子流行病学，在统一的双语界面中整合了成熟引擎（MAFFT、MUSCLE、fastHaN、McAN）与内置算法（RMST、辅助解读）。

**当前界面版本：2.0.0**

---

## 目录

- [功能概览](#功能概览)
- [文档](#文档)
- [分析流程](#分析流程)
- [支持的平台](#支持的平台)
- [安装与运行](#安装与运行)
- [快速使用](#快速使用)
- [输入数据](#输入数据)
- [metadata 与可视化刷新](#metadata-与可视化刷新)
- [网络算法与参数](#网络算法与参数)
- [可视化（tcsBU）](#可视化tcsbu)
- [辅助解读分析](#辅助解读分析)
- [数据导出与格式转换](#数据导出与格式转换)
- [输出文件](#输出文件)
- [项目结构](#项目结构)
- [子进程控制](#子进程控制)
- [打包](#打包)
- [开发说明](#开发说明)
- [已知限制](#已知限制)
- [引用](#引用)
- [License](#license)

---

## 功能概览

- 从 File 菜单导入 **FASTA、NEXUS、PHYLIP 或 VCF** 序列数据；metadata 可从旧文件的样本 ID 解析，也可通过 CSV/TSV 单独导入。
- 将当前数据导出为 FASTA、NEXUS、PHYLIP、VCF+metadata，或独立导出 metadata 表（CSV/TSV）。
- 导入多样本 VCF（可选参考 FASTA 重建全长序列）；metadata 从样本 ID 解析，也可选带一个 metadata 文件以启用 McAN 原生 VCF 模式。
- 在导入时清理、替换或拆分样本 ID，并兼容提取样本名、分类型性状和数值型性状。
- 从 CSV/TSV 一次导入多个分类型/数值型 metadata 性状，指定一个分类型性状作为分组，并支持可视化列映射与分隔符自动识别。
- 在表格中检查、编辑、选择或取消选择参与分析的序列。
- 使用 **MAFFT** 或 **MUSCLE** 进行多序列比对；将完全相同的比对序列归并为唯一单倍型。
- 使用 fastHaN 构建 **Original TCS、Modified TCS、MSN 或 MJN** 网络，使用内置 **RMST**，或使用 **McAN** 最小代价树形网络。
- 使用内嵌 **tcsBU / D3.js** 页面以同心多环展示多个分类型/数值型性状，并生成对应的多环图例；侧栏可折叠、可拖拽调宽。
- 网络构建后补充或修改 metadata 时，可将分组与数值型性状重新映射到现有网络，**无需重建网络**。
- 在 **Analysis → 辅助解读** 中以可视化方式探索数据与网络：序列质量/多样性、缺失感知成对 **p-distance + PCoA**、网络**拓扑指标**，并明确区分拓扑描述与祖先/传播推断。
- 支持**中文和英文**界面，语言切换时同步刷新。
- 耗时分析在后台线程运行，可从状态栏取消；超时或取消时会清理外部进程及其子进程。

## 文档

提供中英文两版完整的分步使用手册：

- 📗 **[NetST 使用手册（中文）](docs/NetST-使用手册.md)**
- 📘 **[NetST User Manual (English)](docs/NetST-User-Manual.md)**

手册中贯穿使用两套 SARS-CoV-2 示例数据集：

- **SL-SARS-CoV-2** — 130 个代表性单倍型，区分 L / S 谱系（分类型性状）。
- **DP-SARS-CoV-2** — 482 条基因组序列，带地理位置（分类型）与采集日期（连续型）。

## 分析流程

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

## 支持的平台

| 平台 | 源码运行 | 仓库内置分析程序 | PyInstaller 配置 |
|---|:---:|---|---|
| macOS Apple Silicon | 是 | MAFFT、MUSCLE 3、fastHaN、McAN 1.4.3 arm64 | `netst-mac-arm64.spec` |
| Windows x86-64 | 是 | MAFFT、MUSCLE 3、fastHaN、McAN 1.4.3 | `netst-win.spec` |
| Linux | 有代码路径 | 未完整提供 | 未提供 |

Linux 用户需要自行准备兼容的外部程序，并根据 `AnalysisService` 的平台路径约定放置二进制文件。当前正式打包目标是 macOS Apple Silicon 和 Windows x86-64。

## 安装与运行

建议使用 Python 3.10 和独立虚拟环境。

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

主要 Python 依赖：`PyQt6`、`PyQt6-WebEngine` 与 `chardet`（`PyInstaller` 仅构建发布包时需要）。RMST 不依赖 NumPy。

macOS 与 Windows 所需的 MAFFT、MUSCLE、fastHaN、McAN 和 RMST 二进制已放在 `lib/` 下。Apple Silicon 使用原生 arm64 引擎；Windows McAN 与 RMST 是静态运行库的 x86-64 构建。若内置 MAFFT 不可用，程序会尝试调用系统 `PATH` 中的 `mafft`。

## 快速使用

1. 在 **File** 菜单选择 **Import FASTA / NEXUS / PHYLIP / VCF** 导入序列文件。
2. 在标准化窗口预览并配置样本名清理、替换、拆分或编号；旧文件仍可从样本 ID 提取分类型/数值型性状。
3. 对于独立 metadata 表，选择 **File → Load Metadata** 导入 CSV/TSV，并映射样本名、分类型性状和数值型性状列。
4. 在 **Data** 页检查数据，勾选需要参与分析的样本。
5. 在右侧填写项目名称并选择输出目录，默认目录是 `~/HaplotypeOutput`。
6. 根据需要选择功能：
   - **Tools → Multiple Sequence Alignment**：仅运行 MAFFT/MUSCLE；
   - **Tools → Calculate Haplotype**：比对并计算单倍型，不构网；
   - **Analysis → Build / Rebuild Haplotype Network**：执行完整网络分析；
   - **Metadata → 应用可视化配置**：网络已构建后再补充/修改 metadata 时，无需重建网络（详见下文）。
7. 在 **Network、Alignment、Haplotype** 页查看结果。
8. 从 **Analysis → 辅助解读** 运行质量/多样性、遗传距离/PCoA 或网络拓扑分析，结果显示在**辅助解读**页。
9. 使用 **File → Export Sequence Data** 选择序列格式，或使用 **Export Metadata** 单独导出 metadata（CSV/TSV）。

分析运行时，窗口底部会显示进度和 **取消** 按钮。取消会请求后台任务停止，并终止当前外部程序的整个进程组。程序关闭或新任务替换旧任务时也使用相同清理流程。

## 输入数据

### FASTA

普通 FASTA 即可：

```fasta
>sample_01|population_A|12.5
ATGCTAGCTAGCTACG
>sample_02|population_B|13.1
ATGCTAGCTAGTTACG
```

导入对话框可以清理、替换或按分隔符和从 0 开始的字段索引提取样本名称、分类型性状与数值型性状，从而兼容旧式复合标题；也可以只处理样本名，再用 **File → Load Metadata** 导入多个性状。数值型性状必须是有效数值；含 `RYSWKMBDHVN` 模糊碱基的序列可在导入时选择过滤。FASTA 标题中的空白会规范化为下划线，避免 PHYLIP 和 fastHaN 将一个名称误拆成多个字段。

### NEXUS 与 PHYLIP

- **File → Import NEXUS** 支持 `DATA`/`CHARACTERS` 块中的 DNA/RNA `MATRIX`，可读取顺序矩阵、带名称的交错矩阵、无名称的交错续行、引号包裹的样本名、嵌套注释与 `MATCHCHAR`。
- **File → Import PHYLIP** 支持顺序及常见交错 PHYLIP；文件首行声明的序列数和比对长度必须与实际数据一致。
- 两种格式导入后均进入与 FASTA 相同的名称标准化窗口，并作为当前原始数据载入 Data 页。导入失败不会覆盖表格中已有的数据。

### metadata 表（CSV / TSV）

除了从样本 ID 解析，metadata 也可以从单独的 CSV/TSV 文件导入（**File → Load Metadata**）。文件第一行为表头，至少需要一列能与已导入的序列名称一一对应：

```csv
sample,population,value
sample_01,population_A,12.5
sample_02,population_B,13.1
```

导入时按首个数据行自动识别分隔符（制表符优先）。每一列可设为样本名、忽略、分类型性状或数值型性状；一次可选择任意多个性状，但必须至少指定一个分类型性状作为 Group。软件会检查数据表与文件的样本名是否完整匹配，并拒绝任一侧的重复名称。

每个数值型性状都有独立的**连续型转换**按钮，可选择：

- **普通数值**：严格检查每个非空值是否为数值；
- **日期 / 时间**：支持 `2022-10-1`、`2022/10/1`、`2022-10` 及 ISO
  日期时间，可按天、日历月或日历年计算相对于指定起始日期的时间差；起始日期留空时，自动采用该列最早的有效日期；
- **带单位测量值**：将混合的长度（`mm/cm/m/km/in/ft`）、质量（`mg/g/kg`）或温度（`°C/°F/K`）统一到选定单位；无单位后缀的数值可单独指定其原始单位。

转换窗口会显示原始值与转换后数值的预览，并检查整列数据；遇到无效值时会指出 metadata
源文件的行号。空值保持为空，源文件不会被修改；转换后的数值进入 Data 表，并直接使用现有的连续渐变与 ring 可视化流程。

导入后会出现 **Metadata** 页。每行对应一个性状，可切换分类型/数值型、选择唯一 Group、控制是否可视化并编辑颜色（类别配色或数值梯度低/高端点，可用色卡或直接输入十六进制）。分类型性状在 2–10 个类别时使用按类别数匹配的预设色板，超过 10 类时生成稳定且不重复的颜色；连续型默认使用灰色（`#BDBDBD`）到黑色（`#000000`）渐变，并在每个节点内先按数值从小到大排序，再依次绘制 ring 扇区。程序会阻止删除最后一个分类型 Group。网络节点按 Metadata 表顺序绘制同心环——Group 最内层，其他向外——tcsBU 的 **Legend** 按相同顺序列出全部类别色块与数值梯度范围。

### VCF 导入

**File → Import VCF** 可导入含样本基因型列的 VCF 或 `VCF.GZ`。当前序列工作流面向单个序列区域，因此要求 VCF 仅包含一个 contig，并需要每条记录包含 `GT` 字段。VCF 样本名与其他格式一样进入标准化窗口。

metadata 文件可选：

- **不提供**：metadata 仅从样本 ID 解析。
- **普通 CSV/TSV**：按样本名匹配，填充离散性状（分组）与连续性状。
- **McAN 六列 TSV**（`SampleName AccessionID SamplingDate Country State City`，缺失用 `*`，表头可选）：填充由 Country/State/City 合并的离散性状，且在样本名保持不变时启用 McAN 原生 VCF 分析（`McAN --vcf`），保留真实采样日期用于网络定向。若重命名/删除样本或之后编辑数据表，程序会自动退回 aligned-FASTA → mutation 适配流程。

比对重建：未提供参考 FASTA 时，将每个 VCF 记录转换为等宽变异位点块；提供参考 FASTA 时，校验每条 `REF` 与参考一致并补回不变区域生成全长比对。多等位基因按 GT 编号解析；杂合单碱基位点用 IUPAC 字符，杂合复杂 indel 用 `N`。符号型 ALT、breakend、多 contig 与相互重叠的记录会被明确拒绝。

## metadata 与可视化刷新

单倍型网络的**拓扑**由输入样本与序列决定；metadata 的类型、分组、圆环与颜色只决定已有拓扑**如何显示**。

| 变化 | 操作 |
|---|---|
| 导入新的 FASTA/NEXUS/PHYLIP/VCF | **重新构建**单倍型网络 |
| 修改样本名、序列、参与分析的样本集合 | **重新构建**单倍型网络 |
| 更换网络算法/参数 | **重新构建**单倍型网络 |
| 导入或修改 metadata 值 | 仅点击 **应用可视化配置** |
| 修改性状类型、Group、Visualize 或颜色 | 仅点击 **应用可视化配置** |
| 在 tcsBU 中调整分组名称、颜色或样本所属分组 | 仅更新当前可视化配置 |

轻量刷新只改写 tcsBU 的 `_hapconf.csv`、`_groupconf.csv`、`_traitconf.csv`、内嵌数据的 `.js` 和 `.html`；现有 `.gml`、比对与样本—单倍型映射保持不变（相同序列得到相同的 H1/H2… 标签）。metadata 按样本名匹配；构建后被改名的样本会退回为空 metadata。真正改动了序列/比对时应改用 **Build / Rebuild Haplotype Network** 重建。

## 网络算法与参数

| 算法 | 引擎标识 | 可配置参数 |
|---|---|---|
| Original TCS | `original_tcs` | 线程、模糊位点、合并中间节点 |
| Modified TCS | `modified_tcs` | 线程 |
| Minimum Spanning Network | `msn` | epsilon |
| Median-Joining Network | `mjn` | 线程、epsilon |
| Randomized Minimum Spanning Tree | `rmst` | 精确/随机模式、重复次数、随机种子、是否排除模糊位点 |
| McAN Minimum-cost Arborescence Network | `mcan` | 线程、参考序列、是否排除模糊位点 |

如果输入序列长度不同，完整网络分析会先运行 MAFFT，失败后尝试 MUSCLE；长度相同时视为已比对。

### RMST 内置实现

随包提供的 C++17 `netst-rmst` 可执行文件读取 `project_hap.fasta` 与 `project_seq.meta.csv`，对唯一单倍型计算未校正突变位点数（Hamming 距离）。**精确模式**（默认、推荐）按距离层确定所有至少能出现在一棵最小生成树中的边，结果确定且不受随机种子影响；**随机模式**多次随机化单倍型顺序并运行稳定 Kruskal，输出每条边的出现次数与频率，固定种子在 macOS 与 Windows 上可复现，但有限重复不保证找到全部兼容边。

原生随机模式采用跨平台固定的 SplitMix64 排列流。因此同一 seed 在新的 macOS 与 Windows 二进制间一致，但不承诺与旧 NumPy 随机数流逐边完全相同。

默认排除任何含非 `A/C/G/T/U/-` 字符的比对列，RNA `U` 统一为 `T`，gap 作为可比较状态。过滤后变为相同序列的单倍型会合并为一个节点（记录在 `warnings` 与节点 `haplotypes`）。仅使用 C++ 标准库的原生引擎不会把 NumPy 带入 Python 打包依赖；精确模式 ≤ 1000 个过滤后节点，随机模式 ≤ 500 个节点、≤ 1000 次重复。RMST 的 `project.gml` 与 fastHaN/McAN 使用相同的 tcsBU 方言。参考：Paradis, E. (2018), *Methods Ecol Evol* 9:1308–1317。

### McAN 适配方式

`service/mcan_adapter.py` 支持两条路径。导入 VCF 时附带 McAN 六列 metadata 且样本名未改动，直接调用 `McAN --vcf` 原生路径并保留真实采样日期用于定向；FASTA/PHYLIP 来源、无 metadata 的 VCF 或样本被重命名/编辑时，从比对序列构建 mutation：以所选参考计算逐位点差异，用 `S0000001` 形式的内部别名生成 mutation/metadata，生成显式 site mask，在独立 `project_mcan/` 目录调用 McAN，再转换为 tcsBU 可读 GML 并恢复原始样本名与距离。

内置 McAN 流程将最大序列坐标限制为 30000，因此更长比对会在调用前被拒绝。FASTA 不含采样日期，适配器不虚构时间顺序，得到以参考序列为根的突变包含关系网络。适配器通过 `--help` 自动选择 McAN 1.2 的 `--outDir` 或 McAN 1.4.x 的 `--out`，并兼容旧版 `haplotype_loci.graphml` 与新版 `<prefix>.haplonet.graphml` 输出。程序优先查找平台 `lib` 目录中的 `McAN`/`McAN.exe`；开发环境可用 `NETST_MCAN_EXECUTABLE` 指定自编译程序。参考：Li, L. et al. (2022), bioRxiv 2022.07.23.501111。

## 可视化（tcsBU）

网络在 **Network** 页以增强版 **tcsBU / D3.js** 渲染，嵌入 Qt WebEngine。每个单倍型节点绘制同心圆环（Group 最内层，其他已启用性状向外），按频率缩放大小；**Legend** 按内外顺序列出全部类别色块与数值梯度范围。

工具栏提供 **Save Image**（SVG / PNG / JPG —— SVG 为标准 `image/svg+xml`，PNG/JPG 默认 2 倍分辨率）、缩放、节点/连边编辑、图例开关、单倍型/距离标签，以及 **Edge Weight**（变异距离越小，连边越粗）。

**Advanced** 高级设置对话框**可拖拽标题栏移动**，分为三个区块：

- **Force-Directed Layout Settings**：Link Distance、Link Strength、Friction、Charge、Gravity，以及 Start/Stop。
- **Node and Edge Settings**：**Node Radius**（频率为 1 的节点半径，调整时保留相对大小）、**Node Line Width**（节点描边）、**Edge Line Width**（连边基础线宽）、**Edge Weight Scale**（加权线宽的最大倍率）、Text Offset。
- **Metadata Ring Settings**：**Ring Line Width**（圆环分段描边）、**Base Ring Width**（非 Group 外环在比例 1 时的基础厚度，实际厚度 = 基础宽度 × 环比例）、Outer Ring Ratios（从内到外的逗号分隔比例）。

Data 页的 Sequence 列为只读，避免误编辑序列导致已有比对、单倍型与网络失效；样本名、选择状态与 metadata 性状仍可正常调整。

## 辅助解读分析

该功能根据旧版辅助脚本审阅结果重新实现，不直接包装旧脚本。计算层使用**不可变的对齐序列快照**，与 Qt 界面、文件输出分离，并在后台线程中运行。

| 菜单功能 | 输入与计算 | 主要结果 |
|---|---|---|
| 序列质量与多样性 | 当前选中的等长对齐序列；可选完整删除或成对删除 | 样本/位点缺失率、有效位点、变异位点、简约信息位点、S、Hd、π、θW、分组丰富度与私有单倍型 |
| 遗传距离与 PCoA | 仅 A/C/G/T 作为确定状态；gap、N、? 和 IUPAC 模糊状态成对删除 | p-distance 矩阵、每对有效比较位点、PCoA 坐标、正/负特征值诊断 |
| 网络拓扑指标 | 当前项目 GML，或用户选择的 tcsBU 兼容 GML | 节点/边数、连通分量、密度、环秩、degree、closeness、betweenness、割点与桥 |

**结果可视化。** 辅助解读页把结果组织为**概览 + 图表 + 表格**：彩色 **KPI 卡片**；**PCoA 排序散点图**（按分组着色）与**遗传距离热图**；**分组多样性小多图**、**样本缺失率**条形图与沿比对的**位点变异/缺失轨道图**；**节点度分布**与枢纽节点排名（割点高亮）。有 `PyQt6-WebEngine` 时图表在网页视图中渲染并支持悬停查看，否则回退为静态 SVG。明细表格保留全部精确数值。

关于缺失数据和解释的约定：

- RNA `U` 统一为 `T`；`-`/`N`/`?`/IUPAC 模糊状态不作为确定等位基因。
- 低于最小有效位点或覆盖率的序列对，距离记为缺失，不补 0，也不使用人为饱和常数。
- PCoA 使用经典多维尺度分析，不将距离矩阵直接作为普通特征运行 PCA。
- McAN 有向 GML 的方向作为来源信息保留；中心性、割点和桥指标使用无向投影。
- 拓扑中心、桥接节点和 PCoA 聚集都是探索性描述，不自动等同于祖先、起源地、传播源或真实群体。
- 当前不自动计算 Tajima's D，因为其稳健解释需要人口史、重组、抽样和零模型假设。

界面中的大表格会限制显示行/列数以保持响应速度；完整结果保存为输出目录中的 JSON。

## 数据导出与格式转换

**File → Export Sequence Data** 导出 Data 页中的全部记录：

- **FASTA**：标题使用 `样本名|离散性状|连续性状`，同时保留序列和 metadata；
- **NEXUS、PHYLIP**：仅写出样本名和序列；
- **VCF**：写入序列变异和 `NetSTSampleMetadata` 头，并生成同名 `_metadata.csv`；
- NEXUS、PHYLIP 和 VCF 要求序列已等长；VCF 还要求至少一个变异位点。

**File → Export Metadata** 单独生成 CSV/TSV metadata 表，仅导出 `sample` 与当前 Metadata 页中的性状字段。

**Tools → Sequence Format Conversion** 支持 FASTA、NEXUS、PHYLIP 与 VCF/VCF.GZ 之间的互转。转 VCF 要求序列已等长比对，会将连续变异列合并为合法等位基因块，并为插入/删除增加参考锚点；完全无变异的比对无法生成只含变异记录的 VCF。输入与输出路径必须不同。

## 输出文件

假设项目名称为 `project`，主要输出包括：

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

Alignment 和 Haplotype 页为保持响应速度只渲染前 500 个位点；输出文件始终保留完整序列。

## 项目结构

```text
NetST-py/
├── main_form.py                    # 应用入口、工作流协调、Qt 后台任务
├── requirements.txt                # Python 依赖
├── netst-mac-arm64.spec            # macOS PyInstaller 配置
├── netst-win.spec                  # Windows PyInstaller 配置
├── docs/                           # 中英文使用手册
├── model/
│   ├── alignment_config.py         # MAFFT/MUSCLE 参数与命令行生成
│   ├── taxon_data.py               # 单条序列/分类单元数据模型
│   └── taxon_table_model.py        # Qt 数据表模型
├── service/
│   ├── file_service.py             # FASTA/CSV/编码与标准化
│   ├── format_conversion_service.py# FASTA/PHYLIP/VCF/metadata 转换
│   ├── analysis_service.py         # 比对、单倍型与网络分析流程
│   ├── process_service.py          # 可取消、可超时的外部进程控制
│   ├── validation_service.py       # 分析输入与安全文件名前缀校验
│   ├── mcan_adapter.py             # aligned FASTA ↔ McAN ↔ tcsBU 格式适配
│   ├── rmst_service.py             # 原生 RMST 进程适配与结果模型
│   ├── interpretation_models.py    # 不可变的对齐序列分析快照
│   ├── diversity_analysis_service.py   # QC 与总体/分组多样性
│   ├── distance_analysis_service.py    # 缺失感知 p-distance 与 PCoA
│   ├── topology_analysis_service.py    # GML 解析与拓扑指标
│   ├── interpretation_charts.py    # 辅助解读结果的 SVG 图表渲染
│   └── gen_network_config.py       # tcsBU 配置与 JS 生成
├── ui/
│   ├── main_window_ui.py           # 主窗口布局
│   ├── data_tab_widget.py          # 数据表页
│   ├── metadata_tab_widget.py      # metadata 配置页
│   ├── alignment_tab_widget.py     # 比对结果页
│   ├── haplotype_tab_widget.py     # 单倍型结果页
│   ├── interpretation_tab_widget.py# 结构化辅助分析结果页
│   ├── *_dialog.py                 # 导入、格式转换与分析参数窗口
│   ├── output_panel.py             # 输出目录和日志面板
│   └── language_manager.py         # 中英文文本
├── static/
│   ├── tcsbu/                      # tcsBU、D3.js、CSS 与 HTML
│   ├── docs/                       # NetST 和 tcsBU 帮助文档
│   └── icon/                       # 应用图标
└── lib/                            # 平台相关 MAFFT/MUSCLE/fastHaN/McAN/RMST
```

**分层关系** —— `MainForm` 继承 `MainWindowUI`，负责界面事件与分析流程协调；`model/` 保存与展示样本数据；`service/` 负责文件操作、计算流程与外部程序生命周期；`ui/` 负责窗口、页签与参数收集；tcsBU 作为本地 Web 应用嵌入 `QWebEngineView`。

## 子进程控制

`service/process_service.py` 为 MAFFT、MUSCLE、fastHaN 和 McAN 提供统一执行接口；RMST 适配器也用相同的轮询方式管理原生子进程。两条路径都响应 Qt 线程取消请求；共享执行器还负责持续读取输出、进程组清理和超时控制。

## 打包

```bash
# 先在独立虚拟环境中安装完整构建依赖
python -m pip install -r requirements-build.txt

# macOS Apple Silicon → dist/NetST.app
# Windows x86-64 → dist/NetST/（推荐目录包）
python scripts/build.py

# Windows 可选单文件 → dist/NetST.exe
python scripts/build.py --onefile
```

构建脚本会检查依赖、目标架构、内置二进制和执行权限，并验证打包结构及 QtWebEngine 运行时资源。PyInstaller 必须在目标系统本机构建，不能在 macOS 上生成 Windows 包或反向操作。签名、公证、压缩发布和常见故障见 [跨平台打包指南](docs/PACKAGING.zh-CN.md)。

## 开发说明

- 新增菜单操作：在 `ui/menu_bar.py` 创建 action，在 `MainForm._get_callbacks()` 注册回调。
- 新增分析算法：扩展参数对话框，并在 `AnalysisService` 中实现服务逻辑；不要在 UI 线程中直接执行耗时任务。
- 新增外部程序：统一通过 `ManagedProcessRunner` 调用，以保留取消、超时和进程树清理能力。
- 更新界面文本：同时修改 `ui/language_manager.py` 的中文和英文条目。
- 生成文件统一使用“输出目录 + 项目名称”作为前缀，避免写入源码目录。

## 已知限制

- 仓库尚未提供完整 Linux 发布包。
- 内置外部二进制需分平台验证。Apple Silicon 使用原生 arm64 McAN 1.4.3。McAN 适配器最多接受 30000 个比对位点。
- 原生 RMST 使用稠密两两距离矩阵与完整图；精确模式限制 1000 个过滤后节点，随机模式限制 500 个节点及计算规模。
- VCF 序列转换限定为单 contig、非重叠的小变异记录，不支持结构变异、breakend 或符号型 ALT。
- 完整 GUI 交互、平台打包和真实数据端到端流程需要在目标系统手动验证。
- PCoA 的无第三方依赖求解器默认限于 200 条序列；更大数据集仍输出距离矩阵但跳过 PCoA 并给出警告。
- 当前辅助分析属于描述性/探索性功能；性状显著性、FST/AMOVA、社区稳定性与人口历史零模型未在本阶段实现。
- tcsBU 依赖 Qt WebEngine；缺少 `PyQt6-WebEngine` 时网络页只能使用降级文本组件。

## 引用

若在研究中使用 NetST，请引用：

> Zhang Z, Yu Y. *NetST: An integrated software for large-scale haplotype network construction, visualization, and automated analytics.*

同时请引用所用到的依赖：fastHaN（Chi et al. 2023）、tcsBU（Múrias Dos Santos et al. 2016）、MAFFT（Nakamura et al. 2018）、RMST（Paradis 2018）与 McAN（Li et al. 2022）。完整参考文献见[使用手册](docs/NetST-使用手册.md#16-引用与致谢)。

## License

MIT License
