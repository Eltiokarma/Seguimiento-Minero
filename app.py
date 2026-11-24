"""Seguimiento Minero – KPIs semanales de flota.

Ejecutar:  streamlit run app.py   (o doble clic en INICIAR.bat)
"""
from datetime import timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from seguimiento import carga, kpis, reporte
from seguimiento.plantillas import crear as crear_plantillas

RAIZ = Path(__file__).resolve().parent
CONFIG = RAIZ / "config"
crear_plantillas()

st.set_page_config(page_title="Seguimiento Minero – KPIs", page_icon="⛏️", layout="wide")


@st.cache_data(show_spinner="Leyendo el Excel de Cognos… (la primera vez tarda ~40 s; luego es instantáneo)")
def _cognos(datos: bytes, contrata: str):
    return carga.leer_cognos(datos, contrata)


@st.cache_data
def _plan(datos: bytes):
    import io
    return carga.leer_plan(io.BytesIO(datos))


def _params(subido):
    import io
    if subido is not None:
        return carga.leer_parametros(io.BytesIO(subido.getvalue()))
    return carga.leer_parametros(CONFIG / "parametros.xlsx")


def _fmt_tabla(df: pd.DataFrame, cump=()):
    fmt = {c: "{:,.1f} %" for c in df.columns if "%" in str(c)}
    fmt.update({c: "{:,.2f}" for c in df.columns
                if any(k in str(c) for k in ("MTBF", "MTTR", "HORAS", "TON", "TP", "TM", "TF", "MnP"))})
    fmt.update({c: "{:,.0f}" for c in df.columns if str(c) in ("PARADAS", "DIAS")})
    fmt.update({c: (lambda d: d.strftime("%d/%m/%Y")) for c in df.columns
                if pd.api.types.is_datetime64_any_dtype(df[c])})
    sty = df.style.format(fmt, na_rep="—")

    def color(v):
        if pd.isna(v):
            return ""
        return "color:#1e8e3e;font-weight:600" if v >= 100 else (
            "color:#c77c02;font-weight:600" if v >= 90 else "color:#c62828;font-weight:600")
    for c in cump:
        if c in df:
            sty = sty.map(color, subset=[c])
    return sty


# ------------------------------------------------------------------ barra lateral
st.sidebar.title("⛏️ Seguimiento Minero")
st.sidebar.caption("1) Sube los archivos  2) Elige la semana  3) Descarga el informe")

f_cognos = st.sidebar.file_uploader("Excel de Cognos (export completo)", type=["xlsx", "xlsb"])
f_plan = st.sidebar.file_uploader("Plan de producción (PLAN_PRODUCCION.xlsx)", type=["xlsx"])
f_prog = st.sidebar.file_uploader("Programa de la semana siguiente (opcional)", type=["xlsx"])
with st.sidebar.expander("Parámetros y plantillas"):
    f_param = st.file_uploader("Parámetros (si no, usa config/parametros.xlsx)", type=["xlsx"])
    st.download_button("⬇️ Plantilla de parámetros", (CONFIG / "parametros.xlsx").read_bytes(),
                       "parametros.xlsx")
    st.download_button("⬇️ Plantilla programa semana siguiente",
                       (CONFIG / "programa_semana_PLANTILLA.xlsx").read_bytes(), "programa_semana.xlsx")

params = _params(f_param)

if f_cognos is None:
    st.title("KPIs semanales de flota")
    st.info("👈 Sube el **Excel de Cognos** en la barra lateral para empezar. "
            "Opcional: el **plan de producción** y el **programa de la semana siguiente**.")
    st.markdown(
        "- **DM %** = (TP − TM) / TP · **Utilización %** = TF / TP\n"
        "- **MTBF** = TF / N.º paradas · **MTTR** = MnP / N.º paradas\n"
        "- **Ton volquete** = viajes mineral × 22.8 + desmonte × 19.8 + otros × 19.8 · **Ton semi** = viajes × 34\n\n"
        "Capacidades, objetivos y equipos excluidos se cambian en `config/parametros.xlsx`.")
    st.stop()

contrata = str(params["general"].get("CONTRATA", "LUCARBAL"))
base = kpis.preparar(_cognos(f_cognos.getvalue(), contrata), params)
if base.empty:
    st.error(f"No hay datos de la contrata {contrata} en el archivo.")
    st.stop()
plan_mes, plan_dia = _plan(f_plan.getvalue()) if f_plan else (None, None)
programa = carga.leer_programa(f_prog) if f_prog else None

