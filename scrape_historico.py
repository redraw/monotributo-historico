#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
#   "pdfplumber",
#   "urllib3",
# ]
# ///
"""
Script para descargar y extraer datos históricos del monotributo de AFIP
Descarga PDFs desde la web de AFIP y extrae los datos en formato JSON normalizado
"""

import os
import json
import requests
import pdfplumber
from typing import List, Dict, Any, Optional
from pathlib import Path
import urllib3
import re

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URLs de los PDFs
PDF_DATA = [
    {"period": "2025-02_2025-07", "url": "documentos/categorias/monotributo-categorias-febrero-julio-2025.pdf"},
    {"period": "2024-08_2025-01", "url": "documentos/categorias/monotributo-categorias-agosto-2024-enero-2025-1.pdf"},
    {"period": "2024-01_2024-07", "url": "documentos/categorias/monotributo-categorias-enero-julio-2024.pdf"},
    {"period": "2023-07_2023-12", "url": "documentos/categorias/monotributo-categorias-julio-diciembre-2023.pdf"},
    {"period": "2023-01_2023-06", "url": "documentos/categorias/monotributo-categorias-enero-junio-2023.pdf"},
    {"period": "2022-07_2022-12", "url": "documentos/categorias/monotributo-categorias-julio-diciembre-2022.pdf"},
    {"period": "2022-01_2022-06", "url": "documentos/categorias/monotributo-categorias-enero-junio-2022.pdf"},
    {"period": "2021-07_2021-12", "url": "documentos/categorias/monotributo-categorias-julio-diciembre-2021.pdf"},
    {"period": "2021-01_2021-06", "url": "documentos/categorias/monotributo-categorias-enero-junio-2021.pdf"},
    {"period": "2020-01_2020-12", "url": "documentos/categorias/monotributo-categorias-enero-diciembre-2020.pdf"},
    {"period": "2019-01_2019-12", "url": "documentos/categorias/monotributo-categorias-enero-diciembre-2019.pdf"},
    {"period": "2018-01_2018-12", "url": "documentos/categorias/monotributo-categorias-enero-diciembre-2018.pdf"},
    {"period": "2017-01_2017-12", "url": "documentos/categorias/monotributo-categorias-enero-diciembre-2017.pdf"},
    {"period": "2016-06_2016-12", "url": "documentos/categorias/monotributo-categorias-junio-diciembre-2016.pdf"},
    {"period": "2015-07_2016-05", "url": "documentos/categorias/monotributo-categorias-julio-2015-mayo-2016.pdf"},
    {"period": "2014-09_2015-06", "url": "documentos/categorias/monotributo-categorias-septiembre-2014-junio-2015.pdf"},
    {"period": "2013-11_2014-08", "url": "documentos/categorias/monotributo-categorias-noviembre-2013-agosto-2014.pdf"},
    {"period": "2013-09_2013-10", "url": "documentos/categorias/monotributo-categorias-septiembre-octubre-2013.pdf"},
    {"period": "2012-07_2013-08", "url": "documentos/categorias/monotributo-categorias-julio-2012-agosto-2013.pdf"},
    {"period": "2010-01_2012-06", "url": "documentos/categorias/monotributo-categorias-enero-2010-junio-2012.pdf"},
]

BASE_URL = "https://www.afip.gob.ar/monotributo/"
OUTPUT_DIR = Path("pdfs")
OUTPUT_JSON = "monotributo_historico.json"


def parse_period(period: str) -> tuple[str, str]:
    """Convierte el período en fechas de inicio y fin"""
    parts = period.split("_")
    start = parts[0]
    end = parts[1]

    start_date = f"{start}-01"

    year, month = end.split("-")
    if month in ["01", "03", "05", "07", "08", "10", "12"]:
        last_day = "31"
    elif month in ["04", "06", "09", "11"]:
        last_day = "30"
    else:
        year_int = int(year)
        if year_int % 4 == 0 and (year_int % 100 != 0 or year_int % 400 == 0):
            last_day = "29"
        else:
            last_day = "28"

    end_date = f"{end}-{last_day}"
    return start_date, end_date


def normalize_number(value: str) -> Optional[int]:
    """Normaliza un string de precio a int"""
    if not value or value.strip() in ["", "-", "None", "null"]:
        return None

    cleaned = value.replace("$", "").replace(" ", "").replace(".", "")

    if "," in cleaned:
        cleaned = cleaned.split(",")[0]

    if not cleaned or not cleaned.lstrip("-").isdigit():
        return None

    return int(cleaned)


def download_pdf(url: str, output_path: Path) -> bool:
    """Descarga un PDF desde la URL especificada"""
    try:
        print(f"Descargando: {url}")
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"  ✓ Guardado en: {output_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error descargando {url}: {e}")
        return False


