"""Exporta el informe semanal a PowerPoint y a Excel."""
from __future__ import annotations

import io
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.util import Emu, Inches, Pt  # noqa: E402

AZUL = RGBColor(0x1F, 0x3A, 0x8A)
GRIS = RGBColor(0x55, 0x5F, 0x6D)
VERDE, AMBAR, ROJO = RGBColor(0x1E, 0x8E, 0x3E), RGBColor(0xC7, 0x7C, 0x02), RGBColor(0xC6, 0x28, 0x28)
CONTEOS = {"PARADAS", "MINERAL", "DESMONTE", "OTROS", "TOTAL VIAJES", "D", "N", "TOTAL", "DIAS"}
C_MIN, C_DES, C_OTR = "#2a78d6", "#0b2a6f", "#e8743b"


def _fmt(v, col: str) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, (int, float)):
        if "%" in col:
            return f"{v:,.1f} %"
        if col in CONTEOS:
            return f"{int(round(v)):,}"
        if len(col) == 5 and col[2] == "/":  # columnas diarias dd/mm
            return f"{v:,.1f}"
        return f"{v:,.2f}"
    return str(v)


def _color_cump(v):
    if v != v:
        return None
    return VERDE if v >= 100 else AMBAR if v >= 90 else ROJO


class Informe:
    def __init__(self, titulo: str, subtitulo: str):
        self.p = Presentation()
        self.p.slide_width, self.p.slide_height = Inches(13.333), Inches(7.5)
        s = self.p.slides.add_slide(self.p.slide_layouts[6])
        self._caja(s, titulo, Inches(0.8), Inches(2.6), Inches(11.7), Inches(1.2), 36, True, AZUL)
        self._caja(s, subtitulo, Inches(0.8), Inches(3.8), Inches(11.7), Inches(1), 18, False, GRIS)

    @staticmethod
    def _caja(s, texto, x, y, w, h, tam, negrita=False, color=GRIS):
        tf = s.shapes.add_textbox(x, y, w, h).text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = texto
        p.font.size, p.font.bold, p.font.color.rgb = Pt(tam), negrita, color

    def diapositiva(self, titulo: str, nota: str | None = None):
        s = self.p.slides.add_slide(self.p.slide_layouts[6])
        self._caja(s, titulo, Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.7), 26, True, AZUL)
        if nota:
            self._caja(s, nota, Inches(0.5), Inches(6.85), Inches(12.3), Inches(0.5), 12)
        return s

    def tabla(self, s, df: pd.DataFrame, x=0.5, y=1.2, w=12.3, alto_fila=0.3, tam=11,
              cump_cols: tuple = ()):
        df = df.reset_index(drop=True)
        filas, cols = len(df) + 1, len(df.columns)
        shp = s.shapes.add_table(filas, cols, Inches(x), Inches(y), Inches(w), Inches(alto_fila * filas))
        t = shp.table
        if cols > 2 and df.columns[0] in ("EQUIPO", "FLOTA", "FECHA", "CARGO"):
            ancho0 = Inches(2.3)
            t.columns[0].width = ancho0
            resto = int((Inches(w) - ancho0) / (cols - 1))
            for j in range(1, cols):
                t.columns[j].width = resto
        for j, c in enumerate(df.columns):
            cel = t.cell(0, j)
            cel.text = str(c)
            cel.fill.solid()
            cel.fill.fore_color.rgb = AZUL
            par = cel.text_frame.paragraphs[0]
            par.font.size, par.font.bold, par.font.color.rgb = Pt(tam), True, RGBColor(255, 255, 255)
        for i, fila in df.iterrows():
            negrita = str(fila.iloc[0]).startswith("TOTAL") or str(fila.iloc[min(1, cols - 1)]).startswith("TOTAL")
            for j, c in enumerate(df.columns):
                cel = t.cell(i + 1, j)
                cel.text = _fmt(fila[c], str(c))
                par = cel.text_frame.paragraphs[0]
                par.font.size, par.font.bold = Pt(tam), negrita
                if c in cump_cols:
                    col = _color_cump(fila[c])
                    if col is not None:
                        par.font.color.rgb = col
                        par.font.bold = True
        return t

    def imagen(self, s, fig, x=0.5, y=1.2, w=12.3):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        s.shapes.add_picture(buf, Inches(x), Inches(y), width=Inches(w))

    def guardar(self) -> bytes:
        buf = io.BytesIO()
        self.p.save(buf)
        return buf.getvalue()


