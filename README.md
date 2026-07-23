# NetST

**Haplotype Network Analysis Tool / 单倍型网络分析工具**

NetST 是一个基于 PyQt6 的桌面科研软件，用于从 DNA/RNA 序列完成多序列比对、单倍型识别、单倍型网络构建与交互式可视化。本项目由旧版 VB.NET 程序重构而来。

NetST is a PyQt6 desktop application for multiple-sequence alignment, haplotype identification, haplotype-network construction, and interactive visualization.

当前界面版本：**2.0.0**

## 功能概览

- 从 File 菜单导入 FASTA、NEXUS、PHYLIP 或 VCF 序列数据。
- 将当前数据导出为 FASTA、NEXUS、PHYLIP、VCF+metadata，或独立导出性状表。
- 导入多样本 VCF 与 McAN metadata，可选参考 FASTA 重建全长序列。
- 在 **Tools** 中运行多序列比对、单倍型计算以及 FASTA、NEXUS、PHYLIP 与 VCF 的格式转换。
- 在导入时清理、替换或拆分 FASTA 标题，并提取样本名和性状。
- 从 CSV 文件导入离散性状与连续性状，支持可视化列映射。
- 在表格中检查、编辑、选择或取消选择参与分析的序列。
- 使用 MAFFT 或 MUSCLE 进行多序列比对。
- 将完全相同的比对序列归并为唯一单倍型。
- 使用 fastHaN 构建 Original TCS、Modified TCS、MSN 或 MJN 网络，使用内置 RMST，或使用 McAN Minimum-cost Arborescence Network。
- 使用内嵌 tcsBU/D3.js 页面交互展示 GML 网络、分组和连续性状。
- 展示比对矩阵、单倍型汇总和样本—单倍型映射。
- 在 **Analysis → 辅助解读** 中报告序列缺失率、变异位点、Hd、π、θW 及分组私有单倍型。
- 使用缺失感知的成对 p-distance 和经典 PCoA 探索序列间结构。
- 从 NetST GML 计算组件、环秩、中心性、割点和桥边，并明确区分拓扑描述与祖先/传播推断。
- 支持中文和英文界面。
- 耗时分析在后台线程运行，可从状态栏取消；超时或取消时会清理外部进程及其子进程。
- 中文/英文切换会同步刷新首页、菜单、页签、数据表头、状态栏、日志提示和结果摘要。
- 精简的学术化 Home 集中展示软件定位、四项核心能力、快速流程、支持算法、输入和输出。
- 分析前检查空名称、空序列、非有限连续性状、重复样本名和不安全的项目名称。

## 分析流程

```text
FASTA / NEXUS / PHYLIP 序列，或 VCF + metadata
  │
  ├─ 标题标准化 / 模糊碱基过滤
  ├─ 可选：导入 CSV 性状
  ▼
MAFFT 或 MUSCLE 多序列比对
  ▼
识别唯一单倍型并生成 PHYLIP/CSV/FASTA 文件
  ▼
fastHaN 构建 TCS / MSN / MJN，内置 RMST，或 McAN 构建有向网络
  ▼
统一转换为 GML 并生成 tcsBU 配置
  ▼
在 Qt WebEngine 中交互可视化
```

## 支持的平台

| 平台 | 源码运行 | 仓库内置分析程序 | PyInstaller 配置 |
|---|---:|---:|---:|
| macOS Apple Silicon | 是 | MAFFT、MUSCLE 3、fastHaN、McAN 1.2 | `netst-mac-arm64.spec` |
| Windows x86-64 | 是 | MAFFT、MUSCLE 3、fastHaN | `netst-win.spec` |
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

主要 Python 依赖：

- `PyQt6`
- `PyQt6-WebEngine`
- `chardet`
- `PyInstaller`（仅构建发布包时需要）

MAFFT、MUSCLE、fastHaN 以及 macOS Apple Silicon 版 McAN 的目标平台二进制已经放在 `lib/` 下。若内置 MAFFT 不可用，程序会尝试调用系统 `PATH` 中的 `mafft`。

## 快速使用

