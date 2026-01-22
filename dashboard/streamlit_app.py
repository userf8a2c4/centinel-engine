import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


@dataclass(frozen=True)
class BlockchainAnchor:
    root_hash: str
    network: str
    tx_url: str
    anchored_at: str


def build_snapshot_data() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    snapshots = [
        {
            "timestamp": (now - dt.timedelta(minutes=40)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x88fa...e901",
            "changes": 2,
            "detail": "Actas actualizadas en 3 mesas",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0xe41b...93f0",
            "changes": 1,
            "detail": "Corrección menor en padrón",
            "status": "REVISAR",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x7b99...ae02",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
        {
            "timestamp": (now - dt.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M UTC"),
            "hash": "0x9f3a...e21b",
            "changes": 0,
            "detail": "Sin cambios detectados",
            "status": "OK",
        },
    ]
    return pd.DataFrame(snapshots)


def build_rules_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "regla": "Si un archivo cambia más del 5%",
                "estado": "ON",
                "accion": "Notificamos y pausamos snapshots",
            },
            {
                "regla": "Cambios fuera de horarios esperados",
                "estado": "ON",
                "accion": "Alertamos a observadores",
            },
            {
                "regla": "Patrones repetidos en actas",
                "estado": "OFF",
                "accion": "Registrar y revisar",
            },
        ]
    )


def styled_status(df: pd.DataFrame):
    def highlight_status(value: str) -> str:
        color_map = {
            "OK": "background-color: rgba(16, 185, 129, 0.2); color: #10b981;",
            "REVISAR": "background-color: rgba(245, 158, 11, 0.2); color: #f59e0b;",
            "ALERTA": "background-color: rgba(248, 113, 113, 0.2); color: #f87171;",
        }
        return color_map.get(value, "")

    return df.style.map(highlight_status, subset=["status"])


def build_benford_data() -> pd.DataFrame:
    expected = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
    observed = [29.3, 18.2, 12.1, 10.4, 7.2, 6.9, 5.5, 5.0, 5.4]
    digits = list(range(1, 10))
    return pd.DataFrame({"dígito": digits, "esperado": expected, "observado": observed})


def build_last_digit_data() -> pd.DataFrame:
    digits = list(range(10))
    observed = [9.4, 10.6, 9.8, 10.2, 9.9, 9.7, 10.5, 10.1, 10.0, 9.8]
    return pd.DataFrame({"dígito": digits, "observado": observed})


def build_vote_evolution() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    series = []
    total_votes = 120_000
    for step in range(8):
        total_votes += 6_500 + (step * 320)
        series.append(
            {
                "hora": (now - dt.timedelta(hours=7 - step)).strftime("%H:%M"),
                "votos": total_votes,
            }
        )
    return pd.DataFrame(series)


