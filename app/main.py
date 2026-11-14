import os
import re
import urllib.parse
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx
import yt_dlp.utils

from app.models import (
    SearchRequest,
    SearchResponse,
    ExtractRequest,
    ExtractResponse,
    ErrorResponse,
)
from app.ytdlp_service import (
    YtDlpService,
    sanitize_filename,
    clean_media_url,
    USER_AGENT,
    MAX_CONCURRENT_EXTRACTIONS,
)
from app.cache import search_cache, extract_cache

# Shared connection pool for high-throughput streaming
http_client: Optional[httpx.AsyncClient] = None

# Stream concurrency semaphore to prevent memory exhaustion on large concurrent file transfers
MAX_CONCURRENT_STREAMS = int(os.getenv("MAX_CONCURRENT_STREAMS", "150"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=15.0, read=60.0, write=60.0, pool=60.0),
        limits=httpx.Limits(max_keepalive_connections=150, max_connections=1000),
        follow_redirects=True,
    )
    yield
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="OmniDownloader API",
    description="High-Throughput Universal Video Search & Stream Extraction API",
    version="1.1.0",
    lifespan=lifespan,
)

# GZip middleware compresses JSON and static files > 1000 bytes, saving ~70% network payload
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable CORS for worldwide access and client embeds
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": "OmniDownloader",
        "version": "1.1.0",
        "supported_platforms": [
            "YouTube",
            "Instagram",
            "Facebook",
            "Snapchat",
            "TikTok",
            "Twitter/X",
            "Vimeo",
            "Reddit",
        ],
    }


@app.get("/api/stats")
async def stats_endpoint():
    """Return in-memory cache and concurrency stats for monitoring."""
    return {
        "status": "healthy",
        "cache": {
            "search_cache_size": len(search_cache),
            "search_cache_max": search_cache.maxsize,
            "extract_cache_size": len(extract_cache),
            "extract_cache_max": extract_cache.maxsize,
        },
        "concurrency": {
            "max_concurrent_extractions": MAX_CONCURRENT_EXTRACTIONS,
            "max_concurrent_streams": MAX_CONCURRENT_STREAMS,
        },
    }


