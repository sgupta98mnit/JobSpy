"""
Export-related Pydantic models for the job search web application.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    # Future formats could be added here (JSON, Excel, etc.)


class ExportRequest(BaseModel):
    """
    Model for export request parameters.
    """
    search_id: str = Field(
        description="Unique identifier for the search results to export"
    )
    format: ExportFormat = Field(
        default=ExportFormat.CSV,
        description="Export format (currently only CSV supported)"
    )
    include_description: bool = Field(
        default=True,
        description="Whether to include job descriptions in export"
    )
    include_company_details: bool = Field(
        default=True,
        description="Whether to include detailed company information"
    )
    filename: Optional[str] = Field(
        default=None,
        description="Custom filename for the export (without extension)"
    )


class ExportMetadata(BaseModel):
    """
    Metadata about an export operation.
    """
    export_id: str = Field(
        description="Unique identifier for this export"
    )
    search_id: str = Field(
        description="Search ID that was exported"
    )
    format: ExportFormat = Field(
        description="Export format used"
    )
    total_jobs_exported: int = Field(
        ge=0,
        description="Number of jobs included in the export"
    )
    export_timestamp: datetime = Field(
        description="When the export was generated"
    )
    file_size_bytes: int = Field(
        ge=0,
        description="Size of the exported file in bytes"
    )
    filename: str = Field(
        description="Generated filename for the export"
    )


class ExportResponse(BaseModel):
    """
    Response model for export operations.
    """
    success: bool = Field(
        description="Whether the export was successful"
    )
    metadata: Optional[ExportMetadata] = Field(
        default=None,
        description="Export metadata (only present if successful)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message (only present if failed)"
    )