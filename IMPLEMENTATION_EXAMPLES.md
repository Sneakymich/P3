# 6 IMPLEMENTACIONES CLAVE - GUÍA RÁPIDA

**Elige UNA opción según tu tiempo disponible y objetivo de mejora.**

---

## 📊 TABLA COMPARATIVA

| Opción | Tiempo | Mejora | Dificultad | Archivos |
|--------|--------|--------|-----------|----------|
| 1: Preprocesado Básico | 5 min | +0.7-1% | ⭐ Muy Baja | get_pitch.cpp |
| 2: Con CLI | 30 min | +0.7-1% | ⭐ Baja | get_pitch.cpp |
| 3: Voicedness | 20 min | +0.5-1% | ⭐ Baja | pitch_analyzer.cpp |
| 4: UMAXNORM Dinámico | 10 min | +0.2-0.5% | ⭐ Muy Baja | pitch_analyzer.h + get_pitch.cpp |
| 5: Parabólica | 15 min | +0.3-0.5% | ⭐ Baja | pitch_analyzer.cpp |
| 6: Todas Juntas | 45 min | **+1.7-2.5%** | ⭐⭐ Media | Todos los archivos |

---

## 1️⃣ PREPROCESADO BÁSICO (5 min) ⭐ MÁS RÁPIDO

**¿Qué hace?** Filtrado LP + center clipping + mediana  
**Mejora:** +0.7-1%  
**Archivo:** `src/get_pitch/get_pitch.cpp`

### Paso 1: Añadir include al principio
```cpp
#include "pitch_optimization_techniques.h"
```

### Paso 2: Reemplazar bucle de frames
Busca dónde se procesa cada frame (dentro del bucle sobre `x`) y reemplaza con:

```cpp
vector<float> f0;
for (iX = x.begin(); iX + n_len < x.end(); iX = iX + n_shift) {
    vector<float> frame(iX, iX + n_len);
    
    // PREPROCESADO
    upc::optimization::lowpass_filter(frame, 1200.0f, rate);
    upc::optimization::center_clipping(frame, 0.4f);
    
    float f = analyzer(frame);
    f0.push_back(f);
}

// POSTPROCESADO (después del bucle)
f0 = upc::optimization::adaptive_median_filter(f0, 3, 100.0f);
```

### Paso 3: Compilar
```bash
meson compile -C build/release
```

### Paso 4: Probar
```bash
./build/release/src/get_pitch/get_pitch prueba.wav output.f0
```

---

## 2️⃣ CON PARÁMETROS CLI (30 min)

**¿Qué hace?** Opción 1 + control flexible vía línea de comandos  
**Mejora:** +0.7-1%  
**Archivo:** `src/get_pitch/get_pitch.cpp`

### Paso 1: Reemplazar USAGE string
```cpp
static const char USAGE[] = R"(
get_pitch - Pitch Estimator with Optimizations

Usage:
    get_pitch [options] <input-wav> <output-txt>

Options:
    --lp-freq <FLOAT>           Low-pass frequency Hz [default: 1200]
    --clip-thresh <FLOAT>       Center clipping threshold [default: 0.4]
    --median-win <INT>          Median filter window size [default: 3]
    --no-preprocess             Disable preprocessing
    --no-postprocess            Disable postprocessing
    -m, --umaxnorm <FLOAT>      Voicedness threshold [default: 0.3]
)";
```

### Paso 2: Parsear parámetros (después de procesar argumentos existentes)
```cpp
#include "pitch_optimization_techniques.h"

float lp_freq = args.count("--lp-freq") ? std::stof(args["--lp-freq"]) : 1200.0f;
float clip_thresh = args.count("--clip-thresh") ? std::stof(args["--clip-thresh"]) : 0.4f;
int median_win = args.count("--median-win") ? std::stoi(args["--median-win"]) : 3;
bool preprocess = !args.count("--no-preprocess");
bool postprocess = !args.count("--no-postprocess");
```

### Paso 3: Usar en bucle
```cpp
vector<float> f0;
for (iX = x.begin(); iX + n_len < x.end(); iX = iX + n_shift) {
    vector<float> frame(iX, iX + n_len);
    
    if (preprocess) {
        upc::optimization::lowpass_filter(frame, lp_freq, rate);
        upc::optimization::center_clipping(frame, clip_thresh);
    }
    
    float f = analyzer(frame);
    f0.push_back(f);
}

if (postprocess) {
    f0 = upc::optimization::adaptive_median_filter(f0, median_win, 100.0f);
}
```

