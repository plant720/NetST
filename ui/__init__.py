"""User-interface classes exposed through lazy package imports."""

_EXPORTS = {
    'MainWindowUI': ('ui.main_window_ui', 'MainWindowUI'),
    'MenuBarBuilder': ('ui.menu_bar', 'MenuBarBuilder'),
    'StatusBarWidget': ('ui.status_bar', 'StatusBarWidget'),
    'DataTabWidget': ('ui.data_tab_widget', 'DataTabWidget'),
    'OutputPanel': ('ui.output_panel', 'OutputPanel'),
    'LanguageManager': ('ui.language_manager', 'LanguageManager'),
    'lang_manager': ('ui.language_manager', 'lang_manager'),
    'StandardizationDialog': ('ui.standardization_dialog', 'StandardizationDialog'),
    'StandardizationConfig': ('ui.standardization_dialog', 'StandardizationConfig'),
    'SequenceAlignmentDialog': ('ui.sequence_alignment_dialog', 'SequenceAlignmentDialog'),
    'SequenceAlignmentConfig': ('model.alignment_config', 'SequenceAlignmentConfig'),
    'IndexTabWidget': ('ui.index_tab_widget', 'IndexTabWidget'),
    'HaplotypeTabWidget': ('ui.haplotype_tab_widget', 'HaplotypeTabWidget'),
    'AlignmentTabWidget': ('ui.alignment_tab_widget', 'AlignmentTabWidget'),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attribute_name = target
    from importlib import import_module
    return getattr(import_module(module_name), attribute_name)
