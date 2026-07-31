"""Maps a file extension to the one extra, format-specific analyzer that
should run for it, on top of the universal analyzer set (Hash, Entropy,
Metadata, Keyword, MIME, YARA - which run for every file regardless of type).

Reuses FileValidator's extension-category sets rather than keeping a 4th
independent copy of "what counts as a video extension".
"""
from typing import Optional, Type

from app.analyzers.base import BaseAnalyzer
from app.utils.file_validator import FileValidator

PDF_EXTENSIONS = {'.pdf'}
# openpyxl only opens the modern zip-based .xlsx format. Legacy .xls (OLE
# binary format) and .ods (OpenDocument) need different libraries entirely,
# and .csv/.tsv are plain-text delimited files, not spreadsheet binaries -
# none of those route here. They still get the universal analyzer set
# (keyword_analyzer already handles .csv as plain text).
EXCEL_EXTENSIONS = {'.xlsx'}
MARKDOWN_EXTENSIONS = {'.md', '.markdown'}

# PE (Portable Executable) is a Windows-specific binary format that pefile
# understands. .app/.msi/.dmg/.deb/.rpm/.apk/.jar are executable/installer
# formats too, but none of them are PE files, so they must NOT route here -
# pefile.PE() would just fail to parse them.
PE_EXTENSIONS = {'.exe', '.dll'}


def get_extra_analyzer(extension: str) -> Optional[Type[BaseAnalyzer]]:
    """Return the extra analyzer class for this extension, or None if only
    the universal analyzer set applies."""
    ext = extension.lower()

    if ext in PDF_EXTENSIONS:
        from app.analyzers.specialized_analyzers import PDFAnalyzer
        return PDFAnalyzer
    if ext in EXCEL_EXTENSIONS:
        from app.analyzers.specialized_analyzers import ExcelAnalyzer
        return ExcelAnalyzer
    if ext in MARKDOWN_EXTENSIONS:
        from app.analyzers.specialized_analyzers import MarkdownAnalyzer
        return MarkdownAnalyzer
    if ext in FileValidator.VIDEO_EXTENSIONS:
        from app.analyzers.specialized_analyzers import VideoAnalyzer
        return VideoAnalyzer
    if ext in FileValidator.AUDIO_EXTENSIONS:
        from app.analyzers.specialized_analyzers import AudioAnalyzer
        return AudioAnalyzer
    if ext in PE_EXTENSIONS:
        from app.analyzers.specialized_analyzers import EXEAnalyzer
        return EXEAnalyzer
    return None
