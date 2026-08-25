# NetST

> [English](README.md) | 中文

**NetST 是一款开源桌面软件，用于以项目为中心开展单倍型网络分析并整合 metadata**。它在同一可复用项目中保存序列、样本—单倍型映射、分类型和数值型 metadata、构网设置、分析结果与可视化状态。NetST 适用于群体遗传学、系统地理学、分子流行病学及其他近缘序列变异研究。

## 主要功能

- 导入 **FASTA、NEXUS、PHYLIP、VCF/VCF.GZ** 以及 CSV/TSV metadata。
- 使用 **MAFFT** 或 **MUSCLE** 比对序列，并将相同的比对序列归并为单倍型。
- 支持六种构网方法：**Original TCS、Modified TCS、MSN、MJN、RMST 和 McAN**。
- 在保持样本—单倍型与 metadata 映射不变的情况下比较不同构网方法。
- 在增强版 **tcsBU** 中，将多个分类型与数值型性状同时显示为节点同心层。
- 计算序列质量/多样性、群体分化、成对 p-distance/PCoA 与网络拓扑描述指标。
- 导出网络、序列、表格、SVG/PNG/JPG/PDF 图片、JSON 报告及可迁移的`<project>.netst.json` 项目记录。
- 提供中英文界面，并可取消耗时任务。

## 下载与运行

已发布的软件包可从[GitHub Releases](https://github.com/plant720/NetST/releases) 页面下载。

| 平台 | 发布目标 | 随包分析工具 |
|---|---|---|
| Windows x86-64 | `NetST\NetST.exe` | MAFFT、MUSCLE、fastHaN、RMST、McAN |
| macOS Apple Silicon | `NetST.app` | MAFFT、MUSCLE、fastHaN、RMST、McAN |

请保持解压后的全部文件位于同一目录。

从源码运行时，请使用 Python 3.10、3.11 或 3.12：

```bash
pip install -r requirements.txt
python main_form.py
```

## 快速开始

1. 选择 **文件 → 导入 FASTA/NEXUS/PHYLIP/VCF**，并在弹窗中标准化样本 ID。
2. 如需独立 metadata 文件，选择 **文件 → 导入 metadata**，映射一个样本名列、分类型性状、数值型性状，以及一个分类型 Group。
3. 在右侧面板设置项目名称与输出目录。
4. 选择 **分析 → 构建 / 重新构建单倍型网络**，再选择方法与参数。
5. 查看 **网络、单倍型、序列比对** 与可选的 **辅助解读** 页。只改变显示性状或颜色时，可在 Metadata 页刷新配置，无需重新构建拓扑。

导入序列后，NetST 会自动维护 `<project>.netst.json`。使用 **文件 → 导出项目配置**保存可迁移副本，或使用 **文件 → 导入并复现项目**校验源文件哈希并恢复已记录的流程与视图。

## 输入与输出

| 类型 | 支持文件或主要结果 |
|---|---|
| 序列输入 | `.fas`、`.fasta`、`.fa`、`.fna`、`.ffn`、`.nex`、`.nexus`、`.nxs`、`.phy`、`.phylip`、`.vcf`、`.vcf.gz` |
| metadata 输入 | `.csv`、`.tsv`、`.txt`；样本名必须与已导入序列名完全一致 |
| 序列与单倍型 | 原始/比对 FASTA、单倍型 FASTA、PHYLIP、样本—单倍型 CSV |
| 网络与可视化 | GML、HTML/JavaScript、tcsBU 配置 CSV、SVG、PNG、JPG、PDF |
| 辅助解读 | `<project>_diversity_analysis.json`、`<project>_distance_analysis.json`、`<project>_topology_analysis.json` |
| 可复用项目 | `<project>.netst.json` 及 `inputs/<role>/` 下的托管输入 |

在同一输出目录中重复使用同一项目名时，后一次运行可能覆盖同名结果。默认输出目录为 `~/HaplotypeOutput`。

## 文档

- 用户手册：[English](docs/NetST-User-Manual.md) ·[中文](docs/NetST-使用手册.md)
- 内嵌 tcsBU 帮助：[HTML](static/tcsbu/help.html) ·[PDF](static/docs/tcsbu.pdf)
- 应用内 NetST 手册：[PDF](static/docs/netst.pdf)

手册详细说明输入校验、算法参数、metadata 映射、输出文件、辅助解读约定、项目复现与已知限制。

## 示例数据

[`examples/`](examples) 目录包含植物、动物和病毒的可运行项目：

| 数据集 | 主要用途 |
|---|---|
| `Bupleurum_chinense` | 未比对的多位点序列，以及分类型和数值型性状 |
| `Rhodiola_bupleuroides` | 较大的已比对质体基因组数据、遗传簇与海拔 |
| `Lepus_europaeus` | 已整理的线粒体单倍型代表及报道的 haplogroup |
| `DP-SARS-CoV-2` | FASTA/PHYLIP/VCF 导入、地理/时间 metadata 与 McAN 输入 |
| `SL-SARS-CoV-2` | 全基因组谱系数据与基于参考序列的 McAN 分析 |

每个示例目录都包含独立 README，说明数据来源与建议流程。

## 引用

当前可暂按以下形式引用配套论文：

> Zhang Z, Song Y, Yu X, Hou J, Yu Y. *NetST: a desktop application for project-based haplotype network analysis with metadata integration.* Manuscript.

同时请按实际使用情况引用 [fastHaN](https://doi.org/10.1111/1755-0998.13829)、 [tcsBU](https://doi.org/10.1093/bioinformatics/btv636)、[MAFFT](https://doi.org/10.1093/bioinformatics/bty121)、[RMST](https://doi.org/10.1111/2041-210X.12969) 和 [McAN](https://doi.org/10.1093/bib/bbad174)。

## 许可与联系

NetST 源代码采用 [MIT License](LICENSE)；随包第三方程序保留各自许可。可通过 [GitHub Issues](https://github.com/plant720/NetST/issues) 报告可复现的软件问题，请勿在公开问题中上传私密或敏感序列数据。其他问题请联系 [yyu@scu.edu.cn](mailto:yyu@scu.edu.cn) 或[zzhen0302@163.com](mailto:zzhen0302@163.com)。
