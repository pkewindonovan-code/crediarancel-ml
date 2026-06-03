import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import os
import requests
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

DB_LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_LOCAL_DIR, "crediarancel_ml.db")

def guardar_en_db(dni, nombre, edad, zona, ingreso, deuda, historial, monto, cuotas, frecuencia, tipo_credito, resultado, confianza):
    try:
        os.makedirs(DB_LOCAL_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT UNIQUE, nombre TEXT, edad INTEGER, zona TEXT,
                telefono TEXT, ingreso_mensual REAL, fecha_registro TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS creditos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER,
                monto_solicitado REAL, numero_cuotas INTEGER, frecuencia_pago TEXT,
                tipo_credito TEXT, deuda_actual REAL, historial_crediticio TEXT,
                estado TEXT, observacion TEXT, fecha_evaluacion TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)
        c.execute("SELECT id FROM clientes WHERE dni = ?", (dni,))
        cl = c.fetchone()
        if cl:
            cliente_id = cl[0]
        else:
            c.execute("INSERT INTO clientes (dni, nombre, edad, zona, telefono, ingreso_mensual, fecha_registro) VALUES (?,?,?,?,?,?,?)",
                      (dni, nombre, edad, zona, "", ingreso, datetime.now().isoformat()))
            cliente_id = c.lastrowid
        obs = f"Prediccion ML - Confianza: {confianza:.1f}%"
        c.execute("INSERT INTO creditos (cliente_id, monto_solicitado, numero_cuotas, frecuencia_pago, tipo_credito, deuda_actual, historial_crediticio, estado, observacion, fecha_evaluacion) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (cliente_id, monto, cuotas, frecuencia, tipo_credito, deuda, historial, resultado, obs, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, classification_report, confusion_matrix,
    ConfusionMatrixDisplay
)

