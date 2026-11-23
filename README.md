# OmniDownloader 🚀

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2024+-red?style=flat-square&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square&logo=render&logoColor=black)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

> **Live Website:** [https://omnidownloader.site](https://omnidownloader.site)  
> **API Backend:** [https://omni-downloader-1r9v.onrender.com](https://omni-downloader-1r9v.onrender.com)

A high-throughput, universal video and audio extraction web application and REST API built with **FastAPI**, **yt-dlp**, and a responsive **Tailwind CSS** frontend. OmniDownloader extracts direct, clean media streams (up to 4K MP4 and high-bitrate audio) from major social and video platforms without watermarks.

---

## 🌟 Key Features

* **Universal Platform Support**: Extract media from **Instagram Reels & Carousels**, **Facebook Watch & Reels**, **Snapchat Spotlight**, **YouTube Shorts & Videos**, **TikTok**, **Twitter/X**, and 1,000+ other platforms supported by `yt-dlp`.
* **Zero-Storage Direct Extraction**: Extracts direct CDN stream URLs with `download=False`, avoiding server disk bloat and reducing server CPU load.
* **Integrated Streaming Proxy (`/api/download`)**: Stream remote video chunks directly to the user's browser with sanitized, clean filenames (`Content-Disposition`).
* **Multi-Format & Quality Separation**: Dynamically separates streams into combined Video+Audio MP4s, individual HD resolution streams (4K, 1440p, 1080p, 720p, 360p), and Audio-only streams (M4A/MP3).
* **Instagram Carousel & Photo Fallback**: Handles mixed photo/video carousels gracefully without failing, automatically providing the original high-resolution JPEG photos when no video stream is present.
* **High-Speed In-Memory Caching**: Caches popular extraction requests using `cachetools` LRU cache to deliver sub-second responses for repeated queries.
* **Production Ready**: Containerized with multi-platform `Dockerfile`, native `Deno` JavaScript challenge engine, and production `Gunicorn + UvicornWorker` configuration.

---

## 📡 API Reference

### 1. Extract Media Streams
**`POST /api/extract`** or **`GET /api/extract?url=...`**

Extracts metadata, thumbnails, and direct downloadable stream formats.

```bash
curl -X POST "https://omnidownloader.site/api/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/C74t7kIvzN1/"}'
```

**Response (`200 OK`):**
```json
{
  "id": "C74t7kIvzN1",
  "title": "Sample Reel Title",
  "platform": "Instagram",
  "duration": 30,
  "thumbnail": "https://...",
  "best_direct_download": "/api/download?url=...",
  "formats": [
    {
      "format_id": "0",
      "ext": "mp4",
      "resolution": "720p HD",
      "quality_label": "720p HD • Video + Audio (MP4)",
      "download_url": "/api/download?url=...",
      "has_video": true,
      "has_audio": true
    }
  ]
}
```

### 2. Search Videos
**`GET /api/search?q={query}&limit={10}`**

Search for videos on YouTube and retrieve metadata, thumbnails, duration, and direct video links.

```bash
curl -X GET "https://omnidownloader.site/api/search?q=lofi+beats&limit=5"
```

### 3. Stream Download Proxy
**`GET /api/download?url={stream_url}&title={filename}&ext={mp4}`**

Streams remote CDN video bytes with range support and proper content headers for direct browser downloads.

### 4. Health Check
**`GET /api/health`**

Returns service health, version, and platform status.

---

## 🛠️ Local Development

### 1. Clone & Setup Environment
```bash
git clone https://github.com/NasirHussain03/omnidownloader.git
cd omnidownloader

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the application:
* **Web UI**: [http://localhost:8000/](http://localhost:8000/)
* **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🐳 Docker Deployment

Build and run locally with Docker:
```bash
docker build -t omnidownloader .
docker run -p 7860:7860 omnidownloader
```

---

## ⚡ Keeping Free Tier Render Always Awake (24/7)

Render's free tier automatically pauses web services after 15 minutes of inactivity, which causes a 50-second cold-start delay for new visitors.

To keep your free instance warm and instantly available 24/7 at **$0 cost**:
1. Go to [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com).
2. Create a new monitor / cron job:
   * **URL to monitor**: `https://omni-downloader-1r9v.onrender.com/api/health`
   * **Interval**: Every **10 minutes**
3. Save the monitor. Every 10 minutes, the monitor sends a lightweight health check ping that resets Render's 15-minute inactivity timer, keeping the service permanently active and ready for users.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
