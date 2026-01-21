# Proyecto C.E.N.T.I.N.E.L.
**Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**

**Automated Electoral Data Integrity System**

---

## Español (principal)

### ¿Qué es Sentinel?
Sentinel es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras. Registra, normaliza y verifica cambios en datos publicados para producir reportes técnicos reproducibles y trazables.

### ¿Por qué importa?
La integridad electoral requiere evidencia verificable. Sentinel aporta transparencia técnica mediante snapshots, hashes encadenados y análisis de anomalías con enfoque ciudadano y neutral.

### Fundamento legal (Honduras)
Este proyecto se basa en la **Ley de Transparencia y Acceso a la Información Pública** (Decreto 170-2006, reformado por Decreto 60-2022):
- **Art. 3 y 4:** Derecho ciudadano al acceso a la información pública.
- **Art. 5:** Obligación de facilitar acceso por medios electrónicos.

Sentinel opera con un enfoque defensivo, respetando límites y registrando evidencia para auditorías reproducibles.

### Estado actual
- **AUDIT ACTIVE**

### Control maestro (todo configurable en un solo lugar)
Todo lo modificable vive en `control_master/` para evitar tocar el resto del código.
- Edita `control_master/config.yaml` y `control_master/.env`.
- Consulta `control_master/README.md` para pasos detallados.

### Primeros pasos (5 minutos)
1. Instala dependencias con Poetry:
   ```bash
   poetry install
   ```
2. Configura fuentes:
   ```bash
   cp control_master/config.yaml.example control_master/config.yaml
   cp control_master/.env.example control_master/.env
   ```
3. Genera un snapshot inicial:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
4. Ejecuta el análisis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```

### Producción con Docker
- Construye la imagen:
  ```bash
  docker build -t centinel-engine .
  ```
- Levanta servicios (cron):
  ```bash
  docker compose up -d
  ```

### Enlaces destacados
- [Guía rápida](QUICKSTART.md)
- [Contribución](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Diario de desarrollo](https://github.com/userf8a2c4/sentinel/tree/dev-v3/Dev%20Diary)
- [Seguridad](Security.md)
- [Licencia: MIT](Security.md)

### Agradecimientos
Gracias a la comunidad cívica, periodistas de datos y personas voluntarias que promueven transparencia electoral con evidencia verificable.

---

## English

### What is Sentinel?
Sentinel is an independent technical system to observe and audit public electoral data in Honduras. It records, normalizes, and verifies changes in published data to produce reproducible, traceable technical reports.

### Why does it matter?
Electoral integrity needs verifiable evidence. Sentinel provides technical transparency through snapshots, chained hashes, and anomaly analysis with a neutral, civic-first focus.

### Legal basis (Honduras)
This project is grounded in the **Law on Transparency and Access to Public Information** (Decree 170-2006, amended by Decree 60-2022):
- **Art. 3 & 4:** Citizen right to access public information.
- **Art. 5:** Obligation to facilitate access through electronic means.

Sentinel operates defensively, respecting limits and recording evidence for reproducible audits.

### Current status
- **AUDIT ACTIVE**

### Master control (single place to edit)
Everything configurable lives under `control_master/` to avoid touching the rest of the code.
- Edit `control_master/config.yaml` and `control_master/.env`.
- See `control_master/README.md` for detailed steps.

### Quick start (5 minutes)
1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
2. Configure sources:
   ```bash
   cp control_master/config.yaml.example control_master/config.yaml
   cp control_master/.env.example control_master/.env
   ```
3. Generate a snapshot:
   ```bash
   poetry run python scripts/download_and_hash.py
   ```
4. Run the analysis:
   ```bash
   poetry run python scripts/analyze_rules.py
   ```

### Production with Docker
- Build the image:
  ```bash
  docker build -t centinel-engine .
  ```
- Start services (cron):
  ```bash
  docker compose up -d
  ```

### Key links
- [Quickstart guide](QUICKSTART.md)
- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Dev diary](https://github.com/userf8a2c4/sentinel/tree/dev-v3/Dev%20Diary)
- [Security](Security.md)
- [License](Security.md)

### Thanks
Thanks to civic community members, data journalists, and volunteers advancing electoral transparency through verifiable evidence.
