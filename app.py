import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

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
    layout="wide"
)

st.markdown("""
<style>
.main { background-color: #f8fafc; }
.stMetric > div { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.titulo { color: #0f172a; font-size: 36px; font-weight: 800; }
.subtitulo { color: #2563eb; font-size: 18px; font-weight: 600; }
.resultado-aprobado { background-color: #dcfce7; color: #166534; padding: 20px; border-radius: 12px; font-size: 26px; font-weight: bold; text-align: center; border: 2px solid #22c55e; }
.resultado-rechazado { background-color: #fee2e2; color: #991b1b; padding: 20px; border-radius: 12px; font-size: 26px; font-weight: bold; text-align: center; border: 2px solid #ef4444; }
.card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

DATA_PATH = "dataset_crediarancel_250_registros.xlsx"

@st.cache_data
def cargar_datos():
    return pd.read_excel(DATA_PATH)

df = cargar_datos()

st.markdown('<div class="titulo">💳 CrediArancel ML</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Sistema de Aprobacion de Creditos con Machine Learning</div>', unsafe_allow_html=True)
st.write("---")

menu = st.sidebar.radio(
    "Menu principal",
    [
        "📊 Dataset y Analisis",
        "🧩 KMeans - Segmentacion",
        "🔗 Apriori - Reglas Asociacion",
        "🤖 Modelos ML",
        "🔮 Predecir Credito"
    ]
)



# =====================================================================
# 1. DATASET Y ANALISIS
# =====================================================================
if menu == "📊 Dataset y Analisis":
    st.write("## 📊 Criterio 1: Dataset Tabular")
    st.write("Dataset financiero de CrediArancel con 250 registros de solicitudes de credito.")
    st.write("Formato: Excel (xlsx) - importado con **pandas.read_excel()**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Registros", df.shape[0])
    col2.metric("Columnas", df.shape[1])
    col3.metric("Aprobados", (df["estado_credito"] == "Aprobado").sum())

    st.write("### Columnas del dataset")
    info_df = pd.DataFrame({
        "Tipo": df.dtypes,
        "Nulos": df.isnull().sum(),
        "Valores unicos": df.nunique()
    })
    st.dataframe(info_df, use_container_width=True)

    st.write("### Vista del dataset")
    st.dataframe(df.head(10), use_container_width=True)

    st.write("### Estadisticas con numpy y pandas")
    st.code("""# numpy
import numpy as np
np.mean(df["ingreso_mensual"])
np.std(df["ingreso_mensual"])

# pandas
df.describe()
df.isnull().sum()
df["estado_credito"].value_counts()""", language="python")
    st.dataframe(df.describe(), use_container_width=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for i, col in enumerate(["edad", "ingreso_mensual", "deuda_actual", "monto_solicitado"]):
        axes[i//2, i%2].hist(df[col], bins=15, color="#2563eb", edgecolor="white")
        axes[i//2, i%2].set_title(f"Distribucion de {col}")
    plt.tight_layout()
    st.pyplot(fig)

# =====================================================================
# 2. KMEANS - SEGMENTACION
# =====================================================================
elif menu == "🧩 KMeans - Segmentacion":
    st.write("## 🧩 KMeans - Segmentacion de Clientes")
    st.code("""from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3, random_state=42)
