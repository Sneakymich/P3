#!/usr/bin/env python3
"""
Script para visualizar análisis de pitch en tiempo real con matplotlib
Genera gráficas interactivas mostrando:
- Forma de onda del audio completo
- Parámetros de voicedness en el tiempo (Potencia, r1norm, rmaxnorm)
- Pitch estimado en el tiempo
"""

import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt
import os
from matplotlib.widgets import Slider

# === Parámetros ===
FILENAME = '../prueba.wav'
FRAME_DURATION = 0.030  # 30 ms
HOP_SIZE = 0.015  # 15 ms entre frames (según enunciado)
MIN_F0 = 50
MAX_F0 = 500

def autocorrelation_sesgada(x):
    """Calcula autocorrelación sesgada"""
    N = len(x)
    r = np.array([np.sum(x[:N - l] * x[l:N]) / N for l in range(N)])
    return r

def hamming_window(N):
    """Genera ventana de Hamming"""
    return np.hamming(N)

def analyze_frame(frame, rate, min_f0, max_f0):
    """Analiza un frame y retorna parámetros de voicedness"""
    # Aplicar ventana
    window = hamming_window(len(frame))
    frame_windowed = frame * window
    
    # Calcular autocorrelación
    r = autocorrelation_sesgada(frame_windowed)
    
    # Protección contra división por cero
    if r[0] == 0.0:
        r[0] = 1e-10
    
    # Parámetros de voicedness
    pot = 10 * np.log10(r[0] + 1e-10)  # Potencia en dB
    
    # Buscar máximo secundario (lag != 0)
    lag_min = int(rate / max_f0)
    lag_max = int(rate / min_f0)
    
    if lag_min < 1:
        lag_min = 1
    if lag_max >= len(r):
        lag_max = len(r) - 1
    
    r_copy = r.copy()
    r_copy[0] = 1e-10  # Ignorar lag=0 para búsqueda de pitch
    
    if lag_min < lag_max:
        lag_range = r_copy[lag_min:lag_max]
        lag = np.argmax(lag_range) + lag_min if len(lag_range) > 0 else 0
    else:
        lag = 0
    
    r1norm = r[1] / r[0] if r[0] != 0 else 0
    rmaxnorm = r[lag] / r[0] if r[0] != 0 and lag > 0 else 0
    
    # ZCR
    zcr = np.sum(np.abs(np.diff(np.sign(frame_windowed)))) / (2 * len(frame_windowed))
    
    pitch = rate / lag if lag > 0 else 0
    
    return {
        'pot': float(pot),
        'r1norm': float(r1norm),
        'rmaxnorm': float(rmaxnorm),
        'zcr': float(zcr),
        'pitch': float(pitch),
        'lag': int(lag)
    }

def process_audio(filename, frame_duration, hop_size, min_f0, max_f0):
    """Procesa el archivo de audio completo"""
    
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Archivo no encontrado: {filename}")
    
    rate, data = wav.read(filename)
    
    # Convertir a mono si es estéreo
    if data.ndim > 1:
        data = data[:, 0]
    
    # Convertir a float32
    data = data.astype(np.float32)
    
    # Normalizar
    data = data / np.max(np.abs(data))
    
    frame_len = int(frame_duration * rate)
    hop_len = int(hop_size * rate)
    
    frames_data = []
    times = []
    
    # Procesar frames
    pos = 0
    while pos + frame_len <= len(data):
        frame = data[pos:pos + frame_len]
        frame -= np.mean(frame)  # Quitar DC
        
        analysis = analyze_frame(frame, rate, min_f0, max_f0)
        time_center = (pos + frame_len / 2) / rate
        
        frames_data.append(analysis)
        times.append(float(time_center))
        
        pos += hop_len
    
    return {
        'rate': rate,
        'duration': len(data) / rate,
        'frames': frames_data,
        'times': times,
        'audio': data,
        'audio_path': os.path.basename(filename)
    }

