# Dashboard Streamlit de C.E.N.T.I.N.E.L.

Este dashboard demuestra los 5 pilares clave de C.E.N.T.I.N.E.L. para comunicar transparencia electoral con evidencia verificable.

## Ejecutar localmente

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/streamlit_app.py
```

## Dependencias PDF

Para habilitar el reporte PDF profesional instala ReportLab:

```bash
pip install reportlab
```

Si usas `requirements.txt` del dashboard ya incluye `reportlab>=4.2.5`.

## Uso del botón Exportar Reporte PDF

1. Abre el dashboard y navega a la pestaña **Reportes y Exportación**.
2. Usa el selector de **Snapshot histórico** en la barra lateral para elegir el snapshot a exportar.
3. Presiona **Exportar Reporte PDF** para descargar un reporte profesional con portada, tablas resumen y secciones bilingües.

## Contenido principal
- Pilar principal: inmutabilidad criptográfica + anclaje en L2.
- Detección automática y reproducible de cambios.
- Reglas configurables para análisis.
- Modos de operación inteligentes.
- Reportes reproducibles y descargables.
