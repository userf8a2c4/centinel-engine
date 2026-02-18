"""
======================== ÍNDICE / INDEX ========================
1. Descripción general / Overview
2. Componentes principales / Main components
3. Notas de mantenimiento / Maintenance notes

======================== ESPAÑOL ========================
Archivo: `command_center/endpoints.py`.
Este módulo forma parte de Centinel Engine y está documentado para facilitar
la navegación, mantenimiento y auditoría técnica.

Componentes detectados:
  - Endpoint
  - EndpointRegistry
  - build_departments_template

Notas:
- Mantener esta cabecera sincronizada con cambios estructurales del archivo.
- Priorizar claridad operativa y trazabilidad del comportamiento.

======================== ENGLISH ========================
File: `command_center/endpoints.py`.
This module is part of Centinel Engine and is documented to improve
navigation, maintenance, and technical auditability.

Detected components:
  - Endpoint
  - EndpointRegistry
  - build_departments_template

Notes:
- Keep this header in sync with structural changes in the file.
- Prioritize operational clarity and behavior traceability.
"""

# Endpoints Module
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



from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Endpoint:
    """Representa un endpoint configurable expuesto en el panel de control.

    Represents a configurable endpoint surfaced in the control panel.
    """

    name: str
    path: str
    method: str
    description: str
    enabled: bool = True
    tags: tuple[str, ...] = ()


@dataclass
class EndpointRegistry:
    """Colección de endpoints con utilidades de búsqueda.

    Collection of endpoints with lookup helpers.
    """

    endpoints: dict[str, Endpoint] = field(default_factory=dict)

    def add(self, endpoint: Endpoint) -> None:
        """Registra un endpoint en el catálogo.

        English:
            Register an endpoint in the catalog.
        """
        self.endpoints[endpoint.name] = endpoint

    def remove(self, name: str) -> None:
        """Elimina un endpoint por nombre si existe.

        English:
            Remove an endpoint by name if it exists.
        """
        self.endpoints.pop(name, None)

    def list_enabled(self) -> Iterable[Endpoint]:
        """Itera endpoints habilitados en el catálogo.

        English:
            Iterate over enabled endpoints in the catalog.
        """
        return (endpoint for endpoint in self.endpoints.values() if endpoint.enabled)


def build_departments_template(*, full_links: dict[str, str]) -> list[Endpoint]:
    """Construye 19 espacios (18 departamentos + nivel nacional) con enlaces completos listos para pegar.

    Build 19 slots (18 departments + national level) with full ready-to-paste links.
    """

    # Nota: pega el enlace completo (https://...) en cada clave.
    # Note: paste the full link (https://...) for each key.
    return [
        Endpoint(
            name="nivel_nacional",
            path=full_links["nivel_nacional"],
            method="GET",
            description=("Configuración activa a nivel nacional.\n" "Active configuration at the national level."),
            tags=("configuracion", "nacional"),
        ),
        Endpoint(
            name="atlantida",
            path=full_links["atlantida"],
            method="GET",
            description=("Configuración activa para Atlántida.\n" "Active configuration for Atlántida."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="choluteca",
            path=full_links["choluteca"],
            method="GET",
            description=("Configuración activa para Choluteca.\n" "Active configuration for Choluteca."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="colon",
            path=full_links["colon"],
            method="GET",
            description=("Configuración activa para Colón.\n" "Active configuration for Colón."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="comayagua",
            path=full_links["comayagua"],
            method="GET",
            description=("Configuración activa para Comayagua.\n" "Active configuration for Comayagua."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="copan",
            path=full_links["copan"],
            method="GET",
            description=("Configuración activa para Copán.\n" "Active configuration for Copán."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="cortes",
            path=full_links["cortes"],
            method="GET",
            description=("Configuración activa para Cortés.\n" "Active configuration for Cortés."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="el_paraiso",
            path=full_links["el_paraiso"],
            method="GET",
            description=("Configuración activa para El Paraíso.\n" "Active configuration for El Paraíso."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="francisco_morazan",
            path=full_links["francisco_morazan"],
            method="GET",
            description=(
                "Configuración activa para Francisco Morazán.\n" "Active configuration for Francisco Morazán."
            ),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="gracias_a_dios",
            path=full_links["gracias_a_dios"],
            method="GET",
            description=("Configuración activa para Gracias a Dios.\n" "Active configuration for Gracias a Dios."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="intibuca",
            path=full_links["intibuca"],
            method="GET",
            description=("Configuración activa para Intibucá.\n" "Active configuration for Intibucá."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="islas_de_la_bahia",
            path=full_links["islas_de_la_bahia"],
            method="GET",
            description=(
                "Configuración activa para Islas de la Bahía.\n" "Active configuration for Islas de la Bahía."
            ),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="la_paz",
            path=full_links["la_paz"],
            method="GET",
            description=("Configuración activa para La Paz.\n" "Active configuration for La Paz."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="lempira",
            path=full_links["lempira"],
            method="GET",
            description=("Configuración activa para Lempira.\n" "Active configuration for Lempira."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="ocotepeque",
            path=full_links["ocotepeque"],
            method="GET",
            description=("Configuración activa para Ocotepeque.\n" "Active configuration for Ocotepeque."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="olancho",
            path=full_links["olancho"],
            method="GET",
            description=("Configuración activa para Olancho.\n" "Active configuration for Olancho."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="santa_barbara",
            path=full_links["santa_barbara"],
            method="GET",
            description=("Configuración activa para Santa Bárbara.\n" "Active configuration for Santa Bárbara."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="valle",
            path=full_links["valle"],
            method="GET",
            description=("Configuración activa para Valle.\n" "Active configuration for Valle."),
            tags=("configuracion", "departamento"),
        ),
        Endpoint(
            name="yoro",
            path=full_links["yoro"],
            method="GET",
            description=("Configuración activa para Yoro.\n" "Active configuration for Yoro."),
            tags=("configuracion", "departamento"),
        ),
    ]
