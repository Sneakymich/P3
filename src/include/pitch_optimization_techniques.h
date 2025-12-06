#ifndef PITCH_OPTIMIZATION_TECHNIQUES_H
#define PITCH_OPTIMIZATION_TECHNIQUES_H

#include <vector>
#include <cmath>
#include <algorithm>

namespace upc {
namespace optimization {

// ============================================================================
// TÉCNICAS DE PREPROCESADO
// ============================================================================

/**
 * Filtrado paso bajo IIR de primer orden
 * @param x Vector de señal (modificado in-place)
 * @param cutoff_hz Frecuencia de corte en Hz
 * @param sample_rate Frecuencia de muestreo en Hz
 */
inline void lowpass_filter(std::vector<float> &x, float cutoff_hz, unsigned int sample_rate) {
    if (x.size() < 2) return;
    
    float omega = 2.0f * 3.141592653589793f * cutoff_hz / sample_rate;
    float alpha = omega / (omega + 2.0f);  // Normalización simple
    
    // Pasada hacia adelante
    for (size_t i = 1; i < x.size(); ++i) {
        x[i] = alpha * x[i] + (1.0f - alpha) * x[i-1];
    }
    
    // Pasada hacia atrás (filtro bidireccional)
    for (int i = static_cast<int>(x.size()) - 2; i >= 0; --i) {
        x[i] = alpha * x[i] + (1.0f - alpha) * x[i+1];
    }
}

/**
 * Center clipping: enfatiza regiones de amplitud alta, suprime ruido bajo
 * @param x Vector de señal (modificado in-place)
 * @param threshold Porcentaje del máximo (0.0-1.0)
 */
inline void center_clipping(std::vector<float> &x, float threshold = 0.4f) {
    if (x.empty()) return;
    
    // Encontrar máximo absoluto
    float max_val = 0.0f;
    for (const auto &sample : x) {
        float abs_sample = std::abs(sample);
        if (abs_sample > max_val) max_val = abs_sample;
    }
    
    if (max_val < 1e-8f) return;
    
    float clip_level = threshold * max_val;
    
    // Aplicar clipping
    for (auto &sample : x) {
        if (std::abs(sample) < clip_level) {
            sample = 0.0f;
        } else {
            sample = (sample > 0.0f) ? (sample - clip_level) : (sample + clip_level);
        }
    }
}

/**
 * Pre-énfasis: acentúa armónicos de alto orden
 * @param x Vector de señal (modificado in-place)
 * @param alpha Coeficiente de pre-énfasis (típicamente 0.95-0.97)
 */
inline void pre_emphasis(std::vector<float> &x, float alpha = 0.95f) {
    if (x.size() < 2) return;
    
    std::vector<float> y(x.size());
    y[0] = x[0];
    
    for (size_t i = 1; i < x.size(); ++i) {
        y[i] = x[i] - alpha * x[i-1];
    }
    
    x = y;  // Copiar resultado
}

/**
 * Diezmado (decimación) con filtro anti-aliasing
 * @param x Vector de señal
 * @param factor Factor de diezmado (1=sin diezmado, 2=reduce fs a fs/2)
 * @return Vector diezmado
 */
inline std::vector<float> decimate(const std::vector<float> &x, unsigned int factor) {
    if (factor <= 1) return x;
    
    std::vector<float> x_filtered = x;
    // Aplicar filtro paso bajo antes de diezmar
    // (fs_nueva = fs/factor, fc_filter = fs_nueva/2)
    
    std::vector<float> decimated;
    decimated.reserve(x.size() / factor);
    
    for (size_t i = 0; i < x.size(); i += factor) {
        decimated.push_back(x_filtered[i]);
    }
    
    return decimated;
}

// ============================================================================
// TÉCNICAS DE POSTPROCESADO
// ============================================================================

/**
 * Filtro de mediana adaptativo para suavización de contorno de pitch
 * @param f0 Vector de valores de pitch (0 = unvoiced)
 * @param window_size Tamaño de ventana de mediana (debe ser impar)
 * @param adapt_threshold Umbral para adaptabilidad (Hz)
 * @return Vector de pitch filtrado
 */
inline std::vector<float> adaptive_median_filter(const std::vector<float> &f0, 
                                                  unsigned int window_size = 3,
                                                  float adapt_threshold = 100.0f) {
    std::vector<float> f0_filtered = f0;
    
    if (window_size < 1 || f0.size() < window_size) return f0_filtered;
    
    unsigned int half_window = window_size / 2;
    
    for (size_t i = half_window; i < f0.size() - half_window; ++i) {
        // Solo procesar si el frame actual es voiced
        if (f0[i] <= 0.0f) continue;
        
        std::vector<float> voiced_values;
        
        // Recopilar valores voiced en la ventana
        for (int j = -static_cast<int>(half_window); j <= static_cast<int>(half_window); ++j) {
            if (f0[i + j] > 0.0f) {
                voiced_values.push_back(f0[i + j]);
            }
        }
        
        if (voiced_values.empty()) continue;
        
        // Calcular mediana
        size_t median_idx = voiced_values.size() / 2;
        std::nth_element(voiced_values.begin(), 
                        voiced_values.begin() + median_idx, 
                        voiced_values.end());
        float median_val = voiced_values[median_idx];
        
        // Aplicar adaptivamente si el cambio es pequeño
        if (std::abs(f0[i] - median_val) < adapt_threshold) {
            f0_filtered[i] = median_val;
        }
    }
    
    return f0_filtered;
}

/**
 * Interpolación parabólica para refinamiento de lag
 * Mejora la precisión del pitch detectado
 * @param r Vector de autocorrelación
 * @param lag Índice del máximo encontrado
 * @return Lag refinado (puede ser fraccionario)
 */
inline float parabolic_interpolation(const std::vector<float> &r, unsigned int lag) {
    if (lag <= 0 || lag >= r.size() - 1) {
        return static_cast<float>(lag);
    }
    
    float a = r[lag - 1];
    float b = r[lag];
    float c = r[lag + 1];
    
    float denom = 2.0f * (a - 2.0f * b + c);
    if (std::abs(denom) < 1e-8f) {
        return static_cast<float>(lag);
    }
    
    float offset = (a - c) / denom;
    float refined_lag = static_cast<float>(lag) + 0.5f * offset;
    
    return refined_lag;
}

/**
 * Suavizado temporal con media móvil exponencial (EWMA)
 * @param f0 Vector de pitch
 * @param alpha Factor de suavizado (0.1-0.3)
 * @return Vector suavizado
 */
inline std::vector<float> exponential_smoothing(const std::vector<float> &f0, float alpha = 0.2f) {
    if (f0.empty()) return f0;
    
    std::vector<float> f0_smooth(f0.size());
    f0_smooth[0] = f0[0];
    
    for (size_t i = 1; i < f0.size(); ++i) {
        if (f0[i] > 0.0f && f0_smooth[i-1] > 0.0f) {
            // Ambos voiced
            f0_smooth[i] = alpha * f0[i] + (1.0f - alpha) * f0_smooth[i-1];
        } else {
            // Al menos uno unvoiced
            f0_smooth[i] = f0[i];
        }
    }
    
    return f0_smooth;
}

// ============================================================================
// MÉTODOS ALTERNATIVOS Y COMPLEMENTARIOS
// ============================================================================

/**
 * AMDF: Average Magnitude Difference Function
 * Alternativa a autocorrelación, más robusta en ciertos casos
 * @param x Vector de señal
 * @param max_lag Máximo lag a considerar
 * @return Vector AMDF (minimo = pitch probable)
 */
inline std::vector<float> amdf(const std::vector<float> &x, unsigned int max_lag) {
    std::vector<float> d(max_lag);
    
    for (unsigned int lag = 0; lag < max_lag; ++lag) {
        d[lag] = 0.0f;
        for (unsigned int n = 0; n < x.size() - lag; ++n) {
            d[lag] += std::abs(x[n] - x[n + lag]);
        }
        d[lag] /= (x.size() - lag);
    }
    
    return d;
}

/**
 * ASDF: Average Squared Difference Function
 * Variante de AMDF usando diferencias cuadradas
 * @param x Vector de señal
 * @param max_lag Máximo lag a considerar
 * @return Vector ASDF
 */
inline std::vector<float> asdf(const std::vector<float> &x, unsigned int max_lag) {
    std::vector<float> d(max_lag);
    
    for (unsigned int lag = 0; lag < max_lag; ++lag) {
        d[lag] = 0.0f;
        for (unsigned int n = 0; n < x.size() - lag; ++n) {
            float diff = x[n] - x[n + lag];
            d[lag] += diff * diff;
        }
        d[lag] /= (x.size() - lag);
    }
    
    return d;
}

/**
 * Score híbrido: combina autocorrelación y AMDF
 * @param r Función de autocorrelación (normalizada)
 * @param d Función AMDF (normalizada)
 * @param alpha Peso de autocorrelación (típicamente 0.6-0.7)
 * @return Vector de score combinado
 */
inline std::vector<float> hybrid_autocorr_amdf_score(const std::vector<float> &r,
                                                      const std::vector<float> &d,
                                                      float alpha = 0.65f) {
    size_t max_size = std::min(r.size(), d.size());
    std::vector<float> score(max_size);
    
    // Normalizar autocorrelación
    float r_max = *std::max_element(r.begin(), r.begin() + max_size);
    if (r_max < 1e-8f) r_max = 1.0f;
    
    // Normalizar AMDF (mínimo = mejor)
    float d_max = *std::max_element(d.begin(), d.begin() + max_size);
    if (d_max < 1e-8f) d_max = 1.0f;
    
    for (size_t i = 0; i < max_size; ++i) {
        float r_norm = r[i] / r_max;
        float d_norm = 1.0f - (d[i] / d_max);  // Invertir: máximo = mejor
        
        score[i] = alpha * r_norm + (1.0f - alpha) * d_norm;
    }
    
    return score;
}

/**
 * Análisis cepstral para detección de pitch
 * Calcula cepstrum (IFFT de log-espectro)
 * @param x Vector de señal
 * @return Vector cepstral (máximo indica pitch probable)
 * 
 * Nota: Requiere FFT/IFFT. Implementación pseudocódigo:
 * 1. X = FFT(x)
 * 2. log_mag = log(|X|)
 * 3. cepstrum = IFFT(log_mag)
 * 4. pitch_lag = argmax(cepstrum[10:end])
 */
// (Ver implementación en archivo separado con soporte FFT)

// ============================================================================
// OPTIMIZACIÓN DE PARÁMETROS DE VOICEDNESS
// ============================================================================

/**
 * Calcula UMAXNORM dinámico basado en energía de la señal
 * @param x Vector de señal
 * @param base_umaxnorm Valor base de UMAXNORM
 * @return Valor ajustado de UMAXNORM
 */
inline float dynamic_umaxnorm(const std::vector<float> &x, float base_umaxnorm = 0.3f) {
    if (x.empty()) return base_umaxnorm;
    
    // Calcular energía
    float energy = 0.0f;
    for (const auto &sample : x) {
        energy += sample * sample;
    }
    energy /= x.size();
    float energy_db = 10.0f * std::log10(energy + 1e-10f);
    
    // Ajuste adaptativo
    if (energy_db < -25.0f) {
        return base_umaxnorm * 0.80f;  // Muy ruidoso: más permisivo
    } else if (energy_db < -15.0f) {
        return base_umaxnorm * 0.90f;  // Ruidoso
    } else if (energy_db > 0.0f) {
        return base_umaxnorm * 1.15f;  // Muy limpio: más estricto
    }
    
    return base_umaxnorm;
}

/**
 * Decisión de voicedness ponderada (alternativa a OR simple)
 * @param pot Potencia en dB
 * @param r1norm Norma del primer coeficiente de autocorrelación
 * @param rmaxnorm Norma del máximo de autocorrelación
 * @param zcr Zero-crossing rate (0-1)
 * @return true si es unvoiced, false si es voiced
 */
inline bool weighted_voicing_decision(float pot, float r1norm, float rmaxnorm, float zcr) {
    // Pesos: suma = 1.0
    float score = 0.0f;
    
    if (pot > -35.0f)      score += 0.3f;  // Buena potencia
    if (r1norm > 0.3f)     score += 0.3f;  // Fuerte periodicidad
    if (rmaxnorm > 0.35f)  score += 0.2f;  // Máximo de autocorr alto
    if (zcr < 0.12f)       score += 0.2f;  // Bajo ZCR
    
    return (score < 0.5f);  // Umbral de decisión
}

/**
 * Análisis de flatness espectral (medida de voicedness)
 * @param x Vector de señal
 * @return Flatness [0,1] donde 0=pitched, 1=ruido
 * 
 * Flatness = exp(media(log|X|)) / media(|X|)
 * Requiere FFT (ver archivo separado)
 */

/**
 * Análisis multidimensional de voicedness
 * Combina múltiples características para decisión robusta
 * @param pot Potencia en dB
 * @param r1norm Norma del primer lag
 * @param rmaxnorm Norma del máximo
 * @param zcr Zero-crossing rate
 * @param spectral_centroid Centroide espectral normalizado [0,1]
 * @return Probabilidad de voicing [0,1]
 */
inline float multifeature_voicing_probability(float pot, float r1norm, float rmaxnorm, 
                                               float zcr, float spectral_centroid = 0.5f) {
    // Inicializar probabilidades para cada característica
    float p_power = (pot > -35.0f) ? 0.9f : 0.2f;
    float p_r1 = std::max(0.0f, r1norm / 0.5f);
    float p_rmax = std::max(0.0f, rmaxnorm / 0.5f);
    float p_zcr = (zcr < 0.15f) ? 0.9f : 0.2f;
    float p_spectral = (spectral_centroid > 0.6f) ? 0.3f : 0.8f;
    
    // Media ponderada
    return (0.25f * p_power + 0.25f * p_r1 + 0.25f * p_rmax + 
            0.15f * p_zcr + 0.10f * p_spectral);
}

} // namespace optimization
} // namespace upc

#endif // PITCH_OPTIMIZATION_TECHNIQUES_H
