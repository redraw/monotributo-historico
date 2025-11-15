#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
#   "beautifulsoup4",
#   "urllib3",
# ]
# ///
"""
Script para extraer la tabla actual del monotributo desde la web de AFIP
y agregarla al archivo histórico
"""

import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import urllib3

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL_ACTUAL = "https://www.afip.gob.ar/monotributo/categorias.asp"


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


def extract_current_data() -> tuple[List[Dict[str, Any]], str, str]:
    """
    Extrae los datos de la tabla actual de monotributo
    Retorna: (lista de registros, fecha_inicio, fecha_fin)
    """
    print("Descargando página actual de monotributo...")
    response = requests.get(URL_ACTUAL, verify=False, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Buscar información de vigencia en el texto
    # Buscar algo como "Vigente desde..." o fecha en el título
    vigencia_text = soup.get_text()

    # Buscar fecha de vigencia (puede estar en diferentes formatos)
    # Por defecto, asumimos que es la fecha actual si no encontramos
    start_date = "2025-08-01"  # Basado en la información del WebFetch
    end_date = "2099-12-31"  # Vigente hasta nuevo aviso

    # Buscar la tabla principal
    table = soup.find('table')
    if not table:
        raise Exception("No se encontró la tabla en la página")

    print("Tabla encontrada, extrayendo datos...")

    records = []
    rows = table.find_all('tr')

    # Buscar la fila de encabezado
    header_row_idx = None
    data_start_idx = None

    for i, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        cell_texts = [c.get_text(strip=True) for c in cells]

        # El encabezado tiene "Categ."
        if any('Categ' in text for text in cell_texts):
            header_row_idx = i
            # Los datos empiezan después del sub-encabezado (fila siguiente)
            data_start_idx = i + 2  # Saltear encabezado y sub-encabezado
            break

    if data_start_idx is None:
        raise Exception("No se encontró el encabezado de la tabla")

    print(f"Datos comienzan en fila {data_start_idx}")

    # Procesar filas de datos
    # Cada fila corresponde a una categoría en orden: A, B, C, D, E, F, G, H, I, J, K
    categorias = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    categoria_idx = 0

    for idx, row in enumerate(rows[data_start_idx:]):
        cells = row.find_all('td')
        if len(cells) != 11:
            continue

        if categoria_idx >= len(categorias):
            break  # Ya procesamos todas las categorías

        categoria = categorias[categoria_idx]
        categoria_idx += 1

        # Extraer el texto de cada celda
        cell_values = [cell.get_text(strip=True) for cell in cells]

        # Las 11 celdas son:
        # [0]: Ingresos brutos
        # [1]: Superficie
        # [2]: Energía
        # [3]: Alquileres
        # [4]: Precio unitario
        # [5]: Impuesto integrado (servicios)
        # [6]: Impuesto integrado (ventas)
        # [7]: Aportes SIPA
        # [8]: Aportes obra social
        # [9]: Total (servicios)
        # [10]: Total (ventas)

        ingresos_brutos = normalize_number(cell_values[0])
        superficie = cell_values[1]
        energia = cell_values[2]
        alquileres = normalize_number(cell_values[3])
        precio_unitario = normalize_number(cell_values[4])
        impuesto_servicios = normalize_number(cell_values[5])
        impuesto_ventas = normalize_number(cell_values[6])
        aporte_sipa = normalize_number(cell_values[7])
        aporte_obra_social = normalize_number(cell_values[8])
        total_servicios = normalize_number(cell_values[9])
        total_ventas = normalize_number(cell_values[10])

        # Crear registro para SERVICIOS
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

        # Crear registro para VENTAS (si es diferente)
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

    print(f"✓ Extraídos {len(records)} registros de la página actual")
    return records, start_date, end_date


def update_historical_data(new_records: List[Dict[str, Any]]):
    """Actualiza el archivo histórico con los nuevos datos"""

    # Leer archivo histórico
    with open('monotributo_historico.json', 'r', encoding='utf-8') as f:
        historical_data = json.load(f)

    # Verificar si ya existen datos para este período
    existing_periods = set()
    for record in historical_data['data']:
        key = f"{record['start_date']}_{record['end_date']}"
        existing_periods.add(key)

    # Verificar el período nuevo
    new_period_key = f"{new_records[0]['start_date']}_{new_records[0]['end_date']}"

    if new_period_key in existing_periods:
        print(f"\n⚠ El período {new_records[0]['start_date']} - {new_records[0]['end_date']} ya existe en el histórico")
        print("  Se reemplazarán los datos existentes...")

        # Remover registros del período existente
        historical_data['data'] = [
            r for r in historical_data['data']
            if not (r['start_date'] == new_records[0]['start_date'] and
                   r['end_date'] == new_records[0]['end_date'])
        ]

    # Agregar nuevos registros
    historical_data['data'].extend(new_records)

    # Ordenar por fecha de inicio (más antiguos primero)
    historical_data['data'].sort(key=lambda x: x['start_date'])

    # Actualizar metadata
    historical_data['metadata']['total_records'] = len(historical_data['data'])
    historical_data['metadata']['date_range']['to'] = max(r['end_date'] for r in historical_data['data'])

    # Guardar archivo actualizado
    with open('monotributo_historico.json', 'w', encoding='utf-8') as f:
        json.dump(historical_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Archivo histórico actualizado")
    print(f"  Total de registros: {historical_data['metadata']['total_records']}")
    print(f"  Rango de fechas: {historical_data['metadata']['date_range']['from']} → {historical_data['metadata']['date_range']['to']}")


def main():
    print("=" * 80)
    print("SCRAPER DE MONOTRIBUTO ACTUAL (HTML)")
    print("=" * 80)
    print()

    try:
        # Extraer datos actuales
        new_records, start_date, end_date = extract_current_data()

        if not new_records:
            print("✗ No se encontraron datos en la página")
            return

        print(f"\nPeríodo detectado: {start_date} → {end_date}")
        print(f"Registros extraídos: {len(new_records)}")

        # Actualizar histórico
        update_historical_data(new_records)

        print("\n" + "=" * 80)
        print("PROCESO COMPLETADO")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
