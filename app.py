import os
import uvicorn
import gradio as gr
from app.main import app

# Mount a lightweight Gradio interface so Hugging Face Spaces detects Gradio
demo = gr.Blocks(title="OmniDownloader")
with demo:
    gr.HTML('<meta http-equiv="refresh" content="0; url=/">')
    gr.Markdown("# 🚀 OmniDownloader is Live!")
    gr.HTML('<p style="font-size:18px;"><a href="/" style="color:#a855f7; font-weight:bold; text-decoration:underline;">Click here to open the full OmniDownloader interface &rarr;</a></p>')

# Mount Gradio to our production FastAPI app at /gradio
app = gr.mount_gradio_app(app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
