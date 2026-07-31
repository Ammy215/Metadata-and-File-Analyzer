import asyncio
import magic
from pathlib import Path
from typing import Dict, Any
from app.analyzers.base import BaseAnalyzer


class MimeAnalyzer(BaseAnalyzer):
    """Analyzer for MIME type detection."""

    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Detect MIME type using python-magic.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with MIME type
        """
        return await asyncio.to_thread(self._analyze_sync, file_path)

    @staticmethod
    def _analyze_sync(file_path: Path) -> Dict[str, Any]:
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(str(file_path))
        except Exception:
            mime_type = "application/octet-stream"

        return {
            "mime_type": mime_type,
        }
