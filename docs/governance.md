# Gobernanza técnica y de releases | Technical Governance and Releases

## Español

### Objetivo
Establecer controles de gobernanza verificables para minimizar riesgos de cadena de suministro, configuración y operación en contextos de alta sensibilidad electoral.

### Controles vigentes
- **Licencia consistente AGPL-3.0** en metadatos y repositorio.
- **Arbitrum deshabilitado por defecto** fuera de ventana electoral.
- **Zero Trust y hashing de logs activados por defecto** en configuración operativa.
- **Checklist de release de seguridad** con validaciones CI, SBOM y revisión de configuración.

### Pendientes operativos externos
- Regenerar `poetry.lock` en entorno con conectividad completa para asegurar hashes de artefactos.
- Reserva formal del nombre del paquete en PyPI para mitigar package squatting.

## English

### Objective
Define verifiable governance controls to reduce supply-chain, configuration, and operational risks in high-sensitivity electoral contexts.

### Active controls
- **AGPL-3.0 license consistency** across repository metadata and source.
- **Arbitrum disabled by default** outside electoral windows.
- **Zero Trust and log hashing enabled by default** in runtime configuration.
- **Security release checklist** with CI validation, SBOM, and config review.

### External operational pending items
- Re-generate `poetry.lock` in a fully connected environment to ensure artifact hashes.
- Formally reserve package name on PyPI to mitigate package squatting.