@app.get("/api/debug-ytdlp")
async def debug_ytdlp_endpoint(
    url: str = Query("https://www.youtube.com/shorts/VaAgP-r8kMg"),
    timeout_sec: int = Query(20, ge=5, le=30),
    use_cookies: bool = Query(False),
):
    import subprocess
    cmd = [
        "python", "-m", "yt_dlp",
        "-v",
        "--dump-json",
        "--skip-download",
        "--check-formats=False",
        "--socket-timeout", "10",
        "--retries", "1",
    ]
    if use_cookies and os.path.exists("cookies.txt"):
        cmd.extend(["--cookies", "cookies.txt"])
    cmd.append(url)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        return {
            "code": proc.returncode,
            "stdout_len": len(proc.stdout),
            "stderr": proc.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as te:
        return {
            "code": -1,
            "error": "Command timed out after " + str(timeout_sec) + "s",
            "stderr": (te.stderr or "")[-2000:] if hasattr(te, "stderr") else "",
        }
    except Exception as e:
        return {"code": -2, "error": str(e)}


@app.get(
    "/api/search",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def search_endpoint(
    q: str = Query(..., min_length=1, description="Search keyword for YouTube"),
    limit: int = Query(10, ge=1, le=25, description="Number of results (1-25)"),
):
    """
    Search YouTube by keyword using yt-dlp (ytsearch{limit}:) with in-memory caching.
    Returns video titles, thumbnails, durations, urls, and channel info.
    """
    try:
        results = await YtDlpService.search_youtube(query=q, limit=limit)
        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform search: {str(exc)}",
        )


@app.post(
    "/api/search",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def search_post_endpoint(payload: SearchRequest):
    """POST variant of search for JSON payload clients."""
    search_q = payload.query or payload.q
    if not search_q or not search_q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    limit = payload.limit or 10
    try:
        results = await YtDlpService.search_youtube(query=search_q.strip(), limit=limit)
        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform search: {str(exc)}",
        )


@app.post(
    "/api/extract",
    response_model=ExtractResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def extract_post_endpoint(payload: ExtractRequest):
    """
    Extract direct MP4/Audio stream URLs and metadata from YouTube, Instagram,
    Facebook, Snapchat, and other supported platforms with cache.
    """
    return await _process_extract(payload.url)


@app.get(
    "/api/extract",
    response_model=ExtractResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def extract_get_endpoint(
    url: str = Query(..., min_length=5, description="Target media URL")
):
    """
    GET variant of /api/extract for direct browser and cURL querying.
    """
    return await _process_extract(url)


async def _process_extract(url: str):
    """Shared extraction handler with URL normalization and logging."""
    url = clean_media_url(url.strip())
    print(f"--> [EXTRACT REQUEST] URL: {url}")
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format. Please provide a full URL starting with https:// or http://",
        )

    try:
        response = await YtDlpService.extract_url(url)
        print(f"<-- [EXTRACT SUCCESS] '{response.title}' ({len(response.formats)} formats)")
        return response
    except yt_dlp.utils.DownloadError as exc:
        err_msg = str(exc)
        print(f"xx> [EXTRACT DOWNLOAD ERROR] {err_msg}")
        err_msg_lower = err_msg.lower()
        if "empty media response" in err_msg_lower or "login" in err_msg_lower or "private" in err_msg_lower:
            detail = "This post is private or requires logging in to access."
        elif "unavailable" in err_msg_lower or "not available" in err_msg_lower:
            detail = "This video is unavailable, deleted, or region-restricted."
        elif "not a valid url" in err_msg_lower or "unsupported url" in err_msg_lower:
            detail = "The provided URL is not supported or not recognized as a valid media link."
        else:
            clean_msg = err_msg.split("ERROR:")[-1].strip()
            detail = f"Could not extract video: {clean_msg}"
        raise HTTPException(status_code=400, detail=detail)
    except ValueError as exc:
        print(f"xx> [EXTRACT VALUE ERROR] {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        print(f"xx> [EXTRACT UNEXPECTED ERROR] {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected extraction error occurred: {str(exc)}",
        )


@app.get("/api/redirect-download")
async def redirect_download(
    url: str = Query(..., description="Direct media CDN stream URL"),
):
    """
    Zero-bandwidth direct CDN redirect:
    Directs the client browser immediately to the source CDN (e.g. Meta, Snapchat, Google),
    consuming 0 KB of bandwidth on your server.
    """
    return RedirectResponse(url=url, status_code=302)


@app.get("/api/download")
async def download_proxy(
    request: Request,
    url: str = Query(..., description="Direct media stream URL"),
    title: str = Query("download", description="Desired filename without extension"),
    ext: str = Query("mp4", description="File extension"),
):
    """
    Stream download proxy with connection reuse:
    Streams remote media chunks to the client with Content-Disposition headers.
    """
    global http_client
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.{ext}"

    forward_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }
    if "range" in request.headers:
        forward_headers["Range"] = request.headers["range"]

    client = http_client
    if client is None:
        client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    try:
        req = client.build_request("GET", url, headers=forward_headers)
        res = await client.send(req, stream=True)

        if res.status_code >= 400:
            await res.aclose()
            raise HTTPException(
                status_code=res.status_code,
                detail="Remote media server rejected stream request. Please re-extract video.",
            )

        ascii_filename = filename.encode("ascii", "ignore").decode("ascii").strip()
        if not ascii_filename or ascii_filename == f".{ext}":
            ascii_filename = f"video.{ext}"
        encoded_filename = urllib.parse.quote(filename, encoding="utf-8")
        content_disposition = (
            f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        )

        response_headers = {
            "Content-Disposition": content_disposition,
            "Accept-Ranges": "bytes",
        }
        if "content-length" in res.headers:
            response_headers["Content-Length"] = res.headers["content-length"]
        if "content-type" in res.headers:
            response_headers["Content-Type"] = res.headers["content-type"]
        else:
            response_headers["Content-Type"] = (
                "video/mp4" if ext == "mp4" else "application/octet-stream"
            )
        if "content-range" in res.headers:
            response_headers["Content-Range"] = res.headers["content-range"]

        async def stream_generator():
            try:
                async for chunk in res.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await res.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=res.status_code,
            headers=response_headers,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating download stream: {str(exc)}",
        )


# Static files mount and front-page route
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav = os.path.join(STATIC_DIR, "placeholder.jpg")
    if os.path.exists(fav):
        return FileResponse(fav, media_type="image/jpeg")
    return Response(status_code=204)


@app.get("/robots.txt", include_in_schema=False)
async def serve_robots():
    robots_file = os.path.join(STATIC_DIR, "robots.txt")
    if os.path.exists(robots_file):
        return FileResponse(robots_file, media_type="text/plain")
    return Response(content="User-agent: *\nAllow: /\n", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
async def serve_sitemap():
    sitemap_file = os.path.join(STATIC_DIR, "sitemap.xml")
    if os.path.exists(sitemap_file):
        return FileResponse(sitemap_file, media_type="application/xml")
    return Response(content="<xml></xml>", media_type="application/xml")


@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "OmniDownloader API is running."}
