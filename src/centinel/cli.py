import typer

app = typer.Typer(help="Centinel Engine CLI")


@app.callback()
def main() -> None:
    """Centinel command line interface."""


if __name__ == "__main__":
    app()
