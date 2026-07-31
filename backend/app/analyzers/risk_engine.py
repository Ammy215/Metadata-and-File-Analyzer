from pathlib import Path
from typing import Dict, Any, List, Optional
from app.analyzers.base import BaseAnalyzer
from app.analyzers.entropy_analyzer import _COMPRESSION_EXPECTED_EXTENSIONS


class RiskEngine(BaseAnalyzer):
    """Engine for calculating risk scores - PROFESSIONAL GRADE."""

    # PROFESSIONAL risk weights - Tuned to avoid false positives
    RISK_WEIGHTS = {
        "critical_keyword_match": 35,  # Up from 25 - these are SERIOUS threats
        "high_keyword_match": 20,      # Up from 15 - actual malware patterns
        "medium_keyword_match": 0,     # DOWN from 8 - too many false positives!
        "yara_rule_match": 40,         # High - YARA catches real malware
        "high_entropy": 5,             # DOWN from 20 - compressed files are normal!
        "medium_entropy": 0,           # Compressed/encrypted = normal
        "dangerous_extension": 15,     # Executables are risky but not auto-fail
        "hidden_metadata": 8,          # Suspicious metadata
        "embedded_urls": 10,           # URLs in documents = possible phishing
        "no_author_metadata": 0,       # Many legit files lack author info
        "suspicious_producer": 5,      # Unknown PDF producer = minor flag
        "mime_mismatch": 15,           # Content doesn't match its extension
        "pe_suspicious_imports": 20,   # PE imports known process-injection APIs
        "pe_section_high_entropy": 10, # A single PE section is packed/obfuscated
        "pdf_has_javascript": 25,      # Embedded JS is the #1 malicious-PDF vector
        "excel_has_macros": 20,        # VBA macros are a common malware delivery path
        "excel_has_external_links": 8, # External refs = possible phishing/data-exfil
    }
    
    DANGEROUS_EXTENSIONS = {
        '.exe': 15, '.bat': 15, '.ps1': 12, '.vbs': 12,
        '.com': 10, '.scr': 15, '.pif': 10, '.cmd': 12,
        '.jar': 8, '.app': 10, '.msi': 10, '.dll': 12,
    }
    
    async def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Placeholder for risk engine. Actual calculation happens
        during analysis pipeline.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with risk info
        """
        return {
            "risk_score": 0,
            "verdict": "PENDING",
            "factors": []
        }
    
    @staticmethod
    def calculate_risk(
        threat_matches: List[Dict[str, Any]],
        entropy_score: float,
        file_extension: str,
        has_hidden_metadata: bool,
        yara_matches: int = 0,
        has_gps: bool = False,
        mime_mismatch: bool = False,
        pe_data: Optional[Dict[str, Any]] = None,
        pdf_data: Optional[Dict[str, Any]] = None,
        excel_data: Optional[Dict[str, Any]] = None,
    ) -> tuple:
        """
        Calculate overall risk score.

        Args:
            threat_matches: List of matched threats
            entropy_score: Shannon entropy value
            file_extension: File extension
            has_hidden_metadata: Whether hidden metadata exists
            yara_matches: Number of YARA rule matches
            has_gps: Whether GPS data is embedded
            mime_mismatch: Detected content type doesn't match the extension
                (e.g. a .txt that's actually an executable)
            pe_data: EXEAnalyzer output, if this file went through PE analysis
            pdf_data: PDFAnalyzer output, if this file went through PDF analysis
            excel_data: ExcelAnalyzer output, if this file went through Excel analysis

        Returns:
            Tuple of (risk_score, verdict, factors)
        """
        risk_score = 0
        factors = []
        
        # Count keyword matches by severity
        critical_count = sum(1 for m in threat_matches if m.get("severity") == "CRITICAL")
        high_count = sum(1 for m in threat_matches if m.get("severity") == "HIGH")
        medium_count = sum(1 for m in threat_matches if m.get("severity") == "MEDIUM")
        
        if critical_count > 0:
            risk_score += critical_count * RiskEngine.RISK_WEIGHTS["critical_keyword_match"]
            factors.append({
                "factor": "critical_keyword_match",
                "weight": RiskEngine.RISK_WEIGHTS["critical_keyword_match"],
                "score_delta": critical_count * RiskEngine.RISK_WEIGHTS["critical_keyword_match"],
                "detail": f"{critical_count} critical keywords found"
            })
        
        if high_count > 0:
            risk_score += high_count * RiskEngine.RISK_WEIGHTS["high_keyword_match"]
            factors.append({
                "factor": "high_keyword_match",
                "weight": RiskEngine.RISK_WEIGHTS["high_keyword_match"],
                "score_delta": high_count * RiskEngine.RISK_WEIGHTS["high_keyword_match"],
                "detail": f"{high_count} high-severity keywords found"
            })
        
        if medium_count > 0:
            # FIXED: Don't count MEDIUM matches for non-binary files!
            # These are too generic (password, admin, config appear in legit docs)
            # Only count them for binary files
            pass  # Skip MEDIUM severity keywords
        
        
        # Entropy-based scoring (FIXED: Don't penalize compression!)
        # Only flag VERY high entropy (7.5+) which indicates encryption -
        # but never for formats that are *expected* to be high-entropy from
        # their own legitimate compression (video/audio/archives), which
        # would otherwise false-positive on every single file of that type.
        if entropy_score > 7.5 and file_extension not in _COMPRESSION_EXPECTED_EXTENSIONS:
            risk_score += RiskEngine.RISK_WEIGHTS["high_entropy"]
            factors.append({
                "factor": "high_entropy",
                "weight": RiskEngine.RISK_WEIGHTS["high_entropy"],
                "score_delta": RiskEngine.RISK_WEIGHTS["high_entropy"],
                "detail": f"Very high entropy detected: {entropy_score:.2f} (possible encryption/packing)"
            })
        # Compressed files are normal, don't flag them!
        
        # Extension-based scoring
        if file_extension in RiskEngine.DANGEROUS_EXTENSIONS:
            delta = RiskEngine.DANGEROUS_EXTENSIONS[file_extension]
            risk_score += delta
            factors.append({
                "factor": "dangerous_extension",
                "weight": RiskEngine.RISK_WEIGHTS["dangerous_extension"],
                "score_delta": delta,
                "detail": f"Dangerous file extension: {file_extension}"
            })
        
        # GPS data embedded - privacy concern
        if has_gps:
            risk_score += 10
            factors.append({
                "factor": "gps_embedded",
                "weight": 10,
                "score_delta": 10,
                "detail": "GPS location data embedded in file metadata"
            })
        
        # Hidden metadata
        if has_hidden_metadata:
            risk_score += RiskEngine.RISK_WEIGHTS["hidden_metadata"]
            factors.append({
                "factor": "hidden_metadata",
                "weight": RiskEngine.RISK_WEIGHTS["hidden_metadata"],
                "score_delta": RiskEngine.RISK_WEIGHTS["hidden_metadata"],
                "detail": "Hidden/suspicious metadata detected"
            })
        
        # YARA matches
        if yara_matches > 0:
            delta = yara_matches * RiskEngine.RISK_WEIGHTS["yara_rule_match"]
            risk_score += delta
            factors.append({
                "factor": "yara_rule_match",
                "weight": RiskEngine.RISK_WEIGHTS["yara_rule_match"],
                "score_delta": delta,
                "detail": f"{yara_matches} YARA rules matched"
            })

        # MIME/extension mismatch - content doesn't match its claimed type
        if mime_mismatch:
            risk_score += RiskEngine.RISK_WEIGHTS["mime_mismatch"]
            factors.append({
                "factor": "mime_mismatch",
                "weight": RiskEngine.RISK_WEIGHTS["mime_mismatch"],
                "score_delta": RiskEngine.RISK_WEIGHTS["mime_mismatch"],
                "detail": f"File content doesn't match its {file_extension} extension"
            })

        # PE-specific signals. Note: pe_suspicious_imports can co-occur with
        # critical_keyword_match above if the same API name shows up both
        # as a printable string AND a parsed import - that's intentional,
        # not double-counting a single fact. They're independent detection
        # methods (naive string-scan vs. structured import-table parsing)
        # that can each catch what the other misses (e.g. packed strings
        # with an intact import table), so agreement between them is a
        # stronger signal, not a duplicate one.
        if pe_data and pe_data.get("is_pe"):
            if pe_data.get("has_suspicious_strings"):
                risk_score += RiskEngine.RISK_WEIGHTS["pe_suspicious_imports"]
                factors.append({
                    "factor": "pe_suspicious_imports",
                    "weight": RiskEngine.RISK_WEIGHTS["pe_suspicious_imports"],
                    "score_delta": RiskEngine.RISK_WEIGHTS["pe_suspicious_imports"],
                    "detail": "PE imports include known process-injection/loader APIs"
                })

            section_entropies = [s.get("entropy", 0) for s in pe_data.get("sections", [])]
            max_section_entropy = max(section_entropies) if section_entropies else 0
            if max_section_entropy > 7.0:
                risk_score += RiskEngine.RISK_WEIGHTS["pe_section_high_entropy"]
                factors.append({
                    "factor": "pe_section_high_entropy",
                    "weight": RiskEngine.RISK_WEIGHTS["pe_section_high_entropy"],
                    "score_delta": RiskEngine.RISK_WEIGHTS["pe_section_high_entropy"],
                    "detail": f"A PE section has entropy {max_section_entropy:.2f} (packed/obfuscated code)"
                })

        # PDF-specific signals
        if pdf_data and pdf_data.get("has_javascript"):
            risk_score += RiskEngine.RISK_WEIGHTS["pdf_has_javascript"]
            factors.append({
                "factor": "pdf_has_javascript",
                "weight": RiskEngine.RISK_WEIGHTS["pdf_has_javascript"],
                "score_delta": RiskEngine.RISK_WEIGHTS["pdf_has_javascript"],
                "detail": "PDF contains embedded JavaScript"
            })

        # Excel-specific signals
        if excel_data:
            if excel_data.get("has_macros"):
                risk_score += RiskEngine.RISK_WEIGHTS["excel_has_macros"]
                factors.append({
                    "factor": "excel_has_macros",
                    "weight": RiskEngine.RISK_WEIGHTS["excel_has_macros"],
                    "score_delta": RiskEngine.RISK_WEIGHTS["excel_has_macros"],
                    "detail": "Workbook contains VBA macros"
                })
            if excel_data.get("has_external_links"):
                risk_score += RiskEngine.RISK_WEIGHTS["excel_has_external_links"]
                factors.append({
                    "factor": "excel_has_external_links",
                    "weight": RiskEngine.RISK_WEIGHTS["excel_has_external_links"],
                    "score_delta": RiskEngine.RISK_WEIGHTS["excel_has_external_links"],
                    "detail": "Workbook references external files"
                })

        # Cap score at 100
        risk_score = min(100, max(0, risk_score))
        
        # PROFESSIONAL verdict thresholds (FIXED to reduce false positives!)
        if risk_score < 30:
            verdict = "SAFE"
        elif risk_score < 60:
            verdict = "SUSPICIOUS"
        elif risk_score < 80:
            verdict = "HIGH RISK"
        else:
            verdict = "CRITICAL"
        
        return risk_score, verdict, factors