1. 在 **File** 菜单选择 **Import FASTA、Import NEXUS** 或 **Import PHYLIP** 导入原始序列文件。
2. 在标准化窗口预览并配置样本名、离散性状和连续性状的提取规则。
3. 如性状保存在单独表格中，选择 **File → Import Traits from CSV** 并完成列映射。
4. 在 **Data** 页检查数据，勾选需要参与分析的样本。
5. 在右侧填写项目名称并选择输出目录。默认目录是 `~/HaplotypeOutput`。
6. 根据需要选择功能：
   - **Tools → Multiple Sequence Alignment**：仅运行 MAFFT/MUSCLE；
   - **Tools → Calculate Haplotype**：比对并计算单倍型，不构网；
   - **Analysis → Build Haplotype Network**：执行完整网络分析；VCF 来源可由 McAN 原生读取。
7. 在 **Network、Alignment、Haplotype** 页查看结果。
8. 从 **Analysis → 辅助解读** 运行质量/多样性、遗传距离/PCoA 或网络拓扑分析，结果显示在 **辅助解读** 页。
9. 使用 **File → Export Sequence Data** 选择序列格式，或使用 **Export Trait Data** 单独导出性状。

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

导入对话框可以按分隔符和从 0 开始的字段索引提取：

- 样本名称；
- 离散性状，例如种群、地区、宿主；
- 连续性状，例如采样时间、海拔、温度。

连续性状必须是数值。空字符串或 `0` 被视为没有有效连续性状。包含 `RYSWKMBDHVN` 模糊碱基的序列可在导入时选择过滤。
FASTA 标题中的空白会规范化为下划线，以避免 PHYLIP 和 fastHaN 将一个名称误拆成多个字段。

### NEXUS 与 PHYLIP

- **File → Import NEXUS** 支持 `DATA` 或 `CHARACTERS` 块中的 DNA/RNA `MATRIX`，可读取顺序矩阵、带名称的交错矩阵、无名称的交错续行、引号包裹的样本名、嵌套注释和 `MATCHCHAR`。
- **File → Import PHYLIP** 支持顺序及常见交错 PHYLIP；文件首行声明的序列数和比对长度必须与实际数据一致。
- 两种格式导入后均进入与 FASTA 相同的名称标准化窗口，并作为当前原始数据载入 Data 页。导入失败不会覆盖表格中已有的数据。

### CSV 性状表

CSV 第一行为表头，至少需要一列能与已导入的序列名称一一对应。例如：

```csv
sample,population,value
sample_01,population_A,12.5
sample_02,population_B,13.1
```

导入时可以分别映射样本名、离散性状和连续性状列。软件会检查 FASTA 与 CSV 的样本名是否完整匹配，并拒绝 CSV 或数据表中的重复名称，避免性状被静默覆盖或错配。

### VCF 与 metadata

选择 **File → Import VCF and Metadata** 可导入含样本基因型列的 VCF 或 `VCF.GZ`。当前序列工作流面向单个序列区域，因此格式转换要求 VCF 仅包含一个 contig，并需要每条记录包含 `GT` 字段。

metadata 推荐使用 McAN 六列、制表符分隔格式：

```text
SampleName  AccessionID  SamplingDate  Country  State  City
strain_1    ACC001       2024-01-01    China    Yunnan *
strain_2    ACC002       2024-02-03    China    Sichuan Chengdu
```

表头可选；无表头时固定按上述六列读取，缺失值使用 `*`。VCF 样本名可与 SampleName 或 AccessionID 匹配。导入时 Country、State 和 City 会合并为离散性状。

- 未提供参考 FASTA：将每个 VCF 记录转换为等宽的变异位点块，生成“仅变异位点比对”。
- 提供参考 FASTA：验证每条 VCF `REF` 与参考序列一致，补回不变区域并生成全长比对。
- 多等位基因按 GT 等位基因编号解析；杂合单碱基位点使用 IUPAC 字符，杂合复杂 indel 使用 `N`。
- 符号型 ALT、breakend、多 contig 和相互重叠的 VCF 记录会被明确拒绝，避免生成含义不确定的序列。

若 VCF 和六列 metadata 导入后样本名与序列没有被修改，选择 McAN 时会直接生成样本子集 VCF/metadata 并调用 `McAN --vcf`，从而保留真实采样日期用于网络定向。若数据表已修改，程序会自动退回 aligned-FASTA → mutation 适配流程。

### 数据导出

**File → Export Sequence Data** 导出 Data 页中的全部记录：

