# OmniDownloader 🚀

Universal Video & Audio Downloader Web Application built with **FastAPI**, **yt-dlp**, and a responsive **Tailwind CSS + Vanilla JavaScript** frontend.

Supported platforms include **YouTube**, **Instagram** (Reels/Posts), **Facebook** (Reels/Watch), **Snapchat** (Spotlight/Stories), **TikTok**, **Twitter/X**, and other media platforms supported by yt-dlp.

---

## ✨ Features

- 🔍 **YouTube Search (`/api/search`)**: Search YouTube via `ytsearch10:` and retrieve title, high-res thumbnail, duration, view count, and URLs.
- ⚡ **Direct Stream Link Extractor (`/api/extract`)**: Extract direct MP4/Audio stream URLs without downloading to server storage (`download=False`).
- 📥 **Integrated Stream Proxy (`/api/download`)**: 1-click clean file downloads with sanitized video title in `Content-Disposition`.
- 🎛️ **Quality & Format Filter**: Sorts between direct Video+Audio MP4s, individual HD video streams (1080p, 720p, etc.), and Audio-only streams (M4A/MP3).
- 📋 **Clipboard Paste & 1-Click Copy**: Paste URLs from clipboard or copy stream URLs instantly.
- 🐳 **Docker & Cloud Ready**: Production `Dockerfile` and `render.yaml` configured for Render.com and Hugging Face Spaces (handles dynamic `$PORT` and non-root user permissions).

---

## 🛠️ Local Development

### 1. Prerequisites
- Python 3.10+
- (Optional) `ffmpeg` installed on your system for audio conversions

### 2. Setup Virtual Environment
```bash
python -m venv .venv

# On Windows
.\.venv\Scripts\activate

# On Linux/macOS
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
- Web App: `http://localhost:8000/`
- Interactive API Swagger Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

---

## 📡 API Endpoints

### 1. `GET /api/search`
Search YouTube for videos.

**Query Parameters:**
- `q`: Search keyword (e.g. `lofi beats`)
- `limit`: Number of results (default 10, max 25)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/search?q=lofi+hip+hop&limit=5"
```

### 2. `POST /api/extract` or `GET /api/extract`
Extract direct media stream URLs and metadata from YouTube, Instagram, Facebook, Snapchat, etc.

**POST Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### 3. `GET /api/download`
Streams the remote media directly to the browser as an attachment file download with proper filenames.

---

## 🚢 Deployment

### Hugging Face Spaces
1. Create a new Space on [Hugging Face](https://huggingface.co/new-space).
2. Choose **Docker** as the SDK.
3. Push this repository to your Space repository.
4. The `Dockerfile` is pre-configured with user UID `1000`, `ffmpeg`, and default port `7860`.

### Render.com
1. Create a new **Web Service** on [Render](https://render.com/).
2. Select **Docker** or link your Git repository (Render automatically detects `render.yaml` or `Dockerfile`).
3. Set the Health Check path to `/api/health`.
4. Deploy! Render will pass its `$PORT` (e.g., 10000) which our Dockerfile dynamically uses.
