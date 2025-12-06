/// @file

#include <iostream>
#include <math.h>
#include "pitch_analyzer.h"

using namespace std;

/// Name space of UPC
namespace upc {
  void PitchAnalyzer::autocorrelation(const vector<float> &x, vector<float> &r) const {

    for (unsigned int l = 0; l < r.size(); ++l) {
  		 /// \TODO Compute the autocorrelation r[l]
       /// autocorrelación sesgada
        r[l] = 0.0f;
      for (unsigned int n = 0; n < x.size() - l; ++n) {
        r[l] += x[n] * x[n+l];
      }
    r[l] /= x.size();//normalización.
    }
  }

  void PitchAnalyzer::set_window(Window win_type) {
    if (frameLen == 0)
      return;

    window.resize(frameLen);

    switch (win_type) {
    case HAMMING:
      /// \TODO Implement the Hamming window
      break;
    case RECT:
    default:
      window.assign(frameLen, 1);
    }
  }

  void PitchAnalyzer::set_f0_range(float min_F0, float max_F0) {
    npitch_min = (unsigned int) samplingFreq/max_F0;
    if (npitch_min < 2)
      npitch_min = 2;  // samplingFreq/2

    npitch_max = 1 + (unsigned int) samplingFreq/min_F0;

    //frameLen should include at least 2*T0
    if (npitch_max > frameLen/2)
      npitch_max = frameLen/2;
  }

  bool PitchAnalyzer::unvoiced(float pot, float r1norm, float rmaxnorm) const {
    /// \TODO Implement a rule to decide whether the sound is voiced or not.
    /// * You can use the standard features (pot, r1norm, rmaxnorm),
    ///   or compute and use other ones.

    if(rmaxnorm > this->umaxnorm)
      return false;
    else
    return true;
  }

  float PitchAnalyzer::compute_pitch(std::vector<float> &x) const {
    if (x.size() != frameLen)
        return -1.0F;

    // Ventaneado
    for (unsigned int i = 0; i < x.size(); ++i)
        x[i] *= window[i];

    // Autocorrelación en [0, npitch_max)
    std::vector<float> r(npitch_max);
    autocorrelation(x, r);

    // Búsqueda del primer máximo secundario en [npitch_min, npitch_max)
    unsigned int lag = npitch_min;
    float max_corr = r[npitch_min];   // r[0] no nos interesa

    for (unsigned int i = npitch_min; i < npitch_max; ++i) {
        if (r[i] > max_corr) {
            max_corr = r[i];
            lag = i;
        }
    }

    // Potencia (en dB) y ZCR para decisión voiced/unvoiced
    float pot = 10.0F * std::log10(r[0]);
    float zcr = 0.0F;
    for (size_t i = 1; i < x.size(); ++i) {
        if ((x[i - 1] >= 0.0F && x[i] < 0.0F) || (x[i - 1] < 0.0F && x[i] >= 0.0F))
            zcr += 1.0F;
    }
    zcr /= static_cast<float>(x.size());

    // Decisión no sonora o lag inválido
    if (unvoiced(pot, r[1] / r[0], r[lag] / r[0], zcr) || lag == 0)
        return 0.0F;

    // Pitch (Hz)
    return static_cast<float>(samplingFreq) / static_cast<float>(lag);
}

}