- FASTA：标题使用 `样本名|离散性状|连续性状`，用于同时保留序列和性状；
- NEXUS、PHYLIP：仅写出样本名和序列，不把性状混入序列标识；
- VCF：写入序列变异和 `NetSTSampleMetadata` 头，同时生成同名的 `_metadata.csv`，保留离散性状、连续性状、数量和物种字段；
- NEXUS、PHYLIP 和 VCF 要求序列已经等长；VCF 还要求至少存在一个变异位点。

**File → Export Trait Data** 可独立生成 CSV 性状表，字段为 `sample`、`discrete_trait`、`continuous_trait`、`quantity` 和 `organism`。

### 格式转换工具

选择 **Tools → Sequence Format Conversion**，支持：

| 输入 | 可转换输出 | 说明 |
|---|---|---|
| FASTA | NEXUS、PHYLIP、VCF | 输出 NEXUS/PHYLIP 要求序列等长；输出 VCF 可指定参考样本 |
| NEXUS | FASTA、PHYLIP、VCF | 读取 DATA/CHARACTERS 矩阵；支持顺序、交错和 MATCHCHAR |
| PHYLIP | FASTA、NEXUS、VCF | 读取顺序或常见交错 PHYLIP，要求声明数量和长度正确 |
| VCF / VCF.GZ | FASTA、NEXUS、PHYLIP | 参考 FASTA 可选；未提供时输出变异位点比对 |

FASTA/NEXUS/PHYLIP 转 VCF 要求序列已经等长比对，会将连续变异列合并为合法等位基因块，并为插入/删除增加参考锚点。NEXUS 输出会保留带空格或引号的样本名，并根据序列字符声明 DNA 或 RNA。完全无变异的比对无法生成只含变异记录的 VCF。输入与输出路径必须不同。

## 辅助解读分析

该功能根据旧版辅助脚本审阅结果重新实现，不直接包装旧脚本。计算层使用不可变的对齐序列快照，与 Qt 界面、文件输出分离，并在后台线程中运行。

| 菜单功能 | 输入与计算 | 主要结果 |
|---|---|---|
| 序列质量与多样性 | 当前选中的等长对齐序列；可选完整删除或成对删除 | 样本/位点缺失率、有效位点、变异位点、简约信息位点、S、Hd、π、θW、分组丰富度与私有单倍型 |
| 遗传距离与 PCoA | 仅 A/C/G/T 作为确定状态；gap、N、? 和 IUPAC 模糊状态成对删除 | p-distance 矩阵、每对有效比较位点、PCoA 坐标、正/负特征值诊断 |
| 网络拓扑指标 | 当前项目 GML，或用户选择的 tcsBU 兼容 GML | 节点/边数、连通分量、密度、环秩、degree、closeness、betweenness、割点和桥 |

关于缺失数据和解释的约定：

- RNA `U` 在内部统一为 `T`；`-`/`N`/`?`/IUPAC 模糊状态不作为确定等位基因。
- 低于最小有效位点或覆盖率的序列对距离记为缺失，不补成 0，也不使用人为饱和常数。
- PCoA 使用经典多维尺度分析，不将距离矩阵直接作为普通特征运行 PCA。
- McAN 有向 GML 的方向作为来源信息保留；当前中心性、割点和桥指标使用无向投影。
- 拓扑中心、桥接节点和 PCoA 聚集都是探索性描述，不自动等同于祖先、起源地、传播源或真实群体。
- 当前不自动计算 Tajima's D，因为其稳健解释需要人口史、重组、抽样和零模型假设。

界面中的大表格会限制显示行/列数以保持响应速度；完整结果保存为输出目录中的 JSON。

## 网络算法与参数

| 算法 | 引擎标识 | 可配置参数 |
|---|---|---|
| Original TCS | `original_tcs` | 线程、模糊位点、合并中间节点 |
| Modified TCS | `modified_tcs` | 线程 |
| Minimum Spanning Network | `msn` | epsilon |
| Median-Joining Network | `mjn` | 线程、epsilon |
| Randomized Minimum Spanning Tree | `rmst` | 精确/随机模式、重复次数、随机种子、是否排除模糊位点 |
| McAN Minimum-cost Arborescence Network | `mcan` | 线程、参考序列、是否排除模糊位点 |

如果输入序列长度不同，完整网络分析会先运行 MAFFT，失败后尝试 MUSCLE。长度相同时视为已经比对并直接进入单倍型处理。

### RMST 内置实现