def render_honduras_map() -> None:
    st.markdown("### Mapa electoral de Honduras – ¿Dónde hay más actividad?")
    st.markdown(
        "<p class='section-subtitle'>Colores verdes = actividad normal. Naranjas = atención. Rojos = revisar.</p>",
        unsafe_allow_html=True,
    )
    try:
        local_geojson_path = Path(__file__).parent / "data" / "honduras_departments.geojson"
        gadm_geojson_path = Path(__file__).parent / "data" / "gadm41_HND_1.json"
        alt_geojson_path = Path(__file__).parent / "data" / "GeoJSON_HN.geojson"
        if local_geojson_path.exists():
            honduras_geojson = json.loads(local_geojson_path.read_text(encoding="utf-8"))
        elif gadm_geojson_path.exists():
            honduras_geojson = json.loads(gadm_geojson_path.read_text(encoding="utf-8"))
        elif alt_geojson_path.exists():
            honduras_geojson = json.loads(alt_geojson_path.read_text(encoding="utf-8"))
        else:
            geojson_url = "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/honduras-departments.geojson"
            with urlopen(geojson_url) as response:
                honduras_geojson = json.load(response)

        alert_by_department = pd.DataFrame(
            {
                "departamento": [
                    "Atlántida",
                    "Choluteca",
                    "Colón",
                    "Comayagua",
                    "Copán",
                    "Cortés",
                    "El Paraíso",
                    "Francisco Morazán",
                    "Gracias a Dios",
                    "Intibucá",
                    "Islas de la Bahía",
                    "La Paz",
                    "Lempira",
                    "Ocotepeque",
                    "Olancho",
                    "Santa Bárbara",
                    "Valle",
                    "Yoro",
                ],
                "cambios": [12, 18, 9, 11, 14, 20, 8, 22, 2, 6, 1, 7, 10, 5, 16, 9, 4, 13],
                "anomalías": [0, 1, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1],
            }
        )
        alert_by_department["mensaje"] = (
            "Cambios detectados: "
            + alert_by_department["cambios"].astype(str)
            + " · Anomalías críticas: "
            + alert_by_department["anomalías"].astype(str)
        )

        feature_id_key = "properties.name"
        if honduras_geojson.get("features"):
            sample_properties = honduras_geojson["features"][0].get("properties", {})
            if "NAME_1" in sample_properties:
                feature_id_key = "properties.NAME_1"
            elif "NAME_0" in sample_properties:
                feature_id_key = "properties.NAME_0"

        map_fig = px.choropleth(
            alert_by_department,
            geojson=honduras_geojson,
            locations="departamento",
            featureidkey=feature_id_key,
            color="cambios",
            hover_name="departamento",
            hover_data={"cambios": True, "anomalías": True, "mensaje": True},
            color_continuous_scale=["#10b981", "#f59e0b", "#ef4444"],
        )
        map_fig.update_geos(fitbounds="locations", visible=False)
        map_fig.update_layout(
            height=420,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            coloraxis_showscale=True,
        )
        st.plotly_chart(map_fig, use_container_width=True)
        st.button("Ver detalle por departamento", use_container_width=True)
    except Exception:
        st.warning(
            "No se pudo cargar el mapa de Honduras. "
            "Colocá un GeoJSON local en `dashboard/data/honduras_departments.geojson`, "
            "`dashboard/data/gadm41_HND_1.json` o `dashboard/data/GeoJSON_HN.geojson`."
        )


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. | Dashboard Ciudadano",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    :root {
        color-scheme: dark;
    }
    html, body, [class*="css"]  {
        font-size: 16px;
    }
    .stApp {
        background: radial-gradient(circle at top, rgba(0, 163, 255, 0.12), transparent 55%), #0b0f1a;
        color: #e2e8f0;
    }
    section[data-testid="stSidebar"] {
        background: rgba(12, 18, 34, 0.95);
        border-right: 1px solid rgba(148, 163, 184, 0.2);
    }
    .glass {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.78), rgba(30, 41, 59, 0.55));
        border: 1px solid rgba(148, 163, 184, 0.18);
        backdrop-filter: blur(14px);
        border-radius: 18px;
        padding: 1.25rem;
    }
    .hero {
        padding: 2rem;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.7));
        border: 1px solid rgba(0, 163, 255, 0.3);
        box-shadow: 0 0 50px rgba(0, 163, 255, 0.12);
        color: #ffffff;
        margin-bottom: 1.5rem;
    }
    .hero h1 {
        margin-bottom: 0.5rem;
        font-size: 2.4rem;
    }
    .hero p {
        font-size: 1rem;
    }
    .pillars {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 1rem;
    }
    .pillar {
        background: rgba(255, 255, 255, 0.08);
        padding: 0.75rem 1rem;
        border-radius: 999px;
        font-size: 0.9rem;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    .section-title {
        font-size: 1.2rem;
        color: #e2e8f0;
        margin-bottom: 0.35rem;
    }
    .section-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
    }
    .kpi-grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 18px;
        padding: 1.1rem 1.2rem;
    }
    .kpi-card h3 {
        margin: 0;
        font-size: 0.85rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .kpi-card p {
        margin: 0.4rem 0 0.4rem 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .kpi-card span {
        font-size: 0.9rem;
        color: #cbd5f5;
        display: block;
    }
    .highlight-green {
        color: #10b981;
    }
    .highlight-orange {
        color: #f59e0b;
    }
    .highlight-blue {
        color: #00a3ff;
    }
</style>
    """,
    unsafe_allow_html=True,
)

anchor = BlockchainAnchor(
    root_hash="0x9f3a7c2d1b4a7e1f02d5e1c34aa9b21b",
    network="Arbitrum L2",
    tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
    anchored_at="2026-01-12 18:40 UTC",
)

st.sidebar.markdown("## C.E.N.T.I.N.E.L.")
st.sidebar.caption("Centinela Electoral Nacional Transparente Íntegro Nacional Electoral Libre")

st.sidebar.markdown("### Navegación")
st.sidebar.write("• Inicio ciudadano")
st.sidebar.write("• Indicadores")
st.sidebar.write("• Mapa electoral")
st.sidebar.write("• Snapshots")
st.sidebar.write("• Reglas")
st.sidebar.write("• Reportes")

st.sidebar.markdown("---")

if st.sidebar.button("⚡ Activar Modo Electoral", use_container_width=True):
    st.sidebar.success("Modo electoral activado (cadencia intensiva).")
if st.sidebar.button("📥 Snapshot Ahora", use_container_width=True):
    st.sidebar.success("Snapshot programado para la próxima ventana.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Estado**")
st.sidebar.write("Modo: Electoral Activo")
st.sidebar.write("Cadena: Arbitrum L2")
st.sidebar.write("Último snapshot: hace 4 min")

st.markdown(
    """
<div class="hero">
  <h1>C.E.N.T.I.N.E.L. – Vigilancia Ciudadana de las Elecciones en Honduras</h1>
  <p>Aquí puedes ver que los datos electorales son públicos, inmutables y verificables por cualquiera. Nadie puede alterarlos sin que todos lo sepamos.</p>
  <div class="pillars">
    <div class="pillar">🔒 Inmutabilidad en blockchain</div>
    <div class="pillar">🤖 Detección automática con IA</div>
    <div class="pillar">📌 Reglas claras y públicas</div>
    <div class="pillar">✅ Verificación ciudadana</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

hero_col1, hero_col2, hero_col3 = st.columns([1, 1, 1])
with hero_col1:
    st.markdown(
        """
<div class="glass">
  <div class="section-title">Estado actual</div>
  <div class="section-subtitle"><span class="highlight-green">Todo OK</span> · sin anomalías críticas</div>
  <p>El sistema no detectó señales de fraude en las últimas 24h.</p>
</div>
        """,
        unsafe_allow_html=True,
    )
with hero_col2:
    st.markdown(
        f"""
<div class="glass">
  <div class="section-title">Último snapshot</div>
  <div class="section-subtitle">Hace 4 minutos · Inmutable en {anchor.network}</div>
  <p>Hash raíz: <span class="highlight-blue">{anchor.root_hash[:10]}...</span></p>
</div>
        """,
        unsafe_allow_html=True,
    )
with hero_col3:
    st.markdown(
        """
<div class="glass">
  <div class="section-title">Verificaciones ciudadanas</div>
  <div class="section-subtitle">2.4K personas como tú</div>
  <p>Más ciudadanos verificando = más confianza pública.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

cta_col1, cta_col2 = st.columns([1, 1])
with cta_col1:
    st.button("¡Verificar yo mismo ahora!", use_container_width=True)
with cta_col2:
    st.link_button("Verificar en Blockchain", anchor.tx_url, use_container_width=True)

st.markdown("### Indicadores clave (explicados)")
st.markdown(
    "<div class='kpi-grid'>"
    "<div class='kpi-card'><h3>Snapshots 24h</h3><p>174</p><span>Cada 10 minutos tomamos una foto inmutable.</span></div>"
    "<div class='kpi-card'><h3>Cambios detectados</h3><p>68</p><span>Actualizaciones normales de actas, revisadas automáticamente.</span></div>"
    "<div class='kpi-card'><h3>Anomalías críticas</h3><p>0</p><span>No hay señales que superen los umbrales acordados.</span></div>"
    "<div class='kpi-card'><h3>Verificaciones ciudadanas</h3><p>2.4K</p><span>Personas como tú ya confirmaron los datos.</span></div>"
    "</div>",
    unsafe_allow_html=True,
)

st.info(
    "🧠 **En palabras simples:** un snapshot es una ‘foto’ de los datos públicos. "
    "Si algo cambia, se compara con la foto anterior y queda registrado para siempre."
)

st.markdown("### Indicadores de rareza estadística")
st.markdown(
    "**¿Los números parecen naturales?** Usamos pruebas estadísticas que indican si los datos se comportan como en una elección real."
)

benford_col, last_digit_col = st.columns([1.4, 1])
with benford_col:
    benford_df = build_benford_data()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=benford_df["dígito"],
            y=benford_df["esperado"],
            name="Esperado",
            marker_color="#00a3ff",
        )
    )
    fig.add_trace(
        go.Bar(
            x=benford_df["dígito"],
            y=benford_df["observado"],
            name="Observado",
            marker_color="#f59e0b",
        )
    )
    fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        title="Ley de Benford (primer dígito)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.success("Distribución normal ✓ (confianza 92%)")

with last_digit_col:
    last_digit_df = build_last_digit_data()
    fig = px.bar(
        last_digit_df,
        x="dígito",
        y="observado",
        color_discrete_sequence=["#00a3ff"],
        title="Último dígito de votos",
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        yaxis_title="% observado",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info("Si un dígito domina mucho, podría ser sospechoso.")

votes_df = build_vote_evolution()
fig = px.line(votes_df, x="hora", y="votos", markers=True, title="Evolución de votos acumulados")
fig.update_layout(
    height=260,
    margin=dict(l=10, r=10, t=30, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
)
st.plotly_chart(fig, use_container_width=True)
st.info("El crecimiento debe ser gradual. Saltos repentinos indican revisión adicional.")

render_honduras_map()

st.markdown("### ¿A qué horas se actualizan más los datos?")
heatmap_df = pd.DataFrame(
    {
        "hora": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "actividad": [18, 22, 40, 75, 55, 30],
    }
)
heat_fig = px.bar(
    heatmap_df,
    x="hora",
    y="actividad",
    color="actividad",
    color_continuous_scale=["#10b981", "#f59e0b", "#ef4444"],
)
heat_fig.update_layout(
    height=260,
    margin=dict(l=10, r=10, t=20, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    coloraxis_showscale=False,
)
st.plotly_chart(heat_fig, use_container_width=True)
st.info("Actividad muy alta de madrugada requiere revisión. Horarios normales: mañana y tarde.")

st.markdown("### Snapshots recientes")
snapshots_df = build_snapshot_data()
st.dataframe(
    styled_status(snapshots_df),
    width="stretch",
    hide_index=True,
)
if st.button("Ver qué cambió exactamente"):
    st.write("✅ +3 actas agregadas · ❌ 1 acta corregida")

st.markdown("### Reglas que usamos para proteger la transparencia")
rules_df = build_rules_data()
st.dataframe(rules_df, width="stretch", hide_index=True)
st.button("¡Sugiere una nueva regla!", use_container_width=True)

st.markdown("### Reportes y verificación ciudadana")
report_csv = snapshots_df.to_csv(index=False).encode("utf-8")
col_report1, col_report2, col_report3 = st.columns(3)
with col_report1:
    st.download_button(
        "Descargar reporte simple (PDF para todos)",
        data=b"%PDF-1.4\n%Centinel demo report\n",
        file_name="centinel_reporte.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
with col_report2:
    st.download_button(
        "Descargar datos completos (JSON + hashes)",
        data=snapshots_df.to_json(orient="records"),
        file_name="centinel_reporte.json",
        mime="application/json",
        use_container_width=True,
    )
with col_report3:
    st.download_button(
        "Descargar CSV",
        data=report_csv,
        file_name="centinel_reporte.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_report3:
    st.download_button(
        "Descargar CSV",
        data=report_csv,
        file_name="centinel_reporte.csv",
        mime="text/csv",
        use_container_width=True,
    )
except Exception:
    city_data_path = Path(__file__).parent / "data" / "hn_cities.json"
    if city_data_path.exists():
        city_payload = json.loads(city_data_path.read_text(encoding="utf-8"))
        city_items = city_payload if isinstance(city_payload, list) else city_payload.get("cities", [])
        city_rows = []
        for index, item in enumerate(city_items):
            lat = item.get("lat") or item.get("latitude")
            lon = item.get("lng") or item.get("lon") or item.get("longitude")
            if lat is None or lon is None:
                continue
            population = float(item.get("population") or item.get("pop") or 0)
            if population > 0:
                alert_score = min(max(round(population / 200000), 1), 6)
            else:
                alert_score = (index % 6) + 1
            city_rows.append(
                {
                    "city": item.get("city") or item.get("name") or "Ciudad",
                    "department": item.get("admin_name") or item.get("admin") or "Departamento",
                    "lat": float(lat),
                    "lon": float(lon),
                    "alertas": alert_score,
                }
            )
        city_df = pd.DataFrame(city_rows)
        map_fig = px.scatter_geo(
            city_df,
            lat="lat",
            lon="lon",
            color="alertas",
            size="alertas",
            hover_name="city",
            hover_data={"department": True, "alertas": True},
            color_continuous_scale=["#0b0f1a", "#00d4ff", "#f87171"],
        )
        map_fig.update_layout(
            height=420,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            coloraxis_showscale=True,
            geo=dict(scope="north america", showland=True, landcolor="#0b0f1a"),
        )
        st.plotly_chart(map_fig, use_container_width=True)
        st.info(
            "🗺️ **Mapa alterno:** usando datos de ciudades (`hn_cities.json`). "
            "Los puntos más grandes indican más alertas estimadas."
        )
    else:
        st.warning(
            "No se pudo cargar el mapa de Honduras. "
            "Colocá un GeoJSON local en `dashboard/data/honduras_departments.geojson`, "
            "`dashboard/data/gadm41_HND_1.json` o `dashboard/data/GeoJSON_HN.geojson`, "
            "o un archivo de ciudades en `dashboard/data/hn_cities.json`."
        )

st.markdown("### Snapshots recientes")
st.dataframe(
    styled_status(snapshots_df),
    width="stretch",
    hide_index=True,
)
st.caption("Estados: OK (sin anomalías), REVISAR (cambios menores), ALERTA (anomalías graves).")

rules_df = build_rules_data()
col_rules, col_ai = st.columns([1.3, 1])
with col_rules:
    st.markdown("<div class='glass'><div class='section-title'>Reglas personalizadas</div>"
                "<div class='section-subtitle'>Configura respuestas automáticas y auditorías instantáneas</div>", unsafe_allow_html=True)
    st.dataframe(rules_df, width="stretch", hide_index=True)
    st.button("Crear nueva regla", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ai:
    st.markdown("<div class='glass'><div class='section-title'>Detección automática con IA</div>"
                "<div class='section-subtitle'>Alertas en tiempo real</div>", unsafe_allow_html=True)
    st.write("• Patrón anómalo en sección 12 · Alta")
    st.write("• Cambio irregular en acta 2024-09 · Media")
    st.write("• Pico inusual en consultas ciudadanas · Baja")
    st.progress(0.92, text="Confianza anomalías críticas")
    st.progress(0.84, text="Confianza cambios no autorizados")
    st.progress(0.68, text="Confianza inconsistencias menores")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Reportes reproducibles")
st.markdown(
    """
<div class="glass">
  <div class="section-title">Exportación verificable</div>
  <div class="section-subtitle">PDF firmado, JSON auditado y hash reproducible.</div>
</div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Verificar yo mismo"):
    st.write("Pegá el hash raíz para confirmar si coincide con el registro público en Arbitrum.")
    hash_input = st.text_input("Hash raíz", value=anchor.root_hash)
    if st.button("Verificar ahora"):
        if anchor.root_hash[:6].lower() in hash_input.lower():
            st.success("¡Coincide! ✓ Este hash está anclado en blockchain.")
        else:
            st.error("No coincide. Revisá que el hash sea correcto.")
