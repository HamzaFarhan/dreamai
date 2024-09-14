from fasthtml.common import H1, Main, fast_app, serve

app = fast_app(live=True)[0]


messages = ["hello", "kya haal hai"]


@app.get("/")
def home():
    return Main(H1("Hello", hx_get="/salam"), cls="container")


@app.get("/salam")
def salam():
    return H1("Salam", hx_get="/")


if __name__ == "__main__":
    serve()