ultimo = base["FECHA"].max().date()
primero = base["FECHA"].min().date()
rango = st.sidebar.date_input("Semana a reportar", (ultimo - timedelta(days=6), ultimo),
                              min_value=primero, max_value=ultimo, format="DD/MM/YYYY")
if not isinstance(rango, tuple) or len(rango) != 2:
    st.stop()
inicio, fin = rango
semana = st.sidebar.text_input("Nombre de la semana (portada)", f"Semana {fin.isocalendar()[1]}")

r = kpis.calcular(base, params, plan_mes, plan_dia, inicio, fin, programa)
disp = r["disponibilidad"]

# ------------------------------------------------------------------ resumen
st.title(f"KPIs de flota · {semana}")
st.caption(f"{contrata} · del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y} · datos hasta el {ultimo:%d/%m/%Y}")
if params["excluir"]:
    st.caption("Equipos excluidos (config/parametros.xlsx): " + ", ".join(params["excluir"]))

tot = disp[disp["EQUIPO"].str.startswith("TOTAL")].set_index("FLOTA")
c = st.columns(6)
if not r["produccion"].empty:
    p = r["produccion"]
    c[0].metric("Ton mineral (semana)", f"{p['TON MINERAL REAL'].sum():,.0f} t",
                f"{p['TON MINERAL REAL'].sum() / p['PLAN DIA TMS'].sum() * 100:.1f} % del plan")
    c[1].metric("Avance del mes", f"{p['AVANCE MES %'].iloc[-1]:.1f} %",
                f"cump. al día {p['CUMP MES AL DIA %'].iloc[-1]:.1f} %")
else:
    c[0].metric("Viajes de mineral", int(r["viajes"]["MINERAL"].sum()))
    c[1].metric("Viajes totales", int(r["viajes"]["TOTAL"].sum()))
for i, fl in enumerate(["Volquetes", "Semitráiler", "Minicargadores"]):
    if fl in tot.index:
        t = tot.loc[fl]
        c[2 + i].metric(f"DM {fl}", f"{t['DM %']:.1f} %", f"Util {t['UTIL %']:.1f} %", delta_color="off")
c[5].metric("Headcount", int(r["headcount"].iloc[-1]["TOTAL"]))

tabs = st.tabs(["Producción", "Viajes", "DM · Util · MTBF · MTTR", "Diario", "t/h",
                "Demoras y fallas", "Headcount y programa", "⬇️ Descargar"])

with tabs[0]:
    if r["produccion"].empty:
        st.warning("Sube el **plan de producción** para ver el cumplimiento contra el plan.")
    else:
        p = r["produccion"]
        g = p.melt("FECHA", ["TON MINERAL REAL", "PLAN DIA TMS"], "serie", "t")
        barras = alt.Chart(p).mark_bar(color="#2a78d6", size=40).encode(
            x=alt.X("yearmonthdate(FECHA):O", title=None), y=alt.Y("TON MINERAL REAL:Q", title="t"),
            tooltip=["FECHA:T", alt.Tooltip("TON MINERAL REAL:Q", format=",.1f")])
        linea = alt.Chart(p).mark_line(color="#333", point=True).encode(
            x="yearmonthdate(FECHA):O", y="PLAN DIA TMS:Q",
            tooltip=["FECHA:T", alt.Tooltip("PLAN DIA TMS:Q", format=",.1f")])
        st.altair_chart(barras + linea, use_container_width=True)
        st.dataframe(_fmt_tabla(p, ("CUMP DIA %", "CUMP MES AL DIA %")), hide_index=True,
                     use_container_width=True)

with tabs[1]:
    v = r["viajes"]
    largo = v.groupby("FECHA")[["MINERAL", "DESMONTE", "OTROS"]].sum().reset_index().melt(
        "FECHA", var_name="TIPO", value_name="VIAJES")
    st.altair_chart(alt.Chart(largo).mark_bar().encode(
        x=alt.X("yearmonthdate(FECHA):O", title=None), y="VIAJES:Q",
        color=alt.Color("TIPO:N", scale=alt.Scale(domain=["MINERAL", "DESMONTE", "OTROS"],
                                                  range=["#2a78d6", "#0b2a6f", "#e8743b"])),
        tooltip=["FECHA:T", "TIPO", "VIAJES"]), use_container_width=True)
    st.caption(f"Viajes 'otros' de relleno cementado: **{r['relleno']}**")
    a, b = st.columns(2)
    a.subheader("Por día y guardia")
    a.dataframe(v, hide_index=True, use_container_width=True)
    b.subheader("Por equipo")
    b.dataframe(_fmt_tabla(r["viajes_equipo"]), hide_index=True, use_container_width=True)

