"""Lectura rápida del Excel de Cognos, del plan de producción y de las plantillas."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from python_calamine import CalamineWorkbook

CACHE = Path(__file__).resolve().parent.parent / "datos" / "cache"

# Columnas del export de Cognos que usa la herramienta (el resto se ignora).
COLUMNAS = {
    "FECHA": "FECHA", "GUARDIA": "GUARDIA", "EQUIPO": "EQUIPO", "GRUPO": "GRUPO",
    "EJECUTOR": "EJECUTOR", "OPERADOR": "OPERADOR", "DNI": "DNI",
    "NUMREPORTE": "NUMREPORTE", "CODACTIVIDAD": "COD", "ACTIVIDAD": "ACTIVIDAD",
    "HORAS": "HORAS", "T_MAT": "T_MAT", "LABORDESTINO": "DESTINO", "Detalle": "DETALLE",
    "Tiempo": "TIEMPO", "NUM_PARADAS": "PARADAS",
    "MTG_NIVEL1_TP": "TP", "MTG_NIVEL3_TM": "TM", "MTG_NIVEL4_TF": "TF",
    "MTG_NIVEL4_MnP": "MnP", "MTG_NIVEL4_RF": "RF",
}
NUMERICAS = ["HORAS", "PARADAS", "TP", "TM", "TF", "MnP", "RF"]
TEXTO = ["GUARDIA", "EQUIPO", "GRUPO", "EJECUTOR", "OPERADOR", "DNI", "NUMREPORTE",
         "COD", "ACTIVIDAD", "T_MAT", "DESTINO", "DETALLE", "TIEMPO"]


def _huella(datos: bytes) -> str:
    h = hashlib.sha1()
    h.update(str(len(datos)).encode())
    h.update(datos[:1_000_000])
    h.update(datos[-1_000_000:])
    return h.hexdigest()[:16]


def _limpiar_texto(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    # Cognos guarda códigos numéricos como '150 ' o '150.0'
    return s.str.replace(r"\.0$", "", regex=True).fillna("")


def leer_cognos(datos: bytes, contrata: str | None = None) -> pd.DataFrame:
    """Lee la hoja de datos del export de Cognos (por defecto 'Consulta1').

    Guarda una copia en Parquet: volver a cargar el mismo archivo es instantáneo.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"cognos_{_huella(datos)}.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
    else:
        import io

        wb = CalamineWorkbook.from_filelike(io.BytesIO(datos))
        hoja = "Consulta1" if "Consulta1" in wb.sheet_names else None
        filas = None
        for nombre in ([hoja] if hoja else wb.sheet_names):
            it = wb.get_sheet_by_name(nombre).iter_rows()
            cab = [str(c).strip() for c in next(it)]
            if "EQUIPO" in cab and "MTG_NIVEL1_TP" in cab:
                idx = {c: cab.index(c) for c in COLUMNAS if c in cab}
                faltan = set(COLUMNAS) - set(idx)
                if faltan:
                    raise ValueError(f"Al Excel le faltan columnas: {', '.join(sorted(faltan))}")
                filas = [[r[i] for i in idx.values()] for r in it]
                break
        if filas is None:
            raise ValueError("No encontré la hoja de datos de Cognos (debe tener EQUIPO y MTG_NIVEL1_TP).")
        df = pd.DataFrame(filas, columns=[COLUMNAS[c] for c in idx])
        for c in TEXTO:
            df[c] = _limpiar_texto(df[c])
        for c in NUMERICAS:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce").dt.normalize()
        df = df[df["FECHA"].notna() & (df["EQUIPO"] != "")]
        df.to_parquet(cache, index=False)
    if contrata:
        df = df[df["EJECUTOR"].str.upper() == contrata.upper()]
    return df.reset_index(drop=True)


def leer_plan(fuente) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PLAN_PRODUCCION.xlsx -> (plan_mensual, plan_diario)."""
    mensual = pd.read_excel(fuente, sheet_name="PLAN_MENSUAL")
    diario = pd.read_excel(fuente, sheet_name="PLAN_SEMANAL")
    mensual.columns = [str(c).strip().upper() for c in mensual.columns]
    diario.columns = [str(c).strip().upper() for c in diario.columns]
    diario["FECHA"] = pd.to_datetime(diario["FECHA"]).dt.normalize()
    mensual = mensual.dropna(subset=["PLAN_MINERAL_TMS"])
    return mensual, diario


def leer_parametros(fuente) -> dict:
    """config/parametros.xlsx -> dict con general, objetivos y equipos excluidos."""
    hojas = pd.read_excel(fuente, sheet_name=None)
    gen = hojas["GENERAL"].dropna(subset=["PARAMETRO"])
    general = {str(k).strip(): v for k, v in zip(gen["PARAMETRO"], gen["VALOR"])}
    objetivos = hojas["OBJETIVOS"].dropna(subset=["FLOTA"]).set_index("FLOTA")
    excluir = hojas["EXCLUIR_EQUIPOS"].dropna(subset=["EQUIPO"])
    return {
        "general": general,
        "objetivos": objetivos,
        "excluir": [str(e).strip() for e in excluir["EQUIPO"]],
    }


def leer_programa(fuente) -> dict[str, pd.DataFrame]:
    """Plantilla del programa de la semana siguiente (mantenimiento, vías, headcount)."""
    hojas = pd.read_excel(fuente, sheet_name=None)
    return {k: v.dropna(how="all") for k, v in hojas.items()}
