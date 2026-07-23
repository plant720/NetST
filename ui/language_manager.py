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
            'menu_load_sequence': {'cn': '导入 FASTA...', 'en': 'Import FASTA...'},
            'menu_load_nexus': {'cn': '导入 NEXUS...', 'en': 'Import NEXUS...'},
            'menu_load_phylip': {'cn': '导入 PHYLIP...', 'en': 'Import PHYLIP...'},
            'menu_load_vcf': {'cn': '导入 VCF 与 metadata...', 'en': 'Import VCF and Metadata...'},
            'menu_load_csv_traits': {'cn': '导入CSV性状...', 'en': 'Load CSV Traits...'},
            'menu_export_sequence': {'cn': '导出序列数据...', 'en': 'Export Sequence Data...'},
            'menu_export_traits': {'cn': '导出性状数据...', 'en': 'Export Trait Data...'},
            'menu_exit': {'cn': '退出', 'en': 'Exit'},

            # CSV Traits Import Dialog
            'dlg_csv_title': {'cn': '从CSV导入性状', 'en': 'Import Traits from CSV'},
            'dlg_csv_mapping': {'cn': '列映射', 'en': 'Column Mapping'},
            'dlg_csv_seq_name': {'cn': '序列名称列:', 'en': 'Sequence Name Column:'},
            'dlg_csv_discrete': {'cn': '离散性状列:', 'en': 'Discrete Traits Column:'},
            'dlg_csv_continuous': {'cn': '连续性状列:', 'en': 'Continuous Traits Column:'},
            'dlg_csv_preview': {'cn': '数据预览（前几行）', 'en': 'Data Preview (first rows)'},
            'option_none': {'cn': '-- 无 --', 'en': '-- None --'},

            # Analysis Menu
            'menu_analysis': {'cn': '分析', 'en': 'Analysis'},
            'menu_build_haplotype_network': {'cn': '构建单倍型网络...', 'en': 'Build Haplotype Network...'},
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
                'cn': 'McAN 最小代价有向生成树网络',
                'en': 'McAN Minimum-cost Arborescence Network'},
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
            'dlg_vcf_import_title': {'cn': '导入 VCF 与 metadata', 'en': 'Import VCF and Metadata'},
            'dlg_vcf_file': {'cn': 'VCF 文件:', 'en': 'VCF file:'},
            'dlg_vcf_metadata': {'cn': 'metadata 文件:', 'en': 'Metadata file:'},
            'dlg_vcf_reference': {'cn': '参考 FASTA（可选）:', 'en': 'Reference FASTA (optional):'},
            'dlg_vcf_import_note': {
                'cn': '未提供参考 FASTA 时，将生成仅包含变异位点的比对序列；提供参考后可重建全长比对。',
                'en': 'Without a reference FASTA, NetST imports a variable-site alignment; with a reference it reconstructs a full-length alignment.'},
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
            'msg_vcf_metadata_required': {
                'cn': '请选择有效的 VCF 文件和 metadata 文件。',
                'en': 'Select an existing VCF file and metadata file.'},
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
            'log_vcf_metadata_not_native': {
                'cn': 'metadata 已导入，但不是 McAN 六列 TSV；McAN 将使用转换后的比对序列。',
                'en': 'Metadata was imported, but it is not McAN six-column TSV; McAN will use the converted alignment.'},
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
            'column_discrete_traits': {'cn': '离散性状', 'en': 'Discrete Traits'},
            'column_continuous_traits': {'cn': '连续性状', 'en': 'Continuous Traits'},
            'tooltip_sequence': {
                'cn': '长度: {length} bp\n点击单元格可查看或编辑完整序列',
                'en': 'Length: {length} bp\nClick the cell to view or edit the full sequence'
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
            'dlg_std_use_as_discrete': {'cn': '作为离散性状', 'en': 'Use as discrete trait'},
            'dlg_std_use_as_continuous': {'cn': '作为连续性状', 'en': 'Use as continuous trait'},
            'dlg_std_numbering': {'cn': '使用序号作为序列名', 'en': 'Use numbering as seq names'},
            'dlg_std_preview_names': {'cn': '预览名称:', 'en': 'Preview Names:'},
            'dlg_std_split_results': {'cn': '拆分结果:', 'en': 'Split Results:'},

            # File dialog titles
            'dlg_load_seq_title': {'cn': '导入 FASTA 文件', 'en': 'Import FASTA File'},
            'dlg_load_nexus_title': {'cn': '导入 NEXUS 文件', 'en': 'Import NEXUS File'},
            'dlg_load_phylip_title': {'cn': '导入 PHYLIP 文件', 'en': 'Import PHYLIP File'},
            'dlg_export_sequences_title': {'cn': '导出序列数据', 'en': 'Export Sequence Data'},
            'dlg_export_traits_title': {'cn': '导出性状数据', 'en': 'Export Trait Data'},
            'dlg_load_csv_title': {'cn': '载入 CSV 性状文件', 'en': 'Load CSV Traits File'},
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
                'cn': 'CSV 文件 (*.csv)', 'en': 'CSV Files (*.csv)'},
            'filter_csv': {'cn': 'CSV 文件 (*.csv);;所有文件 (*.*)',
                           'en': 'CSV Files (*.csv);;All Files (*.*)'},

            # Common message box titles / text
            'title_warning': {'cn': '警告', 'en': 'Warning'},
            'title_error': {'cn': '错误', 'en': 'Error'},
            'title_success': {'cn': '成功', 'en': 'Success'},
            'title_about': {'cn': '关于', 'en': 'About'},
            'title_validation_error': {'cn': '数据校验错误', 'en': 'Validation Error'},
            'title_name_mismatch': {'cn': '名称不匹配', 'en': 'Name Mismatch Error'},
            'title_update_traits': {'cn': '更新性状', 'en': 'Update Traits'},
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
            'msg_load_seq_first': {'cn': '请先载入序列文件再导入性状!',
                                   'en': 'Please load a sequence file first before importing traits!'},
            'msg_csv_empty': {'cn': 'CSV 文件为空!', 'en': 'The CSV file is empty!'},
            'msg_csv_no_header': {'cn': 'CSV 文件缺少表头行!', 'en': 'The CSV file has no header row!'},
            'msg_csv_no_data': {'cn': 'CSV 文件没有数据行!', 'en': 'The CSV file contains no data rows!'},
            'msg_csv_need_name_col': {'cn': '必须选择序列名称列!', 'en': 'Sequence Name column must be selected!'},
            'msg_load_failed': {'cn': '加载文件失败: {err}', 'en': 'Failed to load file: {err}'},
            'msg_export_failed': {'cn': '导出失败: {err}', 'en': 'Failed to export: {err}'},
            'msg_csv_import_failed': {'cn': '导入 CSV 性状失败:\n{err}', 'en': 'Failed to import CSV traits:\n{err}'},
            'msg_set_output_first': {'cn': '请先设置输出目录!', 'en': 'Please set output directory first!'},
            'msg_enter_project_name': {'cn': '请输入项目名称!', 'en': 'Please enter a project name!'},
            'msg_load_data_first': {'cn': '请先加载数据!', 'en': 'Please load data first!'},
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
                'cn': "连续性状“{value}”不是数值（ID: {id}，名称: {name}）。",
                'en': "Continuous trait '{value}' is not numeric (ID: {id}, name: {name})."
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
                'cn': '部分序列已存在性状数据。\n是否使用 CSV 中的数据覆盖已有性状?',
                'en': 'Trait data already exists for some sequences.\n'
                      'Do you want to overwrite the existing traits with the CSV data?',
            },
            'msg_name_mismatch_header': {'cn': '序列名称不匹配:\n', 'en': 'Sequence name mismatch detected:\n'},
            'msg_name_mismatch_missing': {'cn': '数据表中存在但 CSV 中缺失的序列:',
                                          'en': 'Sequences in data table NOT found in CSV:'},
            'msg_name_mismatch_extra': {'cn': 'CSV 中存在但数据表中缺失的名称:',
                                        'en': 'Names in CSV NOT found in data table:'},
            'msg_about_text': {
                'cn': '单倍型网络分析工具\n\n版本: 2.0.0\n\n基于 PyQt6 重构的 Python 版本\n\n用于单倍型网络的构建与分析',
                'en': 'Haplotype Network Analysis Tool\n\n'
                      'Version: 2.0.0\n\n'
                      'Python version rebuilt with PyQt6\n\n'
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
                'cn': '基于当前选择的已比对序列，统一报告缺失数据、变异位点及总体/分组多样性。',
                'en': 'Reports missing data, variable sites, and overall/group diversity from the selected aligned sequences.'},
            'analysis_distance_title': {
                'cn': '遗传距离与 PCoA', 'en': 'Genetic Distance and PCoA'},
            'analysis_distance_description': {
                'cn': '按序列对删除缺失位点计算 p-distance，并使用经典多维尺度分析生成 PCoA 坐标。',
                'en': 'Calculates pairwise-deletion p-distances and classical multidimensional-scaling PCoA coordinates.'},
            'analysis_topology_title': {
                'cn': '单倍型网络拓扑指标', 'en': 'Haplotype Network Topology Metrics'},
            'analysis_topology_description': {
                'cn': '描述网络组件、环、中心性、割点和桥；拓扑中心不等同于祖先或传播源。',
                'en': 'Describes components, cycles, centrality, articulation points, and bridges; topological centrality does not imply ancestry or origin.'},
            'report_overview': {'cn': '概览', 'en': 'Overview'},
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
            'log_cancel_requested': {'cn': '已请求取消，正在停止外部进程…', 'en': 'Cancellation requested; stopping external process…'},
            'log_app_started': {'cn': '应用程序已启动', 'en': 'Application started'},
            'log_working_directory': {'cn': '工作目录: {path}', 'en': 'Working directory: {path}'},
            'log_loading_file': {'cn': '正在载入: {path}', 'en': 'Loading: {path}'},
            'log_load_cancelled': {'cn': '用户取消了载入', 'en': 'Load cancelled by user'},
            'log_loaded_sequences': {'cn': '已载入 {count} 条序列', 'en': 'Loaded {count} sequences'},
            'log_loaded_sequence_format': {
                'cn': '已从 {format} 导入 {count} 条序列',
                'en': 'Loaded {count} sequences from {format}'},
            'log_exported_sequences': {'cn': '序列已导出至: {path}', 'en': 'Sequences exported to: {path}'},
            'log_exported_traits': {'cn': '性状已导出至: {path}', 'en': 'Traits exported to: {path}'},
            'log_csv_cancelled': {'cn': '用户取消了 CSV 性状导入', 'en': 'CSV trait import cancelled by user'},
            'log_csv_existing_kept': {'cn': '已取消 CSV 性状导入，保留原有性状', 'en': 'CSV trait import cancelled; existing traits kept'},
            'log_csv_imported': {'cn': '已从 CSV 更新 {count} 条序列的性状', 'en': 'Traits imported from CSV: {count} sequences updated'},
            'log_no_discrete_selected': {
                'cn': '所选数据无离散性状；网络将使用默认分组，无法按组着色。',
                'en': 'Selected data has no discrete traits; the network will use the Default group.'
            },
            'log_no_continuous_selected': {
                'cn': '所选数据无有效连续性状；将生成基础网络，但不能进行连续性状可视化。',
                'en': 'Selected data has no valid continuous traits; continuous-trait visualization is unavailable.'
            },
            'log_starting_network': {'cn': '开始 {algorithm} 网络分析…', 'en': 'Starting {algorithm} network analysis…'},
            'log_project': {'cn': '项目: {prefix}', 'en': 'Project: {prefix}'},
            'log_output_directory': {'cn': '输出目录: {path}', 'en': 'Output directory: {path}'},
            'log_analysis_cancelled': {'cn': '分析已取消。', 'en': 'Analysis cancelled.'},
            'log_analysis_completed': {'cn': '分析完成。', 'en': 'Analysis completed.'},
            'log_loading_visualization': {'cn': '正在载入网络可视化…', 'en': 'Loading network visualization…'},
            'log_analysis_failed': {'cn': '分析失败: {error}', 'en': 'Analysis failed: {error}'},
            'log_network_page_failed': {'cn': '网络页面载入失败，未能注入可视化数据。', 'en': 'Network view page failed to load; visualization was not injected.'},
            'log_starting_alignment': {'cn': '开始使用 {tool} 比对 {count} 条序列…', 'en': 'Starting {tool} alignment for {count} sequences…'},
            'log_alignment_cancelled': {'cn': '序列比对已取消。', 'en': 'Alignment cancelled.'},
            'log_alignment_completed': {'cn': '序列比对完成 → {path}', 'en': 'Alignment completed → {path}'},
            'log_alignment_failed': {'cn': '序列比对失败: {error}', 'en': 'Alignment failed: {error}'},
            'log_starting_haplotype': {'cn': '开始使用 {tool} 比对并计算 {count} 条序列的单倍型…', 'en': 'Starting haplotype calculation with {tool} for {count} sequences…'},
            'log_haplotype_cancelled': {'cn': '单倍型计算已取消。', 'en': 'Haplotype calculation cancelled.'},
            'log_haplotype_completed': {'cn': '单倍型计算完成。', 'en': 'Haplotype calculation completed.'},
            'log_haplotype_failed': {'cn': '单倍型计算失败: {error}', 'en': 'Haplotype calculation failed: {error}'},
            'log_loading_alignment_view': {'cn': '正在后台载入比对结果…', 'en': 'Loading alignment view in background…'},
            'log_alignment_view_issue': {'cn': '比对结果视图存在问题: {error}', 'en': 'Alignment view loaded with issue: {error}'},
            'log_alignment_view_ready': {'cn': '比对结果视图已就绪。', 'en': 'Alignment view ready.'},
            'log_loading_haplotype_view': {'cn': '正在后台载入单倍型结果…', 'en': 'Loading haplotype view in background…'},
            'log_haplotype_view_ready': {'cn': '单倍型结果视图已就绪。', 'en': 'Haplotype view ready.'},
            'log_haplotype_view_issue': {'cn': '单倍型结果不完整: {error}', 'en': 'Haplotype result is incomplete: {error}'},
            'log_no_discrete_traits': {'cn': '数据中无离散性状，无法进行分组着色。', 'en': 'Data has no discrete traits; group coloring is unavailable.'},
            'log_no_continuous_traits': {'cn': '数据中无有效连续性状，无法进行连续性状可视化。', 'en': 'Data has no valid continuous traits; continuous-trait visualization is unavailable.'},
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