# ------------------------------------------------------------------ gráficos
def grafico_viajes(viajes_dia: pd.DataFrame):
    v = viajes_dia.groupby("FECHA")[["MINERAL", "DESMONTE", "OTROS"]].sum()
    fig, ax = plt.subplots(figsize=(12, 4.2))
    x = [d.strftime("%d %b") for d in v.index]
    base = 0
    for col, color in [("MINERAL", C_MIN), ("DESMONTE", C_DES), ("OTROS", C_OTR)]:
        ax.bar(x, v[col], bottom=base, color=color, label=col.title(), width=0.6,
               edgecolor="white", linewidth=1.5)
        for xi, b, h in zip(x, base + 0 * v[col], v[col]):
            if h >= 4:
                ax.text(xi, b + h / 2, int(h), ha="center", va="center", color="white", fontsize=10, weight="bold")
        base = base + v[col]
    for xi, tot in zip(x, base):
        ax.text(xi, tot + 1, int(tot), ha="center", va="bottom", fontsize=11, weight="bold", color="#333")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_yticks([])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
    return fig


def grafico_produccion(prod: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 3.6))
    x = [d.strftime("%d %b") for d in prod["FECHA"]]
    ax.bar(x, prod["TON MINERAL REAL"], color=C_MIN, width=0.6, label="Real (t)")
    ax.plot(x, prod["PLAN DIA TMS"], color="#333", marker="o", linewidth=2, label="Plan diario (t)")
    for xi, r in zip(x, prod["TON MINERAL REAL"]):
        ax.text(xi, r + 15, f"{r:,.0f}", ha="center", va="bottom", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    return fig


def grafico_pareto(p: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 4.4))
    etiquetas = [f"{c} {a[:22].title()}" for c, a in zip(p["COD"], p["ACTIVIDAD"])]
    ax.bar(etiquetas, p["HORAS"], color=C_MIN)
    ax.set_ylabel("Horas")
    ax2 = ax.twinx()
    ax2.plot(etiquetas, p["% ACUMULADO"], color=C_OTR, marker="o")
    ax2.set_ylim(0, 105)
    ax2.axhline(80, color="#999", linestyle="--", linewidth=1)
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    plt.setp(ax.get_xticklabels(), ha="right")
    ax.spines[["top"]].set_visible(False)
    ax2.spines[["top"]].set_visible(False)
    return fig


