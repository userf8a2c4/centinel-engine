# Proyecto C.E.N.T.I.N.E.L.
**Centinela Electrónico Neutral Transparente Íntegro Nacional Electoral Libre**

**Automated Electoral Data Integrity System**

---

## Español (principal)

### ¿Qué es Centinel?
Centinel es un sistema técnico independiente para observar y auditar datos electorales públicos en Honduras. Registra, normaliza y verifica cambios en datos publicados para producir reportes técnicos reproducibles y trazables.

### ¿Por qué importa?
La integridad electoral requiere evidencia verificable. Sentinel aporta transparencia técnica mediante snapshots, hashes encadenados y análisis de anomalías con enfoque ciudadano y neutral.

### Estado actual
- **EN DESARROLLO**
- **Dashboard:** [Streamlit](https://centinel.streamlit.app/)

### Primeros pasos (5 minutos)
1. Instala dependencias: `pip install -r requirements.txt`.
2. Copia `config.example.yaml` a `config/config.yaml` y ajusta fuentes.
3. Genera un snapshot inicial: `python scripts/download_and_hash.py`.
4. Abre el dashboard: `streamlit run dashboard.py`.

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

### What is Centinel?
Centinel is an independent technical system to observe and audit public electoral data in Honduras. It records, normalizes, and verifies changes in published data to produce reproducible, traceable technical reports.

### Why does it matter?
Electoral integrity needs verifiable evidence. Sentinel provides technical transparency through snapshots, chained hashes, and anomaly analysis with a neutral, civic-first focus.

### Current status
- **IN DEVELOPMENT**
- **Dashboard:** [Streamlit](https://centinel.streamlit.app/)

### Quick start (5 minutes)
1. Install dependencies: `pip install -r requirements.txt`.
2. Copy `config.example.yaml` to `config/config.yaml` and adjust sources.
3. Generate a snapshot: `python scripts/download_and_hash.py`.
4. Run the dashboard: `streamlit run dashboard.py`.

### Key links
- [Quickstart guide](QUICKSTART.md) 
- [Contributing](CONTRIBUTING.md) 
- [Roadmap](ROADMAP.md)
- [Dev diary](https://github.com/userf8a2c4/sentinel/tree/dev-v3/Dev%20Diary) 
- [Security](Security.md)
- [License](Security.md)

### Thanks
Thanks to civic community members, data journalists, and volunteers advancing electoral transparency through verifiable evidence.
