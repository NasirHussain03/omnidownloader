import os
import gradio as gr
from fastapi.responses import FileResponse, Response
from starlette.routing import Route
from app.main import app as fastapi_app

# ZeroGPU decorator compatibility
try:
    import spaces

    @spaces.GPU
    def dummy_gpu_initializer():
        return True
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


async def serve_custom_static(request):
    file_path = request.path_params.get("file_path", "")
    full_path = os.path.join(STATIC_DIR, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return Response(status_code=404)


async def serve_home(request):
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return Response(content="OmniDownloader is initializing...", status_code=200)


async def serve_favicon(request):
    fav_path = os.path.join(STATIC_DIR, "placeholder.jpg")
    if os.path.exists(fav_path):
        return FileResponse(fav_path)
    return Response(status_code=204)


async def serve_robots(request):
    robots_path = os.path.join(STATIC_DIR, "robots.txt")
    if os.path.exists(robots_path):
        return FileResponse(robots_path)
    return Response(status_code=404)


async def serve_sitemap(request):
    sitemap_path = os.path.join(STATIC_DIR, "sitemap.xml")
    if os.path.exists(sitemap_path):
        return FileResponse(sitemap_path, media_type="application/xml")
    return Response(status_code=404)


# Initialize Gradio Blocks wrapper
with gr.Blocks(title="OmniDownloader") as demo:
    gr.HTML('<meta http-equiv="refresh" content="0; url=/">')
    gr.Markdown("# 🚀 OmniDownloader is Live!")

# Launch without thread locking so route customization runs on the active demo.app
demo.launch(prevent_thread_lock=True)

# 1. Mount all FastAPI API routes into demo.app
demo.app.include_router(fastapi_app.router)

# 2. Prepend custom web routes ahead of Gradio's internal router
demo.app.routes.insert(0, Route("/robots.txt", endpoint=serve_robots))
demo.app.routes.insert(0, Route("/sitemap.xml", endpoint=serve_sitemap))
demo.app.routes.insert(0, Route("/favicon.ico", endpoint=serve_favicon))
demo.app.routes.insert(0, Route("/static/{file_path:path}", endpoint=serve_custom_static))
demo.app.routes.insert(0, Route("/", endpoint=serve_home))

# Keep the process alive for Hugging Face Spaces
if __name__ == "__main__":
    demo.block_thread()
