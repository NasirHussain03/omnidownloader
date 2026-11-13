from typing import List, Optional, Union
from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    id: str = "video"
    title: str = "Untitled Video"
    thumbnail: Optional[str] = None
    duration: Optional[Union[float, int]] = None
    duration_formatted: str = "Unknown"
    url: str
    channel: Optional[str] = None
    views: Optional[str] = None
    upload_date: Optional[str] = None


class SearchRequest(BaseModel):
    query: Optional[str] = None
    q: Optional[str] = None
    limit: Optional[int] = 10


class SearchResponse(BaseModel):
    success: bool = True
    query: str = ""
    count: int = 0
    results: List[SearchItem] = []


class FormatItem(BaseModel):
    format_id: str = "0"
    ext: str = "mp4"
    resolution: str = "Standard"
    quality_label: str = "Standard Video"
    category: str = "combined"  # "combined", "video_only", "audio_only"
    has_video: bool = True
    has_audio: bool = True
    filesize: Optional[Union[int, float]] = None
    filesize_formatted: str = "Stream size varies"
    fps: Optional[Union[float, int]] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    url: str
    download_url: str
    is_direct_mp4: bool = False


class ExtractRequest(BaseModel):
    url: str = Field(..., description="Target URL from YouTube, Instagram, Facebook, Snapchat, etc.")


class ExtractResponse(BaseModel):
    success: bool = True
    id: str = "video"
    title: str = "Extracted Media"
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[Union[float, int]] = None
    duration_formatted: str = "Unknown"
    uploader: Optional[str] = None
    platform: str = "Universal Video"
    webpage_url: str = ""
    best_direct_url: Optional[str] = None
    best_direct_download: Optional[str] = None
    formats: List[FormatItem] = []


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
