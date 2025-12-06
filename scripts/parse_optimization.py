#!/usr/bin/env python3
"""
Script para parsear y resumir los resultados de optimización de pitch_evaluate
"""

import re
from pathlib import Path
import numpy as np

def parse_optimization_results(file_path):
    """Parsea el archivo de resultados y extrae la información"""
    
    results = {}
    current_umaxnorm = None
    current_scores = []
    
    with open(file_path, 'r') as f:
        for line in f:
            # Detectar UMAXNORM
            match_param = re.search(r'UMAXNORM=([\d.]+)', line)
            if match_param:
                if current_umaxnorm is not None:
                    # Guardar resultados anteriores
                    results[current_umaxnorm] = current_scores.copy()
                
                current_umaxnorm = float(match_param.group(1))
                current_scores = []
                continue
            
            # Detectar scores individuales
            match_score = re.search(r'===>.*?:\s+([\d.]+)\s+%', line)
            if match_score and current_umaxnorm is not None:
                score = float(match_score.group(1))
                current_scores.append(score)
    
    # Guardar últimos resultados
    if current_umaxnorm is not None and current_scores:
        results[current_umaxnorm] = current_scores
    
    return results

def calculate_statistics(results):
    """Calcula estadísticas para cada UMAXNORM"""
    
    stats = {}
    for umaxnorm, scores in sorted(results.items()):
        stats[umaxnorm] = {
            'num_files': len(scores),
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'min_score': np.min(scores),
            'max_score': np.max(scores),
        }
    
    return stats

def print_table(stats):
    """Imprime una tabla formateada de resultados"""
    
    print("\n" + "="*80)
    print("RESULTADOS DE OPTIMIZACIÓN - pitch_db/train")
    print("="*80)
    print()
    print(f"{'UMAXNORM':<12} {'SCORE MEDIO':<15} {'STD':<12} {'MIN':<12} {'MAX':<12} {'N ARCHIVOS':<12}")
    print("-"*80)
    
    best_umaxnorm = None
    best_score = -1
    
    for umaxnorm in sorted(stats.keys()):
        s = stats[umaxnorm]
        mean = s['mean_score']
        
        print(f"{umaxnorm:<12.2f} {mean:<15.2f} {s['std_score']:<12.2f} {s['min_score']:<12.2f} {s['max_score']:<12.2f} {s['num_files']:<12}")
        
        if mean > best_score:
            best_score = mean
            best_umaxnorm = umaxnorm
    
    print("-"*80)
    print(f"\n✅ MEJOR PARÁMETRO: UMAXNORM = {best_umaxnorm:.2f}")
    print(f"📊 SCORE TOTAL PROMEDIO: {best_score:.2f}%\n")
    
    return best_umaxnorm, best_score

def main():
    results_file = Path("/home/inigo/PAV/P3/optimization_results.txt")
    
    if not results_file.exists():
        print(f"❌ Archivo no encontrado: {results_file}")
        return 1
    
    print("📂 Parseando resultados de optimización...")
    results = parse_optimization_results(results_file)
    
    if not results:
        print("❌ No se encontraron resultados en el archivo")
        return 1
    
    stats = calculate_statistics(results)
    best_umaxnorm, best_score = print_table(stats)
    
    # Guardar resumen en archivo
    summary_file = Path("/home/inigo/PAV/P3/optimization_summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("RESULTADOS DE OPTIMIZACIÓN - pitch_db/train\n")
        f.write("="*80 + "\n\n")
        f.write(f"{'UMAXNORM':<12} {'SCORE MEDIO':<15} {'STD':<12} {'MIN':<12} {'MAX':<12} {'N ARCHIVOS':<12}\n")
        f.write("-"*80 + "\n")
        
        for umaxnorm in sorted(stats.keys()):
            s = stats[umaxnorm]
            f.write(f"{umaxnorm:<12.2f} {s['mean_score']:<15.2f} {s['std_score']:<12.2f} {s['min_score']:<12.2f} {s['max_score']:<12.2f} {s['num_files']:<12}\n")
        
        f.write("-"*80 + "\n")
        f.write(f"\n[MEJOR PARÁMETRO] UMAXNORM = {best_umaxnorm:.2f}\n")
        f.write(f"[SCORE TOTAL PROMEDIO] {best_score:.2f}%\n")
    
    print(f"📄 Resumen guardado en: {summary_file}")
    
    return 0

if __name__ == '__main__':
    exit(main())
