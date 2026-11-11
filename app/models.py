from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class SearchItem(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    duration_formatted: str
    url: str
    channel: Optional[str] = None
    views: Optional[str] = None
    upload_date: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool = True
    query: str
    count: int
    results: List[SearchItem]


class FormatItem(BaseModel):
    format_id: str
    ext: str
    resolution: str
    quality_label: str
    category: str  # "combined", "video_only", "audio_only"
    has_video: bool
    has_audio: bool
    filesize: Optional[int] = None
    filesize_formatted: str
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    url: str
    download_url: str
    is_direct_mp4: bool = False


class ExtractRequest(BaseModel):
    url: str = Field(..., description="Target URL from YouTube, Instagram, Facebook, Snapchat, etc.")


class ExtractResponse(BaseModel):
    success: bool = True
    id: str
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    duration_formatted: str
    uploader: Optional[str] = None
    platform: str
    webpage_url: str
    best_direct_url: Optional[str] = None
    best_direct_download: Optional[str] = None
    formats: List[FormatItem]


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
