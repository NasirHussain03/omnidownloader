import os
import asyncio
import gradio as gr
from app.ytdlp_service import YtDlpService
from app.main import app as fastapi_app

# ZeroGPU decorator compatibility
try:
    import spaces

    @spaces.GPU
    def dummy_gpu_initializer():
        return True
except Exception:
    pass


def extract_media(url: str):
    if not url or not url.strip():
        return "⚠️ Please enter a video URL.", None, []
    try:
        data = asyncio.run(YtDlpService.extract_url(url.strip()))
        
        info_md = f"### 🎬 {data.title}\n\n"
        info_md += f"**Platform**: `{data.platform}` | **Duration**: `{data.duration_formatted}`"
        if data.uploader:
            info_md += f" | **Creator**: `{data.uploader}`"
        
        format_rows = []
        for f in data.formats:
            cat = "Video + Audio" if f.category == "combined" else ("Video Only" if f.category == "video_only" else "Audio Only")
            format_rows.append([
                f.resolution,
                f.ext.upper(),
                cat,
                f.filesize_formatted,
                f'<a href="{f.url}" target="_blank" rel="noopener noreferrer" style="background-color:#7c3aed; color:white; padding:4px 10px; border-radius:6px; text-decoration:none; font-weight:bold;">📥 Direct Link</a>'
            ])
            
        return info_md, data.thumbnail, format_rows
    except Exception as exc:
        return f"❌ Extraction failed: {str(exc)}", None, []


def search_media(query: str):
    if not query or not query.strip():
        return "⚠️ Please enter a search query.", []
    try:
        data = asyncio.run(YtDlpService.search_youtube(query.strip(), limit=8))
        rows = []
        for item in data.results:
            rows.append([
                item.title,
                item.channel or "Unknown",
                item.duration_formatted,
                item.url
            ])
        return f"Found {len(data.results)} results for **{query}**:", rows
    except Exception as exc:
        return f"❌ Search failed: {str(exc)}", []


custom_theme = gr.themes.Soft(
    primary_hue="purple",
    neutral_hue="slate",
)

with gr.Blocks(title="OmniDownloader — Video & Audio Downloader") as demo:
    gr.Markdown("# 🚀 OmniDownloader")
    gr.Markdown("Download high-definition videos (MP4) and audio from **YouTube**, **Facebook**, **Instagram**, **Twitter/X**, and more.")
    
    with gr.Tabs():
        with gr.Tab("📥 Download from Link"):
            with gr.Row():
                url_input = gr.Textbox(
                    label="Video URL",
                    placeholder="Paste link from YouTube, Facebook, Instagram, Twitter/X...",
                    scale=4,
                )
                btn_extract = gr.Button("Extract Links ⚡", variant="primary", scale=1)
            
            with gr.Row():
                sample_yt = gr.Button("YouTube 4K", size="sm")
                sample_fb = gr.Button("Facebook Reel", size="sm")
                sample_short = gr.Button("Shorts Sample", size="sm")
                
            sample_yt.click(lambda: "https://www.youtube.com/watch?v=dQw4w9WgXcQ", outputs=url_input)
            sample_fb.click(lambda: "https://www.facebook.com/reel/2639556433176018", outputs=url_input)
            sample_short.click(lambda: "https://www.youtube.com/shorts/Hr1dpBSNCks", outputs=url_input)
            
            out_info = gr.Markdown()
            out_thumb = gr.Image(label="Thumbnail", visible=True, height=260)
            out_table = gr.Dataframe(
                headers=["Resolution", "Format", "Type", "Size", "Download Link"],
                datatype=["str", "str", "str", "str", "html"],
                label="Available Formats & Streams",
                interactive=False,
            )
            
            btn_extract.click(
                extract_media,
                inputs=[url_input],
                outputs=[out_info, out_thumb, out_table],
            )
            url_input.submit(
                extract_media,
                inputs=[url_input],
                outputs=[out_info, out_thumb, out_table],
            )
            
        with gr.Tab("🔍 Search YouTube"):
            with gr.Row():
                search_input = gr.Textbox(label="Search Query", placeholder="Search YouTube videos, songs, podcasts...", scale=4)
                btn_search = gr.Button("Search 🔍", variant="primary", scale=1)
            
            search_info = gr.Markdown()
            search_table = gr.Dataframe(
                headers=["Title", "Channel", "Duration", "Video URL"],
                datatype=["str", "str", "str", "str"],
                label="Search Results",
                interactive=False,
            )
            
            btn_search.click(search_media, inputs=[search_input], outputs=[search_info, search_table])
            search_input.submit(search_media, inputs=[search_input], outputs=[search_info, search_table])

# Mount underlying FastAPI router
demo.app.include_router(fastapi_app.router)

if __name__ == "__main__":
    demo.launch(theme=custom_theme)
