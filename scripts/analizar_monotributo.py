#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "pandas",
#   "plotly",
#   "jinja2",
# ]
# ///
"""
Script para analizar la evolución histórica del monotributo por categoría
Genera gráficos interactivos usando pandas y plotly
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import argparse

# Configurar argumentos de línea de comandos
parser = argparse.ArgumentParser(
    description='Analiza la evolución del monotributo por categoría con ajuste por inflación'
)
parser.add_argument(
    '--tipo',
    type=str,
    choices=['servicios', 'ventas'],
    default='servicios',
    help='Tipo de actividad a analizar (servicios o ventas)'
)
parser.add_argument(
    '--ipc-base',
    type=str,
    default=None,
    help='Período base para el IPC en formato YYYY-MM (ej: 2025-10). Si no se especifica, usa el último disponible'
)
parser.add_argument(
    '--componente',
    type=str,
    choices=['total', 'impuesto_integrado', 'aporte_sipa', 'aporte_obra_social'],
    default='total',
    help='Componente a analizar: total (suma de todos), impuesto_integrado, aporte_sipa, o aporte_obra_social'
)

args = parser.parse_args()

# Cargar los datos
with open('data/monotributo_historico.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Convertir a DataFrame
df = pd.DataFrame(data['data'])

# Convertir fechas a datetime
df['start_date'] = pd.to_datetime(df['start_date'])
df['end_date'] = pd.to_datetime(df['end_date'])

# Agregar el año del período (usando la fecha de inicio)
df['year'] = df['start_date'].dt.year
df['period'] = df['start_date'].dt.strftime('%Y-%m')

# Crear carpeta para gráficos si no existe
import os
graficos_dir = 'graficos'
os.makedirs(graficos_dir, exist_ok=True)

# Determinar qué monto analizar según el componente seleccionado
if args.componente == 'total':
    df['monto_analizado'] = df.apply(
        lambda row: row['total'] if pd.notna(row['total'])
        else sum([x for x in [row.get('impuesto_integrado'), row.get('aporte_sipa'), row.get('aporte_obra_social')] if pd.notna(x)]),
        axis=1
    )
    componente_label = 'Total'
else:
    df['monto_analizado'] = df[args.componente].fillna(0)
    componente_label = args.componente.replace('_', ' ').title()

# Filtrar por tipo de actividad
df_actividad = df[df['tipo_actividad'] == args.tipo].copy()

# Cargar datos de inflación desde Argentina Datos
print('Cargando datos de inflación desde API...')
df_ipc = pd.read_json('https://api.argentinadatos.com/v1/finanzas/indices/inflacion')

# Convertir fecha a datetime
df_ipc['fecha'] = pd.to_datetime(df_ipc['fecha'])
df_ipc['year_month'] = df_ipc['fecha'].dt.strftime('%Y-%m')

# Ordenar por fecha
df_ipc = df_ipc.sort_values('fecha')

# Determinar el período base para el IPC
if args.ipc_base:
    # Validar que el período base existe en los datos
    if args.ipc_base not in df_ipc['year_month'].values:
        print(f"Error: El período base '{args.ipc_base}' no está disponible en los datos de IPC")
        print(f"Períodos disponibles: {df_ipc['year_month'].min()} a {df_ipc['year_month'].max()}")
        exit(1)

    # Usar el período especificado
    valor_base = df_ipc[df_ipc['year_month'] == args.ipc_base]['valor'].iloc[0]
    fecha_base = df_ipc[df_ipc['year_month'] == args.ipc_base]['fecha'].iloc[0]
else:
    # Usar el primer valor disponible en el dataset del monotributo como base
    primer_periodo = df_actividad['period'].min()
    if primer_periodo in df_ipc['year_month'].values:
        valor_base = df_ipc[df_ipc['year_month'] == primer_periodo]['valor'].iloc[0]
        fecha_base = df_ipc[df_ipc['year_month'] == primer_periodo]['fecha'].iloc[0]
    else:
        # Si no existe, usar el primer valor disponible de IPC
        valor_base = df_ipc['valor'].iloc[0]
        fecha_base = df_ipc['fecha'].min()

# Crear índice acumulado: dividir el valor base por cada valor
# Esto nos da cuánto valía $1 del período base en términos de cada período pasado
df_ipc['indice_acumulado'] = valor_base / df_ipc['valor']

# Crear diccionario para lookup rápido
ipc_dict = dict(zip(df_ipc['year_month'], df_ipc['indice_acumulado']))

# Ajustar montos por inflación
df_actividad['monto_real'] = df_actividad.apply(
    lambda row: row['monto_analizado'] * ipc_dict.get(row['period'], 1),
    axis=1
)

print('=' * 80)
print('ANÁLISIS DE EVOLUCIÓN DEL MONOTRIBUTO POR CATEGORÍA')
print('=' * 80)
print(f'\nComponente: {componente_label}')
print(f'Tipo de actividad: {args.tipo}')
print(f'Categorías disponibles: {", ".join(sorted(df["categoria"].unique()))}')
print(f'Períodos analizados: {df["year"].min()} - {df["year"].max()}')
print(f'Total de registros: {len(df_actividad)}')
print(f'Ajuste por inflación: valores en pesos de {fecha_base.strftime("%B %Y")}')

# Gráfico 1: Evolución de montos por categoría (NOMINALES)
fig1 = go.Figure()

categorias_ordenadas = sorted(df_actividad['categoria'].unique())

for categoria in categorias_ordenadas:
    datos_cat = df_actividad[df_actividad['categoria'] == categoria].sort_values('start_date')
    fig1.add_trace(go.Scatter(
        x=datos_cat['start_date'],
        y=datos_cat['monto_analizado'],
        mode='lines+markers',
        name=f'Categoría {categoria}',
        line=dict(width=2),
        marker=dict(size=6)
    ))

fig1.update_layout(
    title=f'{componente_label} - Monotributo {args.tipo.capitalize()} - VALORES NOMINALES',
    xaxis_title='Período',
    yaxis_title='Monto ($)',
    hovermode='x unified',
    legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
    height=600,
    template='plotly_white'
)

output_prefix = f'monotributo_{args.tipo}_{args.componente}'
output_file = f'{graficos_dir}/{output_prefix}_nominal.html'
fig1.write_html(output_file)
print(f'\n✓ Gráfico 1 generado: {output_file}')

# Gráfico 2: Evolución de montos por categoría (AJUSTADOS POR INFLACIÓN)
fig2 = go.Figure()

for categoria in categorias_ordenadas:
    datos_cat = df_actividad[df_actividad['categoria'] == categoria].sort_values('start_date')
    fig2.add_trace(go.Scatter(
        x=datos_cat['start_date'],
        y=datos_cat['monto_real'],
        mode='lines+markers',
        name=f'Categoría {categoria}',
        line=dict(width=2),
        marker=dict(size=6)
    ))

fig2.update_layout(
    title=f'{componente_label} - Monotributo {args.tipo.capitalize()} - VALORES REALES (pesos de {fecha_base.strftime("%B %Y")})',
    xaxis_title='Período',
    yaxis_title='Monto ($ constantes)',
    hovermode='x unified',
    legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01),
    height=600,
    template='plotly_white'
)

output_file = f'{graficos_dir}/{output_prefix}_real.html'
fig2.write_html(output_file)
print(f'✓ Gráfico 2 generado: {output_file}')

# Gráfico 3: Análisis de incremento porcentual por categoría (NOMINAL vs REAL)
df_incremento = df_actividad.sort_values('start_date').groupby('categoria').agg({
    'monto_analizado': ['first', 'last'],
    'monto_real': ['first', 'last'],
    'start_date': ['min', 'max']
}).reset_index()

df_incremento.columns = ['categoria', 'monto_inicial', 'monto_final', 'monto_real_inicial', 'monto_real_final', 'fecha_inicial', 'fecha_final']
df_incremento['incremento_nominal'] = ((df_incremento['monto_final'] - df_incremento['monto_inicial']) / df_incremento['monto_inicial'] * 100)
df_incremento['incremento_real'] = ((df_incremento['monto_real_final'] - df_incremento['monto_real_inicial']) / df_incremento['monto_real_inicial'] * 100)

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    x=df_incremento['categoria'],
    y=df_incremento['incremento_nominal'],
    name='Incremento Nominal',
    text=[f'{val:.0f}%' for val in df_incremento['incremento_nominal']],
    textposition='outside',
    marker_color='indianred'
))

fig3.add_trace(go.Bar(
    x=df_incremento['categoria'],
    y=df_incremento['incremento_real'],
    name='Incremento Real (ajustado por inflación)',
    text=[f'{val:.0f}%' for val in df_incremento['incremento_real']],
    textposition='outside',
    marker_color='steelblue'
))

fig3.update_layout(
    title=f'{componente_label} - Incremento Porcentual ({args.tipo.capitalize()}) - Nominal vs Real',
    xaxis_title='Categoría',
    yaxis_title='Incremento (%)',
    barmode='group',
    height=500,
    template='plotly_white'
)

output_file = f'{graficos_dir}/{output_prefix}_incremento.html'
fig3.write_html(output_file)
print(f'✓ Gráfico 3 generado: {output_file}')

# Gráfico 4: Heatmap de montos REALES por categoría y período
df_heatmap = df_actividad.pivot_table(
    values='monto_real',
    index='categoria',
    columns='period',
    aggfunc='first'
)

fig4 = go.Figure(data=go.Heatmap(
    z=df_heatmap.values,
    x=df_heatmap.columns,
    y=df_heatmap.index,
    colorscale='Blues',
    text=df_heatmap.values,
    texttemplate='$%{text:.0f}',
    textfont={'size': 8},
    colorbar=dict(title='Monto Real ($)')
))

fig4.update_layout(
    title=f'{componente_label} - Mapa de Calor ({args.tipo.capitalize()}, pesos de {fecha_base.strftime("%B %Y")})',
    xaxis_title='Período',
    yaxis_title='Categoría',
    height=600,
    template='plotly_white'
)

output_file = f'{graficos_dir}/{output_prefix}_heatmap.html'
fig4.write_html(output_file)
print(f'✓ Gráfico 4 generado: {output_file}')

# Mostrar tabla resumen
print('\n' + '=' * 80)
print('RESUMEN DE INCREMENTOS POR CATEGORÍA - NOMINAL VS REAL')
print('=' * 80)
resumen = df_incremento[['categoria', 'monto_inicial', 'monto_final', 'incremento_nominal',
                         'monto_real_inicial', 'monto_real_final', 'incremento_real']].copy()
resumen.columns = ['Cat', 'Inicial', 'Final', 'Inc%Nom', 'RealIni', 'RealFin', 'Inc%Real']
print(resumen.to_string(index=False))

# Calcular tasa de crecimiento anual promedio (CAGR)
years_diff = (df_incremento['fecha_final'] - df_incremento['fecha_inicial']).dt.days / 365.25
df_incremento['cagr_nominal'] = ((df_incremento['monto_final'] / df_incremento['monto_inicial']) ** (1 / years_diff) - 1) * 100
df_incremento['cagr_real'] = ((df_incremento['monto_real_final'] / df_incremento['monto_real_inicial']) ** (1 / years_diff) - 1) * 100

print('\n' + '=' * 80)
print('TASA DE CRECIMIENTO ANUAL COMPUESTA (CAGR) - NOMINAL VS REAL')
print('=' * 80)
cagr_table = df_incremento[['categoria', 'cagr_nominal', 'cagr_real']].copy()
cagr_table.columns = ['Categoría', 'CAGR Nominal (%)', 'CAGR Real (%)']
print(cagr_table.to_string(index=False))

# Análisis de pérdida de valor real
print('\n' + '=' * 80)
print('ANÁLISIS DE PÉRDIDA/GANANCIA DE VALOR REAL')
print('=' * 80)
for _, row in df_incremento.iterrows():
    if row['incremento_real'] < 0:
        print(f"Categoría {row['categoria']}: PÉRDIDA de {abs(row['incremento_real']):.1f}% en términos reales")
    elif row['incremento_real'] > 0:
        print(f"Categoría {row['categoria']}: GANANCIA de {row['incremento_real']:.1f}% en términos reales")
    else:
        print(f"Categoría {row['categoria']}: SIN CAMBIO en términos reales")

print('\n' + '=' * 80)
print('✓ Análisis completado exitosamente!')
print(f'Se generaron 4 archivos HTML con gráficos interactivos en {graficos_dir}/:')
print(f'  1. {output_prefix}_nominal.html - Evolución valores nominales')
print(f'  2. {output_prefix}_real.html - Evolución valores reales (ajustados por IPC)')
print(f'  3. {output_prefix}_incremento.html - Comparación incremental nominal vs real')
print(f'  4. {output_prefix}_heatmap.html - Mapa de calor valores reales')
print('=' * 80)

# Generar index.html usando Jinja2
import glob
from datetime import datetime as dt
from jinja2 import Template

def parse_filename_to_title(basename):
    """Parsea el nombre de archivo y genera un título legible"""
    # Formato: monotributo_{tipo}_{componente}_{grafico}.html
    parts = basename.replace('monotributo_', '').replace('.html', '').split('_')
    title_parts = []

    # Tipo de actividad (servicios/ventas)
    if 'servicios' in parts:
        title_parts.append('Servicios')
        parts.remove('servicios')
    elif 'ventas' in parts:
        title_parts.append('Ventas')
        parts.remove('ventas')

    # Identificar el componente completo
    if 'impuesto' in parts and 'integrado' in parts:
        title_parts.append('Impuesto Integrado')
        parts = [p for p in parts if p not in ['impuesto', 'integrado']]
    elif 'aporte' in parts and 'sipa' in parts:
        title_parts.append('Aporte SIPA')
        parts = [p for p in parts if p not in ['aporte', 'sipa']]
    elif 'obra' in parts and 'social' in parts:
        title_parts.append('Aporte Obra Social')
        parts = [p for p in parts if p not in ['aporte', 'obra', 'social']]
    elif 'total' in parts:
        title_parts.append('Total')
        parts.remove('total')

    # Tipo de gráfico
    grafico_map = {
        'nominal': 'Nominal',
        'real': 'Real',
        'incremento': 'Incremento',
        'heatmap': 'Mapa de Calor'
    }

    for part in parts:
        if part in grafico_map:
            title_parts.append(grafico_map[part])
            break

    return ' - '.join(title_parts) if title_parts else basename

# Obtener fecha de última actualización de los datos
try:
    datos_timestamp = os.path.getmtime('data/monotributo_historico.json')
    fecha_datos = dt.fromtimestamp(datos_timestamp).strftime('%d/%m/%Y %H:%M:%S')
except:
    fecha_datos = 'No disponible'

# Obtener archivos HTML y preparar datos
html_files = sorted(glob.glob(f'{graficos_dir}/monotributo_*.html'))

file_descriptions = {
    'nominal': 'Evolución en valores nominales',
    'real': 'Evolución ajustada por inflación (valores reales)',
    'incremento': 'Comparación de incrementos: nominal vs real',
    'heatmap': 'Mapa de calor por período y categoría'
}

graficos = []
for html_file in html_files:
    basename = os.path.basename(html_file)
    title = parse_filename_to_title(basename)

    # Determinar descripción
    desc = 'Gráfico del monotributo'
    for key, value in file_descriptions.items():
        if key in basename:
            desc = value
            break

    graficos.append({
        'filename': f'{graficos_dir}/{basename}',  # Ruta relativa con carpeta
        'title': title,
        'description': desc
    })

# Cargar template y renderizar
with open('index.jinja', 'r', encoding='utf-8') as f:
    template = Template(f.read())

html_output = template.render(
    fecha_datos=fecha_datos,
    graficos=graficos
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_output)

print('✓ Generado index.html con todos los gráficos disponibles')
