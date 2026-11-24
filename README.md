# Seguimiento Minero – KPIs semanales de flota

Herramienta para pasar del **Excel de Cognos** al **informe del sábado** sin Power BI:
cargas el Excel y te da producción contra el plan, viajes, DM, utilización, MTBF, MTTR,
t/h, el Pareto de demoras, el headcount y el programa de la semana siguiente. Al final
descargas un **PowerPoint** y un **Excel**.

## Instalación (una sola vez)

1. Instala **Python 3.11 o superior** desde <https://www.python.org/downloads/>.
   En el instalador, marca **"Add Python to PATH"**.
2. Descarga esta carpeta: en GitHub, **Code → Download ZIP**, y descomprímela.
3. Haz doble clic en **`INICIAR.bat`**. La primera vez instala los componentes (tarda unos
   minutos). Luego se abre la herramienta en el navegador.

## Uso semanal

1. Doble clic en **`INICIAR.bat`**.
2. En la barra lateral, sube:
   - el **Excel de Cognos** (el export completo, tal como sale);
   - el **PLAN_PRODUCCION.xlsx** (hojas `PLAN_MENSUAL` y `PLAN_SEMANAL`);
   - *(opcional)* el **programa de la semana siguiente**: descarga la plantilla en
     "Parámetros y plantillas", llénala en Excel y súbela.
3. Elige el **rango de la semana**. Por defecto toma los últimos 7 días que tienen datos.
4. Pestaña **⬇️ Descargar** → **Generar informe PowerPoint**.

> La primera lectura de un Excel de 280 MB tarda unos 40 segundos. Después se guarda una
> copia rápida en `datos/cache/` y volver a abrir el mismo archivo es instantáneo.

## Configuración: `config/parametros.xlsx`

| Hoja | Qué contiene |
|---|---|
| `GENERAL` | Contrata (`LUCARBAL`), toneladas por viaje (22.8 / 19.8 / 19.8 / semi 34) y códigos de viaje (150 / 151 / 152) |
| `OBJETIVOS` | DM %, utilización %, MTBF y MTTR objetivo por flota |
| `EXCLUIR_EQUIPOS` | Equipos que no entran en los KPIs (fuera de flota, de baja, etc.) |

## Fórmulas

| KPI | Fórmula | Columnas de Cognos |
|---|---|---|
| DM % | (TP − TM) / TP | `MTG_NIVEL1_TP`, `MTG_NIVEL3_TM` |
| Utilización % | TF / TP | `MTG_NIVEL4_TF` |
| MTBF (h) | TF / N.º paradas | `NUM_PARADAS` |
| MTTR (h) | MnP / N.º paradas | `MTG_NIVEL4_MnP` |
| Ton volquete | viajes mineral × 22.8 + desmonte × 19.8 + otros × 19.8 | viajes = eventos con código 150 / 151 / 152 |
| Ton semitráiler | viajes × 34 | |
| Cumplimiento del mes al día | acumulado / (plan del mes ÷ días del mes × día) | |
| t/h | **provisional**: t mineral / TF | pendiente de la fórmula del supervisor |
| Headcount | DNI distintos que reportaron | `DNI` |

Validado contra `KPI_SEMANA_47.pptx`: producción, viajes, DM y utilización coinciden.

## Privacidad

Los Excel de la operación (con nombres y DNI) **no se suben al repositorio**: `datos/` y
los archivos `COGNOS*`, `PLAN_PRODUCCION*` y `KPI_*` están en `.gitignore`.

## Estructura

```
app.py                    interfaz (Streamlit)
seguimiento/carga.py      lectura rápida del Excel de Cognos, el plan y las plantillas
seguimiento/kpis.py       cálculo de todos los KPIs
seguimiento/reporte.py    exportación a PowerPoint y Excel
seguimiento/plantillas.py genera las plantillas de config/
config/                   parametros.xlsx y plantilla del programa semanal
INICIAR.bat               lanzador para Windows
```
