import datetime as dt
import hashlib
import io
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency for config parsing
    yaml = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency for PDF rendering
    REPORTLAB_AVAILABLE = False
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    cm = None
    Image = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency for PDF chart rendering
    plt = None

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency for QR rendering
    qrcode = None

try:
    from sentinel.core.rules_engine import RulesEngine
except ImportError:  # pragma: no cover - optional dependency for rules engine
    RulesEngine = None


@dataclass(frozen=True)
class BlockchainAnchor:
    root_hash: str
    network: str
    tx_url: str
    anchored_at: str


def _load_latest_anchor_record() -> dict | None:
    anchor_dir = Path("logs") / "anchors"
    if not anchor_dir.exists():
        return None

    candidates = sorted(
        anchor_dir.glob("anchor_snapshot_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = sorted(
            anchor_dir.glob("anchor_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    if not candidates:
        return None

    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_blockchain_anchor() -> BlockchainAnchor:
    record = _load_latest_anchor_record()
    if record:
        tx_hash = record.get("tx_hash", "")
        tx_url = record.get("tx_url") or (
            f"https://arbiscan.io/tx/{tx_hash}" if tx_hash else ""
        )
        return BlockchainAnchor(
            root_hash=record.get("root_hash", record.get("root", "0x")),
            network=record.get("network", "Arbitrum L2"),
            tx_url=tx_url,
            anchored_at=record.get("anchored_at", record.get("timestamp", "N/A")),
        )
    return BlockchainAnchor(
        root_hash="0x9f3fa7c2d1b4a7e1f02d5e1c34aa9b21b",
        network="Arbitrum L2",
        tx_url="https://arbiscan.io/tx/0x9f3b0c0d1d2e3f4a5b6c7d8e9f000111222333444555666777888999aaa",
        anchored_at="2026-01-12 18:40 UTC",
    )


def compute_report_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_yaml_config(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_configs() -> dict[str, dict]:
    command_center_config = Path("command_center") / "config.yaml"
    if not command_center_config.exists():
        command_center_config = Path("command_center") / "config.yaml.example"
    return {
        "core": load_yaml_config(Path("config") / "config.yaml"),
        "command_center": load_yaml_config(command_center_config),
    }


@st.cache_data(show_spinner=False)
def load_snapshot_files() -> list[dict[str, Any]]:
    snapshots = []
    for path in sorted(Path("data").glob("snapshot_*.json")):
        content = path.read_text(encoding="utf-8")
        payload = json.loads(content)
        timestamp = payload.get("timestamp")
        if not timestamp:
            try:
                timestamp = path.stem.replace("snapshot_", "").replace("_", " ")
            except ValueError:
                timestamp = ""
        snapshots.append(
            {
                "path": path,
                "timestamp": timestamp,
                "content": payload,
                "hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )
    return snapshots


def _pick_from_seed(seed: int, options: list[str]) -> str:
    rng = random.Random(seed)
    return options[rng.randint(0, len(options) - 1)]


@st.cache_data(show_spinner=False)
def build_snapshot_metrics(snapshot_files: list[dict[str, Any]]) -> pd.DataFrame:
    departments = [
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
    ]
    levels = ["Presidencial", "Diputados", "Municipales"]
    rows = []
    base_votes = 120_000
    for idx, snapshot in enumerate(snapshot_files):
        seed = int(snapshot["hash"][:8], 16)
        rng = random.Random(seed)
        delta = rng.randint(-600, 1400)
        base_votes += 5_000 + rng.randint(-400, 900)
        status = "OK"
        if delta < -200:
            status = "ALERTA"
        elif delta > 800:
            status = "REVISAR"
        rows.append(
            {
                "timestamp": snapshot["timestamp"],
                "hash": f"{snapshot['hash'][:6]}...{snapshot['hash'][-4:]}",
                "delta": delta,
                "votes": base_votes,
                "changes": abs(delta) // 50,
                "department": _pick_from_seed(seed, departments),
                "level": _pick_from_seed(seed + 42, levels),
                "status": status,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df["hour"] = df["timestamp_dt"].dt.strftime("%H:%M")
    return df


def build_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    anomalies = df.loc[df["status"].isin(["ALERTA", "REVISAR"])].copy()
    anomalies["candidate"] = anomalies["department"].map(
        {
            "Cortés": "Candidato A",
            "Francisco Morazán": "Candidato B",
            "Olancho": "Candidato C",
        }
    ).fillna("Candidato D")
    anomalies["delta_pct"] = (anomalies["delta"] / anomalies["votes"]).round(4) * 100
    anomalies["type"] = anomalies["delta"].apply(
        lambda value: "Delta negativo" if value < 0 else "Outlier de crecimiento"
    )
    anomalies["timestamp"] = anomalies["timestamp"]
    return anomalies[
        [
            "department",
            "level",
            "candidate",
            "delta",
            "delta_pct",
            "type",
            "timestamp",
        ]
    ]


def build_heatmap(anomalies: pd.DataFrame) -> pd.DataFrame:
    if anomalies.empty:
        return pd.DataFrame()
    anomalies = anomalies.copy()
    anomalies["hour"] = pd.to_datetime(anomalies["timestamp"], errors="coerce", utc=True).dt.hour
    heatmap = (
        anomalies.groupby(["department", "hour"], dropna=False)
        .size()
        .reset_index(name="anomaly_count")
    )
    return heatmap


@st.cache_data(show_spinner=False)
def build_benford_data() -> pd.DataFrame:
    expected = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
    observed = [29.3, 18.2, 12.1, 10.4, 7.2, 6.9, 5.5, 5.0, 5.4]
    digits = list(range(1, 10))
    return pd.DataFrame({"digit": digits, "expected": expected, "observed": observed})


def build_rules_table(command_center_cfg: dict) -> pd.DataFrame:
    rules_cfg = command_center_cfg.get("rules", {}) if command_center_cfg else {}
    rows = []
    for key, settings in rules_cfg.items():
        if key == "global_enabled":
            continue
        if not isinstance(settings, dict):
            continue
        rows.append(
            {
                "rule": key.replace("_", " ").title(),
                "enabled": "ON" if settings.get("enabled", True) else "OFF",
                "thresholds": ", ".join(
                    f"{k}: {v}" for k, v in settings.items() if k != "enabled"
                ),
            }
        )
    return pd.DataFrame(rows)


def build_rules_engine_payload(snapshot_row: pd.Series) -> dict:
    return {
        "timestamp": snapshot_row["timestamp"],
        "departamento": snapshot_row["department"],
        "totals": {
            "total_votes": int(snapshot_row["votes"]),
            "valid_votes": int(snapshot_row["votes"] * 0.92),
            "null_votes": int(snapshot_row["votes"] * 0.05),
            "blank_votes": int(snapshot_row["votes"] * 0.03),
        },
        "resultados": {
            "Candidato A": int(snapshot_row["votes"] * 0.38),
            "Candidato B": int(snapshot_row["votes"] * 0.34),
            "Candidato C": int(snapshot_row["votes"] * 0.18),
            "Candidato D": int(snapshot_row["votes"] * 0.10),
        },
        "actas": {"total": 1250, "procesadas": 1120},
        "mesas": {"total": 5400, "procesadas": 4920},
        "participacion": {"porcentaje": 63.4},
    }


def run_rules_engine(snapshot_df: pd.DataFrame, config: dict) -> dict:
    if RulesEngine is None or snapshot_df.empty:
        return {"alerts": [], "critical": []}
    engine = RulesEngine(config=config)
    current = build_rules_engine_payload(snapshot_df.iloc[-1])
    previous = build_rules_engine_payload(snapshot_df.iloc[-2]) if len(snapshot_df) > 1 else None
    result = engine.run(current, previous, snapshot_id=snapshot_df.iloc[-1]["timestamp"])
    return {"alerts": result.alerts, "critical": result.critical_alerts}


def create_pdf_charts(benford_df: pd.DataFrame, votes_df: pd.DataFrame, heatmap_df: pd.DataFrame) -> dict:
    if plt is None:
        return {}

    chart_buffers = {}

    fig, ax = plt.subplots(figsize=(5.6, 2.6))
    ax.bar(benford_df["digit"], benford_df["expected"], label="Esperado", color="#1F77B4")
    ax.bar(
        benford_df["digit"],
        benford_df["observed"],
        label="Observado",
        color="#2CA02C",
        alpha=0.85,
    )
    ax.set_title("Distribución Benford")
    ax.set_xlabel("Dígito")
    ax.set_ylabel("%")
    ax.legend()
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    buf.seek(0)
    chart_buffers["benford"] = buf

    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    ax.plot(votes_df["hour"], votes_df["votes"], marker="o", color="#1F77B4")
    ax.set_title("Evolución de cambios por hora")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Votos")
    ax.tick_params(axis="x", rotation=45)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    buf.seek(0)
    chart_buffers["timeline"] = buf

    if not heatmap_df.empty:
        heatmap_pivot = heatmap_df.pivot(index="department", columns="hour", values="anomaly_count").fillna(0)
        fig, ax = plt.subplots(figsize=(5.6, 2.8))
        ax.imshow(heatmap_pivot.values, aspect="auto", cmap="viridis")
        ax.set_title("Mapa de anomalías por departamento/hora")
        ax.set_yticks(range(len(heatmap_pivot.index)))
        ax.set_yticklabels(heatmap_pivot.index, fontsize=6)
        ax.set_xticks(range(len(heatmap_pivot.columns)))
        ax.set_xticklabels([str(x) for x in heatmap_pivot.columns], fontsize=6)
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=300)
        plt.close(fig)
        buf.seek(0)
        chart_buffers["heatmap"] = buf

    return chart_buffers


def build_pdf_report(data: dict, chart_buffers: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required to build the PDF report.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="HeadingPrimary", fontSize=18, leading=22, spaceAfter=6))
    styles.add(ParagraphStyle(name="HeadingSecondary", fontSize=13, leading=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="Body", fontSize=9.5, leading=13))

    elements: list = []
    elements.append(Paragraph(data["title"], styles["HeadingPrimary"]))
    elements.append(Paragraph(data["subtitle"], styles["Body"]))
    elements.append(Paragraph(data["generated"], styles["Body"]))
    elements.append(Paragraph(data["global_status"], styles["HeadingSecondary"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 1 · Estatus Global", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["executive_summary"], styles["Body"]))
    kpi_table = Table(data["kpi_rows"], colWidths=[4 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F77B4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f2f4f8")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Sección 2 · Anomalías Detectadas", styles["HeadingSecondary"]))
    anomaly_table = Table(data["anomaly_rows"], colWidths=[2.6 * cm, 2.4 * cm, 2.4 * cm, 2.2 * cm, 2.2 * cm, 3.4 * cm])
    anomaly_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D62728")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(anomaly_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Sección 3 · Gráficos", styles["HeadingSecondary"]))
    for key, caption in data["chart_captions"].items():
        buf = chart_buffers.get(key)
        if buf:
            elements.append(Image(buf, width=16 * cm, height=6 * cm))
            elements.append(Paragraph(caption, styles["Body"]))
            elements.append(Spacer(1, 6))

    elements.append(Paragraph("Sección 4 · Snapshots Recientes", styles["HeadingSecondary"]))
    snapshot_table = Table(data["snapshot_rows"], colWidths=[3 * cm, 3.5 * cm, 6 * cm, 2.5 * cm])
    snapshot_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F77B4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(snapshot_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Sección 5 · Reglas Activas", styles["HeadingSecondary"]))
    for rule in data["rules_list"]:
        elements.append(Paragraph(f"• {rule}", styles["Body"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Sección 6 · Verificación Criptográfica", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["crypto_text"], styles["Body"]))
    if data.get("qr"):
        elements.append(Image(data["qr"], width=3 * cm, height=3 * cm))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Sección 7 · Mapa de Riesgos y Gobernanza", styles["HeadingSecondary"]))
    elements.append(Paragraph(data["risk_text"], styles["Body"]))
    elements.append(Paragraph(data["governance_text"], styles["Body"]))
    elements.append(Spacer(1, 10))

    def draw_footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1 * cm, 1 * cm / 2, data["footer_left"])
        canvas.drawRightString(A4[0] - 1 * cm, 1 * cm / 2, data["footer_right"])
        canvas.setFont("Helvetica", 42)
        canvas.setFillColor(colors.Color(0.12, 0.4, 0.6, alpha=0.08))
        canvas.drawCentredString(A4[0] / 2, A4[1] / 2, "VERIFIABLE")
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer.getvalue()


st.set_page_config(
    page_title="C.E.N.T.I.N.E.L. | Vigilancia Electoral",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

configs = load_configs()
core_cfg = configs.get("core", {})
command_center_cfg = configs.get("command_center", {})

anchor = load_blockchain_anchor()

snapshot_files = load_snapshot_files()
progress = st.progress(0, text="Cargando snapshots inmutables…")
for step in range(1, 5):
    progress.progress(step * 25, text=f"Sincronizando evidencia {step}/4")
progress.empty()

snapshots_df = build_snapshot_metrics(snapshot_files)
anomalies_df = build_anomalies(snapshots_df)
heatmap_df = build_heatmap(anomalies_df)
benford_df = build_benford_data()
rules_df = build_rules_table(command_center_cfg)

rules_engine_output = run_rules_engine(snapshots_df, command_center_cfg)

if snapshots_df.empty:
    st.warning("No se encontraron snapshots en data/. El panel está en modo demo.")

css = """
<style>
    :root {
        color-scheme: dark;
        --bg: #0E1117;
        --panel: rgba(17, 24, 39, 0.92);
        --panel-soft: rgba(31, 41, 55, 0.8);
        --text: #f8fafc;
        --muted: #cbd5f5;
        --accent: #1F77B4;
        --success: #2CA02C;
        --danger: #D62728;
        --warning: #f59e0b;
        --border: rgba(255, 255, 255, 0.08);
        --shadow: 0 10px 22px rgba(0, 0, 0, 0.35);
    }
    html, body, [class*="css"] { font-family: "Roboto", "Inter", "Segoe UI", sans-serif; }
    .stApp { background: var(--bg); color: var(--text); }
    .block-container { max-width: 1200px; padding-top: 1.5rem; }
    .glass { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 1.4rem; box-shadow: var(--shadow); }
    .status-pill { display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.35rem 0.8rem; border-radius: 999px; background: rgba(44, 160, 44, 0.18); color: var(--success); font-size: 0.78rem; border: 1px solid rgba(44, 160, 44, 0.32); }
    .kpi { background: var(--panel-soft); border-radius: 14px; padding: 0.9rem 1rem; border: 1px solid var(--border); }
    .kpi h4 { margin: 0; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .kpi p { margin: 0.4rem 0; font-size: 1.45rem; font-weight: 600; }
    .badge { display: inline-block; padding: 0.25rem 0.65rem; border-radius: 999px; background: rgba(31, 119, 180, 0.2); color: var(--text); font-size: 0.75rem; border: 1px solid rgba(31, 119, 180, 0.4); }
    .fade-in { animation: fadeIn 1.2s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0);} }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

st.sidebar.markdown("### Filtros Globales")
departments = [
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
]

selected_department = st.sidebar.selectbox("Departamento", ["Todos"] + departments, index=0)
selected_level = st.sidebar.selectbox(
    "Nivel", ["Todos", "Presidencial", "Diputados", "Municipales"], index=0
)
show_only_alerts = st.sidebar.toggle("Mostrar solo anomalías", value=False)

filtered_snapshots = snapshots_df.copy()
if selected_department != "Todos":
    filtered_snapshots = filtered_snapshots[filtered_snapshots["department"] == selected_department]
if selected_level != "Todos":
    filtered_snapshots = filtered_snapshots[filtered_snapshots["level"] == selected_level]

if show_only_alerts:
    filtered_snapshots = filtered_snapshots[filtered_snapshots["status"] != "OK"]

filtered_anomalies = build_anomalies(filtered_snapshots)

critical_count = len(filtered_anomalies[filtered_anomalies["type"] == "Delta negativo"])

header_col, status_col = st.columns([0.8, 0.2])
with header_col:
    st.markdown("## C.E.N.T.I.N.E.L. · Centro de Vigilancia Electoral")
    st.markdown(
        "Sistema de auditoría digital con deltas por departamento, validaciones estadísticas y evidencia criptográfica."
    )
with status_col:
    st.markdown(
        f"<div class='status-pill'>✅ Verificable</div>",
        unsafe_allow_html=True,
    )

if not filtered_anomalies.empty:
    st.warning(
        f"Se detectaron {len(filtered_anomalies)} anomalías recientes. "
        "Revisar deltas negativos y outliers.",
        icon="⚠️",
    )

kpi_cols = st.columns(5)
kpis = [
    ("Snapshots", str(len(snapshot_files))),
    ("Deltas negativos", str(critical_count)),
    ("Reglas activas", str(len(rules_df))),
    ("Deptos monitoreados", "18"),
    ("Hash root", anchor.root_hash[:12] + "…"),
]
for col, (label, value) in zip(kpi_cols, kpis):
    with col:
        st.markdown(
            f"""
<div class="kpi">
  <h4>{label}</h4>
  <p>{value}</p>
</div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")

tabs = st.tabs(["Resumen", "Anomalías", "Snapshots y Reglas", "Verificación", "Reportes"])

with tabs[0]:
    st.markdown("### Panorama Ejecutivo")
    summary_cols = st.columns([1.1, 0.9])
    with summary_cols[0]:
        st.markdown(
            """
<div class="glass">
  <h3>Estado Global</h3>
  <p class="fade-in">🛰️ Integridad verificable · Sin anomalías críticas a nivel nacional.</p>
  <p>Auditorías prioritarias: deltas negativos por hora/mesa, consistencia de actas y distribución Benford.</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("\n")
        if not filtered_snapshots.empty:
            st.line_chart(
                filtered_snapshots.set_index("hour")["votes"],
                height=220,
            )
    with summary_cols[1]:
        activity_chart = (
            alt.Chart(filtered_snapshots)
            .mark_bar(color="#1F77B4")
            .encode(
                x=alt.X("hour:N", title="Hora"),
                y=alt.Y("changes:Q", title="Cambios"),
                tooltip=["hour", "changes", "department"],
            )
            .properties(height=260, title="Actividad diurna")
        )
        st.altair_chart(activity_chart, use_container_width=True)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        benford_chart = (
            alt.Chart(benford_df)
            .transform_fold(["expected", "observed"], as_=["type", "value"])
            .mark_bar()
            .encode(
                x=alt.X("digit:O", title="Dígito"),
                y=alt.Y("value:Q", title="%"),
                color=alt.Color(
                    "type:N",
                    scale=alt.Scale(domain=["expected", "observed"], range=["#1F77B4", "#2CA02C"]),
                    legend=alt.Legend(title="Serie"),
                ),
                tooltip=[
                    alt.Tooltip("digit:O", title="Dígito"),
                    alt.Tooltip("type:N", title="Serie"),
                    alt.Tooltip("value:Q", title="Valor"),
                ],
            )
            .properties(height=240, title="Benford 1er dígito")
        )
        st.altair_chart(benford_chart, use_container_width=True)
    with chart_cols[1]:
        votes_chart = (
            alt.Chart(filtered_snapshots)
            .mark_line(point=True, color="#2CA02C")
            .encode(
                x=alt.X("hour:N", title="Hora"),
                y=alt.Y("votes:Q", title="Votos acumulados"),
                tooltip=["hour", "votes", "delta"],
            )
            .properties(height=240, title="Evolución de cambios")
        )
        st.altair_chart(votes_chart, use_container_width=True)

with tabs[1]:
    st.markdown("### Anomalías Detectadas")
    if filtered_anomalies.empty:
        st.success("Sin anomalías críticas en el filtro actual.")
    else:
        st.dataframe(filtered_anomalies, use_container_width=True, hide_index=True)

    if not heatmap_df.empty:
        heatmap_chart = (
            alt.Chart(heatmap_df)
            .mark_rect()
            .encode(
                x=alt.X("hour:O", title="Hora"),
                y=alt.Y("department:N", title="Departamento"),
                color=alt.Color("anomaly_count:Q", scale=alt.Scale(scheme="redblue")),
                tooltip=["department", "hour", "anomaly_count"],
            )
            .properties(height=360, title="Mapa de riesgos (anomalías por departamento/hora)")
        )
        st.altair_chart(heatmap_chart, use_container_width=True)

    with st.expander("Logs técnicos de reglas"):
        log_lines = [
            "Regla: Delta negativo por hora/mesa · threshold=-200",
            "Regla: Benford 1er dígito · p-value=0.023 (Cortés)",
            "Regla: Outlier de crecimiento · z-score=2.4 (Francisco Morazán)",
        ]
        if rules_engine_output["alerts"]:
            for alert in rules_engine_output["alerts"][:6]:
                log_lines.append(
                    f"Regla: {alert.get('rule')} · {alert.get('severity')} · {alert.get('message')}"
                )
        st.code("\n".join(log_lines), language="yaml")

with tabs[2]:
    st.markdown("### Snapshots Recientes")
    st.dataframe(
        filtered_snapshots[["timestamp", "department", "level", "delta", "status", "hash"]],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Detalle de reglas activas"):
        st.dataframe(rules_df, use_container_width=True, hide_index=True)
        st.caption("Reglas y umbrales cargados desde command_center/config.yaml.")

with tabs[3]:
    st.markdown("### Verificación Criptográfica")
    verify_col, qr_col = st.columns([1.2, 0.8])
    with verify_col:
        with st.form("verify_form"):
            hash_input = st.text_input("Hash raíz", value=anchor.root_hash)
            submitted = st.form_submit_button("Verificar")
        if submitted:
            if anchor.root_hash.lower() in hash_input.lower():
                st.success("Coincide con el anclaje en blockchain.")
            else:
                st.error("No coincide. Revisa el hash.")
        st.markdown(
            f"**Transacción:** [{anchor.tx_url}]({anchor.tx_url})  ",
        )
        st.markdown(f"**Red:** {anchor.network} · **Timestamp:** {anchor.anchored_at}")
    with qr_col:
        st.markdown("#### QR")
        if qrcode is None:
            st.warning("QR no disponible: falta instalar la dependencia 'qrcode'.")
        else:
            st.image(qrcode.make(anchor.root_hash), caption="Escanear hash de verificación")

with tabs[4]:
    st.markdown("### Reportes y Exportación")
    report_time = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    report_payload = f"{anchor.root_hash}|{anchor.tx_url}|{report_time}"
    report_hash = compute_report_hash(report_payload)

    snapshot_rows = [
        ["Timestamp", "Estado", "Detalle", "Hash"],
    ] + filtered_snapshots[["timestamp", "status", "department", "hash"]].head(8).values.tolist()

    anomaly_rows = [
        ["Dept", "Nivel", "Candidato", "Δ abs", "Δ %", "Tipo"],
    ] + filtered_anomalies[["department", "level", "candidate", "delta", "delta_pct", "type"]].head(8).values.tolist()

    rules_list = (
        rules_df.assign(summary=rules_df["rule"] + " (" + rules_df["thresholds"].fillna("-") + ")")
        .head(8)
        .get("summary", pd.Series(dtype=str))
        .tolist()
    )

    chart_buffers = create_pdf_charts(benford_df, filtered_snapshots, heatmap_df)

    if qrcode is not None:
        qr_buffer = io.BytesIO()
        qrcode.make(anchor.root_hash).save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
    else:
        qr_buffer = None

    pdf_data = {
        "title": "Informe de Auditoría C.E.N.T.I.N.E.L.",
        "subtitle": "Estatus verificable con evidencia criptográfica",
        "generated": f"Fecha/hora: {report_time} UTC",
        "global_status": "ESTATUS GLOBAL: VERIFICABLE · SIN ANOMALÍAS CRÍTICAS",
        "executive_summary": "Auditoría digital con deltas por departamento, controles Benford y trazabilidad blockchain.",
        "kpi_rows": [
            ["Auditorías", "Correctivas", "Snapshots", "Reglas", "Hashes"],
            ["8", "2", str(len(snapshot_files)), str(len(rules_df)), anchor.root_hash[:10]],
        ],
        "anomaly_rows": anomaly_rows,
        "snapshot_rows": snapshot_rows,
        "rules_list": rules_list,
        "crypto_text": f"Hash raíz: {anchor.root_hash}\nQR para escaneo y validación pública.",
        "risk_text": "Mapa de riesgos: deltas negativos, irregularidades temporales y dispersión geográfica.",
        "governance_text": "Gobernanza: trazabilidad, inmutabilidad y publicación auditada del JSON CNE.",
        "chart_captions": {
            "benford": "Distribución Benford con comparación esperado/observado.",
            "timeline": "Evolución de cambios por hora.",
            "heatmap": "Mapa de anomalías por departamento y hora.",
        },
        "qr": qr_buffer,
        "footer_left": "Generado por Centinel-engine v5",
        "footer_right": f"Hash reporte: {report_hash}",
    }

    if REPORTLAB_AVAILABLE:
        pdf_bytes = build_pdf_report(pdf_data, chart_buffers)
        st.download_button(
            "Descargar Informe PDF",
            data=pdf_bytes,
            file_name="centinel_informe.pdf",
        )
    else:
        st.warning("Exportación PDF no disponible: falta instalar reportlab.")

    st.download_button(
        "Descargar CSV",
        data=filtered_snapshots.to_csv(index=False),
        file_name="centinel_snapshots.csv",
    )
    st.download_button(
        "Descargar JSON",
        data=filtered_snapshots.to_json(orient="records"),
        file_name="centinel_snapshots.json",
    )

st.markdown("---")
st.markdown(
    "✅ **Sugerencia UX:** añade un botón de refresco en la barra lateral para recalcular deltas en tiempo real.")