RMST 直接读取 NetST 生成的 `project_hap.fasta` 与 `project_seq.meta.csv`，对唯一单倍型计算未校正突变位点数（Hamming 距离），无需额外可执行程序。界面提供两种模式：

- **精确模式（默认、推荐）**：按距离层确定所有至少能出现在一棵最小生成树中的边；结果确定且不受随机种子影响。
- **随机模式**：多次随机化单倍型顺序并运行稳定 Kruskal；输出每条边出现的次数与频率。固定随机种子可复现结果，但有限重复次数不保证找到全部兼容边。

默认排除任何含非 `A/C/G/T/U/-` 字符的比对列，RNA `U` 统一为 `T`，gap 作为一个可比较状态。若过滤后原本不同的单倍型变为相同序列，RMST 会将它们及其样本成员合并为一个网络节点，并在 JSON 的 `warnings` 和节点 `haplotypes` 字段中记录。若排除后没有可用位点，分析会明确失败，不把缺失距离补为零。

RMST 输出的 `project.gml` 与 fastHaN/McAN 使用相同的 tcsBU 方言，可直接进入现有分组、连续性状和交互网络展示；主干边和替代边在 GML 中共同显示，类型及随机抽样统计保存在 `project_rmst.json` 与 `project_rmst.tsv`。为避免纯 Python 完全图造成界面长期占用，精确模式最多接受 1000 个过滤后节点，随机模式最多 500 个节点、1000 次重复，并限制总边评估规模；计算期间支持状态栏取消。

本模块依据公开算法描述独立实现，提供的 `rsmt_port` 仅作为行为规范与 golden tests 使用，没有逐行复制 pegas/R/C 或该端口实现。算法参考：Paradis, E. “Analysis of haplotype networks: The randomized minimum spanning tree method.” *Methods in Ecology and Evolution* (2018): 1308–1317。

### McAN Minimum-cost Arborescence Network 适配方式

McAN 1.2 原生接收 VCF 或 mutation、metadata 和 site mask，并输出 GraphML/JSON。`service/mcan_adapter.py` 支持两条路径：原始 VCF 数据保持不变时直接调用 `--vcf`；FASTA/PHYLIP 来源或数据被编辑时完成以下适配：

1. 读取已比对 FASTA，并以用户选择的参考序列计算逐位点差异；
2. 使用 `S0000001` 形式的内部别名生成 mutation/metadata，避免 McAN 未转义样本名导致 GraphML 损坏；
3. 生成显式 site mask；可选排除包含非 A/C/G/T/U/缺口字符的列；
4. 在独立的 `project_mcan/` 目录调用 McAN，保留原始 GraphML 和 JSON；
5. 将 GraphML 转换为 tcsBU 可读取的 GML，并恢复原始样本名和网络距离。

McAN 1.2 源码内部固定最大序列坐标为 30000，因此 NetST 会在调用前拒绝更长的比对并给出明确错误。FASTA 不包含采样日期，适配器不会虚构时间顺序，而是为所有内部记录使用同一中性日期；由此得到的是以所选参考序列为根的突变包含关系网络。如研究需要时间定向，应扩展数据模型并提供真实采样日期。

程序优先查找当前平台 `lib` 目录中的 `McAN`/`McAN.exe`。开发环境也可通过环境变量指定自编译程序：

```bash
export NETST_MCAN_EXECUTABLE=/absolute/path/to/McAN
python main_form.py
```

Windows 发布包目前未附带 McAN；请在 Windows 上编译后放置为 `lib/win/McAN.exe`。McAN 及其 cJSON/hashmap 依赖的许可声明随目标平台二进制一并保留。

算法引用：Li, L. et al. *McAN: an ultrafast haplotype network construction algorithm*. bioRxiv 2022.07.23.501111 (2022), doi:10.1101/2022.07.23.501111。

## 输出文件

假设项目名称为 `project`，主要输出包括：