df["segmento"] = kmeans.fit_predict(X)""", language="python")

    X_cluster = df[["ingreso_mensual", "deuda_actual", "monto_solicitado"]]
    scaler_c = StandardScaler()
    X_cluster_s = scaler_c.fit_transform(X_cluster)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df["segmento"] = kmeans.fit_predict(X_cluster_s)

    st.write(f"Inercia del modelo: {kmeans.inertia_:.2f}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sc1 = axes[0].scatter(df["ingreso_mensual"], df["deuda_actual"], c=df["segmento"], cmap="viridis", s=50)
    axes[0].set_xlabel("Ingreso mensual")
    axes[0].set_ylabel("Deuda actual")
    axes[0].set_title("Segmentos: Ingreso vs Deuda")
    plt.colorbar(sc1, ax=axes[0])
    sc2 = axes[1].scatter(df["ingreso_mensual"], df["monto_solicitado"], c=df["segmento"], cmap="viridis", s=50)
    axes[1].set_xlabel("Ingreso mensual")
    axes[1].set_ylabel("Monto solicitado")
    axes[1].set_title("Segmentos: Ingreso vs Monto")
    plt.colorbar(sc2, ax=axes[1])
    st.pyplot(fig)

    centros = pd.DataFrame(
        scaler_c.inverse_transform(kmeans.cluster_centers_),
        columns=["Ingreso mensual", "Deuda actual", "Monto solicitado"]
    )
    centros.index = [f"Segmento {i+1}" for i in range(3)]
    st.dataframe(centros, use_container_width=True)

# =====================================================================
# 3. APRIORI - REGLAS DE ASOCIACION
# =====================================================================
elif menu == "🔗 Apriori - Reglas Asociacion":
    st.write("## 🔗 Algoritmo Apriori - Reglas de Asociacion")

    st.code("""# Implementacion manual del algoritmo Apriori
# Encuentra itemsets frecuentes y reglas de asociacion
# Ej: (zona='La Merced', tipo='Prestamo') -> (estado='Rechazado')

from itertools import combinations

def apriori(transacciones, min_support):
    itemsets frecuentes = ...
    reglas = ...""", language="python")

    cols = ["zona", "tipo_credito", "historial_crediticio", "estado_credito", "nivel_riesgo"]
    trans = df[cols].astype(str).apply(lambda r: [f"{c}={r[c]}" for c in cols], axis=1).tolist()
    n = len(trans)

    items = {}
    for t in trans:
        for item in t:
            items[item] = items.get(item, 0) + 1

    freq = {k: v for k, v in items.items() if v / n >= 0.08}
    st.write(f"Itemsets frecuentes encontrados: {len(freq)}")

    df_freq = pd.DataFrame(list(freq.items()), columns=["Item", "Frecuencia"])
    df_freq["Support"] = df_freq["Frecuencia"] / n
    st.dataframe(df_freq.sort_values("Frecuencia", ascending=False), use_container_width=True)

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
        st.write("### Reglas de asociacion encontradas")
        st.dataframe(pd.DataFrame(reglas[:15], columns=["Antecedente", "Consecuente", "Support", "Confianza"]), use_container_width=True)

        fig, ax = plt.subplots(figsize=(10, 5))
        top = reglas[:10]
        ax.barh(range(len(top)), [r[3] for r in top], color="#2563eb")
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels([f"{r[0]} -> {r[1]}" for r in top], fontsize=8)
        ax.set_xlabel("Confianza")
        ax.set_title("Top 10 reglas de asociacion")
        st.pyplot(fig)
    else:
        st.info("No se encontraron reglas con el soporte minimo configurado.")

# =====================================================================
# 4. MODELOS ML
# =====================================================================
elif menu == "🤖 Modelos ML":
    st.write("## 🤖 Modelos de Machine Learning")
    st.write("Implementacion de **KNN, Decision Tree (ID3), Random Forest y Regresion Lineal** con **scikit-learn**.")

    st.code("""from sklearn.neighbors import KNeighborsClassifier      # KNN
from sklearn.tree import DecisionTreeClassifier           # ID3
from sklearn.ensemble import RandomForestClassifier       # Random Forest
from sklearn.linear_model import LinearRegression         # Regresion Lineal
from sklearn.metrics import mean_squared_error            # MSE""", language="python")

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

    st.write("### Resultados")

    resultados = []
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
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

        ConfusionMatrixDisplay.from_predictions(y_test, y_pred, ax=axes[idx], cmap="Blues", display_labels=["Rechazado", "Aprobado"])
        axes[idx].set_title(f"{nombre} - MSE: {mse:.4f}")

    plt.tight_layout()
    st.pyplot(fig)

    df_res = pd.DataFrame(resultados)
    st.dataframe(df_res.style.highlight_max(axis=0, subset=["Accuracy", "Precision", "Recall", "F1-Score"]).highlight_min(axis=0, subset=["MSE"]), use_container_width=True)



    st.write("### Arbol de decision (ID3)")
    arbol = DecisionTreeClassifier(criterion="entropy", max_depth=3, random_state=42)
    arbol.fit(X_train, y_train)
    fig_a, ax_a = plt.subplots(figsize=(16, 8))
    plot_tree(arbol, feature_names=feature_cols, class_names=["Rechazado", "Aprobado"], filled=True, ax=ax_a, fontsize=8)
    st.pyplot(fig_a)

    st.write("### Importancia de caracteristicas (Random Forest)")
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    imp = pd.DataFrame({"Feature": feature_cols, "Importancia": rf.feature_importances_}).sort_values("Importancia")
    fig_i, ax_i = plt.subplots(figsize=(10, 8))
    ax_i.barh(imp["Feature"], imp["Importancia"], color="#2563eb")
    ax_i.set_xlabel("Importancia")
    st.pyplot(fig_i)

