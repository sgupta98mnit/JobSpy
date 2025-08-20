"""
Export service for generating CSV files from job search results.
"""

import uuid
import io
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from ..models.job import WebJobPost
from ..models.export import ExportFormat, ExportMetadata
from ..models.errors import ExportError, ValidationError


class ExportService:
    """
    Service for exporting job search results to various formats.
    """
    
    def __init__(self):
        """Initialize the export service."""
        pass
    
    async def export_jobs_to_csv(
        self,
        jobs: List[WebJobPost],
        search_id: str,
        include_description: bool = True,
        include_company_details: bool = True,
        filename: Optional[str] = None
    ) -> tuple[bytes, ExportMetadata]:
        """
        Export job posts to CSV format.
        
        Args:
            jobs: List of job posts to export
            search_id: Original search ID
            include_description: Whether to include job descriptions
            include_company_details: Whether to include company details
            filename: Custom filename (without extension)
            
        Returns:
            Tuple of (CSV bytes, export metadata)
            
        Raises:
            ExportError: If export fails
        """
        try:
            if not jobs:
                raise ExportError(
                    "No jobs to export",
                    export_format=ExportFormat.CSV,
                    details={"job_count": 0}
                )
            
            # Convert jobs to DataFrame
            df = self._jobs_to_dataframe(
                jobs, 
                include_description=include_description,
                include_company_details=include_company_details
            )
            
            # Generate CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            # Generate metadata
            export_id = f"export_{uuid.uuid4().hex[:12]}"
            generated_filename = filename or f"job_search_results_{search_id}"
            if not generated_filename.endswith('.csv'):
                generated_filename += '.csv'
            
            metadata = ExportMetadata(
                export_id=export_id,
                search_id=search_id,
                format=ExportFormat.CSV,
                total_jobs_exported=len(jobs),
                export_timestamp=datetime.utcnow(),
                file_size_bytes=len(csv_bytes),
                filename=generated_filename
            )
            
            return csv_bytes, metadata
            
        except Exception as e:
            if isinstance(e, ExportError):
                raise
            raise ExportError(
                f"Failed to export jobs to CSV: {str(e)}",
                export_format=ExportFormat.CSV,
                details={"original_error": str(e), "job_count": len(jobs)}
            )
    
    def _jobs_to_dataframe(
        self,
        jobs: List[WebJobPost],
        include_description: bool = True,
        include_company_details: bool = True
    ) -> pd.DataFrame:
        """
        Convert list of WebJobPost objects to pandas DataFrame.
        
        Args:
            jobs: List of job posts
            include_description: Whether to include descriptions
            include_company_details: Whether to include company details
            
        Returns:
            pandas.DataFrame with job data
        """
        data = []
        
        for job in jobs:
            row = {
                'job_id': job.id,
                'title': job.title,
                'company_name': job.company_name,
                'job_url': job.job_url,
                'site': job.site,
                'date_posted': job.date_posted.isoformat() if job.date_posted else None,
                'is_remote': job.is_remote,
            }
            
            # Add location information
            if job.location:
                row.update({
                    'location_city': job.location.city,
                    'location_state': job.location.state,
                    'location_country': job.location.country,
                })
            else:
                row.update({
                    'location_city': None,
                    'location_state': None,
                    'location_country': None,
                })
            
            # Add compensation information
            if job.compensation:
                row.update({
                    'salary_min': job.compensation.min_amount,
                    'salary_max': job.compensation.max_amount,
                    'salary_interval': job.compensation.interval.value if job.compensation.interval else None,
                    'salary_currency': job.compensation.currency,
                })
            else:
                row.update({
                    'salary_min': None,
                    'salary_max': None,
                    'salary_interval': None,
                    'salary_currency': None,
                })
            
            # Add job type
            if job.job_type:
                # JobType.value is a tuple of translations, use the first (English) value
                job_type_values = []
                for jt in job.job_type:
                    if isinstance(jt.value, tuple) and len(jt.value) > 0:
                        job_type_values.append(jt.value[0])  # Use English translation
                    else:
                        job_type_values.append(str(jt.value))
                row['job_type'] = ', '.join(job_type_values)
            else:
                row['job_type'] = None
            
            # Add description if requested
            if include_description:
                row['description'] = job.description
            
            # Add company details if requested
            if include_company_details:
                row.update({
                    'company_url': job.company_url,
                    'company_industry': job.company_industry,
                    'company_num_employees': job.company_num_employees,
                    'company_revenue': job.company_revenue,
                    'company_rating': job.company_rating,
                    'company_reviews_count': job.company_reviews_count,
                })
            
            # Add additional fields
            row.update({
                'job_level': job.job_level,
                'job_function': job.job_function,
                'skills': ', '.join(job.skills) if job.skills else None,
                'experience_range': job.experience_range,
                'emails': ', '.join(job.emails) if job.emails else None,
                'listing_type': job.listing_type,
                'work_from_home_type': job.work_from_home_type,
                'vacancy_count': job.vacancy_count,
            })
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported export formats.
        
        Returns:
            List of supported format strings
        """
        return [format_enum.value for format_enum in ExportFormat]
    
    def validate_export_request(
        self,
        jobs: List[WebJobPost],
        export_format: ExportFormat
    ) -> bool:
        """
        Validate export request parameters.
        
        Args:
            jobs: List of jobs to export
            export_format: Requested export format
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        if not jobs:
            raise ValidationError(
                "Cannot export empty job list",
                field_errors=[]
            )
        
        if export_format not in ExportFormat:
            raise ValidationError(
                f"Unsupported export format: {export_format}",
                field_errors=[]
            )
        
        return True