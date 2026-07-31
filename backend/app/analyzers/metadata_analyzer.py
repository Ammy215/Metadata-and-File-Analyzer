import asyncio
import piexif
from pathlib import Path
from typing import Dict, Any, List
import os
from datetime import datetime
from app.analyzers.base import BaseAnalyzer


class MetadataAnalyzer(BaseAnalyzer):
    """Analyzer for extracting file metadata."""

    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata based on file type.

        Args:
            file_path: Path to the file (can be string or Path object)

        Returns:
            Dictionary with metadata entries
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        return await asyncio.to_thread(self._analyze_sync, file_path)

    def _analyze_sync(self, file_path: Path) -> Dict[str, Any]:
        metadata = {"entries": [], "flagged_items": []}

        # Always extract system metadata first
        metadata["entries"].extend(self._extract_system_metadata(file_path))

        extension = file_path.suffix.lower()

        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            metadata["entries"].extend(self._extract_image_exif(file_path))
        elif extension == '.pdf':
            metadata["entries"].extend(self._extract_pdf_metadata(file_path))
        elif extension in ['.docx', '.doc']:
            metadata["entries"].extend(self._extract_docx_metadata(file_path))
        elif extension in ['.exe', '.dll']:
            metadata["entries"].extend(self._extract_pe_metadata(file_path))

        # Check for hidden/suspicious metadata
        metadata["flagged_items"] = self._check_suspicious_metadata(metadata["entries"])

        return metadata

    def _extract_system_metadata(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract basic system metadata for any file."""
        entries = []
        try:
            stat = os.stat(file_path)

            entries.append({
                "category": "system",
                "meta_key": "filename",
                "meta_value": file_path.name,
                "flagged": False,
            })

            entries.append({
                "category": "system",
                "meta_key": "size_bytes",
                "meta_value": str(stat.st_size),
                "flagged": False,
            })

            entries.append({
                "category": "system",
                "meta_key": "size_human",
                "meta_value": self._human_readable_size(stat.st_size),
                "flagged": False,
            })

            entries.append({
                "category": "system",
                "meta_key": "created",
                "meta_value": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "flagged": False,
            })

            entries.append({
                "category": "system",
                "meta_key": "modified",
                "meta_value": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "flagged": False,
            })

            entries.append({
                "category": "system",
                "meta_key": "extension",
                "meta_value": file_path.suffix.lower(),
                "flagged": False,
            })

        except Exception:
            pass

        return entries

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _extract_image_exif(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract EXIF data from images."""
        entries = []
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS

            with Image.open(file_path) as img:
                # Basic image info
                entries.append({
                    "category": "image",
                    "meta_key": "format",
                    "meta_value": str(img.format),
                    "flagged": False,
                })

                entries.append({
                    "category": "image",
                    "meta_key": "mode",
                    "meta_value": str(img.mode),
                    "flagged": False,
                })

                entries.append({
                    "category": "image",
                    "meta_key": "size",
                    "meta_value": f"{img.width}x{img.height}",
                    "flagged": False,
                })

                # Extract EXIF (getexif() is Pillow's public API;
                # _getexif() is a private/legacy method)
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)

                        # Check for GPS data
                        if tag == "GPSInfo":
                            gps_data = {}
                            for gps_tag_id in value:
                                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                gps_data[gps_tag] = value[gps_tag_id]

                            entries.append({
                                "category": "exif",
                                "meta_key": "GPS_DETECTED",
                                "meta_value": "GPS location data present",
                                "flagged": True,  # Always flag GPS
                            })
                        else:
                            try:
                                # Convert to string safely
                                value_str = str(value)
                                if len(value_str) > 200:
                                    value_str = value_str[:200] + "..."

                                entries.append({
                                    "category": "exif",
                                    "meta_key": str(tag),
                                    "meta_value": value_str,
                                    "flagged": False,
                                })
                            except Exception:
                                pass
        except Exception:
            pass

        return entries

    def _extract_pdf_metadata(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract metadata from PDF."""
        entries = []
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                # Add page count
                entries.append({
                    "category": "pdf",
                    "meta_key": "pages",
                    "meta_value": str(len(pdf.pages)),
                    "flagged": False,
                })

                # Extract metadata
                if pdf.metadata:
                    for key, value in pdf.metadata.items():
                        if value:
                            # Check for suspicious creators/producers
                            is_flagged = False
                            if key in ['Creator', 'Producer'] and value.lower() in ['unknown', '', 'none']:
                                is_flagged = True

                            entries.append({
                                "category": "pdf",
                                "meta_key": str(key),
                                "meta_value": str(value),
                                "flagged": is_flagged,
                            })
        except Exception:
            pass

        return entries

    def _extract_docx_metadata(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract metadata from DOCX."""
        entries = []
        try:
            from docx import Document

            doc = Document(file_path)
            props = doc.core_properties

            # Extract core properties
            for prop in ['author', 'created', 'modified', 'subject', 'title', 'last_modified_by', 'revision']:
                value = getattr(props, prop, None)
                if value:
                    entries.append({
                        "category": "docx",
                        "meta_key": prop,
                        "meta_value": str(value),
                        "flagged": False,
                    })

            # Add paragraph count
            entries.append({
                "category": "docx",
                "meta_key": "paragraph_count",
                "meta_value": str(len(doc.paragraphs)),
                "flagged": False,
            })
        except Exception:
            pass

        return entries

    def _extract_pe_metadata(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract metadata from PE (EXE/DLL) files."""
        entries = []
        pe = None
        try:
            import pefile

            pe = pefile.PE(str(file_path))

            entries.append({
                "category": "pe",
                "meta_key": "machine",
                "meta_value": hex(pe.FILE_HEADER.Machine),
                "flagged": False,
            })

            entries.append({
                "category": "pe",
                "meta_key": "timestamp",
                "meta_value": str(pe.FILE_HEADER.TimeDateStamp),
                "flagged": False,
            })

            entries.append({
                "category": "pe",
                "meta_key": "subsystem",
                "meta_value": str(pe.OPTIONAL_HEADER.Subsystem),
                "flagged": False,
            })

            # Extract sections
            section_info = []
            for section in pe.sections:
                section_info.append({
                    "name": section.Name.decode().strip('\x00'),
                    "virtual_size": section.Misc_VirtualSize,
                    "raw_size": section.SizeOfRawData,
                    "entropy": round(section.get_entropy(), 4)
                })

            entries.append({
                "category": "pe",
                "meta_key": "sections",
                "meta_value": str(len(section_info)),
                "flagged": False,
            })

            # Check for imports
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                import_count = len(pe.DIRECTORY_ENTRY_IMPORT)
                entries.append({
                    "category": "pe",
                    "meta_key": "imports",
                    "meta_value": str(import_count),
                    "flagged": False,
                })

        except Exception:
            pass
        finally:
            if pe is not None:
                pe.close()

        return entries

    @staticmethod
    def _check_suspicious_metadata(entries: List[Dict[str, Any]]) -> List[str]:
        """Check for suspicious metadata patterns."""
        suspicious = []

        suspicious_keywords = [
            'password', 'confidential', 'secret', 'private',
            'administrator', 'admin', 'test', 'temp'
        ]

        for entry in entries:
            value = entry.get("meta_value", "").lower()
            for keyword in suspicious_keywords:
                if keyword in value:
                    suspicious.append(f"{entry.get('meta_key')}: {entry.get('meta_value')}")
                    entry["flagged"] = True

        return suspicious
