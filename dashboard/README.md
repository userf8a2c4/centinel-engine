# Dashboard Streamlit de Centinel

Este dashboard demuestra los 5 pilares clave de Centinel para comunicar transparencia electoral con evidencia verificable.

## Ejecutar localmente

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/streamlit_app.py
```

## Ver resultados de simulación
1. Ejecuta la simulación retroactiva para generar outputs en `results/simulation_2025/`.
2. En el dashboard, selecciona **"Simulación (results)"** y confirma la carpeta.
3. Ajusta el auto-refresco para ver cómo se incorporan snapshots nuevos.

## Contenido principal
- Pilar principal: inmutabilidad criptográfica + anclaje en L2.
- Detección automática y reproducible de cambios.
- Reglas configurables para análisis.
- Modos de operación inteligentes.
- Reportes reproducibles y descargables.
