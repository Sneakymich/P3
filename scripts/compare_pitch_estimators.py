#!/usr/bin/env python3
"""
Script para comparar los resultados del estimador de pitch propio (get_pitch)
con el estimador de WaveSurfer. Genera gráficas ilustrativas de la comparación.
"""

import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

def compare_pitch_estimators(file_pitch_own, file_pitch_ws):
    """
    Compara dos estimadores de pitch y genera visualización.
    
    Args:
        file_pitch_own: Ruta al archivo de pitch del estimador propio (get_pitch)
        file_pitch_ws: Ruta al archivo de pitch del estimador WaveSurfer
    
    Returns:
        dict con estadísticas de la comparación
    """
    
    # Verificar existencia de archivos
    if not os.path.exists(file_pitch_own):
        raise FileNotFoundError(f"Archivo no encontrado: {file_pitch_own}")
    if not os.path.exists(file_pitch_ws):
        raise FileNotFoundError(f"Archivo no encontrado: {file_pitch_ws}")
    
    print(f"📂 Cargando archivos...")
    print(f"   Estimador propio: {file_pitch_own}")
    print(f"   WaveSurfer: {file_pitch_ws}")
    
    # Cargar datos
    try:
        pitch_own = np.loadtxt(file_pitch_own)
    except Exception as e:
        print(f"❌ Error cargando {file_pitch_own}: {e}")
        return None
    
    try:
        # wavesurfer_pitch tiene 4 columnas, el pitch está en la 3ª (índice 2)
        pitch_ws = np.loadtxt(file_pitch_ws, usecols=2)
    except Exception as e:
        print(f"❌ Error cargando {file_pitch_ws}: {e}")
        return None
    
    # Asegurar que tienen el mismo número de frames
    n = min(len(pitch_own), len(pitch_ws))
    frames = np.arange(n)
    
    pitch_own = pitch_own[:n]
    pitch_ws = pitch_ws[:n]
    
    print(f"\n📊 Estadísticas:")
    print(f"   Número de frames: {n}")
    
    # Calcular diferencias y errores
    diff = np.abs(pitch_own - pitch_ws)
    
    # Filtrar frames con pitch válido (> 0)
    valid_own = pitch_own > 0
    valid_ws = pitch_ws > 0
    valid_both = valid_own & valid_ws
    
    print(f"   Frames con pitch válido (get_pitch): {np.sum(valid_own)}/{n}")
    print(f"   Frames con pitch válido (WaveSurfer): {np.sum(valid_ws)}/{n}")
    print(f"   Frames con ambos válidos: {np.sum(valid_both)}/{n}")
    
    if np.sum(valid_both) > 0:
        mae = np.mean(diff[valid_both])
        rmse = np.sqrt(np.mean(diff[valid_both]**2))
        max_error = np.max(diff[valid_both])
        print(f"\n   MAE (Mean Absolute Error): {mae:.2f} Hz")
        print(f"   RMSE (Root Mean Square Error): {rmse:.2f} Hz")
        print(f"   Error máximo: {max_error:.2f} Hz")
        
        # Correlación
        corr = np.corrcoef(pitch_own[valid_both], pitch_ws[valid_both])[0, 1]
        print(f"   Correlación: {corr:.4f}")
    
    # === Crear visualización ===
    print(f"\n📈 Generando gráficas...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plotear ambos estimadores en el mismo gráfico
    ax.plot(frames, pitch_own, label="get_pitch (propio)", color='steelblue', linewidth=2, alpha=0.8)
    ax.plot(frames, pitch_ws, label="WaveSurfer", color='darkorange', linestyle='--', linewidth=2, alpha=0.8)
    
    ax.set_xlabel("Número de trama", fontsize=12)
    ax.set_ylabel("Pitch [Hz]", fontsize=12)
    ax.set_title("Comparación de Estimadores de Pitch: get_pitch vs WaveSurfer", fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plt.show()
    
    # Retornar estadísticas
    stats = {
        'num_frames': n,
        'valid_own': np.sum(valid_own),
        'valid_ws': np.sum(valid_ws),
        'valid_both': np.sum(valid_both),
    }
    
    if np.sum(valid_both) > 0:
        stats.update({
            'mae': mae,
            'rmse': rmse,
            'max_error': max_error,
            'correlation': corr,
            'mean_own': np.mean(pitch_own[valid_own]),
            'mean_ws': np.mean(pitch_ws[valid_ws]),
        })
    
    return stats

def main():
    """Función principal"""
    
    # Rutas de los archivos
    file_pitch_own = "../prueba.f0"
    file_pitch_ws = "../wavesurfer_pitch_200frames"
    
    print("🎵 Comparador de estimadores de pitch\n")
    
    try:
        stats = compare_pitch_estimators(file_pitch_own, file_pitch_ws)
        
        if stats:
            print(f"\n✅ Comparación completada exitosamente")
    
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("\n💡 Asegúrate de tener:")
        print(f"   - {file_pitch_own}")
        print(f"   - {file_pitch_ws}")
        return 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