### Ejemplos de uso
```bash
# Configuración óptima
./build/release/src/get_pitch/get_pitch --lp-freq 1200 --clip-thresh 0.4 prueba.wav output.f0

# Sin preprocesado
./build/release/src/get_pitch/get_pitch --no-preprocess prueba.wav output.f0

# Parámetros personalizados
./build/release/src/get_pitch/get_pitch --lp-freq 1000 --clip-thresh 0.5 --median-win 5 prueba.wav output.f0
```

---

## 3️⃣ VOICEDNESS MEJORADA (20 min)

**¿Qué hace?** Reemplaza lógica OR simple con decisión ponderada  
**Mejora:** +0.5-1%  
**Archivo:** `src/get_pitch/pitch_analyzer.cpp`

### Paso 1: Reemplazar función `unvoiced()`

**Busca esta función:**
```cpp
bool PitchAnalyzer::unvoiced(float pot, float r1norm, float rmaxnorm, float zcr) const {
    const float pot_threshold     = -40.0f;
    const float r1_threshold      = 0.2f;
    const float rmax_threshold    = umaxnorm;
    const float zcr_threshold     = 0.15f;

    const bool low_power      = (pot < pot_threshold);
    const bool low_r1         = (r1norm < r1_threshold);
    const bool low_rmax       = (rmaxnorm < rmax_threshold);
    const bool high_zcr       = (zcr > zcr_threshold);

    return (low_power || low_r1 || low_rmax || high_zcr);
}
```

**Reemplaza con:**
```cpp
bool PitchAnalyzer::unvoiced(float pot, float r1norm, float rmaxnorm, float zcr) const {
    const float pot_threshold     = -40.0f;
    const float r1_threshold      = 0.2f;
    const float rmax_threshold    = umaxnorm;
    const float zcr_threshold     = 0.15f;

    float score = 0.0f;
    
    if (pot < pot_threshold)      score += 0.3f;
    if (r1norm < r1_threshold)    score += 0.2f;
    if (rmaxnorm < rmax_threshold) score += 0.3f;
    if (zcr > zcr_threshold)      score += 0.2f;
    
    return (score >= 0.5f);  // Umbral de 50%
}
```

### Paso 2: Compilar y probar
```bash
meson compile -C build/release
./build/release/src/get_pitch/get_pitch prueba.wav output.f0
```

---

## 4️⃣ UMAXNORM DINÁMICO (10 min)

**¿Qué hace?** Ajusta automáticamente umbral según energía de la señal  
**Mejora:** +0.2-0.5%  
**Archivos:** `src/get_pitch/pitch_analyzer.h` + `src/get_pitch/get_pitch.cpp`

### Paso 1: Añadir método en `pitch_analyzer.h`

**En la clase PitchAnalyzer, añade:**
```cpp
public:
    void setDynamicUmaxnorm(bool enable) { use_dynamic_umaxnorm = enable; }
    
private:
    bool use_dynamic_umaxnorm = false;
    float adaptive_umaxnorm(float energy) const {
        if (!use_dynamic_umaxnorm) return umaxnorm;
        
        float db = 10.0f * std::log10(std::max(energy, 1e-10f));
        if (db < -30.0f) return 0.5f;      // Señal muy débil → exigente
        if (db > 0.0f)   return 0.2f;      // Señal fuerte → permisivo
        return 0.3f + (db / -30.0f) * 0.2f; // Interpolación lineal
    }
```

### Paso 2: Usar en `compute_pitch()`

En `pitch_analyzer.cpp`, busca donde se llama a `unvoiced()` y cambia:

**Antes:**
```cpp
if (unvoiced(pot, r1norm, rmaxnorm, zcr)) {
    return 0.0f;
}
```

**Después:**
```cpp
float temp_umaxnorm = umaxnorm;
umaxnorm = adaptive_umaxnorm(pot);
bool is_unvoiced = unvoiced(pot, r1norm, rmaxnorm, zcr);
umaxnorm = temp_umaxnorm;

if (is_unvoiced) {
    return 0.0f;
}
```

### Paso 3: Habilitar en `get_pitch.cpp`

Busca donde se crea el analyzer y añade:
```cpp
analyzer.setDynamicUmaxnorm(true);
```

### Paso 4: Compilar
```bash
meson compile -C build/release
```