| 文件 | 内容 |
|---|---|
| `project.fasta` | 本次分析的原始输入序列 |
| `project_aln.fasta` | 比对后的序列 |
| `project_seq.fasta` | 带原始样本名的分析序列 |
| `project_seq.phy` | fastHaN 使用的 PHYLIP 输入 |
| `project_hap.fasta` | 去冗余的 H1、H2…单倍型序列 |
| `project_seq.meta.csv` | 样本、单倍型和性状映射 |
| `project_hap_trait.csv` | 单倍型数量、成员及成员性状汇总；同一单倍型内不同的连续性状值以分号保留 |
| `project_seq_trait.csv` | 逐样本性状表 |
| `project_traitconf.csv` | 连续性状配置；仅有有效值时生成 |
| `project.gml` | fastHaN、RMST，或由 McAN GraphML 转换后的 tcsBU 网络图 |
| `project_rmst.json` | RMST 参数、保留/排除位点、节点合并、边类型和随机抽样统计；仅 RMST 生成 |
| `project_rmst.tsv` | RMST 边表，含距离、主干/替代类型、计数与频率；仅 RMST 生成 |
| `project_mcan/` | McAN 输入、样本别名映射及原始 GraphML/JSON；仅 McAN 分析生成 |
| `project_hapconf.csv` | tcsBU 单倍型配置 |
| `project_groupconf.csv` | tcsBU 分组及颜色配置 |
| `project.js` / `project.html` | 本地交互可视化资源 |
| `project_diversity_analysis.json` | 序列 QC、总体/分组多样性及计算警告 |
| `project_distance_analysis.json` | p-distance、有效比较位点、PCoA 特征值与坐标 |
| `project_topology_analysis.json` | 网络概况、节点/边拓扑指标及方向来源信息 |

Alignment 和 Haplotype 页为保持响应速度，只渲染前 500 个位点；输出文件始终保留完整序列。

## 项目结构

```text
NetST-py/
├── main_form.py                 # 应用入口、工作流协调、Qt 后台任务
├── requirements.txt            # Python 依赖
├── netst-mac-arm64.spec         # macOS PyInstaller 配置
├── netst-win.spec               # Windows PyInstaller 配置
├── model/
│   ├── alignment_config.py      # MAFFT/MUSCLE 参数与命令行生成
│   ├── taxon_data.py            # 单条序列/分类单元数据模型
│   └── taxon_table_model.py     # Qt 数据表模型
├── service/
│   ├── file_service.py          # FASTA/CSV/编码与标准化
│   ├── format_conversion_service.py # FASTA/PHYLIP/VCF/metadata 转换
│   ├── analysis_service.py      # 比对、单倍型与网络分析流程
│   ├── process_service.py       # 可取消、可超时的外部进程控制
│   ├── validation_service.py    # 分析输入和安全文件名前缀校验
│   ├── mcan_adapter.py          # aligned FASTA ↔ McAN ↔ tcsBU 格式适配
│   ├── rmst_service.py          # 内置 RMST、距离计算与 GML/JSON/TSV 输出
│   ├── interpretation_models.py # 不可变的对齐序列分析快照
│   ├── diversity_analysis_service.py # QC 与总体/分组多样性
│   ├── distance_analysis_service.py  # 缺失感知 p-distance 与 PCoA
│   ├── topology_analysis_service.py  # GML 解析与拓扑指标
│   └── gen_network_config.py    # tcsBU 配置与 JS 生成
├── ui/
│   ├── main_window_ui.py        # 主窗口布局
│   ├── data_tab_widget.py       # 数据表页
│   ├── alignment_tab_widget.py  # 比对结果页
│   ├── haplotype_tab_widget.py  # 单倍型结果页
│   ├── vcf_import_dialog.py     # VCF + metadata 导入
│   ├── format_conversion_dialog.py # 通用格式转换界面
│   ├── interpretation_options_dialog.py # 缺失/覆盖率参数
│   ├── interpretation_tab_widget.py # 结构化辅助分析结果页
│   ├── *_dialog.py              # 标准化、性状导入和分析参数窗口
│   ├── output_panel.py          # 输出目录和日志面板
│   └── language_manager.py      # 中英文文本
├── static/
│   ├── tcsbu/                   # tcsBU、D3.js、CSS 与 HTML
│   ├── docs/                    # NetST 和 tcsBU 帮助文档
│   └── icon/                    # 应用图标
├── lib/                         # 平台相关 MAFFT/MUSCLE/fastHaN/McAN
└── tests/                       # 标准库 unittest 测试
```

### 分层关系

- `MainForm` 继承 `MainWindowUI`，负责界面事件与分析流程协调。
- `model/` 保存与展示样本数据，不执行分析。
- `service/` 负责文件操作、计算流程和外部程序生命周期。
- `ui/` 负责窗口、页签和参数收集。
- tcsBU 作为本地 Web 应用嵌入 `QWebEngineView`。