st.set_page_config(
    page_title="CrediArancel ML - Aprobacion de Creditos",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .stApp {
        background: #f1f5f9;
    }

    .main > div {
        padding: 0 0.5rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: #e2e8f0;
    }

    section[data-testid="stSidebar"] .stRadio label {
        color: #cbd5e1 !important;
        font-weight: 500;
        transition: all 0.2s;
    }

    section[data-testid="stSidebar"] .stRadio label:hover {
        color: #ffffff !important;
        background: rgba(59,130,246,0.15);
        border-radius: 8px;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        padding: 10px 14px;
        margin: 2px 0;
        border-radius: 8px;
        cursor: pointer;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(135deg, #1e40af, #3b82f6);
        color: white !important;
        box-shadow: 0 4px 15px rgba(59,130,246,0.3);
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"] p {
        color: white !important;
        font-weight: 600;
    }

    .sidebar-logo {
        text-align: center;
        padding: 20px 0 10px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 16px;
    }

    .sidebar-logo h1 {
        font-size: 20px;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .sidebar-logo p {
        font-size: 11px;
        color: #94a3b8;
        margin: 4px 0 0;
        -webkit-text-fill-color: #94a3b8;
    }

    .sidebar-footer {
        position: fixed;
        bottom: 16px;
        left: 16px;
        right: 16px;
        text-align: center;
        font-size: 10px;
        color: #475569;
        border-top: 1px solid rgba(255,255,255,0.05);
        padding-top: 12px;
    }

    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
    }

    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid rgba(226,232,240,0.6);
        transition: all 0.25s;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }

    .kpi-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        line-height: 1.1;
    }

    .kpi-delta {
        font-size: 11px;
        margin-top: 4px;
        font-weight: 500;
    }

    .page-title {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
        margin: 0 0 4px;
        letter-spacing: -0.5px;
    }

    .page-subtitle {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
        font-weight: 400;
    }

    .card {
        background: white;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid rgba(226,232,240,0.6);
        margin-bottom: 16px;
        transition: all 0.2s;
    }

    .card-title {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .result-card {
        border-radius: 16px;
        padding: 28px 32px;
        margin: 20px 0;
        position: relative;
        overflow: hidden;
    }

    .result-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }

    .result-card.aprobado {
        background: linear-gradient(135deg, #f0fdf4, #dcfce7);
        border: 1px solid #bbf7d0;
    }

    .result-card.aprobado::before { background: linear-gradient(90deg, #22c55e, #4ade80); }

    .result-card.rechazado {
        background: linear-gradient(135deg, #fef2f2, #fee2e2);
        border: 1px solid #fecaca;
    }

    .result-card.rechazado::before { background: linear-gradient(90deg, #ef4444, #f87171); }

    .result-card.requiere {
        background: linear-gradient(135deg, #fffbeb, #fef3c7);
        border: 1px solid #fde68a;
    }

    .result-card.requiere::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

    .result-title {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #64748b;
        margin-bottom: 8px;
    }

    .result-status {
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 16px;
    }

    .result-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin-top: 12px;
    }

    .result-item {
        background: rgba(255,255,255,0.7);
        border-radius: 10px;
        padding: 12px 14px;
    }

    .result-item-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        color: #64748b;
    }

    .result-item-value {
        font-size: 18px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 2px;
    }

    .model-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #e2e8f0;
        transition: all 0.2s;
    }

    .model-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }

    .model-card.aprobado { border-left: 4px solid #22c55e; }
    .model-card.rechazado { border-left: 4px solid #ef4444; }

    .model-card-name {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 6px;
    }

    .model-card-icon {
        font-size: 32px;
        margin-bottom: 4px;
    }

    .model-card-result {
        font-size: 16px;
        font-weight: 700;
    }

    div[data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
    }

    div[data-testid="stMetric"] label {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #64748b !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 800 !important;
    }

    div.stButton button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        padding: 8px 28px;
        transition: all 0.2s;
        border: none;
    }

    div.stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(59,130,246,0.25);
    }

    div.stButton button[kind="primary"] {
        background: linear-gradient(135deg, #1e40af, #3b82f6);
        color: white;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox select {
        border-radius: 10px !important;
        border: 1.5px solid #e2e8f0 !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        transition: all 0.2s;
    }

    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }

    div[data-testid="stDataFrame"] th {
        background: #f8fafc;
        font-weight: 600;
        font-size: 13px;
        color: #475569;
    }

    .stAlert {
        border-radius: 12px;
        border: none;
        font-weight: 500;
    }

    div[data-baseweb="toast"] {
        border-radius: 12px !important;
    }

    .regla-card {
        background: white;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 4px 0;
        border-left: 4px solid #e2e8f0;
        font-size: 13px;
    }

    .regla-card.ok { border-left-color: #22c55e; background: #f0fdf4; }
    .regla-card.fail { border-left-color: #ef4444; background: #fef2f2; }

    hr { margin: 20px 0; border-color: #e2e8f0; }

    @media (max-width: 768px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
        .result-grid { grid-template-columns: repeat(2, 1fr); }
        .page-title { font-size: 22px; }
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.4s ease-out;
    }

    .stSpinner > div {
        border-top-color: #3b82f6 !important;
        border-width: 3px;
    }

    .tab-container {
        display: flex;
        gap: 6px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }

    .tab-btn {
        padding: 8px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        background: white;
        border: 1.5px solid #e2e8f0;
        color: #475569;
        cursor: pointer;
        transition: all 0.2s;
    }

    .tab-btn:hover {
        border-color: #3b82f6;
        color: #1e40af;
    }

    .tab-btn.active {
        background: linear-gradient(135deg, #1e40af, #3b82f6);
        color: white;
        border-color: transparent;
        box-shadow: 0 4px 12px rgba(59,130,246,0.2);
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        border-radius: 12px !important;
    }

    div.stCodeBlock {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0;
    }

    button[kind="secondary"] {
        border-radius: 10px !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

DATA_PATH = "dataset_crediarancel_250_registros.xlsx"

@st.cache_data
def cargar_datos():
    return pd.read_excel(DATA_PATH)

df = cargar_datos()

st.markdown("""
<div class="sidebar-logo">
    <h1>💳 CrediArancel</h1>
    <p>Sistema de Aprobación de Créditos con ML</p>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Menú principal",
    [
        "📊 Dataset y Analisis",
        "🧩 KMeans - Segmentacion",
        "🔗 Apriori - Reglas Asociacion",
        "🤖 Modelos ML",
        "🔮 Predecir Credito"
    ],
    label_visibility="collapsed"
)

st.markdown('<div class="sidebar-footer">© 2026 CrediArancel • v2.0 ML</div>', unsafe_allow_html=True)

aprobados = (df["estado_credito"] == "Aprobado").sum()
rechazados = (df["estado_credito"] == "Rechazado").sum()
total = len(df)
pendientes = max(0, total - aprobados - rechazados)
riesgo_prom = df["nivel_riesgo"].value_counts(normalize=True).get("Alto", 0) * 100

# =====================================================================
# 1. DATASET Y ANALISIS
# =====================================================================
if menu == "📊 Dataset y Analisis":
    st.markdown('<div class="page-title">📊 Análisis del Dataset</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Dataset financiero de CrediArancel con 250 registros de solicitudes de crédito</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">Total Solicitudes</div><div class="kpi-value" style="color:#1e40af;">{total}</div><div class="kpi-delta" style="color:#64748b;">{df.shape[1]} columnas</div></div>
        <div class="kpi-card"><div class="kpi-label">Aprobados</div><div class="kpi-value" style="color:#22c55e;">{aprobados}</div><div class="kpi-delta" style="color:#22c55e;">{aprobados/total*100:.0f}% del total</div></div>
        <div class="kpi-card"><div class="kpi-label">Rechazados</div><div class="kpi-value" style="color:#ef4444;">{rechazados}</div><div class="kpi-delta" style="color:#ef4444;">{rechazados/total*100:.0f}% del total</div></div>
        <div class="kpi-card"><div class="kpi-label">Riesgo Alto</div><div class="kpi-value" style="color:#f59e0b;">{riesgo_prom:.0f}%</div><div class="kpi-delta" style="color:#64748b;">del total evaluado</div></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown('<div class="card"><div class="card-title">📋 Vista del Dataset</div>', unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card"><div class="card-title">📐 Estadísticas Descriptivas</div>', unsafe_allow_html=True)
        st.dataframe(df.describe(), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">📊 Distribución de Variables</div>', unsafe_allow_html=True)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]
    for i, col in enumerate(["edad", "ingreso_mensual", "deuda_actual", "monto_solicitado"]):
        axes[i//2, i%2].hist(df[col], bins=20, color=colors[i], edgecolor="white", alpha=0.85)
        axes[i//2, i%2].set_title(col.replace("_", " ").title(), fontsize=14, fontweight=600, color="#0f172a")
        axes[i//2, i%2].set_facecolor("#f8fafc")
        axes[i//2, i%2].spines["top"].set_visible(False)
        axes[i//2, i%2].spines["right"].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">🔍 Info de Columnas</div>', unsafe_allow_html=True)
    info_df = pd.DataFrame({"Tipo": df.dtypes, "Nulos": df.isnull().sum(), "Valores Únicos": df.nunique()})
    st.dataframe(info_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">💻 Código de Análisis</div>', unsafe_allow_html=True)
    st.code("""import numpy as np
import pandas as pd

# Estadisticas basicas
np.mean(df["ingreso_mensual"])
np.std(df["ingreso_mensual"])
df.describe()
df.isnull().sum()
df["estado_credito"].value_counts()""", language="python")
    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# 2. KMEANS - SEGMENTACION
# =====================================================================
elif menu == "🧩 KMeans - Segmentacion":
    st.markdown('<div class="page-title">🧩 Segmentación de Clientes</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Algoritmo KMeans para segmentar clientes según su perfil financiero</div>', unsafe_allow_html=True)

    X_cluster = df[["ingreso_mensual", "deuda_actual", "monto_solicitado"]]
    scaler_c = StandardScaler()
    X_cluster_s = scaler_c.fit_transform(X_cluster)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df["segmento"] = kmeans.fit_predict(X_cluster_s)

    col1, col2, col3 = st.columns(3)
    col1.metric("Inercia del Modelo", f"{kmeans.inertia_:.0f}")
    col2.metric("Clusters", "3")
    col3.metric("Clientes Segmentados", len(df))

    st.markdown('<div class="card"><div class="card-title">📈 Visualización de Segmentos</div>', unsafe_allow_html=True)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    ax1, ax2 = axes
    ax1.set_facecolor("#f8fafc")
    ax2.set_facecolor("#f8fafc")
    sc1 = ax1.scatter(df["ingreso_mensual"], df["deuda_actual"], c=df["segmento"], cmap="viridis", s=60, edgecolors="white", linewidth=0.5)
    ax1.set_xlabel("Ingreso Mensual (S/)", fontsize=12, fontweight=600)
    ax1.set_ylabel("Deuda Actual (S/)", fontsize=12, fontweight=600)
    ax1.set_title("Segmentos: Ingreso vs Deuda", fontsize=14, fontweight=700)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    plt.colorbar(sc1, ax=ax1)
    sc2 = ax2.scatter(df["ingreso_mensual"], df["monto_solicitado"], c=df["segmento"], cmap="viridis", s=60, edgecolors="white", linewidth=0.5)
    ax2.set_xlabel("Ingreso Mensual (S/)", fontsize=12, fontweight=600)
    ax2.set_ylabel("Monto Solicitado (S/)", fontsize=12, fontweight=600)
    ax2.set_title("Segmentos: Ingreso vs Monto", fontsize=14, fontweight=700)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    plt.colorbar(sc2, ax=ax2)
    plt.tight_layout()
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">📊 Centros de Clusters</div>', unsafe_allow_html=True)
    centros = pd.DataFrame(
        scaler_c.inverse_transform(kmeans.cluster_centers_),
        columns=["Ingreso Mensual", "Deuda Actual", "Monto Solicitado"]
    )
    centros.index = [f"Segmento {i+1}" for i in range(3)]
    st.dataframe(centros.style.format("S/ {:.2f}"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">💻 Código KMeans</div>', unsafe_allow_html=True)
    st.code("""from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3, random_state=42)
df["segmento"] = kmeans.fit_predict(X)""", language="python")
    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# 3. APRIORI - REGLAS DE ASOCIACION
# =====================================================================
elif menu == "🔗 Apriori - Reglas Asociacion":
    st.markdown('<div class="page-title">🔗 Reglas de Asociación</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Algoritmo Apriori para descubrir patrones en solicitudes de crédito</div>', unsafe_allow_html=True)

    cols = ["zona", "tipo_credito", "historial_crediticio", "estado_credito", "nivel_riesgo"]
    trans = df[cols].astype(str).apply(lambda r: [f"{c}={r[c]}" for c in cols], axis=1).tolist()
    n = len(trans)

    items = {}
    for t in trans:
        for item in t:
            items[item] = items.get(item, 0) + 1

    freq = {k: v for k, v in items.items() if v / n >= 0.08}

    col1, col2, col3 = st.columns(3)
    col1.metric("Transacciones", n)
    col2.metric("Itemsets Frecuentes", len(freq))
    col3.metric("Soporte Mínimo", "8%")

    st.markdown('<div class="card"><div class="card-title">📋 Itemsets Frecuentes</div>', unsafe_allow_html=True)
    df_freq = pd.DataFrame(list(freq.items()), columns=["Item", "Frecuencia"])
    df_freq["Support"] = df_freq["Frecuencia"] / n
    st.dataframe(df_freq.sort_values("Frecuencia", ascending=False), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    from itertools import combinations
    reglas = []
    for a, b in combinations(list(freq.keys()), 2):
        ambos = sum(1 for t in trans if a in t and b in t)
        sup = ambos / n
        if sup >= 0.08:
            conf = ambos / items[a]
            reglas.append((a, b, sup, conf))

    reglas.sort(key=lambda x: x[3], reverse=True)

    if reglas:
        st.markdown('<div class="card"><div class="card-title">📊 Reglas de Asociación Encontradas</div>', unsafe_allow_html=True)
        df_reglas = pd.DataFrame(reglas[:15], columns=["Antecedente", "Consecuente", "Support", "Confianza"])
        st.dataframe(df_reglas.style.format({"Support": "{:.2%}", "Confianza": "{:.2%}"}), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">📈 Top Reglas por Confianza</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_facecolor("#f8fafc")
        top = reglas[:10]
        colors_bar = ["#3b82f6"] * len(top)
        ax.barh(range(len(top)), [r[3] for r in top], color=colors_bar, edgecolor="white", height=0.65)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels([f"{r[0]} → {r[1]}" for r in top], fontsize=9)
        ax.set_xlabel("Confianza", fontsize=12, fontweight=600)
        ax.set_title("Top 10 Reglas de Asociación", fontsize=14, fontweight=700, color="#0f172a")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(0, 1.05)
        for i, v in enumerate([r[3] for r in top]):
            ax.text(v + 0.01, i, f"{v:.1%}", va="center", fontsize=10, fontweight=600, color="#475569")
        st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No se encontraron reglas con el soporte mínimo configurado.")

    st.markdown('<div class="card"><div class="card-title">💻 Código Apriori</div>', unsafe_allow_html=True)
    st.code("""# Implementacion manual del algoritmo Apriori
# Encuentra itemsets frecuentes y reglas de asociacion
# Ej: (zona='La Merced', tipo='Prestamo') -> (estado='Rechazado')

from itertools import combinations

def apriori(transacciones, min_support):
    itemsets frecuentes = ...
    reglas = ...""", language="python")
    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# 4. MODELOS ML
# =====================================================================
elif menu == "🤖 Modelos ML":
    st.markdown('<div class="page-title">🤖 Modelos de Machine Learning</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Implementación de KNN, ID3, Random Forest y Regresión Lineal con scikit-learn</div>', unsafe_allow_html=True)

    data = df.copy()
    le_dict = {}
    for col in ["historial_crediticio", "frecuencia_pago", "tipo_credito", "zona", "nivel_riesgo", "tiene_mora"]:
        le = LabelEncoder()
        data[col] = le.fit_transform(data[col].astype(str))
        le_dict[col] = le

    data["estado_credito_bin"] = (data["estado_credito"] == "Aprobado").astype(int)
    data["razon_deuda_ingreso"] = data["deuda_actual"] / (data["ingreso_mensual"] + 1)
    data["razon_monto_ingreso"] = data["monto_solicitado"] / (data["ingreso_mensual"] + 1)
    data["capacidad_pago"] = data["ingreso_mensual"] - data["deuda_actual"]
    data["monto_por_cuota"] = data["monto_solicitado"] / (data["numero_cuotas"] + 1)
    data["esfuerzo_pago"] = data["monto_por_cuota"] / (data["ingreso_mensual"] + 1)

    feature_cols = [
        "edad", "ingreso_mensual", "deuda_actual", "monto_solicitado", "numero_cuotas",
        "razon_deuda_ingreso", "razon_monto_ingreso", "capacidad_pago",
        "monto_por_cuota", "esfuerzo_pago", "dias_atraso",
        "historial_crediticio", "frecuencia_pago", "tipo_credito",
        "nivel_riesgo", "tiene_mora", "zona"
    ]

    X = data[feature_cols]
    y = data["estado_credito_bin"]
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_s, y, test_size=0.25, random_state=42)

    modelos = {
        "KNN (K-Vecinos)": KNeighborsClassifier(n_neighbors=5),
        "ID3 (Arbol Decision)": DecisionTreeClassifier(criterion="entropy", max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Regresion Lineal": LinearRegression()
    }

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">Modelos</div><div class="kpi-value" style="color:#1e40af;">4</div><div class="kpi-delta" style="color:#64748b;">KNN, ID3, RF, Reg. Lineal</div></div>
        <div class="kpi-card"><div class="kpi-label">Features</div><div class="kpi-value" style="color:#3b82f6;">{len(feature_cols)}</div><div class="kpi-delta" style="color:#64748b;">variables predictivas</div></div>
        <div class="kpi-card"><div class="kpi-label">Train/Test</div><div class="kpi-value" style="color:#f59e0b;">75/25</div><div class="kpi-delta" style="color:#64748b;">split ratio</div></div>
    </div>
    """, unsafe_allow_html=True)

    resultados = []
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, (nombre, modelo) in enumerate(modelos.items()):
        if nombre == "Regresion Lineal":
            modelo.fit(X_train, y_train)
            y_prob = modelo.predict(X_test)
            y_pred = (y_prob >= 0.5).astype(int)
            mse = mean_squared_error(y_test, y_prob)
        else:
            modelo.fit(X_train, y_train)
            y_pred = modelo.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)

        resultados.append({
            "Modelo": nombre,
            "Accuracy": round(accuracy_score(y_test, y_pred), 4),
            "Precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "Recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
            "F1-Score": round(f1_score(y_test, y_pred, zero_division=0), 4),
            "MSE": round(mse, 4)
        })

        axes[idx].set_facecolor("#f8fafc")
        ConfusionMatrixDisplay.from_predictions(y_test, y_pred, ax=axes[idx], cmap="Blues", display_labels=["Rechazado", "Aprobado"], colorbar=False)
        axes[idx].set_title(f"{nombre} — MSE: {mse:.4f}", fontsize=13, fontweight=700, color="#0f172a")
        for text in axes[idx].texts:
            text.set_fontweight(600)
            text.set_fontsize(11)

    plt.tight_layout()
    st.markdown('<div class="card"><div class="card-title">📊 Matrices de Confusión</div>', unsafe_allow_html=True)
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

    df_res = pd.DataFrame(resultados)
    st.markdown('<div class="card"><div class="card-title">📋 Comparativa de Modelos</div>', unsafe_allow_html=True)
    st.dataframe(df_res.style.highlight_max(axis=0, subset=["Accuracy", "Precision", "Recall", "F1-Score"], color="#dcfce7")
                 .highlight_min(axis=0, subset=["MSE"], color="#fee2e2")
                 .format({k: "{:.4f}" for k in ["Accuracy", "Precision", "Recall", "F1-Score", "MSE"]}),
                 use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">🌳 Árbol de Decisión (ID3)</div>', unsafe_allow_html=True)
    arbol = DecisionTreeClassifier(criterion="entropy", max_depth=3, random_state=42)
    arbol.fit(X_train, y_train)
    fig_a, ax_a = plt.subplots(figsize=(18, 10))
    ax_a.set_facecolor("#f8fafc")
    plot_tree(arbol, feature_names=feature_cols, class_names=["Rechazado", "Aprobado"], filled=True, ax=ax_a, fontsize=9, rounded=True)
    st.pyplot(fig_a)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">📈 Importancia de Variables (Random Forest)</div>', unsafe_allow_html=True)
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    imp = pd.DataFrame({"Feature": feature_cols, "Importancia": rf.feature_importances_}).sort_values("Importancia")
    fig_i, ax_i = plt.subplots(figsize=(12, 8))
    ax_i.set_facecolor("#f8fafc")
    bars = ax_i.barh(imp["Feature"], imp["Importancia"], color="#3b82f6", edgecolor="white", height=0.65)
    ax_i.set_xlabel("Importancia", fontsize=12, fontweight=600)
    ax_i.set_title("Importancia de Características — Random Forest", fontsize=14, fontweight=700, color="#0f172a")
    ax_i.spines["top"].set_visible(False)
    ax_i.spines["right"].set_visible(False)
    for bar, val in zip(bars, imp["Importancia"]):
        ax_i.text(val + 0.002, bar.get_y() + bar.get_height()/2, f"{val:.3f}", va="center", fontsize=9, fontweight=600, color="#475569")
    st.pyplot(fig_i)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">💻 Código de Modelos</div>', unsafe_allow_html=True)
    st.code("""from sklearn.neighbors import KNeighborsClassifier      # KNN
from sklearn.tree import DecisionTreeClassifier           # ID3
from sklearn.ensemble import RandomForestClassifier       # Random Forest
from sklearn.linear_model import LinearRegression         # Regresion Lineal
from sklearn.metrics import mean_squared_error            # MSE""", language="python")
    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# 5. PREDECIR CREDITO
# =====================================================================
elif menu == "🔮 Predecir Credito":
    st.markdown('<div class="page-title">🔮 Evaluar y Predecir Crédito</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Ingrese los datos del cliente para obtener una evaluación crediticia con Machine Learning</div>', unsafe_allow_html=True)

    data_p = df.copy()
    le_dict_p = {}
    for col in ["historial_crediticio", "frecuencia_pago", "tipo_credito", "zona", "nivel_riesgo", "tiene_mora"]:
        le = LabelEncoder()
        data_p[col] = le.fit_transform(data_p[col].astype(str))
        le_dict_p[col] = le

    data_p["razon_deuda_ingreso"] = data_p["deuda_actual"] / (data_p["ingreso_mensual"] + 1)
    data_p["razon_monto_ingreso"] = data_p["monto_solicitado"] / (data_p["ingreso_mensual"] + 1)
    data_p["capacidad_pago"] = data_p["ingreso_mensual"] - data_p["deuda_actual"]
    data_p["monto_por_cuota"] = data_p["monto_solicitado"] / (data_p["numero_cuotas"] + 1)
    data_p["esfuerzo_pago"] = data_p["monto_por_cuota"] / (data_p["ingreso_mensual"] + 1)

    fcols = [
        "edad", "ingreso_mensual", "deuda_actual", "monto_solicitado", "numero_cuotas",
        "razon_deuda_ingreso", "razon_monto_ingreso", "capacidad_pago",
        "monto_por_cuota", "esfuerzo_pago", "dias_atraso",
        "historial_crediticio", "frecuencia_pago", "tipo_credito",
        "nivel_riesgo", "tiene_mora", "zona"
    ]

    X_p = data_p[fcols]
    y_p = (data_p["estado_credito"] == "Aprobado").astype(int).values
    scaler_p = StandardScaler()
    X_ps = scaler_p.fit_transform(X_p)
    X_tr, X_te, y_tr, y_te = train_test_split(X_ps, y_p, test_size=0.25, random_state=42)

    modelos_p = {
        "KNN (K-Vecinos)": KNeighborsClassifier(n_neighbors=5),
        "ID3 (Arbol)": DecisionTreeClassifier(criterion="entropy", max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    }
    for m in modelos_p.values():
        m.fit(X_tr, y_tr)

    # ---------- Información Personal ----------
    st.markdown('<div class="card"><div class="card-title">👤 Información Personal</div>', unsafe_allow_html=True)
    col_id1, col_id2, col_id3 = st.columns(3)
    with col_id1:
        dni_cliente = st.text_input("DNI del cliente *", max_chars=8, placeholder="Ej: 12345678", help="DNI debe tener 8 dígitos")
    with col_id2:
        nombre_cliente = st.text_input("Nombre completo del cliente *", placeholder="Ej: Juan Pérez López")
    with col_id3:
        edad_cliente = st.number_input("Edad", 18, 80, 30)

    col_dir1, col_dir2, col_dir3 = st.columns(3)
    with col_dir1:
        departamento = st.selectbox("Departamento", ["Junín", "Lima", "Huancavelica", "Cusco", "Ayacucho", "Pasco", "Loreto", "Ucayali"])
    with col_dir2:
        provincia = st.selectbox("Provincia", ["Chanchamayo", "Huancayo", "Satipo", "Jauja", "Concepción", "Tarma", "Yauli"])
    with col_dir3:
        distrito = st.selectbox("Distrito", ["La Merced", "Pichanaki", "Perené", "San Ramón", "Villa Rica", "Satipo", "Mazamari", "Pangoa", "Río Negro"])
    zona_cliente = distrito
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Información Financiera ----------
    st.markdown('<div class="card"><div class="card-title">💰 Información Financiera</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        ingreso = st.number_input("Ingreso mensual (S/)", 0.0, 100000.0, 2500.0, help="Ingresos declarados del cliente")
        deuda = st.number_input("Deuda actual (S/)", 0.0, 50000.0, 500.0, help="Total de cuotas mensuales que ya paga")
        monto = st.number_input("Monto solicitado (S/)", 0.0, 50000.0, 2000.0)
        cuotas = st.number_input("Número de cuotas", 1, 60, 12)
    with col2:
        frecuencia = st.selectbox("Frecuencia de pago", ["Mensual", "Quincenal", "Semanal", "Diario"])
        tipo = st.selectbox("Tipo de crédito", ["Prestamo personal", "Artefacto", "Celular", "Mueble", "Electrodomestico", "Moto", "Comercio"])
        riesgo = st.selectbox("Nivel de riesgo", ["Bajo", "Medio", "Alto"])
        tiempo_laboral = st.selectbox("Antigüedad laboral", ["Menos de 6 meses", "6-12 meses", "1-3 años", "3-5 años", "Más de 5 años"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Historial Crediticio ----------
    st.markdown('<div class="card"><div class="card-title">📋 Historial Crediticio</div>', unsafe_allow_html=True)
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        historial = st.selectbox("Historial crediticio", ["Excelente", "Bueno", "Regular", "Malo"])
    with col_h2:
        mora = st.selectbox("Tiene mora", ["No", "Si"])
    with col_h3:
        dias = st.number_input("Días de atraso", 0, 90, 0)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Botón Predecir ----------
    col_btn = st.columns([1, 2, 1])
    with col_btn[1]:
        predecir_click = st.button("🔮 Predecir con Machine Learning", type="primary", use_container_width=True)

    if predecir_click:
        if not dni_cliente or not nombre_cliente:
            st.error("⚠️ Ingrese DNI y nombre del cliente para registrar en el sistema")
            st.stop()
        if len(dni_cliente) != 8 or not dni_cliente.isdigit():
            st.error("⚠️ El DNI debe tener exactamente 8 dígitos numéricos")
            st.stop()

        # ---------- Reglas de Negocio ----------
        st.markdown('<div class="card"><div class="card-title">📋 Validación de Reglas de Negocio</div>', unsafe_allow_html=True)
        reglas_cumplidas = 0
        reglas_total = 0
        motivos_rechazo = []

        checks = []

        reglas_total += 1
        if ingreso < 1025:
            motivos_rechazo.append("❌ Ingreso mínimo debe ser ≥ S/1,025 (Sueldo Mínimo)")
            checks.append(("Ingreso mínimo ≥ S/1,025", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Ingreso de S/{ingreso:.0f} cumple el mínimo", True))

        relacion_deuda = deuda / ingreso if ingreso > 0 else 999
        reglas_total += 1
        if relacion_deuda > 0.40:
            motivos_rechazo.append(f"❌ Deuda actual ({deuda:.0f}) representa {relacion_deuda*100:.1f}% del ingreso. Máximo permitido: 40%")
            checks.append((f"Deuda {relacion_deuda*100:.1f}% > 40% máximo", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Deuda {relacion_deuda*100:.1f}% ≤ 40% permitido", True))

        relacion_cuota = (monto / max(cuotas, 1)) / ingreso if ingreso > 0 else 999
        reglas_total += 1
        if relacion_cuota > 0.35:
            motivos_rechazo.append(f"❌ La cuota estimada ({monto/max(cuotas,1):.0f}) representa {relacion_cuota*100:.1f}% del ingreso. Máximo: 35%")
            checks.append((f"Cuota {relacion_cuota*100:.1f}% > 35% máximo", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Cuota {relacion_cuota*100:.1f}% ≤ 35% permitido", True))

        reglas_total += 1
        if edad_cliente < 21 or edad_cliente > 70:
            motivos_rechazo.append("❌ Edad debe estar entre 21 y 70 años")
            checks.append((f"Edad {edad_cliente} fuera del rango 21-70", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Edad {edad_cliente} dentro del rango permitido", True))

        reglas_total += 1
        if mora == "Si":
            motivos_rechazo.append("❌ Cliente con mora registrada")
            checks.append(("Cliente sin mora", False))
        else:
            reglas_cumplidas += 1
            checks.append(("Cliente sin mora", True))

        reglas_total += 1
        if historial == "Malo":
            motivos_rechazo.append("❌ Historial crediticio Malo")
            checks.append(("Historial crediticio", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Historial: {historial}", True))

        reglas_total += 1
        if dias > 30:
            motivos_rechazo.append(f"❌ Días de atraso ({dias}) supera el límite de 30")
            checks.append((f"Días de atraso: {dias} > 30", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Días de atraso: {dias} ≤ 30", True))

        reglas_total += 1
        if monto > ingreso * 12:
            motivos_rechazo.append(f"❌ Monto solicitado ({monto}) excede 12 veces el ingreso mensual ({ingreso*12})")
            checks.append((f"Monto S/{monto:.0f} ≤ S/{ingreso*12:.0f} (12x ingreso)", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Monto S/{monto:.0f} ≤ S/{ingreso*12:.0f} (12x ingreso)", True))

        reglas_total += 1
        if tiempo_laboral in ("Menos de 6 meses",):
            motivos_rechazo.append("❌ Antigüedad laboral menor a 6 meses")
            checks.append(("Antigüedad laboral ≥ 6 meses", False))
        else:
            reglas_cumplidas += 1
            checks.append((f"Antigüedad: {tiempo_laboral}", True))

        for label, ok in checks:
            icon = "✅" if ok else "❌"
            cls = "ok" if ok else "fail"
            st.markdown(f'<div class="regla-card {cls}">{icon} {label}</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="margin-top:12px;font-size:15px;font-weight:600;">Reglas cumplidas: {reglas_cumplidas}/{reglas_total} ({reglas_cumplidas/reglas_total*100:.0f}%)</div>', unsafe_allow_html=True)

        # ---------- Decisión por Reglas ----------
        rechazado_por_reglas = reglas_cumplidas < reglas_total * 0.6
        if rechazado_por_reglas:
            st.markdown("""
            <div class="result-card rechazado fade-in">
                <div class="result-title">Decisión Crediticia</div>
                <div class="result-status" style="color:#dc2626;">❌ RECHAZADO</div>
                <div style="font-size:14px;color:#64748b;margin-bottom:12px;">No cumple con las reglas de negocio establecidas</div>
            </div>
            """, unsafe_allow_html=True)
            estado_eval = "RECHAZADO"
            votos_aprobado = 0
            votos_rechazado = 3
            modelos_utilizados = 3
            confianza = 0
            resultado_final = "Rechazado"
            obs_extra = "; ".join(motivos_rechazo)
        else:
            # ---------- ML Prediction ----------
            entrada = pd.DataFrame([[
                edad_cliente, ingreso, deuda, monto, cuotas,
                deuda / (ingreso + 1), monto / (ingreso + 1), ingreso - deuda,
                monto / (cuotas + 1), (monto / (cuotas + 1)) / (ingreso + 1), dias,
                le_dict_p["historial_crediticio"].transform([historial])[0],
                le_dict_p["frecuencia_pago"].transform([frecuencia])[0],
                le_dict_p["tipo_credito"].transform([tipo])[0],
                le_dict_p["nivel_riesgo"].transform([riesgo])[0],
                le_dict_p["tiene_mora"].transform([mora])[0],
                le_dict_p["zona"].transform([zona_cliente])[0]
            ]], columns=fcols)
            entrada_s = scaler_p.transform(entrada)

            # ---------- Model Results ----------
            st.markdown('<div class="card"><div class="card-title">🤖 Resultados por Modelo</div>', unsafe_allow_html=True)
            cols_res = st.columns(3)
            votos_aprobado = 0
            votos_rechazado = 0
            modelos_utilizados = len(modelos_p)
            pred_results = []

            for i, (nombre, modelo) in enumerate(modelos_p.items()):
                pred = modelo.predict(entrada_s)[0]
                aprobado = pred == 1
                if aprobado:
                    votos_aprobado += 1
                    pred_results.append((nombre, True))
                    cols_res[i].markdown(f"""
                    <div class="model-card aprobado">
                        <div class="model-card-name">{nombre}</div>
                        <div class="model-card-icon">✅</div>
                        <div class="model-card-result" style="color:#22c55e;">Aprobado</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    votos_rechazado += 1
                    pred_results.append((nombre, False))
                    cols_res[i].markdown(f"""
                    <div class="model-card rechazado">
                        <div class="model-card-name">{nombre}</div>
                        <div class="model-card-icon">❌</div>
                        <div class="model-card-result" style="color:#ef4444;">Rechazado</div>
                    </div>
                    """, unsafe_allow_html=True)

            resultado_final = "Aprobado" if votos_aprobado > votos_rechazado else "Rechazado"
            confianza = max(votos_aprobado, votos_rechazado) / modelos_utilizados * 100

            if votos_aprobado == 3:
                estado_eval = "APROBADO"
            elif votos_aprobado == 2:
                estado_eval = "REQUIERE EVALUACIÓN DEL ANALISTA"
            elif votos_aprobado == 1:
                estado_eval = "REQUIERE MÁS REQUISITOS"
            else:
                estado_eval = "RECHAZADO"

            capacidad_pago = ingreso - deuda
            score_estimado = int(confianza * 0.85 + (1 - relacion_deuda) * 15) if relacion_deuda <= 0.4 else int(confianza * 0.6)

            # ---------- Result Card ----------
            if estado_eval == "APROBADO":
                card_class = "aprobado"
                status_icon = "✅"
                status_color = "#16a34a"
                status_text = "APROBADO"
                recomendacion = "Proceder con el desembolso del crédito."
                observacion_text = "Cliente cumple con las condiciones para acceder al crédito."
            elif "REQUIERE" in estado_eval:
                card_class = "requiere"
                status_icon = "🟡"
                status_color = "#d97706"
                status_text = "REQUIERE EVALUACIÓN"
                recomendacion = "Derivar a evaluación manual del analista."
                observacion_text = "Se requiere revisión adicional para determinar viabilidad."
            else:
                card_class = "rechazado"
                status_icon = "❌"
                status_color = "#dc2626"
                status_text = "RECHAZADO"
                recomendacion = "No procede el desembolso."
                observacion_text = "No cumple con la capacidad de pago mínima requerida."

            nivel_riesgo_text = riesgo
            if riesgo == "Bajo":
                riesgo_color = "#22c55e"
            elif riesgo == "Medio":
                riesgo_color = "#f59e0b"
            else:
                riesgo_color = "#ef4444"

            st.markdown(f"""
            <div class="result-card {card_class} fade-in">
                <div class="result-title">Decisión Crediticia</div>
                <div class="result-status" style="color:{status_color};">{status_icon} {status_text}</div>
                <div style="font-size:14px;color:#64748b;margin-bottom:12px;">Votación Ensemble: {votos_aprobado}/{modelos_utilizados} modelos a favor</div>
                <div class="result-grid">
                    <div class="result-item">
                        <div class="result-item-label">Confianza</div>
                        <div class="result-item-value">{confianza:.0f}%</div>
                    </div>
                    <div class="result-item">
                        <div class="result-item-label">Nivel de Riesgo</div>
                        <div class="result-item-value" style="color:{riesgo_color};">{nivel_riesgo_text}</div>
                    </div>
                    <div class="result-item">
                        <div class="result-item-label">Score Crediticio</div>
                        <div class="result-item-value">{min(score_estimado, 100)}/100</div>
                    </div>
                    <div class="result-item">
                        <div class="result-item-label">Capacidad de Pago</div>
                        <div class="result-item-value">S/ {capacidad_pago:.0f}</div>
                    </div>
                </div>
                <hr style="margin:16px 0;border-color:#e2e8f0;">
                <div style="font-size:13px;color:#475569;"><strong>Observación:</strong> {observacion_text}</div>
                <div style="font-size:13px;color:#475569;margin-top:4px;"><strong>Recomendación:</strong> {recomendacion}</div>
            </div>
            """, unsafe_allow_html=True)
            obs_extra = ""

        # ---------- Enviar a CrediArancel ----------
        historial_map = {"Excelente": "Bueno", "Bueno": "Bueno", "Regular": "Regular", "Malo": "Malo"}
        direccion_completa = f"{distrito}, {provincia}, {departamento}"

        payload = {
            "dni": dni_cliente,
            "cliente": nombre_cliente,
            "edad": edad_cliente,
            "ocupacion": tiempo_laboral,
            "direccion": direccion_completa,
            "telefono": "",
            "ingreso_mensual": ingreso,
            "monto_solicitado": monto,
            "plazo": int(cuotas),
            "tipo_credito": tipo,
            "num_deudas_activas": 0,
            "total_cuotas_mensuales": deuda,
            "historial_pagos": historial_map.get(historial, "Regular"),
            "tiene_aval": "No",
            "tiene_garantia": "No",
            "resultado_ml": estado_eval,
            "prediccion_knn": "RECHAZADO" if rechazado_por_reglas else ("APROBADO" if pred_results[0][1] else "RECHAZADO"),
            "prediccion_id3": "RECHAZADO" if rechazado_por_reglas else ("APROBADO" if pred_results[1][1] else "RECHAZADO"),
            "prediccion_rf": "RECHAZADO" if rechazado_por_reglas else ("APROBADO" if pred_results[2][1] else "RECHAZADO"),
            "confianza_ml": round(confianza, 2) if not rechazado_por_reglas else 0,
            "observaciones": f"Evaluado via ML - {modelos_utilizados if not rechazado_por_reglas else 3} modelos - {votos_aprobado if not rechazado_por_reglas else 0} votos a favor" + (f" | Rechazado por reglas: {obs_extra}" if obs_extra else ""),
            "analista": "Sistema ML"
        }

        api_url = os.environ.get("CREDIARANCEL_API_URL", "http://localhost:3000/api/evaluacion/evaluar")
        st.markdown('<div class="card"><div class="card-title">📤 Enviar a CrediArancel</div>', unsafe_allow_html=True)
        try:
            api_resp = requests.post(api_url, json=payload, timeout=10)
            if api_resp.status_code == 200:
                api_data = api_resp.json()
                st.success(f"✅ Evaluación enviada a CrediArancel (ID: {api_data.get('id', 'N/A')})")
                if api_data.get('estado') == 'APROBADO':
                    st.info("💡 Este cliente está APROBADO. Ve al módulo de CrediArancel > Clientes Aprobados para efectuar el desembolso.")
                elif 'REQUIERE' in (api_data.get('estado') or ''):
                    st.warning("⚠️ Este cliente requiere evaluación del analista. Revisa la sección Pendientes en CrediArancel.")
                else:
                    st.error("❌ Solicitud rechazada. No cumple con la capacidad de pago mínima requerida.")
            else:
                st.warning(f"⚠️ No se pudo enviar a CrediArancel: {api_resp.status_code}")
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ Sistema CrediArancel no disponible. La evaluación solo quedó registrada localmente.")
        except Exception as e:
            st.warning(f"⚠️ Error de conexión con CrediArancel: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

        guardado = guardar_en_db(
            dni_cliente, nombre_cliente, edad_cliente, zona_cliente, ingreso,
            deuda, historial, monto, cuotas, frecuencia, tipo,
            resultado_final, confianza if not rechazado_por_reglas else 0
        )
        if guardado:
            st.info("📦 Copia local guardada en data/crediarancel_ml.db")

        if not rechazado_por_reglas:
            st.markdown('<div class="card"><div class="card-title">📋 Datos Ingresados</div>', unsafe_allow_html=True)
            st.dataframe(entrada, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
