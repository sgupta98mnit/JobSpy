"""
Export API endpoints for downloading job search results.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional
import io

from ....models.export import ExportFormat, ExportResponse
from ....services.export_service import ExportService
from ....services.cache_service import search_results_cache
from ....models.errors import ExportError, ValidationError


router = APIRouter()
export_service = ExportService()


@router.get("/{search_id}")
async def export_search_results(
    search_id: str,
    format: ExportFormat = Query(default=ExportFormat.CSV, description="Export format"),
    include_description: bool = Query(default=True, description="Include job descriptions"),
    include_company_details: bool = Query(default=True, description="Include company details"),
    filename: Optional[str] = Query(default=None, description="Custom filename (without extension)")
) -> StreamingResponse:
    """
    Export job search results to the specified format.
    
    Args:
        search_id: Unique identifier for the search results
        format: Export format (currently only CSV supported)
        include_description: Whether to include job descriptions
        include_company_details: Whether to include company details
        filename: Custom filename for the download
        
    Returns:
        StreamingResponse: File download with appropriate headers
        
    Raises:
        HTTPException: If search results not found or export fails
    """
    try:
        # Retrieve search results from cache
        cache_entry = await search_results_cache.get_search_results(search_id)
        
        if cache_entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Search results not found for search_id: {search_id}. "
                       "Results may have expired or the search_id is invalid."
            )
        
        # Validate export request
        export_service.validate_export_request(cache_entry.jobs, format)
        
        # Generate export based on format
        if format == ExportFormat.CSV:
            file_bytes, metadata = await export_service.export_jobs_to_csv(
                jobs=cache_entry.jobs,
                search_id=search_id,
                include_description=include_description,
                include_company_details=include_company_details,
                filename=filename
            )
            
            # Create streaming response for file download
            file_stream = io.BytesIO(file_bytes)
            
            return StreamingResponse(
                io.BytesIO(file_bytes),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={metadata.filename}",
                    "Content-Length": str(metadata.file_size_bytes),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Export format '{format}' is not supported. Supported formats: {export_service.get_supported_formats()}"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {e.message}"
        )
    except ExportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during export: {str(e)}"
        )


@router.get("/{search_id}/info")
async def get_export_info(search_id: str) -> dict:
    """
    Get information about available export data for a search.
    
    Args:
        search_id: Unique identifier for the search results
        
    Returns:
        Dictionary with export information
        
    Raises:
        HTTPException: If search results not found
    """
    try:
        cache_entry = await search_results_cache.get_search_results(search_id)
        
        if cache_entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Search results not found for search_id: {search_id}"
            )
        
        return {
            "search_id": search_id,
            "total_jobs": len(cache_entry.jobs),
            "search_timestamp": cache_entry.timestamp.isoformat(),
            "search_metadata": cache_entry.search_metadata,
            "supported_formats": export_service.get_supported_formats(),
            "estimated_csv_size_kb": len(cache_entry.jobs) * 2  # Rough estimate: 2KB per job
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving export info: {str(e)}"
        )