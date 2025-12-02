import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
import os

# === Parámetros ===
filename = '../prueba.wav'
frame_duration = 0.030  # 30 ms
frame_start_time = 0.775  # Inicio de segmento analizado (segundos)

# === Leer WAV con manejo de errores ===
if not os.path.exists(filename):
    raise FileNotFoundError(f"Archivo no encontrado: {filename}")
rate, data = wav.read(filename)
if data.ndim > 1:  # Convertir a mono si el archivo es estéreo
    data = data[:, 0]

# === Extraer segmento de 30 ms ===
start_sample = int(frame_start_time * rate)
frame_len = int(frame_duration * rate)
frame = data[start_sample:start_sample + frame_len].astype(np.float32)
frame -= np.mean(frame)  # Quitar DC

# === Calcular autocorrelación sesgada ===
def autocorrelation_sesgada(x):
    N = len(x)
    r = np.array([np.sum(x[:N - l] * x[l:N]) / N for l in range(N)])
    return r

r = autocorrelation_sesgada(frame)

# === Buscar máximo secundario (lag != 0) ===
r[0] = 1e-10
lag_min = int(rate / 500)  # pitch máximo: 500 Hz
lag_max = int(rate / 50)   # pitch mínimo: 50 Hz

lag_range = r[lag_min:lag_max]
lag = np.argmax(lag_range) + lag_min
pitch_period = lag
pitch_freq = rate / pitch_period

# === Prepare visual style ===
plt.style.use('seaborn-v0_8-darkgrid')  # Estilo visual profesional
fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=False)

# Subplot 1: señal temporal
t = np.arange(frame_len) / rate * 1000
axs[0].plot(t, frame, color="royalblue")
axs[0].scatter(pitch_period / rate * 1000, frame[int(pitch_period)], color='red', zorder=5, label='Periodo de pitch')
axs[0].set_title(f"Señal temporal (30 ms)\n{os.path.basename(filename)} | Pitch ≈ {pitch_freq:.2f} Hz")
axs[0].set_xlabel("Tiempo [ms]")
axs[0].set_ylabel("Amplitud")
axs[0].axvline(x=pitch_period / rate * 1000, color='red', linestyle='--')
axs[0].legend(loc='upper right', frameon=True)

# Subplot 2: autocorrelación sesgada
lags = np.arange(len(r))
axs[1].plot(lags, r, color='slateblue')
axs[1].axvline(x=lag, color='crimson', linestyle='--', label='Primer máximo secundario (pitch)')
axs[1].set_title("Autocorrelación sesgada del segmento")
axs[1].set_xlabel("Lag [muestras]")
axs[1].set_ylabel("r[lag]")
axs[1].legend(loc='best', frameon=True)
axs[1].grid(True, linestyle=':')

plt.tight_layout()
plt.suptitle("Análisis de Pitch en Segmento de Audio", fontsize=14, y=1.02)
plt.show()