def visualize_analysis(analysis_data):
    """Crea visualización interactiva con matplotlib"""
    
    times = np.array(analysis_data['times'])
    frames = analysis_data['frames']
    audio = analysis_data['audio']
    rate = analysis_data['rate']
    
    # Extraer datos para gráficas
    pots = np.array([f['pot'] for f in frames])
    r1norms = np.array([f['r1norm'] for f in frames])
    rmaxnorms = np.array([f['rmaxnorm'] for f in frames])
    pitches = np.array([f['pitch'] for f in frames])
    
    # Crear figura con subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f"Análisis de Pitch y Voicedness - {analysis_data['audio_path']}", 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Crear grid
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3)
    
    # Plot 1: Forma de onda completa
    ax1 = fig.add_subplot(gs[0, :])
    t_audio = np.arange(len(audio)) / rate
    ax1.plot(t_audio, audio, color='steelblue', linewidth=0.5, alpha=0.8)
    ax1.scatter(times, [audio[int(t*rate)] for t in times], color='red', s=20, alpha=0.6, label='Centros de frames')
    ax1.set_xlabel('Tiempo (s)')
    ax1.set_ylabel('Amplitud')
    ax1.set_title('Forma de Onda del Audio Completo', fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Potencia en el tiempo
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(times, pots, 'o-', color='#ff6b6b', linewidth=2, markersize=4)
    ax2.axhline(y=-40, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Umbral (-40 dB)')
    ax2.fill_between(times, pots, -40, where=(pots < -40), alpha=0.2, color='red', label='Unvoiced')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Potencia (dB)')
    ax2.set_title('Potencia (r[0]) - Parámetro de Voicedness', fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Pitch en el tiempo
    ax3 = fig.add_subplot(gs[1, 1])
    pitches_filtered = np.where(pitches > 0, pitches, np.nan)
    ax3.plot(times, pitches_filtered, 'o-', color='#4ecdc4', linewidth=2, markersize=4)
    ax3.set_xlabel('Tiempo (s)')
    ax3.set_ylabel('Pitch (Hz)')
    ax3.set_title('Pitch Estimado en el Tiempo', fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim([0, 500])
    
    # Plot 4: r1norm en el tiempo
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(times, r1norms, 'o-', color='#ffd93d', linewidth=2, markersize=4)
    ax4.axhline(y=0.2, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Umbral (0.2)')
    ax4.fill_between(times, r1norms, 0.2, where=(r1norms < 0.2), alpha=0.2, color='red', label='Unvoiced')
    ax4.set_xlabel('Tiempo (s)')
    ax4.set_ylabel('r1norm (r[1]/r[0])')
    ax4.set_title('r1norm - Autocorrelación Normalizada Lag=1', fontweight='bold')
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: rmaxnorm en el tiempo
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(times, rmaxnorms, 'o-', color='#a8e6cf', linewidth=2, markersize=4)
    ax5.axhline(y=0.4, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Umbral (0.4)')
    ax5.fill_between(times, rmaxnorms, 0.4, where=(rmaxnorms < 0.4), alpha=0.2, color='red', label='Unvoiced')
    ax5.set_xlabel('Tiempo (s)')
    ax5.set_ylabel('rmaxnorm (r[lag]/r[0])')
    ax5.set_title('rmaxnorm - Máximo Secundario Normalizado', fontweight='bold')
    ax5.legend(loc='best')
    ax5.grid(True, alpha=0.3)
    
    plt.show()

def main():
    """Función principal"""
    try:
        print("🎵 Procesando archivo de audio...")
        
        # Procesar audio
        analysis = process_audio(
            FILENAME,
            FRAME_DURATION,
            HOP_SIZE,
            MIN_F0,
            MAX_F0
        )
        
        print(f"✅ Análisis completado: {len(analysis['frames'])} frames procesados")
        print(f"   Duración total: {analysis['duration']:.2f}s")
        print(f"   Frecuencia de muestreo: {analysis['rate']}Hz")
        print(f"   Archivo: {analysis['audio_path']}")
        print("\n📊 Abriendo visualización interactiva...")
        
        # Generar visualización
        visualize_analysis(analysis)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