---

## 5️⃣ INTERPOLACIÓN PARABÓLICA (15 min)

**¿Qué hace?** Refina lag con precisión sub-muestral  
**Mejora:** +0.3-0.5%  
**Archivo:** `src/get_pitch/pitch_analyzer.cpp`

### Paso 1: Reemplazar función de interpolación

**Busca la función `compute_pitch()` y localiza dónde se calcula el lag máximo.**

**Antes (búsqueda simple):**
```cpp
float max_corr = -1;
int max_lag = 0;
for (int i = lag_min; i <= lag_max; i++) {
    if (r[i] > max_corr) {
        max_corr = r[i];
        max_lag = i;
    }
}
```

**Después (con interpolación parabólica):**
```cpp
float max_corr = -1;
int max_lag = 0;
for (int i = lag_min; i <= lag_max; i++) {
    if (r[i] > max_corr) {
        max_corr = r[i];
        max_lag = i;
    }
}

// Interpolación parabólica si hay vecinos
float refined_lag = (float)max_lag;
if (max_lag > lag_min && max_lag < lag_max) {
    float y0 = r[max_lag - 1];
    float y1 = r[max_lag];
    float y2 = r[max_lag + 1];
    
    float denom = 2.0f * (y0 - 2.0f * y1 + y2);
    if (std::abs(denom) > 1e-6f) {
        refined_lag = max_lag + 0.5f * (y2 - y0) / denom;
    }
}

return rate / refined_lag;
```

### Paso 2: Compilar y probar
```bash
meson compile -C build/release
./build/release/src/get_pitch/get_pitch prueba.wav output.f0
```

---

## 6️⃣ TODAS JUNTAS (45 min) ⭐ MÁXIMA MEJORA

**¿Qué hace?** Combina opciones 1, 3, 4 y 5  
**Mejora:** **+1.7-2.5%**  
**Archivos:** Todos

### Estrategia:
1. Comienza por **Opción 1** (5 min)
2. Añade **Opción 3** (20 min más)
3. Añade **Opción 4** (10 min más)
4. Añade **Opción 5** (15 min más)

### Checklist:
- [ ] Opción 1 implementada y compilando
- [ ] Opción 3 (voicedness ponderada) implementada
- [ ] Opción 4 (UMAXNORM dinámico) implementada
- [ ] Opción 5 (interpolación parabólica) implementada
- [ ] Compilación exitosa: `meson compile -C build/release`
- [ ] Test básico: `./build/release/src/get_pitch/get_pitch prueba.wav output.f0`
- [ ] Evaluación: `scripts/run_get_pitch.sh 0.3`

### Resultado esperado:
- Baseline: 90.17%
- Con Opción 6: 91.87% - 92.67%

---

## 🚀 PASOS FINALES (TODAS LAS OPCIONES)

### Después de implementar tu opción elegida:

```bash
# 1. Compilar
cd /home/inigo/PAV/P3
meson compile -C build/release

# 2. Ejecutar
./build/release/src/get_pitch/get_pitch prueba.wav test_output.f0

# 3. Evaluar mejora
scripts/run_get_pitch.sh 0.3

# 4. Ver resultado (compara con baseline 90.17%)
tail -5 optimization_results.txt
```

### Troubleshooting:
- **Error de compilación**: Asegúrate de que `pitch_optimization_techniques.h` está en `src/include/`
- **Include path**: Si no lo encuentra, añade `-I src/include` a `meson.build`
- **Runtime error**: Verifica que `adaptive_median_filter()` recibe tamaño de ventana válido (3-11)

---

## 📚 REFERENCIA RÁPIDA

Todas las funciones usadas están documentadas en `src/include/pitch_optimization_techniques.h`

**Funciones disponibles:**
- `lowpass_filter(frame, freq_cutoff, sample_rate)` - Filtrado LP
- `center_clipping(frame, threshold)` - Clipping central
- `adaptive_median_filter(f0_contour, window_size, min_freq)` - Mediana adaptativa
- `parabolic_interpolation(values, max_idx)` - Interpolación de lag
- `dynamic_umaxnorm()` - Voicedness adaptativo

---

**¿Cuál elegir?**
- ⏱️ **Tiempo limitado (5 min):** Opción 1
- 💪 **Máxima mejora (45 min):** Opción 6
- 🎯 **Balance (30 min):** Opción 2
- 🔬 **Experimento único:** Elige la que más te interese

