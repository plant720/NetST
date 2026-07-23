"""Data models, loaded lazily to keep non-GUI utilities lightweight."""

__all__ = ['TaxonData', 'TaxonTableModel', 'SequenceAlignmentConfig']


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
    raise AttributeError(name)