with tabs[2]:
    for fl in ["Volquetes", "Semitráiler", "Minicargadores"]:
        d = disp[disp["FLOTA"] == fl].drop(columns="FLOTA")
        if d.empty:
            continue
        st.subheader(fl)
        d = d.dropna(axis=1, how="all")
        st.dataframe(_fmt_tabla(d, [c for c in d.columns if c.startswith("CUMP")]),
                     hide_index=True, use_container_width=True)
    st.caption("Objetivos editables en config/parametros.xlsx → hoja OBJETIVOS. "
               "En MTTR el cumplimiento es plan/real (menos horas es mejor).")

with tabs[3]:
    kpi = st.radio("Indicador", ["DM %", "UTIL %"], horizontal=True)
    st.dataframe(r[f"diaria_{kpi}"].style.format("{:.1f}", na_rep="—")
                 .background_gradient(cmap="RdYlGn", vmin=0, vmax=100, axis=None),
                 use_container_width=True)

with tabs[4]:
    st.warning("Fórmula **provisional**: t de mineral / horas de funcionamiento (TF). "
               "Pendiente de reemplazar por la fórmula TN HR del supervisor.")
    st.subheader("Volquetes")
    st.dataframe(r["tph_vol"].style.format("{:.2f}", na_rep="—"), use_container_width=True)
    st.subheader("Semitráiler")
    st.dataframe(r["tph_semi"].style.format("{:.2f}", na_rep="—"), use_container_width=True)

with tabs[5]:
    fl = st.selectbox("Flota", ["Volquetes", "Semitráiler", "Minicargadores"])
    par = kpis.pareto_demoras(kpis.filtrar(base, inicio, fin), fl)
    par["ETIQUETA"] = par["COD"] + " " + par["ACTIVIDAD"].str.title()
    orden = list(par["ETIQUETA"])
    b = alt.Chart(par).mark_bar(color="#2a78d6").encode(
        x=alt.X("ETIQUETA:N", sort=orden, title=None, axis=alt.Axis(labelAngle=-40, labelLimit=180)),
        y=alt.Y("HORAS:Q"), tooltip=["ETIQUETA", alt.Tooltip("HORAS:Q", format=".1f")])
    l = alt.Chart(par).mark_line(color="#e8743b", point=True).encode(
        x=alt.X("ETIQUETA:N", sort=orden), y=alt.Y("% ACUMULADO:Q", scale=alt.Scale(domain=[0, 100])))
    st.altair_chart(alt.layer(b, l).resolve_scale(y="independent"), use_container_width=True)
    st.dataframe(_fmt_tabla(par.drop(columns="ETIQUETA")), hide_index=True, use_container_width=True)
    st.subheader("Mantenimiento correctivo de la semana")
    st.dataframe(_fmt_tabla(r["fallas"]), hide_index=True, use_container_width=True)

with tabs[6]:
    st.subheader("Headcount real (personas distintas que reportaron)")
    st.dataframe(r["headcount"], hide_index=True)
    if programa:
        for hoja, titulo in [("MANT_EQUIPOS", "Programa de mantenimiento – semana siguiente"),
                             ("MANT_VIAS", "Programa de mantenimiento de vías – semana siguiente"),
                             ("HEADCOUNT", "Headcount programado – semana siguiente")]:
            if hoja in programa:
                st.subheader(titulo)
                st.dataframe(programa[hoja], hide_index=True, use_container_width=True)
    else:
        st.info("Descarga la **plantilla del programa** (barra lateral → Parámetros y plantillas), "
                "llénala en Excel y súbela para incluir el mantenimiento, las vías y el headcount de la "
                "semana siguiente en el informe.")

with tabs[7]:
    st.write("Descarga el informe listo para la reunión del sábado.")
    if st.button("Generar informe PowerPoint", type="primary"):
        with st.spinner("Armando el PPT…"):
            st.session_state["ppt"] = reporte.generar_ppt(r, inicio, fin, semana)
    if "ppt" in st.session_state:
        st.download_button("⬇️ Descargar PPT", st.session_state["ppt"],
                           f"KPI_{semana.replace(' ', '_').upper()}.pptx")
    st.download_button("⬇️ Descargar tablas en Excel", reporte.generar_excel(r),
                       f"KPI_{semana.replace(' ', '_').upper()}.xlsx")
