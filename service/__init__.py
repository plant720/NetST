"""Service package for business logic.

Public classes are loaded lazily so lightweight utilities such as
``service.process_service`` do not require GUI or file-encoding dependencies.
"""

__all__ = ['FileService', 'AnalysisService', 'AnalysisResult', 'AlignmentResult']


def __getattr__(name):
    if name == 'FileService':
        from service.file_service import FileService
        return FileService
    if name in {'AnalysisService', 'AnalysisResult', 'AlignmentResult'}:
        from service.analysis_service import AnalysisService, AnalysisResult, AlignmentResult
        return {
            'AnalysisService': AnalysisService,
            'AnalysisResult': AnalysisResult,
            'AlignmentResult': AlignmentResult,
        }[name]
    raise AttributeError(name)
