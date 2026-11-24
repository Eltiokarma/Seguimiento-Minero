# Prompt — Seguimiento Minero: KPIs semanales de flota

## Rol y contexto

Actúa como analista de datos de operaciones mineras y desarrollador. Vas a construir una herramienta para un supervisor de flota de una contrata de transporte en una unidad minera subterránea (U.M. Ticlio).

**Quién lo usa y qué necesita.** El supervisor tiene a su cargo tres tipos de equipo:

| Equipo | Trabajo | Capacidad por viaje |
|---|---|---|
| **Volquetes** | Extraen mineral y desmonte desde interior mina hasta superficie | **22.8 t** (mineral) / **19.8 t** (desmonte y otros) |
| **Encapsulados (semitráiler)** | Transportan mineral en superficie | **34 t** ⚠️ *ver nota* |
| **2 minicargadores** | Mantenimiento de vías | — |

> ⚠️ **Por confirmar:** en el audio el supervisor dice que los encapsulados cargan **38 t**; en las notas escritas dice **34 t**. Deja el valor como parámetro editable y usa 34 t hasta que se confirme.

**Cómo llega la data.** Cada equipo reporta sus actividades con **códigos**, por guardia de **12 horas** (día: 07:00–19:00; noche: 19:00–07:00). Ese reporte se carga en una base de datos y se descarga como Excel (~200 MB). Columnas conocidas del modelo actual de Power BI: `CONTRATA`, `EQUIPO`, `GUARDIA`, `SEMANA`, `ACTIVIDAD`, `LABORDESTINO`, `HORAS DEMORA`, fecha, y conteos de `VIAJES MINERAL`, `VIAJES DESMONTE`, `VIAJES OTROS` y `VIAJES REL` (relleno cementado).

**Para qué.** Todos los **sábados** hay reunión de KPIs. El supervisor presenta el avance contra el **plan semanal** y el **plan mensual** (ejemplo: `KPI_SEMANA_47.pptx`).

**Objetivo principal:** *"meter la data y ¡pum! que me bote todos los KPIs"*. Cargar el Excel exportado y obtener el reporte semanal completo, sin trabajo manual.

## Entradas

1. **Excel de la base de datos** (reporte por códigos, por equipo y por guardia).
2. **`PLAN_PRODUCCION.xlsx`**, con dos hojas:
   - `PLAN_MENSUAL`: `AÑO, MES_NUM, MES, PLAN_MINERAL_TMS, PLAN_MINERAL_TMH`
   - `PLAN_SEMANAL`: `Fecha, Día, Semana, TMS, TMH` (plan diario; las semanas van de sábado a viernes con etiqueta `SEM NN`)
3. **Programas de la semana siguiente** (los ingresa el usuario): mantenimiento de equipos, mantenimiento de vías y headcount.
4. **Objetivos**: plan de DM %, plan de utilización %, MTBF objetivo y MTTR objetivo.

## Fórmulas

```
TON TRANSPORTADAS (volquetes) =
      [VIAJES MINERAL]  * 22.8
    + [VIAJES DESMONTE] * 19.8
    + [VIAJES OTROS]    * 19.8

TON SEMITRÁILER = [VIAJES SEMI] * 34          (parámetro; posible 38)
```

Definiciones estándar (deben ajustarse al mapeo de códigos de la base):

- **Disponibilidad mecánica (DM %)** = (Horas programadas − Horas en mantenimiento/reparación) / Horas programadas
- **Utilización (%)** = Horas operativas / Horas disponibles
- **MTBF** = Horas operativas / N.º de fallas (paradas correctivas)
- **MTTR** = Horas de reparación correctiva / N.º de fallas
- **Productividad (t/h)** = Toneladas transportadas / Horas operativas
- **Velocidad promedio (km/h)** = Distancia recorrida / Horas en traslado (si la base tiene distancias por labor/destino; si no, ciclo promedio en min/viaje)
- **Cumplimiento** = Real / Plan, por día, por semana y acumulado del mes

## Entregables (secciones del reporte semanal)

1. **Producción vs. plan**: TMS real vs. plan diario, semanal y mensual (avance % y cumplimiento al día).
2. **Viajes** por guardia y por equipo (mineral, desmonte, otros y relleno cementado).
3. **Productividad t/h** de volquetes y de semitráileres.
4. **Disponibilidad mecánica y utilización**, por equipo y diaria, para volquetes, semis y minis.
   - ➕ **Añadir MTBF y MTTR** por equipo.
   - ➕ **Añadir objetivos** (plan DM %, plan Util %, MTBF y MTTR objetivo) y la variación contra ellos.
5. ➕ **Cálculo de velocidades y ratio de t/h** por equipo y por guardia.
6. **Pareto de demoras** (horas por código/actividad) con sus causas, por ejemplo: *"CAJ917: módulo averiado"*.
7. ➕ **Programa de mantenimiento de la semana siguiente** (equipos).
8. ➕ **Programa de mantenimiento de vías de la semana siguiente** (minicargadores).
9. ➕ **Headcount de la semana**.

## Requisitos

- Que sea fácil: un solo paso para cargar el Excel y que todo se recalcule.
- Que aguante archivos de ~200 MB (lectura por columnas o en bloques; no cargar a mano).
- Capacidades, objetivos y mapeo de códigos en una **hoja/archivo de parámetros editable**, nunca fijos en el código.
- Salida lista para la reunión del sábado: dashboard y/o PPT con el mismo orden que `KPI_SEMANA_47.pptx`.
- Si falta un dato (por ejemplo, el catálogo de códigos o las distancias), **pregúntalo**. No lo inventes.

## Primera tarea

1. Leer una muestra del Excel de la base y listar columnas, códigos de actividad y rangos de fechas.
2. Proponer el mapeo **código → categoría** (operativo, demora operativa, mantenimiento preventivo, correctivo, stand-by) para validarlo con el supervisor.
3. Recién después, implementar los cálculos y el reporte.
