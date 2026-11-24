"""Cálculo de KPIs de flota a partir del registro de eventos de Cognos.

Definiciones (confirmadas con el supervisor):
    DM %          = (TP - TM) / TP
    Utilización % = TF / TP
    MTBF          = TF  / NRO PARADAS
    MTTR          = MnP / NRO PARADAS
    Ton volquete  = viajes mineral*22.8 + viajes desmonte*19.8 + viajes otros*19.8
    Ton semi      = viajes * 34
"""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

FLOTAS = {"VOL": "Volquetes", "STR": "Semitráiler", "CAR": "Minicargadores"}
ORDEN_FLOTAS = list(FLOTAS.values())


def _div(a, b):
    """DIVIDE(a, b, 0) de DAX."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(b != 0, a / b, 0.0)
    return r if r.ndim else float(r)


def preparar(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    df = df.copy()
    df["FLOTA"] = df["EQUIPO"].str.extract(r"-(VOL|STR|CAR)-", expand=False).map(FLOTAS)
    df = df[df["FLOTA"].notna() & ~df["EQUIPO"].isin(params["excluir"])]
    g = params["general"]
    cod = {str(int(g["COD_VIAJE_MINERAL"])): "MINERAL",
           str(int(g["COD_VIAJE_DESMONTE"])): "DESMONTE",
           str(int(g["COD_VIAJE_OTROS"])): "OTROS"}
    df["VIAJE"] = df["COD"].map(cod)
    es_semi = df["FLOTA"] == "Semitráiler"
    ton = df["VIAJE"].map({"MINERAL": g["TON_VOLQUETE_MINERAL"],
                           "DESMONTE": g["TON_VOLQUETE_DESMONTE"],
                           "OTROS": g["TON_VOLQUETE_OTROS"]}).astype(float)
    ton[es_semi & df["VIAJE"].notna()] = float(g["TON_SEMITRAILER"])
    df["TON"] = ton.fillna(0.0)
    df["TON_MINERAL"] = np.where(df["VIAJE"] == "MINERAL", df["TON"], 0.0)
    return df


def filtrar(df, inicio, fin):
    return df[(df["FECHA"] >= pd.Timestamp(inicio)) & (df["FECHA"] <= pd.Timestamp(fin))]


# ---------------------------------------------------------------- tiempos
def _tiempos(g: pd.DataFrame) -> pd.DataFrame:
    t = g[["TP", "TM", "TF", "MnP", "PARADAS"]].sum() if isinstance(g, pd.DataFrame) else g
    return t


def _ratios(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["DM %"] = _div(t["TP"] - t["TM"], t["TP"]) * 100
    t["UTIL %"] = _div(t["TF"], t["TP"]) * 100
    t["MTBF h"] = _div(t["TF"], t["PARADAS"])
    t["MTTR h"] = _div(t["MnP"], t["PARADAS"])
    return t


def disponibilidad(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """DM, utilización, MTBF y MTTR por equipo, con objetivos y cumplimiento."""
    cols = ["TP", "TM", "TF", "MnP", "PARADAS"]
    eq = df.groupby(["FLOTA", "EQUIPO"])[cols].sum().reset_index()
    fl = df.groupby("FLOTA")[cols].sum().reset_index()
    fl["EQUIPO"] = "TOTAL " + fl["FLOTA"].str.upper()
    t = _ratios(pd.concat([eq, fl], ignore_index=True))
    obj = params["objetivos"]
    for k, col in [("DM %", "DM_%"), ("UTIL %", "UTIL_%"), ("MTBF h", "MTBF_h"), ("MTTR h", "MTTR_h")]:
        plan = t["FLOTA"].map(obj[col]) if col in obj else np.nan
        t[f"PLAN {k}"] = pd.to_numeric(plan, errors="coerce")
        t[f"VAR {k}"] = t[k] - t[f"PLAN {k}"]
        # En MTTR, menos es mejor: cumplimiento = plan / real
        t[f"CUMP {k}"] = (_div(t[f"PLAN {k}"], t[k]) if k == "MTTR h" else _div(t[k], t[f"PLAN {k}"])) * 100
        t.loc[t[f"PLAN {k}"].isna(), [f"VAR {k}", f"CUMP {k}"]] = np.nan
    t["_o"] = t["FLOTA"].map({f: i for i, f in enumerate(ORDEN_FLOTAS)})
    t["_t"] = t["EQUIPO"].str.startswith("TOTAL")
    t = t.sort_values(["_o", "_t", "DM %"], ascending=[True, True, False]).drop(columns=["_o", "_t"])
    return t.reset_index(drop=True)


def disponibilidad_diaria(df: pd.DataFrame, kpi: str = "DM %") -> pd.DataFrame:
    """Tabla equipo x día de DM % o UTIL %."""
    t = _ratios(df.groupby(["FLOTA", "EQUIPO", "FECHA"])[["TP", "TM", "TF", "MnP", "PARADAS"]].sum())
    tab = t[kpi].unstack("FECHA")
    tab.columns = [c.strftime("%d/%m") for c in tab.columns]
    return tab


# ---------------------------------------------------------------- producción
def viajes(df: pd.DataFrame) -> pd.DataFrame:
    """Viajes por día, guardia y tipo (volquetes)."""
    v = df[(df["FLOTA"] == "Volquetes") & df["VIAJE"].notna()]
    tab = v.pivot_table(index=["FECHA", "GUARDIA"], columns="VIAJE", values="COD",
                        aggfunc="count", fill_value=0)
    for c in ["MINERAL", "DESMONTE", "OTROS"]:
        if c not in tab:
            tab[c] = 0
    tab = tab[["MINERAL", "DESMONTE", "OTROS"]]
    tab["TOTAL"] = tab.sum(axis=1)
    return tab.reset_index()


def viajes_por_equipo(df: pd.DataFrame) -> pd.DataFrame:
    v = df[df["VIAJE"].notna()]
    tab = v.pivot_table(index=["FLOTA", "EQUIPO"], columns="VIAJE", values="TON",
                        aggfunc="count", fill_value=0)
    for c in ["MINERAL", "DESMONTE", "OTROS"]:
        if c not in tab:
            tab[c] = 0
    tab = tab[["MINERAL", "DESMONTE", "OTROS"]]
    tab["TOTAL VIAJES"] = tab.sum(axis=1)
    tab["TON TRANSPORTADAS"] = v.groupby(["FLOTA", "EQUIPO"])["TON"].sum()
    return tab.reset_index()


def relleno(df: pd.DataFrame) -> int:
    """Viajes 'otros' que son relleno cementado (T_MAT = REL)."""
    v = df[(df["FLOTA"] == "Volquetes") & (df["VIAJE"] == "OTROS")]
    return int((v["T_MAT"] == "REL").sum())


def productividad(df: pd.DataFrame, flota: str) -> pd.DataFrame:
    """t/h por equipo y día = toneladas de mineral / horas de funcionamiento (TF).

    PROVISIONAL: falta confirmar la fórmula exacta de TN HR del supervisor.
    """
    d = df[df["FLOTA"] == flota]
    g = d.groupby(["EQUIPO", "FECHA"])[["TON_MINERAL", "TF"]].sum()
    g["TPH"] = _div(g["TON_MINERAL"], g["TF"])
    tab = g["TPH"].unstack("FECHA")
    tab.columns = [c.strftime("%d/%m") for c in tab.columns]
    tot = d.groupby("EQUIPO")[["TON_MINERAL", "TF"]].sum()
    tab["SEMANA"] = _div(tot["TON_MINERAL"], tot["TF"])
    return tab.replace(0, np.nan)


def produccion_vs_plan(df_todo: pd.DataFrame, plan_mes: pd.DataFrame, plan_dia: pd.DataFrame,
                       inicio, fin) -> pd.DataFrame:
    """Tonelaje de mineral (volquetes) por día frente al plan diario y mensual."""
    inicio, fin = pd.Timestamp(inicio), pd.Timestamp(fin)
    vol = df_todo[df_todo["FLOTA"] == "Volquetes"]
    real = vol.groupby("FECHA")["TON_MINERAL"].sum()
    filas = []
    for dia in pd.date_range(inicio, fin):
        mes = plan_mes[(plan_mes["AÑO"] == dia.year) & (plan_mes["MES_NUM"] == dia.month)]
        p_mes = float(mes["PLAN_MINERAL_TMS"].iloc[0]) if len(mes) else np.nan
        dias_mes = calendar.monthrange(dia.year, dia.month)[1]
        acum = real[(real.index >= dia.replace(day=1)) & (real.index <= dia)].sum()
        p_dia = plan_dia.loc[plan_dia["FECHA"] == dia, "TMS"]
        p_dia = float(p_dia.iloc[0]) if len(p_dia) else np.nan
        r = float(real.get(dia, 0.0))
        filas.append({
            "FECHA": dia, "TON MINERAL REAL": r, "TON MINERAL ACUMULADO MES": acum,
            "PLAN DIA TMS": p_dia, "CUMP DIA %": _div(r, p_dia) * 100 if p_dia == p_dia else np.nan,
            "PLAN MES TMS": p_mes,
            "AVANCE MES %": _div(acum, p_mes) * 100 if p_mes == p_mes else np.nan,
            "CUMP MES AL DIA %": _div(acum, p_mes / dias_mes * dia.day) * 100 if p_mes == p_mes else np.nan,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- demoras
def pareto_demoras(df: pd.DataFrame, flota: str | None = None, top: int = 15) -> pd.DataFrame:
    """Horas fuera de funcionamiento (TP - TF) por actividad, ordenadas con % acumulado."""
    d = df if flota is None else df[df["FLOTA"] == flota]
    d = d[d["TF"] == 0]
    p = d.groupby(["COD", "ACTIVIDAD", "TIEMPO"])["HORAS"].sum().sort_values(ascending=False).reset_index()
    p["% ACUMULADO"] = p["HORAS"].cumsum() / p["HORAS"].sum() * 100
    return p.head(top)


def fallas(df: pd.DataFrame) -> pd.DataFrame:
    """Eventos de mantenimiento correctivo (MnP > 0) con su detalle."""
    d = df[df["MnP"] > 0]
    g = (d.groupby(["FLOTA", "EQUIPO", "ACTIVIDAD"])
         .agg(HORAS=("MnP", "sum"), DIAS=("FECHA", "nunique"),
              DETALLE=("DETALLE", lambda s: " | ".join(sorted({x for x in s if x})[:3])))
         .reset_index().sort_values("HORAS", ascending=False))
    if not g["DETALLE"].str.len().any():
        g = g.drop(columns="DETALLE")
    return g.reset_index(drop=True)


# ---------------------------------------------------------------- personal
def headcount(df: pd.DataFrame) -> pd.DataFrame:
    """Personas distintas (DNI) que reportaron, por flota y guardia."""
    d = df[df["DNI"] != ""]
    t = d.pivot_table(index="FLOTA", columns="GUARDIA", values="DNI", aggfunc="nunique", fill_value=0)
    t["TOTAL"] = d.groupby("FLOTA")["DNI"].nunique()
    t.loc["TOTAL"] = list(t.drop(columns="TOTAL").sum()) + [d["DNI"].nunique()]
    return t.reset_index()


# ---------------------------------------------------------------- todo junto
def calcular(df: pd.DataFrame, params: dict, plan_mes, plan_dia, inicio, fin, programa=None) -> dict:
    """Calcula todas las tablas del informe semanal para el rango [inicio, fin]."""
    w = filtrar(df, inicio, fin)
    r = {
        "viajes": viajes(w),
        "viajes_equipo": viajes_por_equipo(w),
        "relleno": relleno(w),
        "disponibilidad": disponibilidad(w, params),
        "diaria_DM %": disponibilidad_diaria(w, "DM %"),
        "diaria_UTIL %": disponibilidad_diaria(w, "UTIL %"),
        "tph_vol": productividad(w, "Volquetes"),
        "tph_semi": productividad(w, "Semitráiler"),
        "pareto": pareto_demoras(w, "Volquetes"),
        "fallas": fallas(w),
        "headcount": headcount(w),
        "programa": programa,
    }
    r["produccion"] = (produccion_vs_plan(df, plan_mes, plan_dia, inicio, fin)
                       if plan_mes is not None else pd.DataFrame())
    return r
