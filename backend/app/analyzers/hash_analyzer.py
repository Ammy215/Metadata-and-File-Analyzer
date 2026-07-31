import asyncio
import hashlib
from pathlib import Path
from typing import Dict, Any
from app.analyzers.base import BaseAnalyzer


class HashAnalyzer(BaseAnalyzer):
    """Analyzer for computing file hashes."""

    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Compute SHA256, MD5, and SHA1 hashes.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with hash values
        """
        return await asyncio.to_thread(self._analyze_sync, file_path)

    @staticmethod
    def _analyze_sync(file_path: Path) -> Dict[str, Any]:
        sha256_hash = hashlib.sha256()
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()

        # Read file in chunks to handle large files
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
                sha1_hash.update(chunk)

        return {
            "sha256": sha256_hash.hexdigest(),
            "md5": md5_hash.hexdigest(),
            "sha1": sha1_hash.hexdigest(),
        }
