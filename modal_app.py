from modal import App, Image, Secret, asgi_app

from rfp_ui import app as fasthtml_app

DEV_DIR = "/home/hamza/dev"

image = (
    Image.debian_slim()
    .pip_install("uv", "jsonref")
    .apt_install("git", "graphviz")
    .run_commands(
        f"mkdir -p {DEV_DIR} && cd {DEV_DIR} && git clone https://github.com/HamzaFarhan/dreamai.git",
        f"cd {DEV_DIR}/dreamai && uv pip install --system --compile-bytecode -r pyproject.toml",
    )
)

app = App("rfp-ui")


@app.function(gpu="t4", image=image, secrets=[Secret.from_dotenv()], timeout=200)
@asgi_app()
def get():
    return fasthtml_app
