import asyncio
import os
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Union
import yt_dlp

from app.models import SearchItem, SearchResponse, FormatItem, ExtractResponse
from app.cache import search_cache, extract_cache, get_or_set_cached

# Standard user agent for web platform requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# Concurrency limiter to protect CPU and avoid IP rate-limiting from media providers
MAX_CONCURRENT_EXTRACTIONS = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "30"))
EXTRACTION_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)


def format_duration(seconds: Optional[Union[float, int]]) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds is None:
        return "Live / Unknown"
    try:
        sec = float(seconds)
        if sec < 0:
            return "Live / Unknown"
        sec_int = int(round(sec))
        hours = sec_int // 3600
        minutes = (sec_int % 3600) // 60
        secs = sec_int % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
    except Exception:
        return "Live / Unknown"


def format_filesize(bytes_size: Optional[int]) -> str:
    """Format file size in bytes to human-readable string (KB, MB, GB)."""
    if not bytes_size or bytes_size <= 0:
        return "Stream size varies"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def format_views(views: Optional[int]) -> str:
    """Format view counts into clean K/M/B representation."""
    if views is None:
        return "N/A"
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B views"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M views"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K views"
    return f"{views} views"


def detect_platform(extractor: Optional[str], url: str) -> str:
    """Detect friendly platform name from extractor key or URL."""
    ext = (extractor or "").lower()
    url_low = url.lower()

    if "youtube" in ext or "youtu.be" in url_low or "youtube.com" in url_low:
        return "YouTube"
    if "instagram" in ext or "instagram.com" in url_low:
        return "Instagram"
    if "facebook" in ext or "fb.watch" in url_low or "facebook.com" in url_low:
        return "Facebook"
    if "snapchat" in ext or "snapchat.com" in url_low:
        return "Snapchat"
    if "tiktok" in ext or "tiktok.com" in url_low:
        return "TikTok"
    if "twitter" in ext or "x.com" in url_low or "twitter.com" in url_low:
        return "Twitter / X"
    if "vimeo" in ext:
        return "Vimeo"
    if "reddit" in ext:
        return "Reddit"
    if extractor:
        return extractor.capitalize()
    return "Universal Video"


