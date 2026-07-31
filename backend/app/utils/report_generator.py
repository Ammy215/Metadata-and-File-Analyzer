import asyncio
import html
from typing import Dict, Any
from datetime import datetime, timezone


class ReportGenerator:
    """Generator for security reports."""

    @staticmethod
    def generate_report(
        file_data: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate complete security report.

        Args:
            file_data: File information
            analysis_data: Analysis results

        Returns:
            Dictionary representing the report
        """
        report = {
            "file_id": str(file_data.get("id")),
            "report_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "file_info": {
                "name": file_data.get("original_name"),
                "mime_type": file_data.get("mime_type"),
                "size_bytes": file_data.get("size_bytes"),
                "extension": file_data.get("extension"),
            },
            "hashes": {
                "sha256": file_data.get("sha256"),
                "md5": file_data.get("md5"),
                "sha1": file_data.get("sha1"),
            },
            "risk_assessment": {
                "score": file_data.get("risk_score", 0),
                "verdict": file_data.get("verdict", "UNKNOWN"),
            },
            "detailed_analysis": analysis_data,
            "recommendations": ReportGenerator._get_recommendations(
                file_data.get("verdict", "UNKNOWN")
            ),
        }

        return report

    @staticmethod
    def _get_recommendations(verdict: str) -> list:
        """Get security recommendations based on verdict."""
        recommendations = {
            "SAFE": [
                "File appears safe",
                "Normal entropy levels detected",
                "No suspicious patterns found"
            ],
            "SUSPICIOUS": [
                "Exercise caution with this file",
                "Review metadata before opening",
                "Consider isolating on test system"
            ],
            "HIGH RISK": [
                "Do not open on production systems",
                "Isolate on sandboxed environment",
                "Contact security team for review"
            ],
            "CRITICAL": [
                "QUARANTINE IMMEDIATELY",
                "Do not open or execute",
                "Report to security team",
                "Scan system with antivirus"
            ],
        }

        return recommendations.get(verdict, ["Unknown verdict"])

    @staticmethod
    async def export_pdf(report: Dict[str, Any]) -> bytes:
        """
        Render the report as PDF bytes.

        Runs WeasyPrint's synchronous, CPU-bound rendering in a thread so
        it doesn't block the event loop - the same pattern used for every
        analyzer's blocking-I/O work.
        """
        from weasyprint import HTML

        html_content = ReportGenerator._create_html_report(report)
        return await asyncio.to_thread(lambda: HTML(string=html_content).write_pdf())

    @staticmethod
    def _create_html_report(report: Dict[str, Any]) -> str:
        """Create HTML representation of report.

        Every value that traces back to user-controlled data (filename,
        MIME type, etc.) is HTML-escaped. This previously interpolated
        those values raw into the template - a crafted filename could
        inject arbitrary HTML/CSS, and since WeasyPrint fetches external
        resources referenced in the HTML it renders, that was a realistic
        SSRF vector too, not just cosmetic corruption.
        """
        def esc(value) -> str:
            return html.escape(str(value)) if value is not None else ""

        verdict_raw = report['risk_assessment']['verdict']
        verdict_css_class = verdict_raw.lower().replace(' ', '-')  # "HIGH RISK" -> "high-risk"

        recommendations_html = "".join(
            f"<li>{esc(rec)}</li>" for rec in report['recommendations']
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>FileShield Security Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #0a0f1e; color: #00d4ff; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #1e2d45; }}
                .verdict {{ font-size: 24px; font-weight: bold; }}
                .safe {{ color: #00ff88; }}
                .suspicious {{ color: #ffaa00; }}
                .high-risk {{ color: #ff4466; }}
                .critical {{ color: #ff0000; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #1e2d45; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FileShield Security Report</h1>
                <p>Generated: {esc(report['generated_at'])}</p>
            </div>

            <div class="section">
                <h2>File Information</h2>
                <table>
                    <tr><td><strong>Name:</strong></td><td>{esc(report['file_info']['name'])}</td></tr>
                    <tr><td><strong>MIME Type:</strong></td><td>{esc(report['file_info']['mime_type'])}</td></tr>
                    <tr><td><strong>Size:</strong></td><td>{esc(report['file_info']['size_bytes'])} bytes</td></tr>
                </table>
            </div>

            <div class="section">
                <h2>Risk Assessment</h2>
                <p class="verdict"><span class="verdict {esc(verdict_css_class)}">{esc(verdict_raw)}</span></p>
                <p>Risk Score: {esc(report['risk_assessment']['score'])}/100</p>
            </div>

            <div class="section">
                <h2>Hashes</h2>
                <p><strong>SHA256:</strong> {esc(report['hashes']['sha256'])}</p>
                <p><strong>MD5:</strong> {esc(report['hashes']['md5'])}</p>
                <p><strong>SHA1:</strong> {esc(report['hashes']['sha1'])}</p>
            </div>

            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    {recommendations_html}
                </ul>
            </div>
        </body>
        </html>
        """
        return html_content
