"""Aplicacion Streamlit para la evaluacion forestal Tara + INIA."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import DB_PATH, query, table


st.set_page_config(
    page_title="Evaluacion forestal | SERFOR",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = ["#176B55", "#D89B32", "#4C8FA3", "#843E52", "#7B8E57", "#8E5A3C"]

st.markdown(
    """
    <style>
      :root { --forest:#176B55; --sand:#F3EFE6; --ink:#17352D; }
      .stApp { background: linear-gradient(180deg,#F8FAF7 0,#FFFFFF 22rem); }
      [data-testid="stSidebar"] { background:#123E34; }
      [data-testid="stSidebar"] * { color:#F7F2E8; }
      [data-testid="stMetric"] {
        background:white; border:1px solid #DDE7E1; border-radius:8px;
        padding:1rem 1.1rem; box-shadow:0 4px 18px rgba(23,53,45,.06);
      }
      .hero { padding:1.5rem 1.7rem; border-radius:8px; color:white;
        background:linear-gradient(120deg,#123E34,#24765F); margin-bottom:1.2rem; }
      .hero h1 { margin:0; font-size:2rem; letter-spacing:0; }
      .hero p { margin:.45rem 0 0; color:#E4F0EA; }
      .eyebrow { color:#DDB46A; font-size:.78rem;
        text-transform:uppercase; font-weight:700; }
      .note { border-left:4px solid #D89B32; background:#FFF9ED;
        padding:.75rem 1rem; border-radius:0 8px 8px 0; }
      div[data-testid="stPlotlyChart"] { background:white; border-radius:8px; }
      #MainMenu, footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not DB_PATH.exists():
    st.error(
        "No se encontro `App_forestal/data/forestal.db`. "
        "Ejecute `python scripts/prepare_tara_inia_data.py` con el entorno Conda sigexpert."
    )
    st.stop()


@st.cache_data(show_spinner=False)
def filter_catalog() -> pd.DataFrame:
    return query("SELECT DISTINCT region, manejo, clase FROM tara_integrada")


def options(frame: pd.DataFrame, column: str) -> list[str]:
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def apply_filters(frame: pd.DataFrame, selected: dict[str, list[str]]) -> pd.DataFrame:
    result = frame.copy()
    for column, values in selected.items():
        if values and column in result:
            result = result[result[column].isin(values)]
    return result


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def download_button(frame: pd.DataFrame, filename: str) -> None:
    st.download_button(
        "Descargar datos filtrados",
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">SERFOR · Tara e INIA</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state() -> None:
    st.warning("No hay observaciones para la combinacion de filtros seleccionada.")
    st.stop()


def style_figure(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=55, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", color="#17352D"),
        legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#E8EEE9")
    fig.update_yaxes(gridcolor="#E8EEE9")
    return fig


catalog = filter_catalog()
with st.sidebar:
    st.markdown("## Evaluacion forestal")
    st.caption("Tara · INIA")
    page = st.radio(
        "Navegacion",
        ["Resumen", "Tara sitios", "Tara clima", "Tara suelos", "INIA", "Metodologia"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("#### Filtros Tara")
    selected_region = st.multiselect("Region", options(catalog, "region"))
    dependent = catalog[catalog["region"].isin(selected_region)] if selected_region else catalog
    selected_manejo = st.multiselect("Manejo", options(dependent, "manejo"))
    if selected_manejo:
        dependent = dependent[dependent["manejo"].isin(selected_manejo)]
    selected_clase = st.multiselect("Clase diametrica", options(dependent, "clase"))
    st.caption("Los filtros vacios incluyen todos los valores.")

filters = {"region": selected_region, "manejo": selected_manejo, "clase": selected_clase}


def render_summary() -> None:
    hero("Panorama Tara e INIA", "Lectura integrada de sitios de tara, variables edafoclimaticas e informacion institucional INIA.")
    tara = apply_filters(table("tara_integrada"), filters)
    inia_eea = table("inia_eea")
    inia_lineas = table("inia_lineas")
    if tara.empty:
        empty_state()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros Tara", f"{len(tara):,}")
    c2.metric("Departamentos Tara", tara["region"].nunique())
    c3.metric("EEA INIA", f"{len(inia_eea):,}")
    c4.metric("Lineas INIA", f"{len(inia_lineas):,}")

    left, right = st.columns([1.2, 1])
    with left:
        counts = tara.groupby(["region", "manejo"], dropna=False).size().reset_index(name="registros")
        fig = px.bar(counts, x="region", y="registros", color="manejo", barmode="group", color_discrete_sequence=COLORS, title="Cobertura Tara por departamento y manejo")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        summary = apply_filters(table("vw_tara_resumen_region"), {"region": selected_region})
        fig = px.scatter(summary, x="temperatura_media", y="ph_medio", size="sitios", color="region", hover_data=["precipitacion_total_media", "materia_organica_media"], color_discrete_sequence=COLORS, title="Relacion clima-suelo por departamento")
        st.plotly_chart(style_figure(fig), width="stretch")

    st.markdown(
        '<div class="note">La aplicacion ya no consume informacion de taninos ni presenta una pestana de comparacion. '
        "El analisis operativo se concentra en Tara e INIA.</div>",
        unsafe_allow_html=True,
    )


def render_tara_sites() -> None:
    hero("Tara sitios", "Registro de unidades de evaluacion, productores, ubicacion y practicas de manejo.")
    data = apply_filters(table("tara_sitios"), filters)
    if data.empty:
        empty_state()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(data):,}")
    c2.metric("Localidades", data["localidad"].nunique())
    c3.metric("Propietarios", data["propietario"].nunique())
    c4.metric("Altitud media", f"{numeric(data['altitud']).mean():,.0f} m")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(data, x="altitud", color="manejo", color_discrete_sequence=COLORS, title="Distribucion de altitud")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        reg = data.groupby(["region", "clase"], dropna=False).size().reset_index(name="registros")
        fig = px.bar(reg, x="region", y="registros", color="clase", color_discrete_sequence=COLORS, title="Clases diametricas por departamento")
        st.plotly_chart(style_figure(fig), width="stretch")

    visible = ["codigo_dei", "region", "provincia", "distrito", "localidad", "manejo", "clase", "altitud", "superficie_registrada_ha", "edad_de_plantacion", "fuente_de_riego", "plagas", "fertilizacion"]
    st.dataframe(data[[col for col in visible if col in data]], width="stretch", hide_index=True)
    download_button(data, "tara_sitios_filtrados.csv")


CLIMATE_METRICS = {
    "tmedia_prom": "Temperatura media",
    "tmax_prom": "Temperatura maxima promedio",
    "tmin_prom": "Temperatura minima promedio",
    "humedad_prom": "Humedad promedio",
    "precip_total_mm": "Precipitacion total",
}


def render_tara_climate() -> None:
    hero("Tara clima", "Condiciones climaticas asociadas a las unidades de evaluacion.")
    data = apply_filters(table("tara_clima"), filters)
    if data.empty:
        empty_state()
    metric = st.selectbox("Variable climatica", list(CLIMATE_METRICS), format_func=CLIMATE_METRICS.get)
    values = numeric(data[metric]).dropna()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(data):,}")
    c2.metric("Estaciones", data["estacion"].nunique())
    c3.metric("Promedio", f"{values.mean():,.2f}" if len(values) else "-")
    c4.metric("Maximo", f"{values.max():,.2f}" if len(values) else "-")

    left, right = st.columns(2)
    with left:
        fig = px.box(data, x="region", y=metric, color="manejo", color_discrete_sequence=COLORS, title=f"{CLIMATE_METRICS[metric]} por departamento")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        fig = px.scatter(data, x="tmedia_prom", y="precip_total_mm", color="region", symbol="clase", hover_data=["estacion", "altitud_est"], color_discrete_sequence=COLORS, title="Temperatura media y precipitacion")
        st.plotly_chart(style_figure(fig), width="stretch")

    visible = ["region", "manejo", "clase", "estacion", "altitud_est", "tmedia_prom", "humedad_prom", "precip_total_mm", "dias_registrados"]
    st.dataframe(data[[col for col in visible if col in data]], width="stretch", hide_index=True)
    download_button(data, "tara_clima_filtrado.csv")


SOIL_METRICS = {
    "ph": "pH",
    "mat_org": "Materia organica",
    "conductividad": "Conductividad",
    "fosforo_disp": "Fosforo disponible",
    "potasio_disp": "Potasio disponible",
    "arena": "Arena",
    "arcilla": "Arcilla",
    "limo": "Limo",
}


def render_tara_soils() -> None:
    hero("Tara suelos", "Propiedades fisicas y quimicas del suelo para priorizar interpretaciones productivas.")
    data = apply_filters(table("tara_suelos"), filters)
    if data.empty:
        empty_state()
    metric = st.selectbox("Variable de suelo", list(SOIL_METRICS), format_func=SOIL_METRICS.get)
    values = numeric(data[metric]).dropna()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Muestras", f"{len(data):,}")
    c2.metric("Clases texturales", data["clase_text"].nunique())
    c3.metric("Promedio", f"{values.mean():,.2f}" if len(values) else "-")
    c4.metric("Mediana", f"{values.median():,.2f}" if len(values) else "-")

    left, right = st.columns(2)
    with left:
        fig = px.violin(data, x="manejo", y=metric, color="clase", box=True, color_discrete_sequence=COLORS, title=f"{SOIL_METRICS[metric]} por manejo")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        fig = px.scatter(data, x="arena", y="arcilla", color="clase_text", symbol="region", hover_data=["cod_campo", "ph", "mat_org"], color_discrete_sequence=COLORS, title="Textura del suelo")
        st.plotly_chart(style_figure(fig), width="stretch")

    visible = ["region", "manejo", "clase", "cod_campo", "clase_text", "ph", "mat_org", "fosforo_disp", "potasio_disp", "arena", "arcilla", "limo"]
    st.dataframe(data[[col for col in visible if col in data]], width="stretch", hide_index=True)
    download_button(data, "tara_suelos_filtrados.csv")


def render_inia() -> None:
    hero("INIA", "Resumen estructurado de estaciones, lineas de investigacion y especies clave.")
    resumen = table("inia_resumen")
    eea = table("inia_eea")
    lineas = table("inia_lineas")
    secciones = table("inia_secciones")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EEA", f"{len(eea):,}")
    c2.metric("Departamentos", eea["departamento"].nunique())
    c3.metric("Lineas consolidadas", f"{len(lineas):,}")
    c4.metric("Secciones detalladas", f"{len(secciones):,}")

    if not resumen.empty:
        st.markdown("### Resumen ejecutivo")
        st.write(resumen.loc[0, "resumen_ejecutivo"])

    left, right = st.columns([1, 1.2])
    with left:
        counts = table("vw_inia_resumen_departamento")
        fig = px.bar(counts, x="departamento", y="estaciones", color="departamento", color_discrete_sequence=COLORS, title="EEA por departamento")
        st.plotly_chart(style_figure(fig), width="stretch")
    with right:
        st.dataframe(lineas, width="stretch", hide_index=True)

    st.markdown("### Fichas por estacion")
    if secciones.empty:
        st.info("No se identificaron fichas detalladas en el texto INIA.")
    else:
        selected = st.selectbox("Estacion Experimental Agraria", options(secciones, "eea"))
        row = secciones[secciones["eea"] == selected].iloc[0]
        st.markdown(f"**Departamento:** {row['departamento']}")
        st.write(row["resumen"])
        with st.expander("Ver detalle extraido"):
            st.write(row["detalle"])

    download_button(lineas, "inia_lineas_investigacion.csv")


def render_methodology() -> None:
    hero("Metodologia", "Alcance, trazabilidad y criterios de lectura de la version Tara + INIA.")
    st.markdown(
        """
        ### Fuentes incluidas

        - Tara sitios: `Data_InformacionSitios_FINAL.xlsx`, hoja `Datos-SITIOS`.
        - Tara clima: `Data_ClimaSitios_FINAL.xlsx`, hoja `Sitio-Clima`.
        - Tara suelos: `Data_SuelosSitios_FINAL.xlsx`, hoja `Data`.
        - INIA: `informacion_extraida_INIA_SERFOR.md`.

        ### Criterios de integracion

        Las tablas Tara se normalizan por departamento, manejo y clase diametrica.
        La vista integrada se usa para lectura territorial y de priorizacion; los
        archivos originales se conservan como tablas independientes para trazabilidad.

        INIA se procesa desde el texto estructurado, extrayendo estaciones,
        departamentos, lineas de investigacion, especies clave y fichas por EEA
        cuando estan disponibles.

        ### Cambios de alcance

        La fuente de taninos fue excluida del ETL y de la aplicacion. Tambien se
        elimino la pestana Comparacion para evitar lecturas cruzadas no solicitadas.
        """
    )
    coverage = table("vw_tara_cobertura")
    st.dataframe(coverage, width="stretch", hide_index=True)
    download_button(coverage, "cobertura_tara.csv")


renderers = {
    "Resumen": render_summary,
    "Tara sitios": render_tara_sites,
    "Tara clima": render_tara_climate,
    "Tara suelos": render_tara_soils,
    "INIA": render_inia,
    "Metodologia": render_methodology,
}
renderers[page]()
