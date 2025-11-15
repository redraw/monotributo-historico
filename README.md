# Datos Históricos del Monotributo AFIP

Datos históricos del monotributo argentino desde 2010 hasta la actualidad, extraídos automáticamente desde el sitio oficial de AFIP.

## Estructura de Datos

Cada registro incluye:

- `start_date`, `end_date` - Período de vigencia
- `categoria` - Categoría (A-K)
- `tipo_actividad` - "servicios" o "ventas"
- `ingresos_brutos` - Tope de ingresos (int)
- `superficie_afectada` - Superficie máxima (string)
- `energia_electrica` - Energía consumida (string)
- `alquileres_devengados` - Alquileres (int)
- `precio_unitario_maximo` - Precio unitario (int)
- `impuesto_integrado` - Impuesto mensual (int)
- `aporte_sipa` - Aporte jubilatorio (int)
- `aporte_obra_social` - Aporte obra social (int)
- `total` - Total mensual (int)

## Uso de los Scripts

Los scripts usan [uv inline script dependencies](https://docs.astral.sh/uv/guides/scripts/), por lo que no necesitas instalar dependencias manualmente.

### Actualizar datos históricos (PDFs)
```bash
./scripts/scrape_historico.py
# o
uv run scripts/scrape_historico.py
```

### Agregar datos actuales (HTML)
```bash
./scripts/scrape_actual.py
# o
uv run scripts/scrape_actual.py
```

Las dependencias se definen en el docstring de cada script y se instalan automáticamente por uv.

### Analizar y visualizar datos

El script `analizar_monotributo.py` genera gráficos interactivos con análisis de la evolución del monotributo:

```bash
# Análisis básico (servicios, total, IPC más reciente)
./scripts/analizar_monotributo.py

# Analizar ventas
./scripts/analizar_monotributo.py --tipo ventas

# Analizar solo el impuesto integrado
./scripts/analizar_monotributo.py --componente impuesto_integrado

# Usar un período base específico para el IPC
./scripts/analizar_monotributo.py --ipc-base 2020-01

# Combinación de opciones
./scripts/analizar_monotributo.py --tipo servicios --componente aporte_sipa --ipc-base 2023-06
```

**Parámetros disponibles:**
- `--tipo {servicios,ventas}` - Tipo de actividad a analizar (default: servicios)
- `--componente {total,impuesto_integrado,aporte_sipa,aporte_obra_social}` - Componente del monotributo a analizar (default: total)
- `--ipc-base YYYY-MM` - Período base para el ajuste por inflación (default: primer período del dataset)

**Gráficos generados:**
- **Evolución nominal** - Valores históricos sin ajustar
- **Evolución real** - Valores ajustados por inflación (IPC)
- **Incremento porcentual** - Comparación nominal vs real
- **Mapa de calor** - Visualización por categoría y período
- **index.html** - Página índice con enlaces a todos los gráficos

Todos los gráficos son interactivos (zoom, hover, activar/desactivar series).

## Actualización Automática

Este repositorio incluye un GitHub Action que se ejecuta automáticamente:
- **Frecuencia:** Todos los lunes a las 10:00 UTC
- **Proceso:**
  1. Ejecuta `scripts/scrape_actual.py` para extraer datos actuales de AFIP
  2. Detecta si hubo cambios en `data/monotributo_historico.json`
  3. Si hay cambios, regenera todos los gráficos (32 archivos HTML)
  4. Hace commit y push de los datos y gráficos actualizados
- **Ejecución manual:** Puedes ejecutar el workflow manualmente desde la pestaña "Actions" en GitHub

## Fuentes

- **Monotributo histórico:** https://www.afip.gob.ar/monotributo/montos-y-categorias-anteriores.asp
- **Monotributo actual:** https://www.afip.gob.ar/monotributo/categorias.asp
- **Datos de inflación (IPC):** https://api.argentinadatos.com/v1/finanzas/indices/inflacion

## Análisis Disponibles

El script de análisis genera visualizaciones que permiten entender:

- **Evolución temporal:** ¿Cómo ha cambiado cada categoría a lo largo de los años?
- **Impacto de la inflación:** ¿El monotributo creció más o menos que la inflación?
- **Comparación de componentes:** ¿Qué parte del monotributo creció más: impuesto, aportes jubilatorios u obra social?
- **Diferencias entre actividades:** ¿Cómo difieren los aumentos entre servicios y ventas?
- **CAGR (Tasa de crecimiento anual compuesta):** ¿Cuál es el crecimiento promedio anual de cada categoría?