# =====================================================================
# 5. PREDECIR CREDITO
# =====================================================================
elif menu == "🔮 Predecir Credito":
    st.write("## 🔮 Evaluar y Predecir Credito")

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

    col1, col2 = st.columns(2)

    with col1:
        edad = st.number_input("Edad", 18, 80, 30)
        ingreso = st.number_input("Ingreso mensual (S/)", 0.0, 50000.0, 2500.0)
        deuda = st.number_input("Deuda actual (S/)", 0.0, 50000.0, 500.0)
        historial = st.selectbox("Historial crediticio", ["Excelente", "Bueno", "Regular", "Malo"])
        mora = st.selectbox("Tiene mora", ["No", "Si"])
        zona = st.selectbox("Zona", ["La Merced", "Mazamari", "Pangoa", "Pichanaki", "Huancayo", "Tarma", "Satipo"])

    with col2:
        monto = st.number_input("Monto solicitado (S/)", 0.0, 50000.0, 2000.0)
        cuotas = st.number_input("Numero de cuotas", 1, 60, 12)
        frecuencia = st.selectbox("Frecuencia de pago", ["Mensual", "Quincenal", "Semanal", "Diario"])
        tipo = st.selectbox("Tipo de credito", ["Prestamo personal", "Artefacto", "Celular", "Mueble", "Electrodomestico", "Moto"])
        riesgo = st.selectbox("Nivel de riesgo", ["Bajo", "Medio", "Alto"])
        dias = st.number_input("Dias de atraso", 0, 30, 0)

    if st.button("Predecir con Machine Learning", type="primary"):
        entrada = pd.DataFrame([[
            edad, ingreso, deuda, monto, cuotas,
            deuda / (ingreso + 1), monto / (ingreso + 1), ingreso - deuda,
            monto / (cuotas + 1), (monto / (cuotas + 1)) / (ingreso + 1), dias,
            le_dict_p["historial_crediticio"].transform([historial])[0],
            le_dict_p["frecuencia_pago"].transform([frecuencia])[0],
            le_dict_p["tipo_credito"].transform([tipo])[0],
            le_dict_p["nivel_riesgo"].transform([riesgo])[0],
            le_dict_p["tiene_mora"].transform([mora])[0],
            le_dict_p["zona"].transform([zona])[0]
        ]], columns=fcols)

        entrada_s = scaler_p.transform(entrada)

        st.write("### Resultados por modelo")
        cols = st.columns(3)
        votos_aprobado = 0
        votos_rechazado = 0

        for i, (nombre, modelo) in enumerate(modelos_p.items()):
            pred = modelo.predict(entrada_s)[0]
            if pred == 1:
                votos_aprobado += 1
                cols[i].success(f"**{nombre}**\n\n✅ Aprobado")
            else:
                votos_rechazado += 1
                cols[i].error(f"**{nombre}**\n\n❌ Rechazado")

        st.write("### Votacion final (Ensemble)")
        if votos_aprobado > votos_rechazado:
            st.markdown(f'<div class="resultado-aprobado">✅ CREDITO APROBADO ({votos_aprobado}/{votos_aprobado + votos_rechazado} modelos)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="resultado-rechazado">❌ CREDITO RECHAZADO ({votos_rechazado}/{votos_aprobado + votos_rechazado} modelos)</div>', unsafe_allow_html=True)

        st.write("### Datos ingresados")
        st.dataframe(entrada, use_container_width=True)