# ------------------------------------------------------------------ informe
def generar_ppt(r: dict, inicio: date, fin: date, semana: str) -> bytes:
    inf = Informe(f"Informe semanal de productividad – {semana}",
                  f"Del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}")

    prod = r["produccion"].copy()
    if not prod.empty:
        s = inf.diapositiva("Cumplimiento de producción de mineral – Volquetes",
                            "Ton mineral = viajes de mineral × 22.8 t")
        inf.tabla(s, prod[["FECHA", "TON MINERAL REAL", "TON MINERAL ACUMULADO MES", "PLAN DIA TMS",
                           "CUMP DIA %", "AVANCE MES %", "CUMP MES AL DIA %"]],
                  y=1.1, alto_fila=0.32, cump_cols=("CUMP DIA %", "CUMP MES AL DIA %"))
        inf.imagen(s, grafico_produccion(prod), y=4.0, w=10)

    s = inf.diapositiva("Viajes por día (mineral, desmonte y otros) – Volquetes",
                        f"De los viajes 'otros', {r['relleno']} son de relleno cementado.")
    inf.imagen(s, grafico_viajes(r["viajes"]), y=1.1)

    s = inf.diapositiva("Viajes y toneladas por equipo")
    inf.tabla(s, r["viajes_equipo"], alto_fila=0.32)

    for flota in ["Volquetes", "Semitráiler", "Minicargadores"]:
        d = r["disponibilidad"]
        d = d[d["FLOTA"] == flota]
        if d.empty:
            continue
        s = inf.diapositiva(f"{flota}: DM, utilización, MTBF y MTTR",
                            "DM = (TP−TM)/TP · Util = TF/TP · MTBF = TF/paradas · MTTR = MnP/paradas")
        cols = ["EQUIPO", "DM %", "PLAN DM %", "CUMP DM %", "UTIL %", "PLAN UTIL %", "CUMP UTIL %",
                "MTBF h", "MTTR h", "PARADAS"]
        if d["PLAN MTBF h"].notna().any():
            cols += ["PLAN MTBF h", "PLAN MTTR h"]
        inf.tabla(s, d[cols], alto_fila=0.34, tam=11, cump_cols=("CUMP DM %", "CUMP UTIL %"))

    for kpi in ["DM %", "UTIL %"]:
        s = inf.diapositiva(f"{'Disponibilidad' if kpi == 'DM %' else 'Utilización'} diaria (%)")
        t = r[f"diaria_{kpi}"].reset_index().drop(columns="FLOTA")
        inf.tabla(s, t, alto_fila=0.3, tam=10)

    s = inf.diapositiva("Productividad mineral (t/h) – Volquetes",
                        "PROVISIONAL: t mineral / horas de funcionamiento (TF). Falta confirmar la fórmula.")
    inf.tabla(s, r["tph_vol"].reset_index(), alto_fila=0.32, tam=11)
    s = inf.diapositiva("Productividad mineral (t/h) – Semitráiler",
                        "PROVISIONAL: t mineral / horas de funcionamiento (TF). Falta confirmar la fórmula.")
    inf.tabla(s, r["tph_semi"].reset_index(), alto_fila=0.32, tam=11)

    s = inf.diapositiva("Pareto de demoras – Volquetes (horas fuera de funcionamiento)")
    inf.imagen(s, grafico_pareto(r["pareto"]), y=1.1)

    s = inf.diapositiva("Mantenimiento correctivo de la semana (horas)")
    inf.tabla(s, r["fallas"].head(15), alto_fila=0.3, tam=11)

    s = inf.diapositiva("Headcount de la semana (personas que reportaron)")
    inf.tabla(s, r["headcount"], w=7, alto_fila=0.36, tam=12)

    prog = r.get("programa") or {}
    for hoja, titulo in [("MANT_EQUIPOS", "Programa de mantenimiento – semana siguiente"),
                         ("MANT_VIAS", "Programa de mantenimiento de vías – semana siguiente"),
                         ("HEADCOUNT", "Headcount programado – semana siguiente")]:
        if hoja in prog and not prog[hoja].empty:
            s = inf.diapositiva(titulo)
            inf.tabla(s, prog[hoja].head(18).fillna(""), alto_fila=0.3, tam=11)

    s = inf.diapositiva("Gracias")
    return inf.guardar()


def generar_excel(r: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        r["produccion"].to_excel(xw, sheet_name="PRODUCCION", index=False)
        r["viajes"].to_excel(xw, sheet_name="VIAJES_DIA_GUARDIA", index=False)
        r["viajes_equipo"].to_excel(xw, sheet_name="VIAJES_EQUIPO", index=False)
        r["disponibilidad"].to_excel(xw, sheet_name="DM_UTIL_MTBF_MTTR", index=False)
        r["diaria_DM %"].to_excel(xw, sheet_name="DM_DIARIA")
        r["diaria_UTIL %"].to_excel(xw, sheet_name="UTIL_DIARIA")
        r["tph_vol"].to_excel(xw, sheet_name="TPH_VOLQUETES")
        r["tph_semi"].to_excel(xw, sheet_name="TPH_SEMI")
        r["pareto"].to_excel(xw, sheet_name="PARETO_DEMORAS", index=False)
        r["fallas"].to_excel(xw, sheet_name="MANT_CORRECTIVO", index=False)
        r["headcount"].to_excel(xw, sheet_name="HEADCOUNT", index=False)
        for k, v in (r.get("programa") or {}).items():
            v.to_excel(xw, sheet_name=f"PROG_{k}"[:31], index=False)
    return buf.getvalue()
