"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Models

class SearchRequest(BaseModel):
    """Request model for initiating a lead search."""
    keywords: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    min_budget: Optional[float] = Field(None, ge=0)
    max_budget: Optional[float] = Field(None, ge=0)
    posted_within_hours: int = Field(72, ge=0)
    min_quality_score: float = Field(0.0, ge=0, le=100)
    max_results_per_platform: int = Field(100, ge=1, le=500)


class ConfigUpdateRequest(BaseModel):
    """Request model for updating configuration."""
    apify_token: Optional[str] = None
    platform_auth: Optional[Dict[str, Dict[str, str]]] = None


# Response Models

class LeadSummaryResponse(BaseModel):
    """Summary of a lead for list view."""
    id: int
    job_title: str
    platform: str
    quality_score: float
    budget_amount: Optional[float]
    payment_type: Optional[str]
    posted_datetime: datetime
    is_favorited: bool = False

    class Config:
        from_attributes = True


class LeadDetailResponse(BaseModel):
    """Complete lead details."""
    id: int
    job_title: str
    job_description: str
    platform: str
    quality_score: float
    budget_amount: Optional[float]
    payment_type: Optional[str]
    client_info: Optional[Dict[str, Any]]
    job_url: str
    posted_datetime: datetime
    skills_tags: List[str]
    is_potential_duplicate: bool
    is_favorited: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LeadsListResponse(BaseModel):
    """Paginated list of leads."""
    leads: List[LeadSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    """Dashboard statistics."""
    total_leads: int
    leads_by_platform: Dict[str, int]
    leads_last_24h: int
    leads_last_7d: int


class SearchStatusResponse(BaseModel):
    """Search execution status."""
    is_running: bool
    current_platform: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None


class SearchInitResponse(BaseModel):
    """Response when search is initiated."""
    search_id: str
    status: str
    message: str


class ConfigResponse(BaseModel):
    """Configuration data (with masked sensitive values)."""
    apify_token: str
    platforms: List[str]
    has_auth: Dict[str, bool]


class ConfigUpdateResponse(BaseModel):
    """Response after config update."""
    status: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    errors: Optional[List[str]] = None


class ToggleFavoriteResponse(BaseModel):
    """Response after toggling favorite status."""
    id: int
    is_favorited: bool
    message: str
