from sqlalchemy import Column, String, Integer, BigInteger, Boolean, TIMESTAMP, Float, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from typing import TYPE_CHECKING
from app.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    from app.models.user import User


class UploadedFile(Base):
    """Model for uploaded files."""
    __tablename__ = "uploaded_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False, unique=True)
    extension = Column(String)
    mime_type = Column(String)
    size_bytes = Column(BigInteger)
    # Indexed for fast hash lookups, but intentionally NOT unique: sha256
    # identifies file *content*, not an upload event. Two different users
    # uploading identical bytes must get independent rows (own audit trail,
    # own risk-score/verdict lifecycle) - a table-wide unique constraint here
    # would make one user's upload fail/collide based on another user's
    # prior upload of the same content, breaking per-user isolation.
    sha256 = Column(String, nullable=False, index=True)
    md5 = Column(String)
    sha1 = Column(String)
    upload_time = Column(TIMESTAMP(timezone=True), default=_utcnow)
    analyzed = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)
    verdict = Column(String)  # SAFE | SUSPICIOUS | HIGH_RISK | CRITICAL
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    metadata_entries = relationship("MetadataEntry", back_populates="file", cascade="all, delete-orphan")
    threat_matches = relationship("ThreatMatch", back_populates="file", cascade="all, delete-orphan")
    risk_breakdowns = relationship("RiskBreakdown", back_populates="file", cascade="all, delete-orphan")
    # A file has exactly one entropy result per analysis run - true 1:1,
    # enforced by the unique constraint on EntropyResult.file_id below.
    entropy_result = relationship("EntropyResult", back_populates="file", cascade="all, delete-orphan", uselist=False)


class MetadataEntry(Base):
    """Model for file metadata entries."""
    __tablename__ = "metadata_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text)
    flagged = Column(Boolean, nullable=False, default=False)

    # Relationship
    file = relationship("UploadedFile", back_populates="metadata_entries")


class ThreatMatch(Base):
    """Model for threat detection matches."""
    __tablename__ = "threat_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # LOW | MEDIUM | HIGH | CRITICAL
    description = Column(Text)
    matched_data = Column(Text)
    
    # Relationship
    file = relationship("UploadedFile", back_populates="threat_matches")


class RiskBreakdown(Base):
    """Model for risk factor breakdown."""
    __tablename__ = "risk_breakdowns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False, index=True)
    factor_name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    contribution = Column(Integer, nullable=False)
    details = Column(Text)
    
    # Relationship
    file = relationship("UploadedFile", back_populates="risk_breakdowns")


class EntropyResult(Base):
    """Model for entropy analysis results."""
    __tablename__ = "entropy_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False, unique=True, index=True)
    entropy_score = Column(Float, nullable=False)
    classification = Column(String, nullable=False)  # LOW | MEDIUM | HIGH
    details = Column(JSON)

    # Relationship
    file = relationship("UploadedFile", back_populates="entropy_result")
