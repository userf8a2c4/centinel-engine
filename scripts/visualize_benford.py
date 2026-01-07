import json
import matplotlib.pyplot as plt
import os
import shutil
import collections
import math
from datetime import datetime

def get_first_digit(number):
    """Extrae el primer dígito significativo de un número."""
    s = str(number).replace(".", "").replace("-", "").lstrip("0")
    return int(s[0]) if s else None

def generate_benford_plot():
    # 1. Configuración de rutas y tiempo
    report_path = 'anomalies_report.json'
    output_dir = 'plots'
    now_dt = datetime.now()
    file_timestamp = now_dt.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f'benford_analysis_{file_timestamp}.png')
    latest_path = os.path.join(output_dir, 'latest.png')
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 2. Datos ideales de Benford (Ley Matemática)
    digits = list(range(1, 10))
    benford_ideal = [math.log10(1 + 1/d) * 100 for d in digits]

    # 3. Intentar cargar datos reales del reporte
    real_frequencies = [0] * 9
    has_real_data = False
    data_timestamp = now # Por defecto usamos la hora actual

    if os.path.exists(report_path):
        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
                
                # Intentar extraer timestamp del JSON si existe
                if isinstance(data, dict) and 'timestamp' in data:
                    data_timestamp = data['timestamp']
                
                all_votos = []
                if isinstance(data, dict):
                    # Buscamos valores numéricos en el reporte
                    for key, value in data.items():
                        if isinstance(value, (int, float)) and value > 0:
                            all_votos.append(value)
                
                if all_votos:
                    first_digits = [get_first_digit(v) for v in all_votos if get_first_digit(v) is not None]
                    counts = collections.Counter(first_digits)
                    total = len(first_digits)
                    real_frequencies = [(counts[d] / total) * 100 for d in digits]
                    has_real_data = True
        except Exception as e:
            print(f"Error procesando datos reales: {e}")

    # 4. Creación de la Gráfica
    plt.figure(figsize=(10, 7))
    
    # Dibujar Curva Ideal (Azul)
    plt.plot(digits, benford_ideal, 'o-', label='Ley de Benford (Ideal)', color='#1f77b4', linewidth=3, alpha=0.8)
    
    # Dibujar Curva Real (Roja)
    if has_real_data:
        plt.plot(digits, real_frequencies, 's--', label='Datos CNE (Real)', color='#d62728', linewidth=2)
        plt.fill_between(digits, benford_ideal, real_frequencies, color='red', alpha=0.1, label='Desviación')
    
    # 5. Estética y Títulos Dinámicos
    plt.title(f'Sentinel 2029: Auditoría Estadística\nEjecución: {data_timestamp}', fontsize=14, fontweight='bold', pad=20)
    plt.xlabel('Primer Dígito Significativo', fontsize=12)
    plt.ylabel('Frecuencia de Aparición (%)', fontsize=12)
    plt.xticks(digits)
    plt.ylim(0, 45)
    plt.legend(loc='upper right')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Marcas de identificación en el pie de la imagen
    plt.figtext(0.02, 0.02, f"Archivo origen: {report_path}", fontsize=8, color='gray')
    plt.figtext(0.98, 0.02, "HND-SENTINEL-2029 | Hash-Verified Evidence", fontsize=8, color='gray', ha='right')

    # 6. Guardar y Cerrar
    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajustar espacio para el pie de foto
    plt.savefig(output_path)
    shutil.copyfile(output_path, latest_path)
    plt.close()
    print(
        "Gráfica generada: "
        f"{output_path} con timestamp {data_timestamp} (latest: {latest_path})"
    )

if __name__ == "__main__":
    generate_benford_plot()
