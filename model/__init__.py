"""Data models, loaded lazily to keep non-GUI utilities lightweight."""

__all__ = [
    'TaxonData', 'TaxonTableModel', 'SequenceAlignmentConfig',
    'ProjectManifest', 'ProjectConfigError',
]


def __getattr__(name):
    if name == 'TaxonData':
        from model.taxon_data import TaxonData
        return TaxonData
    if name == 'TaxonTableModel':
        from model.taxon_table_model import TaxonTableModel
        return TaxonTableModel
    if name == 'SequenceAlignmentConfig':
        from model.alignment_config import SequenceAlignmentConfig
        return SequenceAlignmentConfig
    if name in {'ProjectManifest', 'ProjectConfigError'}:
        from model.project_config import ProjectConfigError, ProjectManifest
        return {
            'ProjectManifest': ProjectManifest,
            'ProjectConfigError': ProjectConfigError,
        }[name]
    raise AttributeError(name)
