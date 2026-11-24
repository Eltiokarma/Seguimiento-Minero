"""Genera las plantillas Excel editables: parámetros y programa de la semana siguiente.

Uso:  python -m seguimiento.plantillas
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

CONFIG = Path(__file__).resolve().parent.parent / "config"
AZUL = PatternFill("solid", fgColor="1F3A8A")
BLANCO = Font(color="FFFFFF", bold=True)


def _hoja(wb, titulo, cabecera, filas, anchos, nota=None):
    ws = wb.create_sheet(titulo)
    ws.append(cabecera)
    for c in ws[1]:
        c.fill, c.font = AZUL, BLANCO
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for f in filas:
        ws.append(f)
    for i, w in enumerate(anchos):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "A2"
    if nota:
        col = chr(65 + len(cabecera) + 1)
        ws[f"{col}1"] = nota
        ws[f"{col}1"].font = Font(italic=True, color="666666")
    return ws


def parametros(ruta: Path):
    wb = Workbook()
    wb.remove(wb.active)
    _hoja(wb, "GENERAL", ["PARAMETRO", "VALOR", "DESCRIPCION"], [
        ["CONTRATA", "LUCARBAL", "Valor de la columna EJECUTOR a analizar"],
        ["TON_VOLQUETE_MINERAL", 22.8, "Toneladas por viaje de mineral (volquete)"],
        ["TON_VOLQUETE_DESMONTE", 19.8, "Toneladas por viaje de desmonte (volquete)"],
        ["TON_VOLQUETE_OTROS", 19.8, "Toneladas por viaje de otros (volquete)"],
        ["TON_SEMITRAILER", 34, "Toneladas por viaje de semitráiler"],
        ["COD_VIAJE_MINERAL", 150, "Código de actividad que cuenta un viaje de mineral"],
        ["COD_VIAJE_DESMONTE", 151, "Código de actividad que cuenta un viaje de desmonte"],
        ["COD_VIAJE_OTROS", 152, "Código de actividad que cuenta un viaje de otros"],
    ], [26, 14, 55])
    _hoja(wb, "OBJETIVOS", ["FLOTA", "DM_%", "UTIL_%", "MTBF_h", "MTTR_h"], [
        ["Volquetes", 85, 50, None, None],
        ["Semitráiler", 85, 50, None, None],
        ["Minicargadores", 85, 50, None, None],
    ], [18, 10, 10, 10, 10], nota="Deja vacío el objetivo que no aplique. MTBF/MTTR en horas.")
    _hoja(wb, "EXCLUIR_EQUIPOS", ["EQUIPO", "MOTIVO"], [
        ["LUC-VOL-BSB806", "No figura en el reporte semanal (por confirmar)"],
        ["LUC-VOL-BWF793", "No figura en el reporte semanal (por confirmar)"],
    ], [20, 50], nota="Equipos que no deben entrar en los KPIs (fuera de flota, de baja, etc.)")
    wb.save(ruta)


def programa(ruta: Path):
    wb = Workbook()
    wb.remove(wb.active)
    ws = _hoja(wb, "MANT_EQUIPOS",
               ["FECHA", "EQUIPO", "TIPO", "DESCRIPCION", "HORAS_EST", "RESPONSABLE"],
               [["2026-11-21", "LUC-VOL-BRK919", "PM", "Mantenimiento preventivo 250 h", 8, "Taller"]],
               [12, 18, 22, 45, 11, 18])
    dv = DataValidation(type="list", formula1='"PM,Correctivo programado,Inspección,Predictivo,Otro"')
    ws.add_data_validation(dv)
    dv.add("C2:C200")
    ws = _hoja(wb, "MANT_VIAS",
               ["FECHA", "GUARDIA", "EQUIPO", "TRAMO / LABOR", "ACTIVIDAD", "OBSERVACION"],
               [["2026-11-21", "D", "LUC-CAR-0001", "Rampa 640", "Perfilado y lastrado", ""]],
               [12, 9, 16, 24, 30, 30])
    dv = DataValidation(type="list", formula1='"D,N"')
    ws.add_data_validation(dv)
    dv.add("B2:B200")
    _hoja(wb, "HEADCOUNT", ["CARGO", "GUARDIA_D", "GUARDIA_N", "OBSERVACION"], [
        ["Operador de volquete", None, None, ""],
        ["Operador de semitráiler", None, None, ""],
        ["Operador de minicargador", None, None, ""],
        ["Mecánico", None, None, ""],
        ["Supervisor", None, None, ""],
    ], [28, 12, 12, 35])
    wb.save(ruta)


def crear(forzar: bool = False):
    CONFIG.mkdir(exist_ok=True)
    for nombre, fn in [("parametros.xlsx", parametros), ("programa_semana_PLANTILLA.xlsx", programa)]:
        ruta = CONFIG / nombre
        if forzar or not ruta.exists():
            fn(ruta)
            print("creado", ruta)


if __name__ == "__main__":
    crear(forzar=True)