def sanitize_filename(name: str) -> str:
    """Sanitize string for use in HTTP Content-Disposition filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip()
    return clean[:100] if clean else "video"


def clean_media_url(raw_url: str) -> str:
    """Normalize URL, strip outer quotes/brackets, and remove tracking parameters."""
    url = raw_url.strip().strip('"\'<>')
    if not url.startswith("http://") and not url.startswith("https://"):
        if "." in url and not url.startswith("://"):
            url = "https://" + url
    try:
        parsed = urllib.parse.urlparse(url)
        # Strip tracking query params for Instagram, Facebook, TikTok, Twitter, Snapchat, YouTube
        netloc = parsed.netloc.lower()
        if any(domain in netloc for domain in [
            "instagram.com", "tiktok.com", "facebook.com", "fb.watch",
            "snapchat.com", "x.com", "twitter.com", "youtube.com", "youtu.be"
        ]):
            query_params = urllib.parse.parse_qs(parsed.query)
            filtered = {
                k: v for k, v in query_params.items()
                if not k.lower().startswith("utm_") and k.lower() not in [
                    "igsh", "fbclid", "ref", "rdid", "mibextid", "sfnsn", "s", "t", "feature", "si"
                ]
            }
            new_query = urllib.parse.urlencode(filtered, doseq=True)
            return urllib.parse.urlunparse(parsed._replace(query=new_query))
    except Exception:
        pass
    return url


class YtDlpService:
    @staticmethod
    def _get_base_opts() -> Dict[str, Any]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
            "source_address": "0.0.0.0",
            "geo_bypass": True,
            "socket_timeout": 15,
            "retries": 3,
            "http_headers": {
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
            },
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },
        }

        # Automatic cookie detection for cloud environments
        cookie_path = os.getenv("COOKIES_FILE", "cookies.txt")
        if os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0:
            opts["cookiefile"] = cookie_path
        elif os.getenv("YOUTUBE_COOKIES"):
            tmp_cookie = "/tmp/cookies.txt"
            if not os.path.exists(tmp_cookie):
                try:
                    with open(tmp_cookie, "w", encoding="utf-8") as f:
                        f.write(os.getenv("YOUTUBE_COOKIES"))
                except Exception:
                    pass
            if os.path.exists(tmp_cookie):
                opts["cookiefile"] = tmp_cookie

        return opts

    @classmethod
    async def search_youtube(cls, query: str, limit: int = 10) -> SearchResponse:
        """Search YouTube using ytsearch{limit}: and return structured metadata with caching."""
        normalized_q = query.strip()
        cache_key = f"{normalized_q}:{limit}"

        async def _fetch():
            search_query = f"ytsearch{limit}:{normalized_q}"

            def _do_search():
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "extract_flat": "in_playlist",
                    "socket_timeout": 15,
                    "http_headers": {"User-Agent": USER_AGENT},
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(search_query, download=False)

            async with EXTRACTION_SEMAPHORE:
                try:
                    info = await asyncio.wait_for(asyncio.to_thread(_do_search), timeout=20.0)
                except asyncio.TimeoutError:
                    raise ValueError("YouTube search timed out. Please try again with different keywords.")

            entries = info.get("entries", []) if info else []

            results: List[SearchItem] = []
            for entry in entries:
                if not entry:
                    continue

                entry_id = entry.get("id") or ""
                title = entry.get("title") or "Untitled Video"
                duration = entry.get("duration")
                url = entry.get("url")
                if not url or not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={entry_id}"

                # Best thumbnail
                thumbnail = entry.get("thumbnail")
                if not thumbnail and entry.get("thumbnails"):
                    thumbnail = entry["thumbnails"][-1].get("url")

                results.append(
                    SearchItem(
                        id=entry_id,
                        title=title,
                        thumbnail=thumbnail,
                        duration=duration,
                        duration_formatted=format_duration(duration),
                        url=url,
                        channel=entry.get("channel") or entry.get("uploader"),
                        views=format_views(entry.get("view_count")),
                        upload_date=entry.get("upload_date"),
                    )
                )

            return SearchResponse(
                success=True,
                query=normalized_q,
                count=len(results),
                results=results,
            )

        return await get_or_set_cached(search_cache, "search", cache_key, _fetch)

    @classmethod
    async def extract_url(cls, url: str) -> ExtractResponse:
        """Extract metadata and direct MP4/Audio stream links for a video URL with caching."""
        cleaned_url = clean_media_url(url.strip())

        async def _fetch():
            def _do_extract():
                opts = cls._get_base_opts()
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        return ydl.extract_info(cleaned_url, download=False)
                except Exception as first_exc:
                    url_low = cleaned_url.lower()
                    if "youtube" in url_low or "youtu.be" in url_low:
                        # Fallback 1: Try android_creator (bypasses bot checks for old / restricted videos)
                        try:
                            fb1_opts = dict(opts)
                            fb1_opts["extractor_args"] = {
                                "youtube": {"player_client": ["android_creator"]}
                            }
                            with yt_dlp.YoutubeDL(fb1_opts) as fb1_ydl:
                                return fb1_ydl.extract_info(cleaned_url, download=False)
                        except Exception:
                            pass

                        # Fallback 2: Try web_embedded client
                        try:
                            fb2_opts = dict(opts)
                            fb2_opts["extractor_args"] = {
                                "youtube": {"player_client": ["web_embedded", "android"]}
                            }
                            with yt_dlp.YoutubeDL(fb2_opts) as fb2_ydl:
                                return fb2_ydl.extract_info(cleaned_url, download=False)
                        except Exception:
                            pass
                    raise first_exc

            async with EXTRACTION_SEMAPHORE:
                try:
                    info = await asyncio.wait_for(asyncio.to_thread(_do_extract), timeout=60.0)
                except asyncio.TimeoutError:
                    raise ValueError("Media extraction timed out. The provider took too long to respond.")

            if not info:
                raise ValueError("No video data could be extracted from this URL.")

            # In case a playlist or multi-entry object was returned, safely pick the first valid video
            if "entries" in info and info["entries"] is not None:
                try:
                    entries_list = list(info["entries"])
                    first_valid = next((e for e in entries_list if e and isinstance(e, dict)), None)
                    if first_valid:
                        info = first_valid
                except Exception:
                    pass

            video_id = str(info.get("id") or "")
            title = info.get("title") or "Extracted Media"
            safe_title = sanitize_filename(title)
            description = info.get("description")
            if description and len(description) > 280:
                description = description[:280] + "..."

            duration = info.get("duration")
            thumbnail = info.get("thumbnail")
            if not thumbnail and info.get("thumbnails"):
                thumbnail = info["thumbnails"][-1].get("url")

            uploader = info.get("uploader") or info.get("channel") or info.get("creator")
            platform = detect_platform(info.get("extractor"), cleaned_url)
            webpage_url = info.get("webpage_url") or cleaned_url

            raw_formats = info.get("formats", [])
            parsed_formats: List[FormatItem] = []

            # If formats is empty but there's a direct url at top-level
            if not raw_formats and info.get("url"):
                raw_formats = [
                    {
                        "format_id": "direct",
                        "ext": info.get("ext", "mp4"),
                        "url": info.get("url"),
                        "vcodec": "unknown",
                        "acodec": "unknown",
                        "resolution": "direct",
                    }
                ]

            # Parse and categorize formats
            for f in raw_formats:
                f_url = f.get("url")
                if not f_url:
                    continue

                ext = (f.get("ext") or "mp4").lower()
                if ext in ["mhtml", "json"]:
                    continue

                vcodec_raw = f.get("vcodec")
                acodec_raw = f.get("acodec")

                # In yt-dlp:
                # "none" explicitly means absent stream
                # None usually means unspecified progressive stream (like Facebook SD/HD, direct MP4)
                if vcodec_raw == "none" and acodec_raw == "none":
                    continue

                has_video = vcodec_raw != "none"
                has_audio = acodec_raw != "none"

                if vcodec_raw is None and acodec_raw is None:
                    if ext in ["mp3", "m4a", "aac", "wav", "flac", "ogg", "opus"]:
                        has_video = False
                        has_audio = True
                    else:
                        has_video = True
                        has_audio = True

                format_id = str(f.get("format_id") or "0")
                height = f.get("height")
                fps = f.get("fps")
                tbr = f.get("tbr")
                filesize = f.get("filesize") or f.get("filesize_approx")

                # Estimate missing filesize
                if not filesize and tbr and duration and duration > 0:
                    try:
                        filesize = int((float(tbr) * 1000 / 8) * float(duration))
                    except Exception:
                        filesize = None

                if filesize is not None:
                    try:
                        filesize = int(round(float(filesize)))
                    except Exception:
                        filesize = None

                if fps is not None:
                    try:
                        fps = round(float(fps), 2)
                    except Exception:
                        fps = None

                # Build resolution & label
                tag_str = str(f.get("tag") or "")
                format_note = str(f.get("format_note") or "")

                if height:
                    res = f"{height}p"
                    if fps and fps > 30:
                        res += f"{int(round(fps))}"
                elif any(q in tag_str for q in ["2160p", "1440p", "1080p", "720p", "480p", "360p"]):
                    match = re.search(r"(\d+p)", tag_str)
                    res = match.group(1) if match else "HD"
                elif format_id.lower() == "hd" or "hd" in format_note.lower():
                    res = "720p HD"
                elif format_id.lower() == "sd" or "sd" in format_note.lower():
                    res = "360p SD"
                elif not has_video and has_audio:
                    abr = f.get("abr") or tbr
                    try:
                        res = f"{int(round(float(abr)))} kbps" if abr else "Audio"
                    except Exception:
                        res = "Audio"
                else:
                    res = f.get("resolution") or ext.upper()

                if has_video and has_audio:
                    category = "combined"
                    quality_label = f"{res} • Video + Audio ({ext.upper()})"
                    is_direct_mp4 = ext == "mp4"
                elif has_video:
                    category = "video_only"
                    quality_label = f"{res} • Video only ({ext.upper()})"
                    is_direct_mp4 = False
                else:
                    category = "audio_only"
                    abr = f.get("abr") or tbr
                    try:
                        abr_int = int(round(float(abr))) if abr else None
                    except Exception:
                        abr_int = None
                    quality_label = (
                        f"{abr_int} kbps • Audio ({ext.upper()})"
                        if abr_int
                        else f"Audio ({ext.upper()})"
                    )
                    is_direct_mp4 = False

                # Build download proxy URL
                dl_query = urllib.parse.urlencode(
                    {
                        "url": f_url,
                        "title": safe_title,
                        "ext": ext,
                    }
                )
                download_url = f"/api/download?{dl_query}"

                parsed_formats.append(
                    FormatItem(
                        format_id=format_id,
                        ext=ext,
                        resolution=res,
                        quality_label=quality_label,
                        category=category,
                        has_video=has_video,
                        has_audio=has_audio,
                        filesize=filesize,
                        filesize_formatted=format_filesize(filesize),
                        fps=fps,
                        vcodec=vcodec_raw if has_video and vcodec_raw != "none" else None,
                        acodec=acodec_raw if has_audio and acodec_raw != "none" else None,
                        url=f_url,
                        download_url=download_url,
                        is_direct_mp4=is_direct_mp4,
                    )
                )

            # Fallback: if parsed_formats is empty but info has a direct media url
            if not parsed_formats and info.get("url"):
                ext = (info.get("ext") or "mp4").lower()
                dl_query = urllib.parse.urlencode(
                    {
                        "url": info["url"],
                        "title": safe_title,
                        "ext": ext,
                    }
                )
                parsed_formats.append(
                    FormatItem(
                        format_id="direct",
                        ext=ext,
                        resolution="Original",
                        quality_label=f"Original Stream ({ext.upper()})",
                        category="combined",
                        has_video=True,
                        has_audio=True,
                        filesize=info.get("filesize"),
                        filesize_formatted=format_filesize(info.get("filesize")),
                        fps=info.get("fps"),
                        url=info["url"],
                        download_url=f"/api/download?{dl_query}",
                        is_direct_mp4=ext == "mp4",
                    )
                )

            if not parsed_formats:
                raise ValueError("No downloadable video or audio streams were found for this URL.")

            # Sort formats intelligently:
            # 1. Combined (Video+Audio) sorted by resolution descending
            # 2. Video-only sorted by resolution descending
            # 3. Audio-only sorted by bitrate descending
            def sort_key(item: FormatItem):
                h_match = re.search(r"(\d+)p?", item.resolution)
                numeric_val = int(h_match.group(1)) if h_match else 0
                if item.category == "audio_only":
                    b_match = re.search(r"(\d+)", item.resolution)
                    numeric_val = int(b_match.group(1)) if b_match else 0

                cat_order = {"combined": 0, "video_only": 1, "audio_only": 2}.get(
                    item.category, 3
                )
                ext_order = 0 if item.ext == "mp4" else 1
                return (cat_order, -numeric_val, ext_order)

            parsed_formats.sort(key=sort_key)

            # Determine best direct URL
            best_direct_url = None
            best_direct_download = None

            combined_mp4s = [
                f for f in parsed_formats if f.category == "combined" and f.ext == "mp4"
            ]
            video_mp4s = [
                f for f in parsed_formats if f.category == "video_only" and f.ext == "mp4"
            ]

            if combined_mp4s:
                best_direct_url = combined_mp4s[0].url
                best_direct_download = combined_mp4s[0].download_url
            elif video_mp4s:
                best_direct_url = video_mp4s[0].url
                best_direct_download = video_mp4s[0].download_url
            elif parsed_formats:
                best_direct_url = parsed_formats[0].url
                best_direct_download = parsed_formats[0].download_url

            return ExtractResponse(
                success=True,
                id=video_id,
                title=title,
                description=description,
                thumbnail=thumbnail,
                duration=duration,
                duration_formatted=format_duration(duration),
                uploader=uploader,
                platform=platform,
                webpage_url=webpage_url,
                best_direct_url=best_direct_url,
                best_direct_download=best_direct_download,
                formats=parsed_formats,
            )

        return await get_or_set_cached(extract_cache, "extract", cleaned_url, _fetch)
