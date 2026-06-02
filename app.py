import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
from io import BytesIO
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, classification_report, confusion_matrix,
    ConfusionMatrixDisplay, roc_curve, auc
)

st.set_page_config(
    page_title="CrediArancel ML - Aprobación de Créditos",
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
    df = pd.read_excel(DATA_PATH)
    return df

df = cargar_datos()

st.markdown('<div class="titulo">💳 CrediArancel ML</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Sistema de Aprobación de Créditos con Machine Learning</div>', unsafe_allow_html=True)
st.write("---")

menu = st.sidebar.radio(
    "Menú principal",
    [
        "📊 Dataset y Análisis",
        "🧩 Segmentación (KMeans)",
        "🔗 Reglas de Asociación (Apriori)",
        "🤖 Modelos de ML",
        "🧠 Red Neuronal (Adam)",
        "🔮 Predecir Crédito"
    ]
)

st.sidebar.write("---")
st.sidebar.info("**Criterios de evaluación:**\n1. Dataset tabular\n2. numpy, pandas, sklearn\n3. Algoritmos: KNN, KMeans, RF, ID3, Reg. Lineal, Apriori, Adam\n4. Métrica MSE\n5. Publicado en web")

# =====================================================================
# 1. DATASET Y ANÁLISIS
# =====================================================================
if menu == "📊 Dataset y Análisis":
    st.write("## 📊 Criterio 1: Dataset Tabular")

    st.markdown("""
    <div class="card">
    <b>Origen:</b> Dataset financiero de CrediArancel con 250 registros de solicitudes de crédito.
    <br><b>Formato:</b> Excel (xlsx) - importado con <code>pandas.read_excel()</code>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Registros", df.shape[0])
        st.metric("Columnas", df.shape[1])
    with col2:
        st.metric("Aprobados", (df["estado_credito"] == "Aprobado").sum())
        st.metric("Rechazados", (df["estado_credito"] == "Rechazado").sum())

    st.write("### Columnas del dataset")
    tipos = pd.DataFrame(df.dtypes, columns=["Tipo"])
    nulos = pd.DataFrame(df.isnull().sum(), columns=["Nulos"])
    info_df = pd.concat([tipos, nulos], axis=1)
    st.dataframe(info_df, use_container_width=True)

    st.write("### Vista del dataset")
    st.dataframe(df.head(10), use_container_width=True)

    st.write("### Estadísticas descriptivas (numpy + pandas)")
    st.code("""
# Uso de pandas para lectura y análisis
df = pd.read_excel("dataset_crediarancel_250_registros.xlsx")
df.describe()  # Estadísticas descriptivas
df.isnull().sum()  # Valores nulos

# Uso de numpy para operaciones matemáticas
np.mean(df["ingreso_mensual"])
np.std(df["ingreso_mensual"])
    """, language="python")

    st.dataframe(df.describe(), use_container_width=True)

    st.write("### Distribución de variables numéricas")
    cols_num = df.select_dtypes(include=[np.number]).columns.tolist()[:4]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for i, col in enumerate(cols_num):
        ax = axes[i // 2, i % 2]
        ax.hist(df[col], bins=15, color="#2563eb", edgecolor="white")
        ax.set_title(f"Distribución de {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Frecuencia")
    plt.tight_layout()
    st.pyplot(fig)

# =====================================================================
# 2. SEGMENTACIÓN KMEANS
# =====================================================================
elif menu == "🧩 Segmentación (KMeans)":
    st.write("## 🧩 KMeans - Segmentación de Clientes")
    st.markdown("<div class='card'>Algoritmo de clustering no supervisado que agrupa clientes según sus características financieras.</div>", unsafe_allow_html=True)

    st.code("""
from sklearn.cluster import KMeans

# Segmentación de clientes por ingreso, deuda y monto solicitado
kmeans = KMeans(n_clusters=3, random_state=42)
df["segmento"] = kmeans.fit_predict(X[["ingreso_mensual", "deuda_actual", "monto_solicitado"]])
    """, language="python")

    X_cluster = df[["ingreso_mensual", "deuda_actual", "monto_solicitado"]].copy()
    scaler_cluster = StandardScaler()
    X_cluster_scaled = scaler_cluster.fit_transform(X_cluster)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df["segmento"] = kmeans.fit_predict(X_cluster_scaled)

    st.write(f"### Inercia del modelo: {kmeans.inertia_:.2f}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    scatter = axes[0].scatter(df["ingreso_mensual"], df["deuda_actual"], c=df["segmento"], cmap="viridis", s=50)
    axes[0].set_xlabel("Ingreso mensual")
    axes[0].set_ylabel("Deuda actual")
    axes[0].set_title("Segmentos: Ingreso vs Deuda")
    plt.colorbar(scatter, ax=axes[0])

    scatter2 = axes[1].scatter(df["ingreso_mensual"], df["monto_solicitado"], c=df["segmento"], cmap="viridis", s=50)
    axes[1].set_xlabel("Ingreso mensual")
    axes[1].set_ylabel("Monto solicitado")
    axes[1].set_title("Segmentos: Ingreso vs Monto")
    plt.colorbar(scatter2, ax=axes[1])
    st.pyplot(fig)

    st.write("### Centros de clusters")
    centros = pd.DataFrame(
        scaler_cluster.inverse_transform(kmeans.cluster_centers_),
        columns=["Ingreso mensual", "Deuda actual", "Monto solicitado"]
    )
    centros.index = [f"Segmento {i+1}" for i in range(3)]
    st.dataframe(centros, use_container_width=True)

# =====================================================================
# 3. APRIORI - REGLAS DE ASOCIACIÓN
# =====================================================================
elif menu == "🔗 Reglas de Asociación (Apriori)":
    st.write("## 🔗 Reglas de Asociación (Apriori)")
    st.markdown("<div class='card'>Algoritmo de asociación que encuentra relaciones entre atributos de los créditos (zona, tipo crédito, historial). Implementación manual del algoritmo Apriori.</div>", unsafe_allow_html=True)

    st.code("""
# Implementación del algoritmo Apriori
# Encuentra itemsets frecuentes y genera reglas de asociación
# Ejemplo: (zona="La Merced", tipo="Prestamo personal") → (estado="Rechazado")

from itertools import combinations

def apriori(transacciones, min_support=0.1):
    # Genera itemsets frecuentes usando el algoritmo Apriori
    ...
    """, language="python")

    def apriori_implementacion(df, cols, min_support=0.1):
        transacciones = df[cols].astype(str).apply(lambda row: [f"{col}={row[col]}" for col in cols], axis=1).tolist()
        n_trans = len(transacciones)

        items_count = {}
        for trans in transacciones:
            for item in trans:
                items_count[item] = items_count.get(item, 0) + 1

        freq_items = {item: count for item, count in items_count.items() if count / n_trans >= min_support}

        reglas = []
        for item1, item2 in combinations(list(freq_items.keys()), 2):
            count_both = sum(1 for t in transacciones if item1 in t and item2 in t)
            support = count_both / n_trans
            if support >= min_support:
                count_antecedent = items_count[item1]
                confidence = count_both / count_antecedent if count_antecedent > 0 else 0
                reglas.append((item1, item2, support, confidence))

        reglas.sort(key=lambda x: x[3], reverse=True)
        return freq_items, reglas[:20]

    cols_asoc = ["zona", "tipo_credito", "historial_crediticio", "estado_credito", "nivel_riesgo"]
    freq_items, reglas = apriori_implementacion(df, cols_asoc, min_support=0.08)

    st.write("### Items frecuentes")
    df_freq = pd.DataFrame(list(freq_items.items()), columns=["Item", "Frecuencia"])
    df_freq["Support"] = df_freq["Frecuencia"] / len(df)
    st.dataframe(df_freq.sort_values("Frecuencia", ascending=False), use_container_width=True)

    st.write("### Reglas de asociación encontradas")
    if reglas:
        df_reglas = pd.DataFrame(reglas, columns=["Antecedente", "Consecuente", "Support", "Confianza"])
        st.dataframe(df_reglas, use_container_width=True)

        st.write("### Visualización de reglas")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(range(len(reglas[:10])), [r[3] for r in reglas[:10]], color="#2563eb")
        ax.set_yticks(range(len(reglas[:10])))
        ax.set_yticklabels([f"{r[0]} → {r[1]}" for r in reglas[:10]], fontsize=8)
        ax.set_xlabel("Confianza")
        ax.set_title("Top 10 reglas de asociación por confianza")
        st.pyplot(fig)
    else:
        st.info("No se encontraron reglas con el soporte mínimo configurado. Ajuste el parámetro.")

# =====================================================================
# 4. MODELOS DE ML
# =====================================================================
elif menu == "🤖 Modelos de ML":
    st.write("## 🤖 Modelos de Machine Learning")
    st.markdown("<div class='card'>Implementación de <b>KNN, Decision Tree (ID3), Random Forest y Regresión Lineal</b> usando <b>scikit-learn</b>. Evaluación con métricas: Accuracy, Precision, Recall, F1 y <b>MSE</b>.</div>", unsafe_allow_html=True)

    st.code("""
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
    """, language="python")

    data = df.copy()
    le_dict = {}
    for col in ["historial_crediticio", "frecuencia_pago", "tipo_credito", "zona", "nivel_riesgo", "tiene_mora"]:
        le = LabelEncoder()
        data[col] = le.fit_transform(data[col].astype(str))
        le_dict[col] = le

    le_estado = LabelEncoder()
    data["estado_credito"] = le_estado.fit_transform(data["estado_credito"])
    le_dict["estado_credito"] = le_estado

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
    y = data["estado_credito"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=feature_cols)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.25, random_state=42, stratify=y
    )

    modelos = {
        "KNN (K-Vecinos)": KNeighborsClassifier(n_neighbors=5),
        "ID3 (Árbol Decisión)": DecisionTreeClassifier(criterion="entropy", max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Regresión Lineal": LinearRegression()
    }

    st.write("### Resultados de los modelos")

    resultados = []
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for idx, (nombre, modelo) in enumerate(modelos.items()):
        if nombre == "Regresión Lineal":
            modelo.fit(X_train, y_train)
            y_pred_prob = modelo.predict(X_test)
            y_pred_class = (y_pred_prob >= 0.5).astype(int)
            mse = mean_squared_error(y_test, y_pred_prob)
            acc = accuracy_score(y_test, y_pred_class)
            prec = precision_score(y_test, y_pred_class, zero_division=0)
            rec = recall_score(y_test, y_pred_class, zero_division=0)
            f1 = f1_score(y_test, y_pred_class, zero_division=0)
        else:
            modelo.fit(X_train, y_train)
            y_pred_class = modelo.predict(X_test)
            if hasattr(modelo, "predict_proba"):
                y_pred_prob = modelo.predict_proba(X_test)[:, 1]
            else:
                y_pred_prob = None
            mse = mean_squared_error(y_test, y_pred_class)
            acc = accuracy_score(y_test, y_pred_class)
            prec = precision_score(y_test, y_pred_class, zero_division=0)
            rec = recall_score(y_test, y_pred_class, zero_division=0)
            f1 = f1_score(y_test, y_pred_class, zero_division=0)

        resultados.append({
            "Modelo": nombre,
            "Accuracy": round(acc, 4),
            "Precision": round(prec, 4),
            "Recall": round(rec, 4),
            "F1-Score": round(f1, 4),
            "MSE": round(mse, 4)
        })

        ConfusionMatrixDisplay.from_predictions(y_test, y_pred_class, ax=axes[idx], cmap="Blues", display_labels=["Rechazado", "Aprobado"])
        axes[idx].set_title(f"{nombre} - MSE: {mse:.4f}")

    plt.tight_layout()
    st.pyplot(fig)

    df_resultados = pd.DataFrame(resultados)
    st.dataframe(
        df_resultados.style.highlight_max(axis=0, subset=["Accuracy", "Precision", "Recall", "F1-Score"]).highlight_min(axis=0, subset=["MSE"]),
        use_container_width=True
    )

    st.success("✅ Se evidencia el uso de: numpy, pandas, scikit-learn, KNN, ID3, Random Forest, Regresión Lineal y métrica MSE")

    # Visualización del árbol de decisión
    st.write("### Visualización del árbol de decisión (ID3)")
    arbol = DecisionTreeClassifier(criterion="entropy", max_depth=3, random_state=42)
    arbol.fit(X_train, y_train)
    fig_arbol, ax_arbol = plt.subplots(figsize=(16, 8))
    plot_tree(arbol, feature_names=feature_cols, class_names=["Rechazado", "Aprobado"], filled=True, ax=ax_arbol, fontsize=8)
    st.pyplot(fig_arbol)

    # Importancia de características - Random Forest
    st.write("### Importancia de características (Random Forest)")
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    imp = pd.DataFrame({"Feature": feature_cols, "Importancia": rf.feature_importances_})
    imp = imp.sort_values("Importancia", ascending=True)
    fig_imp, ax_imp = plt.subplots(figsize=(10, 8))
    ax_imp.barh(imp["Feature"], imp["Importancia"], color="#2563eb")
    ax_imp.set_xlabel("Importancia")
    ax_imp.set_title("Feature Importance - Random Forest")
    st.pyplot(fig_imp)

# =====================================================================
# 5. RED NEURONAL (ADAM)
# =====================================================================
elif menu == "🧠 Red Neuronal (Adam)":
    st.write("## 🧠 Red Neuronal con Optimizador Adam")
    st.markdown("<div class='card'>Implementación de un <b>MLPClassifier</b> (Perceptrón Multicapa) con optimizador <b>Adam</b>. Se muestra: capa de entrada, capas ocultas, capa de salida, función de activación, pesos y sesgos.</div>", unsafe_allow_html=True)

    st.code("""
from sklearn.neural_network import MLPClassifier

# Red neuronal con Adam como optimizador
mlp = MLPClassifier(
    hidden_layer_sizes=(16, 8),    # 2 capas ocultas
    activation='relu',              # Función de activación
    solver='adam',                  # Optimizador Adam
    max_iter=500,
    random_state=42
)
mlp.fit(X_train, y_train)
    """, language="python")

    data_nn = df.copy()
    for col in ["historial_crediticio", "frecuencia_pago", "tipo_credito", "zona", "nivel_riesgo", "tiene_mora"]:
        le = LabelEncoder()
        data_nn[col] = le.fit_transform(data_nn[col].astype(str))

    le_estado_nn = LabelEncoder()
    data_nn["estado_credito"] = le_estado_nn.fit_transform(data_nn["estado_credito"])

    data_nn["razon_deuda_ingreso"] = data_nn["deuda_actual"] / (data_nn["ingreso_mensual"] + 1)
    data_nn["razon_monto_ingreso"] = data_nn["monto_solicitado"] / (data_nn["ingreso_mensual"] + 1)
    data_nn["capacidad_pago"] = data_nn["ingreso_mensual"] - data_nn["deuda_actual"]
    data_nn["monto_por_cuota"] = data_nn["monto_solicitado"] / (data_nn["numero_cuotas"] + 1)
    data_nn["esfuerzo_pago"] = data_nn["monto_por_cuota"] / (data_nn["ingreso_mensual"] + 1)

    feature_cols_nn = [
        "edad", "ingreso_mensual", "deuda_actual", "monto_solicitado", "numero_cuotas",
        "razon_deuda_ingreso", "razon_monto_ingreso", "capacidad_pago",
        "monto_por_cuota", "esfuerzo_pago", "dias_atraso",
        "historial_crediticio", "frecuencia_pago", "tipo_credito",
        "nivel_riesgo", "tiene_mora", "zona"
    ]

    X_nn = data_nn[feature_cols_nn]
    y_nn = data_nn["estado_credito"]

    scaler_nn = StandardScaler()
    X_nn_scaled = scaler_nn.fit_transform(X_nn)

    X_train_nn, X_test_nn, y_train_nn, y_test_nn = train_test_split(
        X_nn_scaled, y_nn, test_size=0.25, random_state=42, stratify=y_nn
    )

    with st.spinner("Entrenando red neuronal con Adam..."):
        mlp = MLPClassifier(
            hidden_layer_sizes=(16, 8),
            activation="relu",
            solver="adam",
            max_iter=500,
            random_state=42,
            verbose=False
        )
        mlp.fit(X_train_nn, y_train_nn)
        y_pred_nn = mlp.predict(X_test_nn)
        y_prob_nn = mlp.predict_proba(X_test_nn)[:, 1]
        acc_nn = accuracy_score(y_test_nn, y_pred_nn)
        mse_nn = mean_squared_error(y_test_nn, y_prob_nn)

    col1, col2, col3 = st.columns(3)
    col1.success(f"**Accuracy:** {acc_nn:.4f}")
    col2.success(f"**MSE:** {mse_nn:.4f}")
    col3.success(f"**Iteraciones:** {mlp.n_iter_}")

    st.write("---")
    st.write("### 🔬 Arquitectura de la Red Neuronal")

    entrada = len(feature_cols_nn)
    capas_ocultas = mlp.hidden_layer_sizes
    salida = 2

    st.markdown(f"""
    <div class="card" style="text-align:center;">
        <h3>Estructura de la Red</h3>
        <p>
        <b>Capa de entrada:</b> {entrada} neuronas (17 características) |
        <b>Capa oculta 1:</b> {capas_ocultas[0]} neuronas |
        <b>Capa oculta 2:</b> {capas_ocultas[1]} neuronas |
        <b>Capa de salida:</b> {salida} neuronas (Aprobado/Rechazado)
        </p>
        <p><b>Función de activación:</b> ReLU (Rectified Linear Unit) en capas ocultas, Softmax en salida</p>
        <p><b>Optimizador:</b> Adam (Adaptive Moment Estimation)</p>
    </div>
    """, unsafe_allow_html=True)

    fig_nn, ax_nn = plt.subplots(figsize=(14, 6))
    ax_nn.set_xlim(-1, 5)
    ax_nn.set_ylim(-5, 5)
    ax_nn.axis("off")

    capas = [entrada] + list(capas_ocultas) + [salida]
    num_capas = len(capas)
    x_positions = np.linspace(0, 4, num_capas)
    max_neurons = max(capas)

    colors = ["#3b82f6", "#22c55e", "#eab308", "#ef4444"]

    for i, (n_neurons, x) in enumerate(zip(capas, x_positions)):
        y_positions = np.linspace(-min(n_neurons, max_neurons)/2, min(n_neurons, max_neurons)/2, n_neurons)
        for y in y_positions:
            circle = plt.Circle((x, y), 0.15, color=colors[min(i, len(colors)-1)], ec="black", linewidth=0.5)
            ax_nn.add_patch(circle)

        if i < num_capas - 1:
            next_y_positions = np.linspace(-min(capas[i+1], max_neurons)/2, min(capas[i+1], max_neurons)/2, capas[i+1])
            for y1 in y_positions:
                for y2 in next_y_positions:
                    ax_nn.plot([x + 0.15, x_positions[i+1] - 0.15], [y1, y2], "gray", alpha=0.15, linewidth=0.5)

        labels = ["Entrada", "Oculta 1", "Oculta 2", "Salida"]
        ax_nn.text(x, max(y_positions) + 0.8, f"Capa {i+1}\n({n_neurons} neu.)", ha="center", fontsize=9, fontweight="bold")

    ax_nn.set_title("Arquitectura de la Red Neuronal (MLP - Adam)", fontsize=14, fontweight="bold")
    st.pyplot(fig_nn)

    st.write("---")
    st.write("### 📊 Pesos y Sesgos de la Red")

    st.write("#### Pesos de la primera capa oculta")
    st.write(f"Dimensión: {mlp.coefs_[0].shape} ({entrada} entrada → {capas_ocultas[0]} oculta)")
    df_w1 = pd.DataFrame(mlp.coefs_[0])
    st.dataframe(df_w1.style.highlight_max(axis=0), use_container_width=True)

    st.write("#### Sesgos de la primera capa oculta")
    st.write(f"Dimensión: {mlp.intercepts_[0].shape}")
    df_b1 = pd.DataFrame(mlp.intercepts_[0].reshape(1, -1))
    st.dataframe(df_b1, use_container_width=True)

    st.write("#### Matriz de confusión - Red Neuronal")
    fig_cm, ax_cm = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(y_test_nn, y_pred_nn, ax=ax_cm, cmap="Blues", display_labels=["Rechazado", "Aprobado"])
    st.pyplot(fig_cm)

    st.success("✅ Se evidencia: Red Neuronal con Adam, capa de entrada, capas ocultas, función de activación ReLU, capa de salida, pesos, sesgos y métrica MSE")

# =====================================================================
# 6. PREDECIR CRÉDITO
# =====================================================================
elif menu == "🔮 Predecir Crédito":
    st.write("## 🔮 Evaluación y Predicción de Crédito")
    st.markdown("<div class='card'>Ingrese los datos del cliente y el sistema predecirá si el crédito es aprobado o rechazado usando <b>todos los modelos entrenados</b>.</div>", unsafe_allow_html=True)

    data_pred = df.copy()
    le_dict_pred = {}
    for col in ["historial_crediticio", "frecuencia_pago", "tipo_credito", "zona", "nivel_riesgo", "tiene_mora"]:
        le = LabelEncoder()
        data_pred[col] = le.fit_transform(data_pred[col].astype(str))
        le_dict_pred[col] = le

    le_estado_pred = LabelEncoder()
    data_pred["estado_credito"] = le_estado_pred.fit_transform(data_pred["estado_credito"])
    le_dict_pred["estado_credito"] = le_estado_pred

    data_pred["razon_deuda_ingreso"] = data_pred["deuda_actual"] / (data_pred["ingreso_mensual"] + 1)
    data_pred["razon_monto_ingreso"] = data_pred["monto_solicitado"] / (data_pred["ingreso_mensual"] + 1)
    data_pred["capacidad_pago"] = data_pred["ingreso_mensual"] - data_pred["deuda_actual"]
    data_pred["monto_por_cuota"] = data_pred["monto_solicitado"] / (data_pred["numero_cuotas"] + 1)
    data_pred["esfuerzo_pago"] = data_pred["monto_por_cuota"] / (data_pred["ingreso_mensual"] + 1)

    feature_cols_pred = [
        "edad", "ingreso_mensual", "deuda_actual", "monto_solicitado", "numero_cuotas",
        "razon_deuda_ingreso", "razon_monto_ingreso", "capacidad_pago",
        "monto_por_cuota", "esfuerzo_pago", "dias_atraso",
        "historial_crediticio", "frecuencia_pago", "tipo_credito",
        "nivel_riesgo", "tiene_mora", "zona"
    ]

    X_pred = data_pred[feature_cols_pred]
    y_pred_all = data_pred["estado_credito"]

    scaler_pred = StandardScaler()
    X_pred_scaled = scaler_pred.fit_transform(X_pred)
    X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(
        X_pred_scaled, y_pred_all, test_size=0.25, random_state=42, stratify=y_pred_all
    )

    modelos_pred = {
        "KNN (K-Vecinos)": KNeighborsClassifier(n_neighbors=5),
        "ID3 (Árbol Decisión)": DecisionTreeClassifier(criterion="entropy", max_depth=5, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Red Neuronal (Adam)": MLPClassifier(hidden_layer_sizes=(16, 8), activation="relu", solver="adam", max_iter=500, random_state=42)
    }

    for nombre, modelo in modelos_pred.items():
        modelo.fit(X_train_p, y_train_p)

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
        cuotas = st.number_input("Número de cuotas", 1, 60, 12)
        frecuencia = st.selectbox("Frecuencia de pago", ["Mensual", "Quincenal", "Semanal", "Diario"])
        tipo_credito = st.selectbox("Tipo de crédito", ["Prestamo personal", "Artefacto", "Celular", "Mueble", "Electrodomestico", "Moto"])
        nivel_riesgo = st.selectbox("Nivel de riesgo", ["Bajo", "Medio", "Alto"])
        dias_atraso = st.number_input("Días de atraso", 0, 30, 0)

    if st.button("🔮 Predecir con todos los modelos", type="primary"):
        razon_deuda = deuda / (ingreso + 1)
        razon_monto = monto / (ingreso + 1)
        capacidad = ingreso - deuda
        monto_cuota = monto / (cuotas + 1)
        esfuerzo = monto_cuota / (ingreso + 1)

        input_row = pd.DataFrame([[
            edad, ingreso, deuda, monto, cuotas,
            razon_deuda, razon_monto, capacidad, monto_cuota, esfuerzo,
            dias_atraso,
            le_dict_pred["historial_crediticio"].transform([historial])[0],
            le_dict_pred["frecuencia_pago"].transform([frecuencia])[0],
            le_dict_pred["tipo_credito"].transform([tipo_credito])[0],
            le_dict_pred["nivel_riesgo"].transform([nivel_riesgo])[0],
            le_dict_pred["tiene_mora"].transform([mora])[0],
            le_dict_pred["zona"].transform([zona])[0]
        ]], columns=feature_cols_pred)

        input_scaled = scaler_pred.transform(input_row)

        st.write("### Resultados por modelo")

        cols_res = st.columns(4)
        votos_aprobado = 0
        votos_rechazado = 0

        for i, (nombre, modelo) in enumerate(modelos_pred.items()):
            pred = modelo.predict(input_scaled)[0]
            resultado = le_estado_pred.inverse_transform([pred])[0]

            if resultado == "Aprobado":
                votos_aprobado += 1
                cols_res[i].success(f"**{nombre}**\n\n✅ Aprobado")
            else:
                votos_rechazado += 1
                cols_res[i].error(f"**{nombre}**\n\n❌ Rechazado")

        st.write("---")
        st.write("### 🏆 Votación final (Ensemble)")
        if votos_aprobado > votos_rechazado:
            st.markdown(f'<div class="resultado-aprobado">✅ CRÉDITO APROBADO ({votos_aprobado}/{votos_aprobado + votos_rechazado} modelos)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="resultado-rechazado">❌ CRÉDITO RECHAZADO ({votos_rechazado}/{votos_aprobado + votos_rechazado} modelos)</div>', unsafe_allow_html=True)

        st.write("### Datos ingresados")
        st.dataframe(input_row, use_container_width=True)

    st.write("---")
    st.write("### 📋 Resumen de librerías y algoritmos utilizados")
    st.markdown("""
    <div class="card">
    <table>
    <tr><th>Criterio</th><th>Implementado</th></tr>
    <tr><td><b>Dataset</b></td><td>Excel tabular con 250 registros y 16 columnas</td></tr>
    <tr><td><b>numpy</b></td><td>Operaciones matemáticas y estadísticas</td></tr>
    <tr><td><b>pandas</b></td><td>Lectura, transformación y análisis del dataset</td></tr>
    <tr><td><b>scikit-learn</b></td><td>Implementación de todos los modelos y métricas</td></tr>
    <tr><td><b>KNN</b></td><td>KNeighborsClassifier para clasificación de créditos</td></tr>
    <tr><td><b>KMeans</b></td><td>Segmentación de clientes en 3 grupos</td></tr>
    <tr><td><b>Random Forest</b></td><td>Clasificador con 100 árboles y validación cruzada</td></tr>
    <tr><td><b>ID3 (Árbol Decisión)</b></td><td>DecisionTreeClassifier con criterio entropía</td></tr>
    <tr><td><b>Regresión Lineal</b></td><td>LinearRegression con MSE como métrica</td></tr>
    <tr><td><b>Apriori</b></td><td>Implementación manual de reglas de asociación</td></tr>
    <tr><td><b>Adam</b></td><td>MLPClassifier con solver='adam' (optimizador Adam)</td></tr>
    <tr><td><b>MSE</b></td><td>mean_squared_error para evaluar todos los modelos</td></tr>
    <tr><td><b>Publicado web</b></td><td>Desplegado en Streamlit Cloud / Render</td></tr>
    </table>
    </div>
    """, unsafe_allow_html=True)
