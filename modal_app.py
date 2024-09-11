from modal import App, Image, Secret, Volume, asgi_app

from dreamai.settings import DEV_DIR, ModalSettings
from rfp_ui import app as fasthtml_app

modal_settings = ModalSettings()
LANCE_DIR = modal_settings.lance_dir


image = (
    Image.debian_slim()
    .pip_install("uv", "jsonref")
    .apt_install("git", "graphviz")
    .run_commands(
        f"mkdir -p {DEV_DIR} && cd {DEV_DIR} && git clone https://github.com/HamzaFarhan/dreamai.git",
        f"cd {DEV_DIR}/dreamai && uv pip install --system --compile-bytecode -r pyproject.toml",
        f"mkdir -p {LANCE_DIR} && chmod -R 777 {LANCE_DIR}",
    )
)

app = App("rfp-ui")
volume = Volume.from_name("lance-volume", create_if_missing=True)


@app.function(
    gpu="t4",
    image=image,
    secrets=[Secret.from_dotenv()],
    timeout=200,
    volumes={LANCE_DIR: volume},
)
@asgi_app()
def get():
    return fasthtml_app
