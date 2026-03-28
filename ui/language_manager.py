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
            'menu_add_sequence': {'cn': '增加序列...', 'en': 'Add Sequence...'},
            'menu_load_gml': {'cn': '载入GML文件...', 'en': 'Load GML...'},
            'menu_load_html': {'cn': '载入HTML文件...', 'en': 'Load HTML...'},
            'menu_export_table': {'cn': '导出表格...', 'en': 'Export Table...'},
            'menu_export_sequence': {'cn': '导出序列...', 'en': 'Export Sequence...'},
            'menu_exit': {'cn': '退出', 'en': 'Exit'},

            # Edit Menu
            'menu_edit': {'cn': '编辑', 'en': 'Edit'},
            'menu_select_all': {'cn': '全选', 'en': 'Select All'},
            'menu_deselect_all': {'cn': '清除选择', 'en': 'Clear Selection'},

            # Analysis Menu
            'menu_analysis': {'cn': '分析', 'en': 'Analysis'},
            'menu_msn_network': {'cn': 'MSN单倍型网络', 'en': 'MSN Haplotype Network'},
            'menu_mjn_network': {'cn': 'MJN单倍型网络', 'en': 'MJN Haplotype Network'},
            'menu_tcs_network': {'cn': 'TCS单倍型网络', 'en': 'TCS Haplotype Network'},
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

            # View Menu
            'menu_view': {'cn': '浏览', 'en': 'View'},
            'menu_forward': {'cn': '前进', 'en': 'Forward'},
            'menu_back': {'cn': '后退', 'en': 'Back'},
            'menu_analysis_history': {'cn': '分析记录', 'en': 'Analysis History'},

            # Tools Menu
            'menu_tools': {'cn': '工具', 'en': 'Tools'},
            'menu_clean_sequences': {'cn': '清理序列', 'en': 'Clean Sequences'},
            'menu_sequence_info': {'cn': '获取序列信息', 'en': 'Get Sequence Info'},
            'menu_date_to_number': {'cn': '日期转换数字', 'en': 'Date to Number'},
            'menu_language': {'cn': '语言 / Language', 'en': 'Language / 语言'},
            'menu_chinese': {'cn': '中文', 'en': '中文 (Chinese)'},
            'menu_english': {'cn': 'English', 'en': 'English'},

            # Help Menu
            'menu_help': {'cn': '帮助', 'en': 'Help'},
            'menu_about': {'cn': '关于', 'en': 'About'},
            'menu_help_docs': {'cn': '帮助文档', 'en': 'Help Docs'},

            # Tab Names
            'tab_index':     {'cn': '首页',     'en': 'Index'},
            'tab_network':   {'cn': '网络视图', 'en': 'Network View'},
            'tab_data':      {'cn': '数据',     'en': 'Data'},
            'tab_haplotype': {'cn': '单倍型',   'en': 'Haplotype'},
            'tab_report':    {'cn': '分析结果', 'en': 'Analysis Report'},
            'tab_log':       {'cn': '日志',     'en': 'Log'},

            # Data Tab
            'btn_select_all': {'cn': '全选', 'en': 'Select All'},
            'btn_deselect_all': {'cn': '取消全选', 'en': 'Deselect All'},
            'label_selected': {'cn': '已选择', 'en': 'Selected'},

            # Log Tab / Output Panel
            'btn_clear_log': {'cn': '清除日志', 'en': 'Clear Log'},
            'btn_copy_log': {'cn': '复制日志', 'en': 'Copy Log'},
            'label_output': {'cn': '输出目录', 'en': 'Output'},
            'btn_open': {'cn': '打开', 'en': 'Open'},
            'btn_change': {'cn': '更改', 'en': 'Change'},
            'log_hint': {'cn': '日志', 'en': 'Logs'},

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
