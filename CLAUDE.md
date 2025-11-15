# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project scrapes, analyzes, and visualizes historical data of Argentina's "monotributo" (simplified tax regime) from AFIP's official website. It generates interactive charts showing the evolution of different tax categories over time, with inflation-adjusted comparisons.

## Commands

All scripts use [uv inline script dependencies](https://docs.astral.sh/uv/guides/scripts/), so dependencies are automatically installed.

### Data Collection

```bash
# Scrape historical data from AFIP PDFs (2010-2025)
./scripts/scrape_historico.py
# or
uv run scripts/scrape_historico.py

# Add current data from AFIP HTML table
./scripts/scrape_actual.py
# or
uv run scripts/scrape_actual.py
```

### Data Analysis & Visualization

```bash
# Basic analysis (servicios, total component, latest IPC base)
./scripts/analizar_monotributo.py

# Analyze specific type
./scripts/analizar_monotributo.py --tipo {servicios|ventas}

# Analyze specific component
./scripts/analizar_monotributo.py --componente {total|impuesto_integrado|aporte_sipa|aporte_obra_social|ingresos_brutos}

# Use custom IPC base period
./scripts/analizar_monotributo.py --ipc-base YYYY-MM

# Combined options
./scripts/analizar_monotributo.py --tipo servicios --componente aporte_sipa --ipc-base 2023-06
```

The analysis script can be run with your pre-approved permissions:
```bash
# These commands are pre-approved in your config
./analizar_monotributo.py
./scripts/analizar_monotributo.py
```

## Architecture

### Data Sources

1. **Historical PDFs**: `scrape_historico.py` downloads PDFs from AFIP and extracts tabular data using `pdfplumber`
2. **Current HTML**: `scrape_actual.py` scrapes the live AFIP table using `BeautifulSoup`
3. **Inflation Data**: Analysis script fetches IPC (consumer price index) from [Argentina Datos API](https://api.argentinadatos.com/v1/finanzas/indices/inflacion)

### Data Flow

```
AFIP PDFs → scrape_historico.py → data/monotributo_historico.json
AFIP HTML → scrape_actual.py    ↗

data/monotributo_historico.json → analizar_monotributo.py → graficos/*.html + index.html
Argentina Datos IPC API         ↗
```

### Data Structure

The main data file `data/monotributo_historico.json` contains:
- `metadata`: source info, total records, unique categories, date range
- `data`: array of records with fields:
  - `start_date`, `end_date`: period of validity (YYYY-MM-DD)
  - `categoria`: category letter (A-K)
  - `tipo_actividad`: "servicios" or "ventas"
  - `ingresos_brutos`: gross income limit (int)
  - `superficie_afectada`: max surface area (string with m²)
  - `energia_electrica`: energy consumption (string with Kw)
  - `alquileres_devengados`: rental income limit (int)
  - `precio_unitario_maximo`: max unit price (int)
  - `impuesto_integrado`: integrated tax (int)
  - `aporte_sipa`: pension contribution (int)
  - `aporte_obra_social`: health insurance contribution (int)
  - `total`: total monthly payment (int)

### Script Architecture

**scrape_historico.py**:
- Downloads 20 historical PDFs from AFIP (2010-2025)
- Uses `pdfplumber` to extract tables from PDFs
- Normalizes currency strings to integers
- Creates two records per category (servicios/ventas) when they differ
- Outputs to `data/monotributo_historico.json`

**scrape_actual.py**:
- Fetches current categories from AFIP's live HTML page
- Parses the 11-column table structure
- Merges new data into historical JSON (replaces if period exists)
- Maintains chronological order and updates metadata

**analizar_monotributo.py**:
- Loads historical data and IPC inflation index from Argentina Datos API
- Filters by activity type and component (via CLI args)
- **Constructs accumulated price index** from monthly variations:
  - API returns monthly inflation rates (e.g., 2.3%)
  - Converts to multiplicative factors: `factor = 1 + (rate% / 100)`
  - Builds cumulative index: `index[n] = index[n-1] × factor[n]`
  - Normalizes to base period = 100
- Calculates inflation-adjusted "real" values: `monto_real = monto_nominal × (100 / index_periodo)`
- Generates 4 interactive Plotly charts per run:
  1. Nominal evolution (line chart)
  2. Real evolution (inflation-adjusted line chart)
  3. Increment comparison (grouped bar chart)
  4. Heatmap (category × period)
- Generates `index.html` from `index.jinja` template with links to all charts
- Prints statistical analysis (increments, CAGR, value loss/gain)

### GitHub Actions Automation

**Workflow**: `.github/workflows/update-monotributo.yml`
- Runs weekly on Mondays at 10:00 UTC
- Can be triggered manually via GitHub Actions UI
- Process:
  1. Runs `scrape_actual.py` to fetch latest AFIP data
  2. Checks if `data/monotributo_historico.json` changed
  3. If changed: regenerates ALL charts (10 combinations: 2 tipos × 5 componentes)
  4. Commits and pushes updated data + charts

### Output Structure

Generated files go to:
- `graficos/`: all interactive HTML charts
  - Naming: `monotributo_{tipo}_{componente}_{grafico}.html`
  - Example: `monotributo_servicios_total_nominal.html`
- `index.html`: main index with cards linking to all charts
- `index.jinja`: Jinja2 template for index generation

## Important Notes

- All scripts use SSL verification disabled (`verify=False`) for AFIP requests due to certificate issues
- The `normalize_number()` function is duplicated across scrapers - maintains consistency in parsing currency strings
- Categories A-K are hardcoded in specific order matching AFIP's table structure
- When ventas total equals servicios total, only one record is created
- **IPC adjustment methodology:**
  - The Argentina Datos API returns **monthly inflation rates** (not cumulative index)
  - Script builds cumulative price index using: `index[n] = index[n-1] × (1 + rate[n]/100)`
  - Real values calculated as: `monto_real = monto_nominal × (index_base / index_periodo)`
  - All values expressed in constant pesos of the base period (default: first period in dataset)
