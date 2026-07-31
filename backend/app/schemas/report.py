from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class UploadResponse(BaseModel):
    """Response after file upload."""
    file_id: uuid.UUID
    original_name: str
    size_bytes: int
    message: str


class MetadataEntrySchema(BaseModel):
    """Schema for metadata entries."""
    category: str
    key: str
    value: Optional[str]
    flagged: bool = False


class ThreatMatchSchema(BaseModel):
    """Schema for threat matches."""
    rule_name: str
    severity: str
    description: Optional[str]
    matched_data: Optional[str]


class RiskBreakdownSchema(BaseModel):
    """Schema for risk scoring breakdown."""
    factor_name: str
    weight: float
    contribution: int
    details: Optional[str]


class EntropyResultSchema(BaseModel):
    """Schema for entropy analysis."""
    entropy_score: float
    classification: str
    details: Optional[Dict[str, Any]] = None


class AnalysisResultSchema(BaseModel):
    """Complete analysis result."""
    file_id: uuid.UUID
    original_name: str
    mime_type: Optional[str]
    size_bytes: int
    sha256: str
    md5: Optional[str]
    sha1: Optional[str]
    upload_time: datetime
    risk_score: int
    verdict: str
    analyzed: bool
    
    metadata: List[MetadataEntrySchema] = []
    threats: List[ThreatMatchSchema] = []
    risk_factors: List[RiskBreakdownSchema] = []
    entropy: Optional[EntropyResultSchema] = None


class AnalysisRequestSchema(BaseModel):
    """Request to trigger analysis."""
    file_id: uuid.UUID


class HistoryItemSchema(BaseModel):
    """Item in scan history."""
    file_id: uuid.UUID
    original_name: str
    upload_time: datetime
    risk_score: int
    verdict: str


class HistoryResponseSchema(BaseModel):
    """Paginated history response."""
    total: int
    page: int
    page_size: int
    items: List[HistoryItemSchema]


class ReportSchema(BaseModel):
    """Full security report."""
    file_id: uuid.UUID
    original_name: str
    mime_type: Optional[str]
    size_bytes: int
    hashes: Dict[str, str]
    analysis: AnalysisResultSchema
    generated_at: datetime


class StatsSchema(BaseModel):
    """Dashboard statistics."""
    total_files: int
    total_analyzed: int
    critical_files: int
    avg_risk_score: float
    top_threats: List[Dict[str, Any]]
