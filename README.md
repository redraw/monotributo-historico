# Datos Históricos del Monotributo AFIP

Datos históricos del monotributo argentino desde 2010 hasta la actualidad, extraídos automáticamente desde el sitio oficial de AFIP.

## Archivos

- **`monotributo_historico.json`** - Datos históricos normalizados (408 registros)
- **`scrape_historico.py`** - Script para extraer datos históricos desde PDFs
- **`scrape_actual.py`** - Script para extraer datos actuales desde HTML
- **`pdfs/`** - PDFs originales descargados de AFIP (20 archivos)

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
./scrape_historico.py
# o
uv run scrape_historico.py
```

### Agregar datos actuales (HTML)
```bash
./scrape_actual.py
# o
uv run scrape_actual.py
```

Las dependencias se definen en el docstring de cada script y se instalan automáticamente por uv.

## Actualización Automática

Este repositorio incluye un GitHub Action que ejecuta `scrape_actual.py` automáticamente:
- **Frecuencia:** Todos los lunes a las 10:00 UTC
- **Acción:** Extrae los datos actuales del monotributo y actualiza el JSON si hay cambios
- **También puedes:** Ejecutar el workflow manualmente desde la pestaña "Actions" en GitHub

## Fuentes

- Histórico: https://www.afip.gob.ar/monotributo/montos-y-categorias-anteriores.asp
- Actual: https://www.afip.gob.ar/monotributo/categorias.asp