## 子进程控制

`service/process_service.py` 为 MAFFT、MUSCLE、fastHaN 和 McAN 提供统一执行接口：

- 使用 `Popen` 周期性检查 Qt 线程的中断请求；
- 持续读取 stdout/stderr，避免大量输出造成管道死锁；
- 对每个工具创建独立进程组；
- POSIX 上向整个进程组发送 `SIGTERM`，宽限期后发送 `SIGKILL`；
- Windows 上使用 `taskkill /T /F` 清理进程树；
- 区分正常失败、600 秒超时和用户主动取消；
- 取消后的部分比对或单倍型文件仍可在适用时加载。

## 测试

进程控制测试只依赖 Python 标准库：

```bash
python -m unittest discover -s tests -v
```

在无显示器的 macOS/Linux 测试环境中，可在命令前设置 `QT_QPA_PLATFORM=offscreen`。

当前测试覆盖：FASTA/PHYLIP/VCF 双向转换、VCF indel 锚定、参考 REF 校验、metadata 映射、比对参数与 FASTA 强制输出、双语资源完整性、可视化 JavaScript 转义、tcsBU 配置规范化、RMST 精确/随机算法、论文最小示例、模糊位点合并、审计输出与 AnalysisService/tcsBU 兼容、McAN 原生 VCF 及 mutation 输入适配、GraphML 转换、长度边界、进程超时/取消/后代清理、样本与项目名称校验，以及多样性公式/缺失策略、p-distance/PCoA 不变量、GML 拓扑边界情况和辅助结果页。

完整模块语法检查：

```bash
python -m compileall -q main_form.py model service ui tests
```

运行 GUI 或涉及 `AnalysisService` 的测试前，需要先安装 `requirements.txt`。

## 打包

### macOS Apple Silicon

```bash
pyinstaller netst-mac-arm64.spec --noconfirm
```

输出位于 `dist/NetST.app`。

### Windows

```powershell
pyinstaller netst-win.spec --noconfirm
```

输出为单文件 `dist/NetST.exe`。

打包前应在目标操作系统上验证内置二进制的架构、执行权限以及 Qt WebEngine 运行时资源。

## 开发说明

- 单倍型网络辅助分析的旧脚本审阅、方法学风险及分阶段开发建议见 [`docs/HAPLOTYPE_NETWORK_AUXILIARY_ANALYSIS_REVIEW.md`](docs/HAPLOTYPE_NETWORK_AUXILIARY_ANALYSIS_REVIEW.md)。
- 新增菜单操作：在 `ui/menu_bar.py` 创建 action，在 `MainForm._get_callbacks()` 注册回调。
- 新增分析算法：扩展参数对话框，并在 `AnalysisService` 中实现服务逻辑；不要在 UI 线程中直接执行耗时任务。
- 新增外部程序：统一通过 `ManagedProcessRunner` 调用，以保留取消、超时和进程树清理能力。
- 更新界面文本：同时修改 `ui/language_manager.py` 的中文和英文条目。
- 生成文件统一使用“输出目录 + 项目名称”作为前缀，避免写入源码目录。

## 已知限制

- 仓库尚未提供完整 Linux 发布包。
- 内置外部二进制需要分别在目标平台构建和验证，不能跨架构使用。
- McAN 1.2 最多处理 30000 个比对位点；Windows 与 Linux 版本需在对应平台单独编译和放置。
- 内置 RMST 使用稠密两两距离和完整图；精确模式限制 1000 个过滤后节点，随机模式限制 500 个节点及计算规模。更大数据集建议后续接入 C++ 后端。
- VCF 序列转换当前限定为单 contig、非重叠的小变异记录，不支持结构变异、breakend 或符号型 ALT。
- 自动化测试已覆盖核心纯逻辑，但完整 GUI 交互、平台打包和真实数据端到端生物信息学流程仍需在目标系统继续验证。
- PCoA 的无第三方依赖求解器默认限于 200 条序列；更大数据集仍输出距离矩阵，但跳过 PCoA 并给出警告。
- 当前辅助分析属于描述性/探索性功能；性状显著性、FST/AMOVA、社区稳定性与人口历史零模型未在本阶段实现。
- tcsBU 依赖 Qt WebEngine；缺少 `PyQt6-WebEngine` 时网络页只能使用降级文本组件。

## License

MIT License
