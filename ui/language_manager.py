"""
Language Resource Manager Module

This module manages multilingual text resources for the application,
supporting Chinese and English switching.
"""


class LanguageManager:
    """
    Language Resource Manager Class
    
    Singleton pattern, manages Chinese and English versions of all UI texts.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._current_language = 'en'

        self._resources = {
            # Window Title
            'window_title': {
                'cn': '单倍型网络分析工具',
                'en': 'Haplotype Network Analysis Tool'
            },

            # File Menu
            'menu_file': {'cn': '文件', 'en': 'File'},
            'menu_import_project': {
                'cn': '导入并复现项目...', 'en': 'Import and Replay Project...'},
            'menu_export_project': {
                'cn': '导出项目配置...', 'en': 'Export Project Configuration...'},
            'menu_load_sequence': {'cn': '导入 FASTA...', 'en': 'Import FASTA...'},
            'menu_load_nexus': {'cn': '导入 NEXUS...', 'en': 'Import NEXUS...'},
            'menu_load_phylip': {'cn': '导入 PHYLIP...', 'en': 'Import PHYLIP...'},
            'menu_load_vcf': {'cn': '导入 VCF...', 'en': 'Import VCF...'},
            'menu_load_csv_traits': {'cn': '导入 metadata...', 'en': 'Load Metadata...'},
            'menu_export_sequence': {'cn': '导出序列数据...', 'en': 'Export Sequence Data...'},
            'menu_export_traits': {'cn': '导出 metadata...', 'en': 'Export Metadata...'},
            'menu_exit': {'cn': '退出', 'en': 'Exit'},
            'dlg_import_project': {
                'cn': '导入 NetST 项目', 'en': 'Import NetST Project'},
            'dlg_export_project': {
                'cn': '导出 NetST 项目', 'en': 'Export NetST Project'},
            'dlg_relocate_project_source': {
                'cn': '重新定位项目源文件：{role}',
                'en': 'Locate project source: {role}'},
            'filter_netst_project': {
                'cn': 'NetST 项目文件 (*.netst.json);;JSON 文件 (*.json)',
                'en': 'NetST Project Files (*.netst.json);;JSON Files (*.json)'},
            'msg_no_project_to_export': {
                'cn': '请先导入序列数据，再导出项目。',
                'en': 'Import sequence data before exporting a project.'},
            'log_project_exported': {
                'cn': '项目配置已导出至：{path}',
                'en': 'Project configuration exported to: {path}'},
            'log_project_import_failed': {
                'cn': '项目导入失败：{error}',
                'en': 'Project import failed: {error}'},
            'log_project_replay_complete': {
                'cn': '项目复现完成。', 'en': 'Project replay completed.'},

            # Metadata Import Dialog (CSV / TSV)
            'dlg_csv_title': {'cn': '从文件导入 metadata', 'en': 'Import Metadata from File'},
            'dlg_csv_mapping': {'cn': '列映射', 'en': 'Column Mapping'},
            'dlg_csv_seq_name': {'cn': '序列名称列:', 'en': 'Sequence Name Column:'},
            'dlg_csv_discrete': {'cn': '分类型性状（分组）列:', 'en': 'Categorical Trait (group) Column:'},
            'dlg_csv_continuous': {'cn': '数值型性状列:', 'en': 'Numeric Trait Column:'},
            'dlg_csv_preview': {'cn': '数据预览（前几行）', 'en': 'Data Preview (first rows)'},
            'option_none': {'cn': '-- 无 --', 'en': '-- None --'},
            'dlg_csv_hint': {
                'cn': '为每一列指定角色。必须且仅有一列为样本名，且至少一个分类型性状（作为分组）。',
                'en': 'Tag each column. Exactly one Sample Name and at least one Categorical '
                      'trait (the group) are required.'},
            'dlg_csv_col_header': {'cn': '列', 'en': 'Column'},
            'dlg_csv_col_role': {'cn': '角色', 'en': 'Role'},
            'dlg_csv_col_trait': {'cn': '性状名称', 'en': 'Trait name'},
            'dlg_csv_col_conversion': {
                'cn': '连续型转换', 'en': 'Continuous conversion'},
            'dlg_csv_group': {'cn': '分组（内环）性状:', 'en': 'Group (inner ring) trait:'},
            'role_ignore': {'cn': '忽略', 'en': 'Ignore'},
            'role_name': {'cn': '样本名', 'en': 'Sample Name'},
            'role_discrete': {'cn': '分类型数据', 'en': 'Categorical'},
            'role_continuous': {'cn': '数值型数据', 'en': 'Numeric'},
            'msg_csv_need_one_name': {'cn': '请且仅选择一列作为样本名。',
                                      'en': 'Select exactly one Sample Name column.'},
            'msg_csv_trait_name_empty': {'cn': '每个性状列都需要一个名称。', 'en': 'Every trait column needs a name.'},
            'msg_csv_trait_name_dup': {'cn': '性状名称必须唯一：{name}', 'en': 'Trait names must be unique: {name}'},
            'msg_csv_need_discrete': {
                'cn': '至少需要一个分类型性状作为分组。',
                'en': 'At least one Categorical trait is required to serve as the group.'},
            # Continuous metadata conversion
            'dlg_transform_title': {
                'cn': '转换连续型性状：{name}',
                'en': 'Convert Continuous Trait: {name}'},
            'transform_hint': {
                'cn': '选择如何把原始文本转换为数值。空单元格保持为空，源文件不会被修改。',
                'en': 'Choose how source text is converted to numbers. Blank cells remain '
                      'blank; the source file is not modified.'},
            'transform_options': {'cn': '转换规则', 'en': 'Conversion rule'},
            'transform_mode': {'cn': '输入类型:', 'en': 'Input type:'},
            'transform_number': {'cn': '普通数值', 'en': 'Plain number'},
            'transform_date': {'cn': '日期 / 时间', 'en': 'Date / time'},
            'transform_measurement': {
                'cn': '带单位测量值', 'en': 'Measurement with unit'},
            'transform_date_unit': {'cn': '输出时间单位:', 'en': 'Output time unit:'},
            'transform_start_date': {'cn': '起始日期:', 'en': 'Start date:'},
            'transform_start_auto': {
                'cn': '留空 = 本列最早的有效日期',
                'en': 'Blank = earliest valid date'},
            'transform_quantity': {'cn': '测量类型:', 'en': 'Measurement type:'},
            'transform_target_unit': {'cn': '输出单位:', 'en': 'Output unit:'},
            'transform_bare_unit': {
                'cn': '无后缀数值采用的单位:',
                'en': 'Unit for values without a suffix:'},
            'transform_length': {'cn': '长度', 'en': 'Length'},
            'transform_mass': {'cn': '质量', 'en': 'Mass'},
            'transform_temperature': {'cn': '温度', 'en': 'Temperature'},
            'transform_days': {'cn': '天', 'en': 'Days'},
            'transform_months': {'cn': '月', 'en': 'Months'},
            'transform_years': {'cn': '年', 'en': 'Years'},
            'transform_earliest': {'cn': '最早日期', 'en': 'earliest date'},
            'transform_summary_number': {'cn': '普通数值', 'en': 'Plain number'},
            'transform_summary_date': {
                'cn': '日期 → {unit}（{origin}）',
                'en': 'Date → {unit} ({origin})'},
            'transform_summary_measurement': {
                'cn': '{quantity} → {unit}',
                'en': '{quantity} → {unit}'},
            'transform_preview': {'cn': '转换预览', 'en': 'Conversion Preview'},
            'transform_preview_input': {'cn': '原始值', 'en': 'Source value'},
            'transform_preview_output': {'cn': '转换后数值', 'en': 'Converted number'},
            'msg_transform_invalid': {
                'cn': '无法转换该列：{error}',
                'en': 'Cannot convert this column: {error}'},
            'msg_transform_valid': {
                'cn': '可转换 {count} 个非空值。',
                'en': '{count} non-empty values can be converted.'},
            'msg_csv_transform_invalid': {
                'cn': '性状“{name}”无法转换：{error}',
                'en': 'Trait {name!r} cannot be converted: {error}'},
            # Metadata tab
            'tab_metadata': {'cn': 'Metadata', 'en': 'Metadata'},
            'metadata_tab_hint': {
                'cn': '样本名、序列或网络拓扑变化时需要重新构建单倍型网络；性状类型、分组、是否显示和颜色变化只更新网络可视化配置。',
                'en': 'Sample-name, sequence, or topology changes require rebuilding the '
                      'haplotype network. Trait type, group, visibility, and colour '
                      'changes only refresh its visualization configuration.'},
            'btn_apply_metadata': {
                'cn': '应用可视化配置',
                'en': 'Apply Visualization Config'},
            'btn_reset': {'cn': '重置', 'en': 'Reset'},
            'metadata_col_trait': {'cn': '性状', 'en': 'Trait'},
            'metadata_col_type': {'cn': '类型', 'en': 'Type'},
            'metadata_col_group': {'cn': '分组', 'en': 'Group'},
            'metadata_col_visualize': {'cn': '可视化', 'en': 'Visualize'},
            'metadata_col_colors': {'cn': '颜色', 'en': 'Colours'},
            'metadata_edit_colors': {'cn': '编辑…', 'en': 'Edit…'},
            'metadata_gradient_low': {'cn': '低值颜色', 'en': 'Low value'},
            'metadata_gradient_high': {'cn': '高值颜色', 'en': 'High value'},
            'dlg_gradient_title': {
                'cn': '数值型性状渐变颜色', 'en': 'Numeric Trait Gradient'},
            'msg_metadata_keep_discrete': {
                'cn': '必须至少保留一个分类型性状作为分组。',
                'en': 'At least one categorical trait is required as the group.'},
            'msg_invalid_hex_color': {
                'cn': '请输入有效的十六进制颜色，例如 #3B82F6。',
                'en': 'Enter a valid hexadecimal colour such as #3B82F6.'},
            'dlg_colors_title': {'cn': '类别颜色', 'en': 'Category Colours'},
            'dlg_colors_pick': {'cn': '选择颜色', 'en': 'Pick a colour'},
            'label_group_trait': {'cn': '按性状分组:', 'en': 'Group samples by:'},

            # Analysis Menu
            'menu_analysis': {'cn': '分析', 'en': 'Analysis'},
            'menu_build_haplotype_network': {
                'cn': '构建 / 重新构建单倍型网络...',
                'en': 'Build / Rebuild Haplotype Network...'},
            'menu_mafft_auto': {'cn': 'Auto (自动选择)', 'en': 'Auto (Automatic)'},
            'menu_mafft_fftns1': {'cn': 'FFT-NS-1 (极快但粗糙)', 'en': 'FFT-NS-1 (Very Fast)'},
            'menu_mafft_fftns2': {'cn': 'FFT-NS-2 (快速)', 'en': 'FFT-NS-2 (Fast)'},
            'menu_mafft_ginsi': {'cn': 'G-INS-i (全局比对-慢)', 'en': 'G-INS-i (Global-Slow)'},
            'menu_mafft_linsi': {'cn': 'L-INS-i (局部比对-最精确)', 'en': 'L-INS-i (Local-Accurate)'},
            'menu_mafft_einsi': {'cn': 'E-INS-i (含长非比对区域)', 'en': 'E-INS-i (Long Indel)'},
            'menu_interpretation_analysis': {
                'cn': '辅助解读', 'en': 'Interpretation Analysis'},
            'menu_diversity_qc': {
                'cn': '序列质量与多样性...', 'en': 'Sequence Quality and Diversity...'},
            'menu_distance_pcoa': {
                'cn': '遗传距离与 PCoA...', 'en': 'Genetic Distance and PCoA...'},
            'menu_topology_metrics': {
                'cn': '网络拓扑指标...', 'en': 'Network Topology Metrics...'},

            # Multiple Sequence Alignment dialog
            'dlg_msa_title': {'cn': '多序列比对', 'en': 'Multiple Sequence Alignment'},
            'dlg_interpretation_options': {
                'cn': '辅助分析选项', 'en': 'Interpretation Analysis Options'},
            'label_missing_policy': {
                'cn': '缺失数据策略:', 'en': 'Missing-data policy:'},
            'label_permutation_count': {
                'cn': '置换次数:', 'en': 'Permutations:'},
            'permutation_count_tip': {
                'cn': '用于总体 FST 与 AMOVA 显著性检验；设为 0 则不计算 P 值。',
                'en': 'Permutations for global FST and AMOVA; 0 disables P values.'},
            'option_complete_deletion': {
                'cn': '完整删除（仅所有样本均有效的位点）',
                'en': 'Complete deletion (sites called in every sample)'},
            'option_pairwise_deletion': {
                'cn': '成对删除（每个序列对使用自身有效位点）',
                'en': 'Pairwise deletion (pair-specific callable sites)'},
            'label_minimum_comparable_sites': {
                'cn': '最少可比较位点:', 'en': 'Minimum comparable sites:'},
            'label_minimum_coverage': {
                'cn': '最低可比较覆盖率:', 'en': 'Minimum comparable coverage:'},
            'interpretation_options_note': {
                'cn': '缺口、N、? 及 IUPAC 模糊碱基均按不可调用状态处理；结果会报告实际有效位点。',
                'en': 'Gaps, N, ?, and IUPAC ambiguity codes are non-callable; effective sites are reported explicitly.'},
            'dlg_msa_select': {'cn': '算法:', 'en': 'Algorithm:'},
            'dlg_msa_parameters': {'cn': '参数设置', 'en': 'Parameters'},
            'dlg_msa_options': {'cn': '选项', 'en': 'Options'},

            # MAFFT tab
            'dlg_msa_mafft_algorithm': {'cn': '比对算法', 'en': 'Algorithm'},
            'dlg_msa_mafft_op': {'cn': '空位开启罚分 (--op):', 'en': 'Gap Open Penalty (--op):'},
            'dlg_msa_mafft_op_tip': {'cn': '空位开启罚分（默认: 1.53）', 'en': 'Gap opening penalty (default: 1.53)'},
            'dlg_msa_mafft_ep': {'cn': '偏移量 (--ep):', 'en': 'Offset (--ep):'},
            'dlg_msa_mafft_ep_tip': {'cn': '偏移量（类似空位延伸罚分，默认: 0.0）',
                                     'en': 'Offset (works like gap extension penalty, default: 0.0)'},
            'dlg_msa_mafft_maxiterate': {'cn': '最大迭代次数 (--maxiterate):', 'en': 'Max Iterations (--maxiterate):'},
            'dlg_msa_mafft_maxiterate_tip': {'cn': '最大迭代精化次数（0 = 使用算法默认值）',
                                             'en': 'Maximum iterative refinement cycles (0 = algorithm default)'},
            'dlg_msa_mafft_maxiterate_preset_tip': {'cn': '此算法预设已固定为 1000 次',
                                                    'en': 'Fixed at 1000 for this algorithm preset'},
            'dlg_msa_mafft_thread': {'cn': '线程数 (--thread):', 'en': 'Threads (--thread):'},
            'dlg_msa_mafft_thread_tip': {'cn': '线程数（-1 = 自动检测，默认: -1）',
                                         'en': 'Number of threads (-1 = auto-detect, default: -1)'},
            'dlg_msa_mafft_clustalout': {'cn': 'Clustal 输出格式 (--clustalout)',
                                         'en': 'Clustal output format (--clustalout)'},
            'dlg_msa_mafft_clustalout_tip': {'cn': '以 Clustal 格式输出，而非 FASTA',
                                             'en': 'Output in Clustal format instead of FASTA'},
            'dlg_msa_mafft_reorder': {'cn': '按比对顺序输出 (--reorder)',
                                      'en': 'Reorder output by alignment (--reorder)'},
            'dlg_msa_mafft_reorder_tip': {'cn': '按比对顺序输出序列（默认: 输入顺序）',
                                          'en': 'Output sequences in alignment order (default: input order)'},
            'dlg_msa_mafft_quiet': {'cn': '安静模式 (--quiet)', 'en': 'Quiet mode (--quiet)'},
            'dlg_msa_mafft_quiet_tip': {'cn': '不报告进度信息', 'en': 'Do not report progress'},
            'dlg_msa_mafft_dash': {'cn': '添加结构信息 (--dash)', 'en': 'Add structural information (--dash)'},
            'dlg_msa_mafft_dash_tip': {'cn': '添加结构信息（Rozewicki 等人）',
                                       'en': 'Add structural information (Rozewicki et al.)'},

            # MUSCLE tab
            'dlg_msa_muscle_maxiters': {'cn': '最大迭代次数 (-maxiters):', 'en': 'Max Iterations (-maxiters):'},
            'dlg_msa_muscle_maxiters_tip': {'cn': '最大迭代次数（默认: 16）',
                                            'en': 'Maximum number of iterations (default: 16)'},
            'dlg_msa_muscle_maxhours': {'cn': '最长运行时间小时 (-maxhours):', 'en': 'Max Hours (-maxhours):'},
            'dlg_msa_muscle_maxhours_tip': {'cn': '最长运行时间（小时，0.0 = 不限制，默认: 不限制）',
                                            'en': 'Maximum time in hours (0.0 = no limit, default: no limit)'},
            'dlg_msa_muscle_format': {'cn': '输出格式:', 'en': 'Output Format:'},
            'dlg_msa_muscle_format_tip': {'cn': '比对输出格式（默认: FASTA）',
                                          'en': 'Output alignment format (default: FASTA)'},
            'dlg_msa_muscle_diags': {'cn': '查找对角线 (-diags)', 'en': 'Find diagonals (-diags)'},
            'dlg_msa_muscle_diags_tip': {'cn': '启用对角线查找（对相似序列更快）',
                                         'en': 'Enable diagonal finding (faster for similar sequences)'},
            'dlg_msa_muscle_quiet': {'cn': '安静模式 (-quiet)', 'en': 'Quiet mode (-quiet)'},
            'dlg_msa_muscle_quiet_tip': {'cn': '不向 stderr 写入进度信息',
                                         'en': 'Do not write progress messages to stderr'},

            # Build Haplotype Network dialog
            'dlg_haplonet_title': {'cn': '构建单倍型网络', 'en': 'Build Haplotype Network'},
            'dlg_haplonet_algorithm': {'cn': '算法选择', 'en': 'Algorithm'},
            'dlg_haplonet_select': {'cn': '选择算法:', 'en': 'Select:'},
            'dlg_haplonet_params': {'cn': '参数设置', 'en': 'Parameters'},
            'dlg_haplonet_threads': {'cn': '线程数 (-t):', 'en': 'Threads (-t):'},
            'dlg_haplonet_threads_tip': {'cn': '并行线程数（默认: 8）', 'en': 'Number of parallel threads (default: 8)'},
            'dlg_haplonet_ambiguous': {'cn': '屏蔽模糊碱基 (-a):', 'en': 'Mask ambiguous bases (-a):'},
            'dlg_haplonet_ambiguous_tip': {'cn': '标记含模糊碱基的位点：勾选=屏蔽(1)，不勾选=忽略(0)',
                                           'en': 'Mark ambiguous-base sites: checked = mask (1), unchecked = ignore (0)'},
            'dlg_haplonet_merge': {'cn': '合并中间顶点 (-m):', 'en': 'Merge intermediate vertices (-m):'},
            'dlg_haplonet_merge_tip': {'cn': '合并中间顶点：勾选=合并(1)，不勾选=保留(0)',
                                       'en': 'Merge intermediate vertices: checked = merge (1), unchecked = keep (0)'},
            'dlg_haplonet_epsilon': {'cn': 'Epsilon (-e):', 'en': 'Epsilon (-e):'},
            'dlg_haplonet_epsilon_tip': {'cn': '网络构建的 epsilon 值（默认: 0）',
                                         'en': 'Epsilon value for network construction (default: 0)'},
            'dlg_haplonet_mcan_reference': {'cn': '参考序列:', 'en': 'Reference sequence:'},
            'dlg_haplonet_mcan_reference_tip': {
                'cn': 'McAN 以该条已比对序列为参考描述突变；默认使用第一条已选择序列。',
                'en': 'McAN describes mutations relative to this aligned sequence; the first selected sequence is used by default.'},
            'dlg_haplonet_mcan_ambiguous': {'cn': '排除模糊位点:', 'en': 'Exclude ambiguous sites:'},
            'dlg_haplonet_mcan_ambiguous_tip': {
                'cn': '排除包含 A/C/G/T/U 和缺口以外字符的比对列。',
                'en': 'Exclude alignment columns containing bases other than A/C/G/T/U or gaps.'},
            'dlg_haplonet_rmst_method': {'cn': 'RMST 模式:', 'en': 'RMST mode:'},
            'dlg_haplonet_rmst_method_tip': {
                'cn': '精确模式确定性地保留所有可出现在最小生成树中的边（推荐）；随机模式重复抽样并记录边频率。',
                'en': 'Exact mode deterministically retains every MST-compatible edge (recommended); randomized mode repeatedly samples edges and records their frequencies.'},
            'dlg_haplonet_rmst_exact': {
                'cn': '精确模式（推荐）', 'en': 'Exact edge union (recommended)'},
            'dlg_haplonet_rmst_randomized': {
                'cn': '随机重复抽样', 'en': 'Randomized repeated MST'},
            'dlg_haplonet_rmst_iterations': {'cn': '重复次数:', 'en': 'Iterations:'},
            'dlg_haplonet_rmst_iterations_tip': {
                'cn': '随机模式中重复构建最小生成树的次数。',
                'en': 'Number of minimum spanning trees sampled in randomized mode.'},
            'dlg_haplonet_rmst_seed': {'cn': '随机种子:', 'en': 'Random seed:'},
            'dlg_haplonet_rmst_seed_tip': {
                'cn': '固定种子可使随机模式结果可复现。',
                'en': 'Use a fixed seed to make randomized results reproducible.'},
            'dlg_haplonet_rmst_ambiguous': {
                'cn': '排除模糊位点:', 'en': 'Exclude ambiguous sites:'},
            'dlg_haplonet_rmst_ambiguous_tip': {
                'cn': '排除包含 A/C/G/T/U 和缺口以外字符的比对列；过滤后相同的单倍型将合并。',
                'en': 'Exclude columns containing symbols other than A/C/G/T/U or gaps; haplotypes identical after filtering are merged.'},
            'alg_original_tcs': {'cn': 'Original TCS（原始 TCS）', 'en': 'Original TCS'},
            'alg_modified_tcs': {'cn': 'Modified TCS（改进 TCS）', 'en': 'Modified TCS'},
            'alg_msn': {'cn': 'MSN（最小生成网络）', 'en': 'MSN (Minimum Spanning Network)'},
            'alg_mjn': {'cn': 'MJN（中间连接网络）', 'en': 'MJN (Median-Joining Network)'},
            'alg_rmst': {'cn': 'RMST（随机化最小生成树）', 'en': 'RMST (Randomized Minimum Spanning Tree)'},
            'alg_mcan': {
                'cn': 'McAN (最小代价有向生成树网络)',
                'en': 'McAN (Minimum-cost Arborescence Network)'},
            'btn_ok': {'cn': '确定', 'en': 'OK'},
            'btn_cancel': {'cn': '取消', 'en': 'Cancel'},

            # Tools Menu
            'menu_tools': {'cn': '工具', 'en': 'Tools'},
            'menu_msa': {'cn': '多序列比对...', 'en': 'Multiple Sequence Alignment...'},
            'menu_calculate_haplotype': {'cn': '计算单倍型...', 'en': 'Calculate Haplotype...'},
            'menu_format_conversion': {'cn': '序列格式转换...', 'en': 'Sequence Format Conversion...'},
            'menu_language': {'cn': '语言 / Language', 'en': 'Language / 语言'},
            'menu_chinese': {'cn': '中文', 'en': '中文 (Chinese)'},
            'menu_english': {'cn': 'English', 'en': 'English'},

            # VCF import and format conversion
            'dlg_vcf_import_title': {'cn': '导入 VCF', 'en': 'Import VCF'},
            'dlg_vcf_file': {'cn': 'VCF 文件:', 'en': 'VCF file:'},
            'dlg_vcf_metadata': {'cn': 'metadata 文件（可选）:', 'en': 'Metadata file (optional):'},
            'dlg_vcf_reference': {'cn': '参考 FASTA（可选）:', 'en': 'Reference FASTA (optional):'},
            'dlg_vcf_import_note': {
                'cn': '样本 metadata 与其他格式一致，导入后从样本名中解析。metadata 文件可选：'
                      '提供 McAN 六列 TSV 且样本名保持不变时，可启用 McAN 原生 VCF 分析。'
                      '未提供参考 FASTA 时生成仅含变异位点的比对，提供参考后可重建全长比对。',
                'en': 'Sample metadata is parsed from the sample IDs after import, like the other formats. '
                      'A metadata file is optional: a McAN six-column TSV enables native McAN VCF analysis '
                      'while the sample names are unchanged. Without a reference FASTA NetST imports a '
                      'variable-site alignment; with a reference it reconstructs a full-length alignment.'},
            'dlg_convert_title': {'cn': '序列格式转换', 'en': 'Sequence Format Conversion'},
            'dlg_convert_input': {'cn': '输入文件:', 'en': 'Input file:'},
            'dlg_convert_input_format': {'cn': '输入格式:', 'en': 'Input format:'},
            'dlg_convert_output': {'cn': '输出文件:', 'en': 'Output file:'},
            'dlg_convert_output_format': {'cn': '输出格式:', 'en': 'Output format:'},
            'dlg_convert_reference_fasta': {
                'cn': 'VCF 输入的参考 FASTA（可选）:',
                'en': 'Reference FASTA for VCF input (optional):'},
            'dlg_convert_reference_name': {
                'cn': 'VCF 输出的参考样本（可选）:',
                'en': 'Reference sample for VCF output (optional):'},
            'dlg_convert_note': {
                'cn': 'VCF 未提供参考 FASTA 时转换为变异位点比对；FASTA/NEXUS/PHYLIP 输出 VCF 时默认使用第一条序列作为参考。',
                'en': 'VCF without a reference FASTA becomes a variable-site alignment; FASTA/NEXUS/PHYLIP to VCF uses the first sequence as reference unless specified.'},
            'btn_browse': {'cn': '浏览...', 'en': 'Browse...'},
            'btn_convert': {'cn': '转换', 'en': 'Convert'},
            'filter_vcf': {'cn': 'VCF 文件 (*.vcf *.vcf.gz);;所有文件 (*.*)',
                           'en': 'VCF Files (*.vcf *.vcf.gz);;All Files (*.*)'},
            'filter_metadata': {'cn': 'Metadata 文件 (*.tsv *.txt *.csv);;所有文件 (*.*)',
                                'en': 'Metadata Files (*.tsv *.txt *.csv);;All Files (*.*)'},
            'filter_sequence_formats': {
                'cn': '序列文件 (*.fasta *.fas *.fa *.nex *.nexus *.nxs *.phy *.phylip *.vcf *.vcf.gz);;所有文件 (*.*)',
                'en': 'Sequence Files (*.fasta *.fas *.fa *.nex *.nexus *.nxs *.phy *.phylip *.vcf *.vcf.gz);;All Files (*.*)'},
            'msg_vcf_required': {
                'cn': '请选择有效的 VCF 文件。',
                'en': 'Select an existing VCF file.'},
            'msg_metadata_not_found': {'cn': '所选 metadata 文件不存在。',
                                       'en': 'The selected metadata file does not exist.'},
            'msg_reference_not_found': {'cn': '所选参考 FASTA 不存在。',
                                        'en': 'The selected reference FASTA does not exist.'},
            'msg_conversion_paths_required': {
                'cn': '请选择有效的输入文件和输出路径。',
                'en': 'Select an existing input file and an output path.'},
            'msg_conversion_same_path': {'cn': '输入和输出路径不能相同。',
                                         'en': 'Input and output paths must be different.'},
            'vcf_mode_full': {'cn': '全长比对', 'en': 'full-length alignment'},
            'vcf_mode_variable': {'cn': '变异位点比对', 'en': 'variable-site alignment'},
            'msg_vcf_import_complete': {
                'cn': '已从 {records} 条 VCF 记录导入 {samples} 个样本，生成{mode}。',
                'en': 'Imported {samples} samples from {records} VCF records as a {mode}.'},
            'msg_vcf_import_failed': {'cn': 'VCF 导入失败：{error}',
                                      'en': 'VCF import failed: {error}'},
            'msg_conversion_complete': {'cn': '格式转换完成：\n{path}',
                                        'en': 'Format conversion completed:\n{path}'},
            'msg_conversion_failed': {'cn': '格式转换失败：{error}',
                                      'en': 'Format conversion failed: {error}'},
            'log_vcf_native_available': {
                'cn': '样本名保持不变时，McAN 可原生读取该 VCF 与 metadata。',
                'en': 'McAN can read this VCF and metadata natively while the imported sample names are unchanged.'},
            'log_vcf_metadata_not_native': {
                'cn': 'metadata 已导入，但不是 McAN 六列 TSV；McAN 将使用转换后的比对序列，而非原生 VCF 模式。',
                'en': 'Metadata was imported, but it is not McAN six-column TSV; McAN will use the converted alignment instead of native VCF mode.'},
            'log_vcf_loaded': {
                'cn': '已载入 {samples} 个 VCF 样本和 {records} 条变异记录，生成{mode}（{length}个位点）。',
                'en': 'Loaded {samples} VCF samples and {records} variant records as a {mode} ({length} sites).'},
            'log_vcf_import_failed': {'cn': 'VCF 导入失败：{error}',
                                      'en': 'VCF import failed: {error}'},
            'log_conversion_complete': {'cn': '格式转换完成：{path}',
                                        'en': 'Format conversion completed: {path}'},
            'log_conversion_failed': {'cn': '格式转换失败：{error}',
                                      'en': 'Format conversion failed: {error}'},
            'log_vcf_source_modified': {
                'cn': 'VCF 导入后的样本名或序列已修改；McAN 将使用当前比对表而非原始 VCF。',
                'en': 'VCF-derived sequence names or sequences were modified; McAN will use the current aligned table instead of the original VCF.'},

            # Help Menu
            'menu_help': {'cn': '帮助', 'en': 'Help'},
            'menu_about': {'cn': '关于', 'en': 'About'},
            'menu_help_tcsbu': {'cn': 'TCS-BU 帮助文档', 'en': 'TCS-BU Help'},
            'menu_help_netst': {'cn': 'NetST 帮助文档', 'en': 'NetST Help'},

            # Tab Names
            'tab_index': {'cn': '首页', 'en': 'Home'},
            'tab_network': {'cn': '网络视图', 'en': 'Network'},
            'tab_data': {'cn': '数据', 'en': 'Data'},
            'tab_haplotype': {'cn': '单倍型', 'en': 'Haplotype'},
            'tab_alignment': {'cn': '序列比对', 'en': 'Alignment'},
            'tab_interpretation': {'cn': '辅助解读', 'en': 'Interpretation'},

            # Data Tab
            'btn_select_all': {'cn': '全选', 'en': 'Select All'},
            'btn_deselect_all': {'cn': '取消全选', 'en': 'Deselect All'},
            'label_selected': {'cn': '已选择:', 'en': 'Selected:'},
            'column_select': {'cn': '选择', 'en': 'Select'},
            'column_id': {'cn': '编号', 'en': 'ID'},
            'column_name': {'cn': '名称', 'en': 'Name'},
            'column_sequence': {'cn': '序列', 'en': 'Sequence'},
            'column_discrete_traits': {'cn': '分类型数据', 'en': 'Categorical Data'},
            'column_continuous_traits': {'cn': '数值型数据', 'en': 'Numeric Data'},
            'tooltip_sequence': {
                'cn': '长度: {length} bp\n序列为只读内容',
                'en': 'Length: {length} bp\nSequence is read-only'
            },
            'dlg_export_network_image': {
                'cn': '保存网络图片',
                'en': 'Save Network Image'
            },
            'dlg_save_web_export': {
                'cn': '保存导出文件',
                'en': 'Save Exported File'
            },

            # Log Tab / Output Panel
            'label_output': {'cn': '输出', 'en': 'Output'},
            'label_project_name': {'cn': '项目名称:', 'en': 'Project Name:'},
            'label_output_folder': {'cn': '输出目录:', 'en': 'Output Folder:'},
            'placeholder_project': {'cn': '例如: my_project', 'en': 'e.g. my_project'},
            'btn_open': {'cn': '打开', 'en': 'Open'},
            'btn_change': {'cn': '更改', 'en': 'Change'},
            'msg_open_output_failed': {
                'cn': '无法打开输出目录：{error}',
                'en': 'Could not open the output folder: {error}'},
            'log_hint': {'cn': '日志', 'en': 'Logs'},
            'tooltip_collapse_output': {'cn': '收起输出面板', 'en': 'Collapse output panel'},
            'tooltip_expand_output': {'cn': '展开输出面板', 'en': 'Expand output panel'},
            'webengine_unavailable': {
                'cn': 'Qt WebEngine 不可用。\n\n请安装 PyQt6-WebEngine:\npip install PyQt6-WebEngine',
                'en': 'Qt WebEngine is unavailable.\n\nInstall PyQt6-WebEngine:\npip install PyQt6-WebEngine'
            },
            'waiting_title': {'cn': '正在分析', 'en': 'Analysis in progress'},
            'waiting_body': {
                'cn': '正在运行序列处理和网络构建，请稍候。可使用窗口底部的“取消”按钮停止任务。',
                'en': 'Sequence processing and network construction are running. Use the Cancel button in the status bar to stop the task.'
            },

            # Alignment Tab
            'align_no_data': {'cn': '未加载比对结果。', 'en': 'No alignment loaded.'},
            'align_not_found': {'cn': '未找到比对文件。', 'en': 'Alignment file not found.'},
            'align_read_error': {'cn': '读取比对文件失败。', 'en': 'Failed to read alignment file.'},
            'align_empty': {'cn': '比对文件中未找到序列。', 'en': 'No sequences found in alignment file.'},
            'align_label_alignment': {'cn': '比对文件', 'en': 'Alignment'},
            'align_label_sequences': {'cn': '序列数', 'en': 'Sequences'},
            'align_positions': {'cn': '{n} 个位点', 'en': '{n} positions'},
            'align_positions_trunc': {
                'cn': '{total} 个位点（仅显示前 {shown} 个）',
                'en': '{total} positions (showing first {shown})'
            },
            'align_info_source': {'cn': '源文件: {path}', 'en': 'Source: {path}'},
            'align_info_truncated': {
                'cn': '源文件: {path}\n为保证界面响应速度，此处仅展示前 {shown} 个位点。如需完整比对结果，请打开上方源文件。',
                'en': ('Source: {path}\nOnly the first {shown} positions are shown here '
                       'to keep the view responsive. Open the file above for the '
                       'complete alignment.')
            },
            'align_sequences_truncated': {
                'cn': '为保证界面响应速度，仅显示前 {shown}/{total} 条序列。',
                'en': 'Only the first {shown} of {total} sequences are displayed.'},
            'align_header_seqname': {'cn': '序列名称', 'en': 'Sequence Name'},
            'tooltip_position': {'cn': '位点 {position}: {base}', 'en': 'Position {position}: {base}'},

            # Haplotype Tab
            'hap_no_data': {'cn': '未加载结果。', 'en': 'No results loaded.'},
            'hap_label_project': {'cn': '项目', 'en': 'Project'},
            'hap_label_unique': {'cn': '单倍型数', 'en': 'Unique haplotypes'},
            'hap_label_total_seq': {'cn': '序列总数', 'en': 'Total sequences'},
            'hap_positions': {'cn': '    |    {n} 个位点', 'en': '    |    {n} positions'},
            'hap_positions_trunc': {
                'cn': '    |    {total} 个位点（仅显示前 {shown} 个）',
                'en': '    |    {total} positions (showing first {shown})'
            },
            'hap_info_truncated': {
                'cn': '为保证界面响应速度，此处仅展示前 {shown} 个位点。如需查看完整的单倍型比对序列，请打开源文件: {path}',
                'en': ('Only the first {shown} positions are shown here to keep '
                       'the view responsive. For the full aligned haplotypes open '
                       '{path}.')
            },
            'hap_haplotypes_truncated': {
                'cn': '为保证界面响应速度，仅显示前 {shown}/{total} 个单倍型。',
                'en': 'Only the first {shown} of {total} haplotypes are displayed.'},
            'hap_mappings_truncated': {
                'cn': '为保证界面响应速度，仅显示前 {shown}/{total} 条序列映射。',
                'en': 'Only the first {shown} of {total} sequence mappings are displayed.'},
            'hap_section_summary': {'cn': '单倍型摘要', 'en': 'Haplotype Summary'},
            'hap_section_mapping': {'cn': '序列 → 单倍型映射', 'en': 'Sequence → Haplotype Mapping'},
            'hap_header_haplotype': {'cn': '单倍型', 'en': 'Haplotype'},
            'hap_header_total': {'cn': '总数量', 'en': 'Total Count'},
            'hap_header_samples': {'cn': '样本', 'en': 'Samples'},
            'hap_header_seqname': {'cn': '序列名称', 'en': 'Sequence Name'},

            # Standardization dialog
            'dlg_std_title': {'cn': '标准化', 'en': 'Standardization'},
            'dlg_std_group': {'cn': '标准化选项', 'en': 'Standardization'},
            'dlg_std_remove_ambiguous': {'cn': '移除含模糊碱基的序列', 'en': 'Remove seq with ambiguous bases'},
            'dlg_std_replace': {'cn': '替换', 'en': 'Replace'},
            'dlg_std_split_using': {'cn': '按分隔符拆分:', 'en': 'Split names using:'},
            'dlg_std_use_as_name': {'cn': '作为新名称', 'en': 'Use as the new name'},
            'dlg_std_use_as_discrete': {'cn': '作为分类型性状', 'en': 'Use as categorical trait'},
            'dlg_std_use_as_continuous': {'cn': '作为数值型性状', 'en': 'Use as numeric trait'},
            'dlg_std_numbering': {'cn': '使用序号作为序列名', 'en': 'Use numbering as seq names'},
            'dlg_std_preview_names': {'cn': '预览名称:', 'en': 'Preview Names:'},
            'dlg_std_split_results': {'cn': '拆分结果:', 'en': 'Split Results:'},

            # File dialog titles
            'dlg_load_seq_title': {'cn': '导入 FASTA 文件', 'en': 'Import FASTA File'},
            'dlg_load_nexus_title': {'cn': '导入 NEXUS 文件', 'en': 'Import NEXUS File'},
            'dlg_load_phylip_title': {'cn': '导入 PHYLIP 文件', 'en': 'Import PHYLIP File'},
            'dlg_export_sequences_title': {'cn': '导出序列数据', 'en': 'Export Sequence Data'},
            'dlg_export_traits_title': {'cn': '导出 metadata', 'en': 'Export Metadata'},
            'dlg_load_csv_title': {'cn': '载入 metadata 文件', 'en': 'Load Metadata File'},
            'dlg_select_output': {'cn': '选择输出目录', 'en': 'Select Output Folder'},
            'filter_fasta': {
                'cn': 'FASTA 文件 (*.fas *.fasta *.fa *.fna *.ffn);;所有文件 (*.*)',
                'en': 'FASTA Files (*.fas *.fasta *.fa *.fna *.ffn);;All Files (*.*)'},
            'filter_nexus': {
                'cn': 'NEXUS 文件 (*.nex *.nexus *.nxs);;所有文件 (*.*)',
                'en': 'NEXUS Files (*.nex *.nexus *.nxs);;All Files (*.*)'},
            'filter_phylip': {
                'cn': 'PHYLIP 文件 (*.phy *.phylip);;所有文件 (*.*)',
                'en': 'PHYLIP Files (*.phy *.phylip);;All Files (*.*)'},
            'filter_export_fasta': {
                'cn': 'FASTA 文件 (*.fasta *.fas *.fa)',
                'en': 'FASTA Files (*.fasta *.fas *.fa)'},
            'filter_export_nexus': {
                'cn': 'NEXUS 文件 (*.nex *.nexus *.nxs)',
                'en': 'NEXUS Files (*.nex *.nexus *.nxs)'},
            'filter_export_phylip': {
                'cn': 'PHYLIP 文件 (*.phy *.phylip)',
                'en': 'PHYLIP Files (*.phy *.phylip)'},
            'filter_export_vcf': {
                'cn': 'VCF 文件 (*.vcf)', 'en': 'VCF Files (*.vcf)'},
            'filter_export_traits': {
                'cn': 'CSV 文件 (*.csv);;TSV 文件 (*.tsv)',
                'en': 'CSV Files (*.csv);;TSV Files (*.tsv)'},
            'filter_csv': {'cn': 'metadata 文件 (*.csv *.tsv *.txt);;所有文件 (*.*)',
                           'en': 'Metadata Files (*.csv *.tsv *.txt);;All Files (*.*)'},

            # Common message box titles / text
            'title_warning': {'cn': '警告', 'en': 'Warning'},
            'title_error': {'cn': '错误', 'en': 'Error'},
            'title_success': {'cn': '成功', 'en': 'Success'},
            'title_about': {'cn': '关于', 'en': 'About'},
            'title_validation_error': {'cn': '数据校验错误', 'en': 'Validation Error'},
            'title_name_mismatch': {'cn': '名称不匹配', 'en': 'Name Mismatch Error'},
            'title_update_traits': {'cn': '更新 metadata', 'en': 'Update Metadata'},
            'title_duplicate_names': {'cn': '名称重复', 'en': 'Duplicate Names'},
            'title_alignment_failed': {'cn': '比对失败', 'en': 'Alignment Failed'},
            'title_tcsbu_help': {'cn': 'TCS-BU 帮助', 'en': 'TCS-BU Help'},
            'title_netst_help': {'cn': 'NetST 帮助', 'en': 'NetST Help'},

            'msg_no_sequences_in_file': {'cn': '文件中未找到序列!', 'en': 'No sequences found in file!'},
            'msg_no_valid_sequences': {
                'cn': '应用标准化和过滤规则后没有剩余序列。请检查模糊碱基过滤或拆分设置。',
                'en': 'No sequences remain after standardization and filtering. Check the ambiguous-base filter and split settings.'
            },
            'msg_no_export': {'cn': '没有可导出的数据!', 'en': 'No data to export!'},
            'msg_export_files_complete': {
                'cn': '导出完成：\n{paths}', 'en': 'Export completed:\n{paths}'},
            'msg_load_seq_first': {'cn': '请先载入序列文件再导入 metadata!',
                                   'en': 'Please load a sequence file first before importing metadata!'},
            'msg_csv_empty': {'cn': '文件为空!', 'en': 'The file is empty!'},
            'msg_csv_no_header': {'cn': '文件缺少表头行!', 'en': 'The file has no header row!'},
            'msg_csv_no_data': {'cn': '文件没有数据行!', 'en': 'The file contains no data rows!'},
            'msg_csv_need_name_col': {'cn': '必须选择序列名称列!', 'en': 'Sequence Name column must be selected!'},
            'msg_load_failed': {'cn': '加载文件失败: {err}', 'en': 'Failed to load file: {err}'},
            'msg_export_failed': {'cn': '导出失败: {err}', 'en': 'Failed to export: {err}'},
            'msg_csv_import_failed': {'cn': '导入 metadata 失败:\n{err}', 'en': 'Failed to import metadata:\n{err}'},
            'msg_set_output_first': {'cn': '请先设置输出目录!', 'en': 'Please set output directory first!'},
            'msg_enter_project_name': {'cn': '请输入项目名称!', 'en': 'Please enter a project name!'},
            'msg_load_data_first': {'cn': '请先加载数据!', 'en': 'Please load data first!'},
            'msg_build_network_first': {
                'cn': '当前没有可复用的单倍型网络。请先构建网络，再应用可视化配置。',
                'en': 'There is no reusable haplotype network. Build it first, then apply the visualization configuration.'},
            'msg_select_seq_first': {'cn': '请先选择序列!', 'en': 'Please select sequences first!'},
            'msg_analysis_failed': {'cn': '分析失败: {err}', 'en': 'Analysis failed: {err}'},
            'msg_hap_calc_failed': {'cn': '单倍型计算失败:\n{err}', 'en': 'Haplotype calculation failed:\n{err}'},
            'msg_alignment_failed': {'cn': '比对失败:\n{err}', 'en': 'Alignment failed:\n{err}'},
            'msg_alignment_non_fasta_saved': {
                'cn': '已保存所选的非 FASTA 比对结果；当前内置查看器仅支持 FASTA，因此不会打开预览。',
                'en': 'The selected non-FASTA alignment was saved; the built-in viewer only supports FASTA, so no preview was opened.'
            },
            'msg_csv_duplicate_names': {
                'cn': 'CSV 中存在重复的序列名称:\n{names}',
                'en': 'The CSV contains duplicate sequence names:\n{names}'
            },
            'msg_data_duplicate_names': {
                'cn': '当前数据表中存在重复名称，无法明确匹配 CSV 性状:\n{names}',
                'en': 'The data table contains duplicate names, so CSV traits cannot be mapped unambiguously:\n{names}'
            },
            'msg_validation_empty_name': {
                'cn': '序列名称为空（ID: {id}）。',
                'en': 'Sequence name is empty (ID: {id}).'
            },
            'msg_validation_empty_sequence': {
                'cn': '序列内容为空（ID: {id}，名称: {name}）。',
                'en': 'Sequence is empty (ID: {id}, name: {name}).'
            },
            'msg_validation_name_whitespace': {
                'cn': '序列名称不能包含空格、制表符或换行（ID: {id}，名称: {name}）。',
                'en': 'Sequence names cannot contain spaces, tabs, or line breaks (ID: {id}, name: {name}).'
            },
            'msg_validation_invalid_continuous': {
                'cn': "数值型性状“{value}”不是有效数值（ID: {id}，名称: {name}）。",
                'en': "Numeric trait '{value}' is not numeric (ID: {id}, name: {name})."
            },
            'msg_validation_duplicate_names': {
                'cn': '所选序列中存在重复名称，无法建立可靠映射:\n{names}',
                'en': 'Selected sequences contain duplicate names and cannot be mapped reliably:\n{names}'
            },
            'msg_invalid_project_name': {
                'cn': '项目名称不能包含路径分隔符，也不能是“.”或“..”。',
                'en': 'Project name cannot contain path separators or be . or ...'
            },
            'msg_interpretation_aligned_required': {
                'cn': '该分析需要等长的已比对序列。请先运行多序列比对，或完成一次单倍型分析。',
                'en': 'This analysis requires equal-length aligned sequences. Run multiple-sequence alignment or a haplotype analysis first.'
            },
            'msg_interpretation_failed': {
                'cn': '辅助分析失败：{error}',
                'en': 'Interpretation analysis failed: {error}'
            },
            'msg_topology_gml_required': {
                'cn': '当前项目尚未生成网络 GML。请选择已有 GML 文件，或先构建单倍型网络。',
                'en': 'The current project has no network GML. Select an existing GML file or build a haplotype network first.'
            },
            'filter_gml': {
                'cn': 'GML 网络文件 (*.gml);;所有文件 (*.*)',
                'en': 'GML Network Files (*.gml);;All Files (*.*)'
            },
            'dlg_select_gml': {
                'cn': '选择单倍型网络 GML', 'en': 'Select Haplotype Network GML'},
            'msg_pdf_not_found': {'cn': '{name} 帮助 PDF 未找到:\n{path}',
                                  'en': '{name} help PDF not found:\n{path}'},
            'msg_traits_overwrite': {
                'cn': '部分序列已存在 metadata。\n是否使用文件中的数据覆盖已有 metadata?',
                'en': 'Metadata already exists for some sequences.\n'
                      'Do you want to overwrite the existing metadata with the imported file?',
            },
            'msg_name_mismatch_header': {'cn': '序列名称不匹配:\n', 'en': 'Sequence name mismatch detected:\n'},
            'msg_name_mismatch_missing': {'cn': '数据表中存在但 CSV 中缺失的序列:',
                                          'en': 'Sequences in data table NOT found in CSV:'},
            'msg_name_mismatch_extra': {'cn': 'CSV 中存在但数据表中缺失的名称:',
                                        'en': 'Names in CSV NOT found in data table:'},
            'msg_about_text': {
                'cn': '单倍型网络分析工具\n\n用于单倍型网络的构建与分析',
                'en': 'Haplotype Network Analysis Tool\n\n'
                      'For haplotype network construction and analysis',
            },

            # Status Bar
            'status_ready': {'cn': '就绪', 'en': 'Ready'},
            'status_analyzing': {'cn': '分析中...', 'en': 'Analyzing...'},
            'status_aligning': {'cn': '序列比对中...', 'en': 'Aligning...'},
            'status_haplotype': {'cn': '单倍型计算中...', 'en': 'Calculating haplotypes...'},
            'status_interpreting': {'cn': '辅助分析中...', 'en': 'Running interpretation analysis...'},
            'status_cancelling': {'cn': '正在取消...', 'en': 'Cancelling...'},
            'status_complete': {'cn': '完成', 'en': 'Complete'},

            # Messages
            'msg_language_changed': {'cn': '语言已切换到中文', 'en': 'Language changed to English'},

            # Interpretation analysis results
            'analysis_diversity_title': {
                'cn': '序列质量与遗传多样性', 'en': 'Sequence Quality and Genetic Diversity'},
            'analysis_diversity_description': {
                'cn': '基于当前选择的已比对序列，报告多样性、Tajima’s D、错配分布、FST 与 AMOVA。',
                'en': "Reports diversity, Tajima's D, mismatch distributions, FST, and AMOVA from the selected aligned sequences."},
            'analysis_distance_title': {
                'cn': '遗传距离与 PCoA', 'en': 'Genetic Distance and PCoA'},
            'analysis_distance_description': {
                'cn': '按序列对删除缺失位点计算 p-distance，并使用经典多维尺度分析生成 PCoA 坐标。',
                'en': 'Calculates pairwise-deletion p-distances and classical multidimensional-scaling PCoA coordinates.'},
            'analysis_topology_title': {
                'cn': '单倍型网络拓扑指标', 'en': 'Haplotype Network Topology Metrics'},
            'analysis_topology_description': {
                'cn': '联合单倍型、样本频数与性状解释网络组件、环、中心性、割点和桥；拓扑中心不等同于祖先或传播源。',
                'en': 'Interprets components, cycles, centrality, articulation points, and bridges together with haplotypes, sample frequency, and traits; topological centrality does not imply ancestry or origin.'},
            'report_overview': {'cn': '概览', 'en': 'Overview'},
            'report_charts': {'cn': '图表', 'en': 'Visualizations'},
            'report_metric': {'cn': '指标', 'en': 'Metric'},
            'report_value': {'cn': '数值', 'en': 'Value'},
            'report_warnings': {'cn': '警告', 'en': 'Warnings'},
            'report_notes': {'cn': '解释提示', 'en': 'Interpretation notes'},
            'report_not_saved': {'cn': '未保存', 'en': 'not saved'},
            'log_interpretation_started': {
                'cn': '开始运行{analysis}。', 'en': 'Starting {analysis}.'},
            'log_interpretation_complete': {
                'cn': '{analysis}完成，结果已保存至 {path}。',
                'en': '{analysis} completed; results saved to {path}.'},
            'log_interpretation_failed': {
                'cn': '{analysis}失败：{error}', 'en': '{analysis} failed: {error}'},
            'log_interpretation_cancel_requested': {
                'cn': '已请求取消，正在停止辅助分析…',
                'en': 'Cancellation requested; stopping interpretation analysis…'},

            # Runtime logs and analysis guidance
            'log_cancel_requested': {'cn': '已请求取消，正在停止外部进程…',
                                     'en': 'Cancellation requested; stopping external process…'},
            'log_app_started': {'cn': '应用程序已启动', 'en': 'Application started'},
            'log_working_directory': {'cn': '工作目录: {path}', 'en': 'Working directory: {path}'},
            'log_loading_file': {'cn': '正在载入: {path}', 'en': 'Loading: {path}'},
            'log_load_cancelled': {'cn': '用户取消了载入', 'en': 'Load cancelled by user'},
            'log_loaded_sequences': {'cn': '已载入 {count} 条序列', 'en': 'Loaded {count} sequences'},
            'log_loaded_sequence_format': {
                'cn': '已从 {format} 导入 {count} 条序列',
                'en': 'Loaded {count} sequences from {format}'},
            'log_exported_sequences': {'cn': '序列已导出至: {path}', 'en': 'Sequences exported to: {path}'},
            'log_exported_traits': {'cn': 'metadata 已导出至: {path}', 'en': 'Metadata exported to: {path}'},
            'log_csv_cancelled': {'cn': '用户取消了 metadata 导入', 'en': 'Metadata import cancelled by user'},
            'log_csv_existing_kept': {'cn': '已取消 metadata 导入，保留原有 metadata',
                                      'en': 'Metadata import cancelled; existing metadata kept'},
            'log_csv_imported': {'cn': '已从文件更新 {count} 条序列的 metadata',
                                 'en': 'Metadata imported: {count} sequences updated'},
            'log_no_discrete_selected': {
                'cn': '所选数据无分类型性状；网络将使用默认分组，无法按组着色。',
                'en': 'Selected data has no categorical traits; the network will use the Default group.'
            },
            'log_no_continuous_selected': {
                'cn': '所选数据无有效数值型性状；将生成基础网络，但不能进行数值梯度可视化。',
                'en': 'Selected data has no valid numeric traits; numeric-gradient visualization is unavailable.'
            },
            'log_starting_network': {'cn': '开始 {algorithm} 网络分析…',
                                     'en': 'Starting {algorithm} network analysis…'},
            'log_updating_network_metadata': {
                'cn': '正在更新已有单倍型网络的可视化配置（不重新比对、不重建拓扑）…',
                'en': 'Refreshing the existing haplotype-network visualization configuration '
                      '(no realignment or topology rebuild)…'},
            'log_project': {'cn': '项目: {prefix}', 'en': 'Project: {prefix}'},
            'log_output_directory': {'cn': '输出目录: {path}', 'en': 'Output directory: {path}'},
            'log_analysis_cancelled': {'cn': '分析已取消。', 'en': 'Analysis cancelled.'},
            'log_analysis_completed': {'cn': '分析完成。', 'en': 'Analysis completed.'},
            'log_loading_visualization': {'cn': '正在载入网络可视化…', 'en': 'Loading network visualization…'},
            'log_analysis_failed': {'cn': '分析失败: {error}', 'en': 'Analysis failed: {error}'},
            'log_network_page_failed': {'cn': '网络页面载入失败，未能注入可视化数据。',
                                        'en': 'Network view page failed to load; visualization was not injected.'},
            'log_starting_alignment': {'cn': '开始使用 {tool} 比对 {count} 条序列…',
                                       'en': 'Starting {tool} alignment for {count} sequences…'},
            'log_alignment_cancelled': {'cn': '序列比对已取消。', 'en': 'Alignment cancelled.'},
            'log_alignment_completed': {'cn': '序列比对完成 → {path}', 'en': 'Alignment completed → {path}'},
            'log_alignment_failed': {'cn': '序列比对失败: {error}', 'en': 'Alignment failed: {error}'},
            'log_starting_haplotype': {'cn': '开始使用 {tool} 比对并计算 {count} 条序列的单倍型…',
                                       'en': 'Starting haplotype calculation with {tool} for {count} sequences…'},
            'log_haplotype_cancelled': {'cn': '单倍型计算已取消。', 'en': 'Haplotype calculation cancelled.'},
            'log_haplotype_completed': {'cn': '单倍型计算完成。', 'en': 'Haplotype calculation completed.'},
            'log_haplotype_failed': {'cn': '单倍型计算失败: {error}', 'en': 'Haplotype calculation failed: {error}'},
            'log_loading_alignment_view': {'cn': '正在后台载入比对结果…',
                                           'en': 'Loading alignment view in background…'},
            'log_alignment_view_issue': {'cn': '比对结果视图存在问题: {error}',
                                         'en': 'Alignment view loaded with issue: {error}'},
            'log_alignment_view_ready': {'cn': '比对结果视图已就绪。', 'en': 'Alignment view ready.'},
            'log_loading_haplotype_view': {'cn': '正在后台载入单倍型结果…',
                                           'en': 'Loading haplotype view in background…'},
            'log_haplotype_view_ready': {'cn': '单倍型结果视图已就绪。', 'en': 'Haplotype view ready.'},
            'log_haplotype_view_issue': {'cn': '单倍型结果不完整: {error}',
                                         'en': 'Haplotype result is incomplete: {error}'},
            'log_no_discrete_traits': {'cn': '数据中无分类型性状，无法进行分组着色。',
                                       'en': 'Data has no categorical traits; group coloring is unavailable.'},
            'log_no_continuous_traits': {'cn': '数据中无有效数值型性状，无法进行数值梯度可视化。',
                                         'en': 'Data has no valid numeric traits; numeric-gradient visualization is unavailable.'},
        }

    def set_language(self, lang: str):
        """Set current language ('cn' or 'en')"""
        if lang in ('cn', 'en'):
            self._current_language = lang

    def get_language(self) -> str:
        """Get current language code"""
        return self._current_language

    def get(self, key: str, default: str = '') -> str:
        """Get text for specified key in current language"""
        resource = self._resources.get(key)
        if resource:
            return resource.get(self._current_language) or resource.get('en') or default
        return default

    def validate_resources(self) -> list[str]:
        """Return resource keys that do not define both supported languages."""
        return sorted(
            key for key, value in self._resources.items()
            if not value.get('cn') or not value.get('en')
        )


# Global instance
lang_manager = LanguageManager()