def parse_table(table: List[List[str]], period: str) -> List[Dict[str, Any]]:
    """
    Parsea una tabla del PDF y retorna lista de registros normalizados
    """
    if not table or len(table) < 3:
        return []

    records = []
    start_date, end_date = parse_period(period)

    # Buscar la primera fila de datos (la que empieza con una categoría)
    # Las categorías son letras simples: A, B, C, D, E, F, G, H, I, J, K
    data_start = None
    for i, row in enumerate(table):
        if row and row[0] and str(row[0]).strip() in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            data_start = i
            break

    if data_start is None:
        return []

    # Procesar cada fila de datos
    for row in table[data_start:]:
        if not row or not row[0] or not str(row[0]).strip():
            continue

        categoria = str(row[0]).strip()
        if categoria not in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            continue

        # Buscar columnas de forma más flexible
        # Convertir toda la fila a lista de valores normalizados
        row_values = [str(cell).strip() if cell else "" for cell in row]

        # Intentar detectar las columnas importantes
        # Ingresos brutos: segunda columna normalmente
        ingresos_brutos = normalize_number(row_values[1] if len(row_values) > 1 else "")

        # Buscar columnas con "m2" para superficie
        superficie = None
        energia = None
        for val in row_values[2:8]:
            if 'm2' in val or 'M2' in val:
                superficie = val
            elif 'Kw' in val or 'KW' in val or 'kw' in val:
                energia = val

        # Buscar alquileres y precio unitario (generalmente después de superficie/energía)
        alquileres = None
        precio_unitario = None
        for idx in range(4, min(len(row_values), 8)):
            val = normalize_number(row_values[idx])
            if val and alquileres is None:
                alquileres = val
            elif val and precio_unitario is None:
                precio_unitario = val
                break

        # Buscar las dos últimas columnas numéricas (suelen ser los totales)
        # Iterar desde el final
        numeric_cols = []
        for idx in range(len(row_values) - 1, -1, -1):
            val = normalize_number(row_values[idx])
            if val is not None:
                numeric_cols.append((idx, val))
            if len(numeric_cols) >= 6:  # Tomar las últimas 6 columnas numéricas
                break

        numeric_cols.reverse()

        # Asignar valores (las últimas columnas suelen ser: impuesto_serv, impuesto_venta, sipa, obra_social, total_serv, total_venta)
        impuesto_servicios = None
        impuesto_ventas = None
        aporte_sipa = None
        aporte_obra_social = None
        total_servicios = None
        total_ventas = None

        if len(numeric_cols) >= 6:
            impuesto_servicios = numeric_cols[0][1]
            impuesto_ventas = numeric_cols[1][1]
            aporte_sipa = numeric_cols[2][1]
            aporte_obra_social = numeric_cols[3][1]
            total_servicios = numeric_cols[4][1]
            total_ventas = numeric_cols[5][1]
        elif len(numeric_cols) >= 4:
            # Formato simplificado (sin split servicios/ventas)
            aporte_sipa = numeric_cols[0][1]
            aporte_obra_social = numeric_cols[1][1]
            total_servicios = numeric_cols[2][1]
            total_ventas = numeric_cols[3][1]

        # Crear dos registros: uno para servicios, otro para ventas
        # Solo si tienen valores diferentes

        # Registro para SERVICIOS
        if total_servicios is not None:
            records.append({
                "start_date": start_date,
                "end_date": end_date,
                "categoria": categoria,
                "tipo_actividad": "servicios",
                "ingresos_brutos": ingresos_brutos,
                "superficie_afectada": superficie,
                "energia_electrica": energia,
                "alquileres_devengados": alquileres,
                "precio_unitario_maximo": precio_unitario,
                "impuesto_integrado": impuesto_servicios,
                "aporte_sipa": aporte_sipa,
                "aporte_obra_social": aporte_obra_social,
                "total": total_servicios,
            })

        # Registro para VENTAS (solo si es diferente de servicios)
        if total_ventas is not None and total_ventas != total_servicios:
            records.append({
                "start_date": start_date,
                "end_date": end_date,
                "categoria": categoria,
                "tipo_actividad": "ventas",
                "ingresos_brutos": ingresos_brutos,
                "superficie_afectada": superficie,
                "energia_electrica": energia,
                "alquileres_devengados": alquileres,
                "precio_unitario_maximo": precio_unitario,
                "impuesto_integrado": impuesto_ventas,
                "aporte_sipa": aporte_sipa,
                "aporte_obra_social": aporte_obra_social,
                "total": total_ventas,
            })

    return records


def main():
    """Función principal"""
    print("=" * 80)
    print("SCRAPER DE MONOTRIBUTO AFIP")
    print("=" * 80)
    print()

    OUTPUT_DIR.mkdir(exist_ok=True)
    all_data = []

    for pdf_info in PDF_DATA:
        period = pdf_info["period"]
        pdf_url = BASE_URL + pdf_info["url"]
        pdf_filename = pdf_info["url"].split("/")[-1]
        pdf_path = OUTPUT_DIR / pdf_filename

        print(f"\n{'='*80}")
        print(f"Procesando período: {period}")
        print(f"{'='*80}")

        if not pdf_path.exists():
            if not download_pdf(pdf_url, pdf_path):
                continue
        else:
            print(f"PDF ya existe: {pdf_path}")

        # Extraer y parsear tablas
        try:
            print(f"Extrayendo tablas de: {pdf_path.name}")
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables, 1):
                        records = parse_table(table, period)
                        if records:
                            all_data.extend(records)
                            print(f"  Página {page_num}, Tabla {table_num}: {len(records)} registro(s)")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"GUARDANDO DATOS")
    print(f"{'='*80}")
    print(f"Total de registros: {len(all_data)}")

    # Calcular estadísticas
    categorias_unicas = set(r["categoria"] for r in all_data)
    periodos_unicos = set(r["start_date"] for r in all_data)

    output_data = {
        "metadata": {
            "source": "AFIP - Monotributo",
            "url": "https://www.afip.gob.ar/monotributo/montos-y-categorias-anteriores.asp",
            "total_records": len(all_data),
            "total_periods": len(PDF_DATA),
            "unique_categories": sorted(list(categorias_unicas)),
            "date_range": {
                "from": min(r["start_date"] for r in all_data),
                "to": max(r["end_date"] for r in all_data),
            }
        },
        "data": all_data
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Datos guardados en: {OUTPUT_JSON}")
    print(f"  - Categorías únicas: {len(categorias_unicas)}")
    print(f"  - Rango de fechas: {output_data['metadata']['date_range']['from']} → {output_data['metadata']['date_range']['to']}")

    print(f"\n{'='*80}")
    print("PROCESO COMPLETADO")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
