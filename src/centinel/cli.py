# Cli Module
# AUTO-DOC-INDEX
#
# ES: Índice rápido
#   1) Propósito del módulo
#   2) Componentes principales
#   3) Puntos de extensión
#
# EN: Quick index
#   1) Module purpose
#   2) Main components
#   3) Extension points
#
# Secciones / Sections:
#   - Configuración / Configuration
#   - Lógica principal / Core logic
#   - Integraciones / Integrations

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
