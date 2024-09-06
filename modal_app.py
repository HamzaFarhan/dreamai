from modal import App, Image, asgi_app

from rfp_ui import app as fasthtml_app

image = (
    Image.debian_slim()
    .pip_install("uv")
    .apt_install("git")
    .run_commands(
        "git clone https://github.com/HamzaFarhan/dreamai.git",
        "cd dreamai && uv pip install --system --compile-bytecode -r pyproject.toml",
    )
)

app = App("rfp-ui")


@app.function(image=image)
@asgi_app()
def get():
    return fasthtml_app
