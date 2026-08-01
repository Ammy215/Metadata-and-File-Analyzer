import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from collections import Counter
import math
from app.analyzers.base import BaseAnalyzer
from app.utils.file_validator import FileValidator

_CHUNK_SIZE = 1024 * 1024  # 1 MiB - streamed rather than loading the whole
                            # file (up to 2 GB permitted for video/archive)
                            # into memory just to count byte frequencies.

# Formats that are *expected* to sit at 7.5+ Shannon entropy purely because
# of their own (legitimate) compression - h264/aac/mp3/zip etc. are
# statistically indistinguishable from encrypted/packed data at the byte
# level. Without this, every single video/audio/archive upload gets
# mislabeled "Obfuscated / Encrypted" / CRITICAL, which is a false positive
# on 100% of files in those categories, not an edge case.
#
# Modern Office formats (.xlsx/.docx/.pptx and their OpenDocument
# equivalents) are also zip containers under the hood and hit the same
# false positive - confirmed via a real generated .xlsx during testing.
# Legacy .doc/.xls/.ppt (OLE2 Compound File Binary Format) are NOT
# zip-compressed, so they're deliberately left out here.
_OOXML_EXTENSIONS = {'.xlsx', '.docx', '.pptx', '.odt', '.ods', '.odp'}

# PDF is a different case from the formats above: unlike video/audio/zip
# containers, a PDF is NOT *guaranteed* to be high-entropy - a plain,
# uncompressed, text-only PDF can legitimately sit at low entropy. But any
# PDF carrying a meaningful amount of embedded image data (DCTDecode/
# JPXDecode - already-compressed JPEG/JPEG2000 bytes) or a FlateDecode
# -compressed content stream - which is the default in effectively every
# real-world PDF writer (Prawn, ReportLab, wkhtmltopdf, LibreOffice, Word's
# "Save as PDF", etc.) - lands in the same 7.5-8.0 range purely from that
# legitimate compression, confirmed both by a real user-generated Prawn PDF
# (7.94/8.0, flagged CRITICAL/"Obfuscated / Encrypted") and reproduced here
# with a synthetic PDF containing only a placeholder image (7.98/8.0). PDF
# is included here on that basis: in practice this is the common case, not
# an edge case. Trade-off: this also stops flagging a genuinely
# natively-encrypted PDF (PDF supports RC4/AES via /Encrypt) via entropy -
# but there's no dedicated /Encrypt detector in PDFAnalyzer today either, so
# this heuristic wasn't reliably catching that case in a targeted way to
# begin with; a raw /Encrypt marker check (mirroring PDFAnalyzer's existing
# _JS_MARKERS/_FORM_MARKERS pattern) would be a strictly better replacement
# signal if that's ever wanted.
_COMPRESSION_EXPECTED_EXTENSIONS = (
    FileValidator.VIDEO_EXTENSIONS
    | FileValidator.AUDIO_EXTENSIONS
    | FileValidator.ARCHIVE_EXTENSIONS
    | _OOXML_EXTENSIONS
    | {'.pdf'}
)


class EntropyAnalyzer(BaseAnalyzer):
    """Analyzer for Shannon entropy calculation."""

    async def analyze(self, file_path: Path, file_extension: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate Shannon entropy and byte distribution.

        Args:
            file_path: Path to the file
            file_extension: Lowercased extension (e.g. ".mp4"), used to avoid
                mislabeling formats that are expected to be high-entropy

        Returns:
            Dictionary with entropy score and classification
        """
        return await asyncio.to_thread(self._analyze_sync, file_path, file_extension)

    def _analyze_sync(self, file_path: Path, file_extension: Optional[str]) -> Dict[str, Any]:
        counter: Counter = Counter()
        total_size = 0
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(_CHUNK_SIZE), b''):
                counter.update(chunk)
                total_size += len(chunk)

        entropy = self._calculate_entropy(counter, total_size)
        byte_dist = {str(k): v for k, v in counter.items()}
        compression_expected = file_extension in _COMPRESSION_EXPECTED_EXTENSIONS
        classification = self._classify_entropy(entropy, compression_expected)

        if compression_expected:
            # High entropy here just confirms the format's own compression
            # worked as designed - it isn't a risk signal for these types.
            risk = "LOW"
        elif entropy < 4.0:
            risk = "LOW"
        elif entropy < 6.5:
            risk = "MEDIUM"
        elif entropy < 7.5:
            risk = "HIGH"
        else:
            risk = "CRITICAL"

        return {
            "entropy": round(entropy, 4),  # kept alongside entropy_score for backward compatibility
            "entropy_score": round(entropy, 4),
            "classification": classification,
            "is_compressed": compression_expected or (6.5 <= entropy < 7.5),
            "is_encrypted": (not compression_expected) and entropy >= 7.5,
            "risk": risk,
            "byte_distribution": byte_dist,
            "file_size_bytes": total_size,
        }

    @staticmethod
    def _calculate_entropy(counter: Counter, total_size: int) -> float:
        """Calculate Shannon entropy from an aggregated byte-frequency counter."""
        if total_size == 0:
            return 0.0

        entropy = 0.0
        for count in counter.values():
            p = count / total_size
            entropy -= p * math.log2(p)

        return entropy

    @staticmethod
    def _classify_entropy(entropy: float, compression_expected: bool = False) -> str:
        """Classify entropy level - PROFESSIONAL GRADE."""
        if compression_expected:
            return "Compressed (expected for this file type)"
        if entropy < 4.0:
            return "Normal"
        elif entropy < 6.5:
            return "Compressed"
        elif entropy < 7.5:
            return "Encrypted / Packed"
        else:
            return "Obfuscated / Encrypted"
