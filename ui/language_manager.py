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
            'menu_load_sequence': {'cn': '载入序列...', 'en': 'Load Sequence...'},
            'menu_load_table': {'cn': '载入表格...', 'en': 'Load Table...'},
            'menu_load_csv_traits': {'cn': '导入CSV性状...', 'en': 'Load CSV Traits...'},
            'menu_add_sequence': {'cn': '增加序列...', 'en': 'Add Sequence...'},
            'menu_export_table': {'cn': '导出表格...', 'en': 'Export Table...'},
            'menu_export_sequence': {'cn': '导出序列...', 'en': 'Export Sequence...'},
            'menu_exit': {'cn': '退出', 'en': 'Exit'},

            # CSV Traits Import Dialog
            'dlg_csv_title': {'cn': '从CSV导入性状', 'en': 'Import Traits from CSV'},
            'dlg_csv_mapping': {'cn': '列映射', 'en': 'Column Mapping'},
            'dlg_csv_seq_name': {'cn': '序列名称列:', 'en': 'Sequence Name Column:'},
            'dlg_csv_discrete': {'cn': '离散性状列:', 'en': 'Discrete Traits Column:'},
            'dlg_csv_continuous': {'cn': '连续性状列:', 'en': 'Continuous Traits Column:'},
            'dlg_csv_preview': {'cn': '数据预览（前几行）', 'en': 'Data Preview (first rows)'},

            # Edit Menu
            'menu_edit': {'cn': '编辑', 'en': 'Edit'},
            'menu_select_all': {'cn': '全选', 'en': 'Select All'},
            'menu_deselect_all': {'cn': '清除选择', 'en': 'Clear Selection'},

            # Analysis Menu
            'menu_analysis': {'cn': '分析', 'en': 'Analysis'},
            'menu_build_haplotype_network': {'cn': '构建单倍型网络...', 'en': 'Build Haplotype Network...'},
            'menu_mafft': {'cn': '序列比对-MAFFT', 'en': 'Alignment-MAFFT'},
            'menu_mafft_auto': {'cn': 'Auto (自动选择)', 'en': 'Auto (Automatic)'},
            'menu_mafft_fftns1': {'cn': 'FFT-NS-1 (极快但粗糙)', 'en': 'FFT-NS-1 (Very Fast)'},
            'menu_mafft_fftns2': {'cn': 'FFT-NS-2 (快速)', 'en': 'FFT-NS-2 (Fast)'},
            'menu_mafft_ginsi': {'cn': 'G-INS-i (全局比对-慢)', 'en': 'G-INS-i (Global-Slow)'},
            'menu_mafft_linsi': {'cn': 'L-INS-i (局部比对-最精确)', 'en': 'L-INS-i (Local-Accurate)'},
            'menu_mafft_einsi': {'cn': 'E-INS-i (含长非比对区域)', 'en': 'E-INS-i (Long Indel)'},
            'menu_muscle': {'cn': '序列比对-MUSCLE', 'en': 'Alignment-MUSCLE'},
            'menu_muscle_ppp': {'cn': 'PPP 算法', 'en': 'PPP Algorithm'},
            'menu_muscle_super5': {'cn': 'Super5 算法', 'en': 'Super5 Algorithm'},
            'menu_network_visualization': {'cn': '网络图可视化', 'en': 'Network Visualization'},
            'menu_topology_analysis': {'cn': '拓扑结构分析', 'en': 'Topology Analysis'},
            'menu_community_detection': {'cn': '社区检测', 'en': 'Community Detection'},
            'menu_modularity_analysis': {'cn': '模块度分析', 'en': 'Modularity Analysis'},
            'menu_community_plot': {'cn': '社区绘制', 'en': 'Community Plot'},
            'menu_sequence_analysis': {'cn': '序列分析', 'en': 'Sequence Analysis'},
            'menu_population_analysis': {'cn': '群体信息统计', 'en': 'Population Statistics'},
            'menu_trait_analysis': {'cn': '性状关联分析', 'en': 'Trait Association'},

            # Multiple Sequence Alignment menu item
            'menu_msa': {'cn': '多序列比对...', 'en': 'Multiple Sequence Alignment...'},
            # Calculate Haplotype menu item
            'menu_calculate_haplotype': {'cn': '计算单倍型...', 'en': 'Calculate Haplotype...'},

            # Multiple Sequence Alignment dialog
            'dlg_msa_title': {'cn': '多序列比对', 'en': 'Multiple Sequence Alignment'},
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
            'btn_ok': {'cn': '确定', 'en': 'OK'},
            'btn_cancel': {'cn': '取消', 'en': 'Cancel'},

            # View Menu
            'menu_view': {'cn': '浏览', 'en': 'View'},
            'menu_forward': {'cn': '前进', 'en': 'Forward'},
            'menu_back': {'cn': '后退', 'en': 'Back'},
            'menu_analysis_history': {'cn': '分析记录', 'en': 'Analysis History'},

            # Tools Menu
            'menu_tools': {'cn': '工具', 'en': 'Tools'},
            'menu_language': {'cn': '语言 / Language', 'en': 'Language / 语言'},
            'menu_chinese': {'cn': '中文', 'en': '中文 (Chinese)'},
            'menu_english': {'cn': 'English', 'en': 'English'},

            # Help Menu
            'menu_help': {'cn': '帮助', 'en': 'Help'},
            'menu_about': {'cn': '关于', 'en': 'About'},
            'menu_help_docs': {'cn': '帮助文档', 'en': 'Help Docs'},
            'menu_help_tcsbu': {'cn': 'TCS-BU 帮助文档', 'en': 'TCS-BU Help'},
            'menu_help_netst': {'cn': 'NetST 帮助文档', 'en': 'NetST Help'},

            # Tab Names
            'tab_index': {'cn': '首页', 'en': 'Home'},
            'tab_network': {'cn': '网络视图', 'en': 'Network'},
            'tab_data': {'cn': '数据', 'en': 'Data'},
            'tab_haplotype': {'cn': '单倍型', 'en': 'Haplotype'},
            'tab_alignment': {'cn': '序列比对', 'en': 'Alignment'},
            'tab_report': {'cn': '分析结果', 'en': 'Analysis Report'},
            'tab_log': {'cn': '日志', 'en': 'Log'},

            # Data Tab
            'btn_select_all': {'cn': '全选', 'en': 'Select All'},
            'btn_deselect_all': {'cn': '取消全选', 'en': 'Deselect All'},
            'label_selected': {'cn': '已选择:', 'en': 'Selected:'},

            # Log Tab / Output Panel
            'btn_clear_log': {'cn': '清除日志', 'en': 'Clear Log'},
            'btn_copy_log': {'cn': '复制日志', 'en': 'Copy Log'},
            'label_output': {'cn': '输出', 'en': 'Output'},
            'label_project_name': {'cn': '项目名称:', 'en': 'Project Name:'},
            'label_output_folder': {'cn': '输出目录:', 'en': 'Output Folder:'},
            'placeholder_project': {'cn': '例如: my_project', 'en': 'e.g. my_project'},
            'btn_open': {'cn': '打开', 'en': 'Open'},
            'btn_change': {'cn': '更改', 'en': 'Change'},
            'log_hint': {'cn': '日志', 'en': 'Logs'},

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
            'align_header_seqname': {'cn': '序列名称', 'en': 'Sequence Name'},

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
            'dlg_load_seq_title': {'cn': '载入序列文件', 'en': 'Load Sequence File'},
            'dlg_add_seq_title': {'cn': '追加序列文件', 'en': 'Add Sequence File'},
            'dlg_export_fasta_title': {'cn': '导出 FASTA 文件', 'en': 'Export FASTA File'},
            'dlg_load_csv_title': {'cn': '载入 CSV 性状文件', 'en': 'Load CSV Traits File'},
            'dlg_select_output': {'cn': '选择输出目录', 'en': 'Select Output Folder'},
            'dlg_delimiter_title': {'cn': '分隔符', 'en': 'Delimiter'},
            'dlg_delimiter_prompt': {'cn': '请输入 FASTA 头部分隔符:', 'en': 'Enter FASTA header delimiter:'},
            'filter_fasta': {'cn': 'FASTA 文件 (*.fas *.fasta *.fa);;所有文件 (*.*)',
                             'en': 'FASTA Files (*.fas *.fasta *.fa);;All Files (*.*)'},
            'filter_fasta_export': {'cn': 'FASTA 文件 (*.fasta);;所有文件 (*.*)',
                                    'en': 'FASTA Files (*.fasta);;All Files (*.*)'},
            'filter_csv': {'cn': 'CSV 文件 (*.csv);;所有文件 (*.*)',
                           'en': 'CSV Files (*.csv);;All Files (*.*)'},

            # Common message box titles / text
            'title_warning': {'cn': '警告', 'en': 'Warning'},
            'title_error': {'cn': '错误', 'en': 'Error'},
            'title_info': {'cn': '信息', 'en': 'Information'},
            'title_success': {'cn': '成功', 'en': 'Success'},
            'title_about': {'cn': '关于', 'en': 'About'},
            'title_validation_error': {'cn': '数据校验错误', 'en': 'Validation Error'},
            'title_name_mismatch': {'cn': '名称不匹配', 'en': 'Name Mismatch Error'},
            'title_update_traits': {'cn': '更新性状', 'en': 'Update Traits'},
            'title_alignment_failed': {'cn': '比对失败', 'en': 'Alignment Failed'},
            'title_tcsbu_help': {'cn': 'TCS-BU 帮助', 'en': 'TCS-BU Help'},
            'title_netst_help': {'cn': 'NetST 帮助', 'en': 'NetST Help'},

            'msg_no_sequences_in_file': {'cn': '文件中未找到序列!', 'en': 'No sequences found in file!'},
            'msg_no_export': {'cn': '没有可导出的数据!', 'en': 'No data to export!'},
            'msg_export_complete': {'cn': '导出完成!', 'en': 'Export completed!'},
            'msg_load_seq_first': {'cn': '请先载入序列文件再导入性状!',
                                   'en': 'Please load a sequence file first before importing traits!'},
            'msg_csv_empty': {'cn': 'CSV 文件为空!', 'en': 'The CSV file is empty!'},
            'msg_csv_no_header': {'cn': 'CSV 文件缺少表头行!', 'en': 'The CSV file has no header row!'},
            'msg_csv_no_data': {'cn': 'CSV 文件没有数据行!', 'en': 'The CSV file contains no data rows!'},
            'msg_csv_need_name_col': {'cn': '必须选择序列名称列!', 'en': 'Sequence Name column must be selected!'},
            'msg_load_failed': {'cn': '加载文件失败: {err}', 'en': 'Failed to load file: {err}'},
            'msg_add_failed': {'cn': '追加序列失败: {err}', 'en': 'Failed to add sequences: {err}'},
            'msg_export_failed': {'cn': '导出失败: {err}', 'en': 'Failed to export: {err}'},
            'msg_csv_import_failed': {'cn': '导入 CSV 性状失败:\n{err}', 'en': 'Failed to import CSV traits:\n{err}'},
            'msg_set_output_first': {'cn': '请先设置输出目录!', 'en': 'Please set output directory first!'},
            'msg_enter_project_name': {'cn': '请输入项目名称!', 'en': 'Please enter a project name!'},
            'msg_load_data_first': {'cn': '请先加载数据!', 'en': 'Please load data first!'},
            'msg_select_seq_first': {'cn': '请先选择序列!', 'en': 'Please select sequences first!'},
            'msg_analysis_failed': {'cn': '分析失败: {err}', 'en': 'Analysis failed: {err}'},
            'msg_hap_calc_failed': {'cn': '单倍型计算失败:\n{err}', 'en': 'Haplotype calculation failed:\n{err}'},
            'msg_alignment_failed': {'cn': '比对失败:\n{err}', 'en': 'Alignment failed:\n{err}'},
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
            'status_loading': {'cn': '加载中...', 'en': 'Loading...'},
            'status_analyzing': {'cn': '分析中...', 'en': 'Analyzing...'},
            'status_complete': {'cn': '完成', 'en': 'Complete'},

            # Messages
            'msg_no_data': {'cn': '请先加载数据！', 'en': 'Please load data first!'},
            'msg_no_selection': {'cn': '请先选择序列！', 'en': 'Please select sequences first!'},
            'msg_language_changed': {'cn': '语言已切换到中文', 'en': 'Language changed to English'},
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
            return resource.get(self._current_language, default)
        return default


# Global instance
lang_manager = LanguageManager()
