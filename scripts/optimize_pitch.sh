#!/bin/bash

# Script de optimización de parámetros para el estimador de pitch
# Prueba diferentes valores de umaxnorm y captura las métricas de evaluación

set -o pipefail

# Ruta base
BASE_DIR="/home/inigo/PAV/P3"
TRAIN_DIR="$BASE_DIR/pitch_db/train"
BIN_DIR="/home/inigo/PAV/bin"

# Valores de umaxnorm a probar
UMAXNORM_VALUES=(0.2 0.25 0.3 0.35 0.4 0.45 0.5)

# Archivo de resultados
RESULTS_FILE="$BASE_DIR/optimization_results.txt"

echo "🎯 Iniciando optimización de parámetros..."
echo "=====================================" > "$RESULTS_FILE"
echo "Optimización de parámetros - pitch_db/train" >> "$RESULTS_FILE"
echo "=====================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Probar cada valor
for UMAXNORM in "${UMAXNORM_VALUES[@]}"; do
    echo "📊 Probando UMAXNORM=$UMAXNORM..."
    
    # Procesar archivos de audio
    for fwav in $TRAIN_DIR/*.wav; do
        ff0="${fwav/.wav/.f0}"
        $BIN_DIR/get_pitch -m $UMAXNORM "$fwav" "$ff0" > /dev/null 2>&1 || {
            echo "❌ Error procesando $fwav"
            continue
        }
    done
    
    # Evaluar
    echo "Parámetro: UMAXNORM=$UMAXNORM" >> "$RESULTS_FILE"
    echo "---" >> "$RESULTS_FILE"
    
    # Capturar salida de pitch_evaluate
    eval_output=$($BIN_DIR/pitch_evaluate $TRAIN_DIR/*.f0ref 2>&1)
    echo "$eval_output" >> "$RESULTS_FILE"
    echo "" >> "$RESULTS_FILE"
    
    # Mostrar resultado en consola
    echo "  Resultado: $eval_output" | tail -1
done

echo ""
echo "✅ Optimización completada"
echo "📄 Resultados guardados en: $RESULTS_FILE"
echo ""
echo "Resumen de resultados:"
echo "====================="
grep -E "UMAXNORM|overall score" "$RESULTS_FILE"
