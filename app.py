import os
import gradio as gr
from app.main import app as fastapi_app

# Gradio wrapper for Hugging Face Spaces embedding
custom_css = """
footer { visibility: hidden !important; }
.gradio-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }
"""

with gr.Blocks(title="OmniDownloader", css=custom_css) as demo:
    gr.HTML(
        """
        <iframe src="/app" style="width: 100%; height: 95vh; border: none; margin: 0; padding: 0;"></iframe>
        """
    )

# Mount our full FastAPI application onto demo.app
demo.app.mount("/app", fastapi_app)
demo.app.include_router(fastapi_app.router)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
