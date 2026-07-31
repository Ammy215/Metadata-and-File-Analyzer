import asyncio
from pathlib import Path
from typing import Dict, Any, List
import re
import logging
from app.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

_BINARY_CHUNK_SIZE = 1024 * 1024  # 1 MiB
_MIN_STRING_LEN = 4


class KeywordAnalyzer(BaseAnalyzer):
    """Analyzer for detecting suspicious keywords and patterns."""

    # Suspicious keywords with severity levels
    SUSPICIOUS_KEYWORDS = {
        "CRITICAL": [
            r"powershell\s+-enc",
            r"powershell\s+-w\s+hidden",
            r"cmd\.exe\s+/c",
            r"base64_decode",
            r"eval\s*\(",
            r"exec\s*\(",
            r"shell_exec",
            r"system\s*\(",
            r"os\.system",
            r"subprocess\.call",
            r"wget\s+http",
            r"curl\s+http",
            r"\.download\(",
            r"invoke-expression",
            r"iex\s*\(",
            r"createremotethread",
            r"virtualalloc",
            r"writeprocessmemory",
        ],
        "HIGH": [
            r"autorun",
            r"payload",
            r"shellcode",
            r"exploit",
            r"rootkit",
            r"keylogger",
            r"ransomware",
            r"encrypt.*file",
            r"delete.*shadow",
            r"vssadmin",
            r"mimikatz",
            r"metasploit",
            r"createprocess",
            r"winexec",
        ],
        "MEDIUM": [
            r"password\s*=",
            r"passwd\s*=",
            r"api[_-]?key\s*=",
            r"secret\s*=",
            r"token\s*=",
            r"hidden",
            r"obfuscat",
            r"bypass",
            r"disable.*av",
            r"antivirus",
            r"firewall",
        ],
        "LOW": [
            r"download",
            r"execute",
            r"suspicious",
            r"malware",
            r"virus",
            r"trojan",
            r"backdoor",
        ]
    }

    SUSPICIOUS_URLS = re.compile(
        r'https?://[^\s\'"<>]+',
        re.IGNORECASE
    )

    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze file content for suspicious keywords and patterns.

        Args:
            file_path: Path to the file (can be string or Path object)

        Returns:
            Dictionary with keyword matches and risk score
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        return await asyncio.to_thread(self._analyze_sync, file_path)

    def _analyze_sync(self, file_path: Path) -> Dict[str, Any]:
        matches = []
        text = ""
        text_extracted = False

        try:
            text = self._extract_text(file_path)
            text_extracted = len(text) > 0

            if text_extracted:
                matches = self._scan_text(text)

        except Exception as e:
            logger.error(f"Keyword analysis error: {e}")

        # Calculate risk score based on matches
        risk_score = 0
        for match in matches:
            if match['severity'] == 'CRITICAL':
                risk_score += 40
            elif match['severity'] == 'HIGH':
                risk_score += 20
            elif match['severity'] == 'MEDIUM':
                risk_score += 10
            elif match['severity'] == 'LOW':
                risk_score += 5

        # Cap at 100
        risk_score = min(risk_score, 100)

        return {
            "matches": matches,
            "total_matches": len(matches),
            "risk_score": risk_score,
            "text_extracted": text_extracted,
            "text_length": len(text)
        }

    def _extract_text(self, file_path: Path) -> str:
        """Extract readable text from any supported file type."""
        text = ""
        extension = file_path.suffix.lower()

        try:
            # PDF extraction
            if extension == '.pdf':
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = "\n".join(
                        page.extract_text() or ""
                        for page in pdf.pages
                    )

            # DOCX extraction
            elif extension in ['.docx', '.doc']:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join(p.text for p in doc.paragraphs)

            # Plain text files
            elif extension in ['.txt', '.log', '.csv', '.json', '.xml', '.html',
                              '.js', '.py', '.sh', '.bat', '.ps1', '.vbs', '.cmd']:
                with open(file_path, 'rb') as f:
                    raw = f.read()
                text = self._decode_text(raw)

            # Binary files - extract ASCII strings, streamed rather than
            # loading the whole file (up to 500MB permitted) into memory.
            elif extension in ['.exe', '.dll', '.bin', '.so']:
                text = self._extract_binary_strings(file_path)

        except Exception as e:
            logger.error(f"Text extraction error for {file_path}: {e}")

        return text

    @staticmethod
    def _extract_binary_strings(file_path: Path) -> str:
        """Stream-extract printable ASCII strings (min 4 chars) from a
        binary file in fixed-size chunks, instead of loading the whole
        file (up to 500MB permitted) into memory at once.

        A run of printable bytes can span a chunk boundary. Rather than
        carrying a small fixed-size window (which can still split a long
        keyword right where the split falls), if the last run in the
        current buffer touches the very end of it - meaning it might not
        be finished yet - the WHOLE run is held back and prepended to the
        next chunk before re-matching, however long it is. This keeps
        keyword integrity regardless of where a split lands. Worst case
        for a pathological file that's one giant uninterrupted printable
        blob, this carries forward a large chunk of the file - an
        acceptable tradeoff against ever missing a real match.
        """
        pattern = re.compile(rb'[\x20-\x7e]+')
        found = []
        carry = b''

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(_BINARY_CHUNK_SIZE), b''):
                data = carry + chunk
                matches = list(pattern.finditer(data))

                if matches and matches[-1].end() == len(data):
                    # Last run touches the buffer's end - could continue
                    # into the next chunk, don't finalize it yet.
                    carry = data[matches[-1].start():]
                    matches = matches[:-1]
                else:
                    carry = b''

                found.extend(
                    m.group().decode('ascii', errors='ignore')
                    for m in matches if len(m.group()) >= _MIN_STRING_LEN
                )

        if len(carry) >= _MIN_STRING_LEN:
            found.append(carry.decode('ascii', errors='ignore'))

        return " ".join(found)

    @staticmethod
    def _decode_text(raw: bytes) -> str:
        """Decode file bytes to text, honoring a BOM if present.

        Plain-text files aren't always UTF-8 - a blind utf-8 decode on a
        UTF-16 file silently mangles every character (each byte gets
        interleaved with a null byte), which makes every keyword pattern
        fail to match without raising any error. Check for a BOM first.
        """
        if raw.startswith(b'\xff\xfe\x00\x00') or raw.startswith(b'\x00\x00\xfe\xff'):
            return raw.decode('utf-32', errors='ignore')
        if raw.startswith(b'\xff\xfe'):
            return raw.decode('utf-16-le', errors='ignore')
        if raw.startswith(b'\xfe\xff'):
            return raw.decode('utf-16-be', errors='ignore')
        if raw.startswith(b'\xef\xbb\xbf'):
            return raw.decode('utf-8-sig', errors='ignore')
        return raw.decode('utf-8', errors='ignore')

    def _scan_text(self, text: str) -> List[Dict[str, Any]]:
        """Scan text for suspicious patterns."""
        matches = []
        lines = text.split("\n")

        # Scan for keywords by severity
        for severity, patterns in self.SUSPICIOUS_KEYWORDS.items():
            for pattern in patterns:
                try:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Get context (limit to 200 chars)
                            context = line.strip()[:200]

                            matches.append({
                                "match_type": "keyword",
                                "matched_value": pattern,
                                "severity": severity,
                                "line_number": i,
                                "context_line": context
                            })

                            # Only report first match of each pattern to avoid spam
                            break
                except Exception:
                    pass

        # Scan for suspicious URLs
        for i, line in enumerate(lines, 1):
            try:
                for url_match in self.SUSPICIOUS_URLS.finditer(line):
                    url = url_match.group()
                    # Skip common safe domains
                    if not any(domain in url.lower() for domain in
                              ['google.com', 'microsoft.com', 'apple.com', 'github.com']):
                        matches.append({
                            "match_type": "suspicious_url",
                            "matched_value": url,
                            "severity": "HIGH",
                            "line_number": i,
                            "context_line": line.strip()[:200]
                        })
            except Exception:
                pass

        return matches
