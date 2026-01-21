"""CLI mínimo para Centinel.

English: Minimal Centinel CLI.
"""

import typer

app = typer.Typer(help="Centinel Engine CLI")


@app.callback()
def main() -> None:
    """Interfaz de línea de comandos de Centinel.

    English: Centinel command line interface.
    """


if __name__ == "__main__":
    app()
