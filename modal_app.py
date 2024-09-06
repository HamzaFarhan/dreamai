from modal import App, Image, Mount, Secret, asgi_app

from rfp_ui import app as fasthtml_app

image = (
    Image.debian_slim()
    .pip_install("uv", "jsonref")
    .apt_install("git")
    .run_commands(
        "git clone https://github.com/HamzaFarhan/dreamai.git",
        "cd dreamai && uv pip install --system --compile-bytecode -r pyproject.toml",
    )
)

app = App("rfp-ui")


@app.function(
    image=image,
    mounts=[
        Mount.from_local_dir(
            "src/dreamai/dialogs", remote_path="/root/dreamai/src/dreamai/dialogs"
        )
    ],
    secrets=[Secret.from_dotenv()],
)
@asgi_app()
def get():
    return fasthtml_app
