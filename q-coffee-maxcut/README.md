# Q-COFFEE v1.0 — QAOA-MaxCut

**Partición óptima de fincas cafeteras del Suroeste Antioqueño resuelta con QAOA-MaxCut,
ejecutada en IBM Quantum `ibm_marrakesh`.**

Autor: Alber Mauricio Marquez Gutierrez

## Problema

Tres fincas cafeteras (Jericó, Jardín, Hispania) deben repartirse entre **dos camiones**
para su acopio hacia Andes (Antioquia). Se modela como **MaxCut** sobre el grafo de
distancias inter-finca: cada camión es un lado del corte, y maximizar el corte separa las
fincas más distantes en camiones distintos.

- 3 nodos → **3 qubits**
- Distancias: Google Maps, junio 2026
- Corte máximo óptimo: **62 km** (asignación `[0,0,1]` = Jericó+Jardín / Hispania)
- Solución **degenerada**: los bitstrings `100` y `011` son ambos óptimos (simetría Z₂)

> Nota de formulación: el proyecto **pivotó de TSP/VRP a MaxCut** para alinearse con el
> caso canónico de QAOA sobre hardware NISQ (formulación validada desde Farhi et al., 2014).

## Fases

| Fase | Script | Qué hace |
|---|---|---|
| A | `qcoffee_maxcut_fase_a.py` | Evaluación clásica exhaustiva de los 8 cortes posibles |
| B | `qcoffee_maxcut_fase_b.py` | QAOA p=2 en simulador (COBYLA, 5 restarts) → parámetros |
| C | `qcoffee_maxcut_fase_c.py` | Transferencia de parámetros a hardware IBM (4096 shots) |

## Resultados

| Nivel | Prob(óptimo) | Notas |
|---|---|---|
| Simulador ideal | 61.50 % | amplificación 2.46× vs aleatorio |
| Hardware `ibm_marrakesh` | **54.32 %** | Job ID `d918bteu9n7c73am5nmg` |
| Degradación por ruido | 7.18 pts | — |

Parámetros transferidos: γ = [0.9769, 0.5923], β = [0.8456, 0.5700].

## Alcance

Instancia de tamaño trivial, resuelta exactamente por enumeración en la Fase A. Valor
**pedagógico y metodológico**, no ventaja cuántica. La etiqueta "primera implementación"
que aparece en metadatos internos es un reclamo **no verificado** contra la literatura.

## Ejecutar

```bash
python qcoffee_maxcut_fase_a.py     # clásico
python qcoffee_maxcut_fase_b.py     # simulador
# editar TOKEN en fase_c, luego:
python qcoffee_maxcut_fase_c.py     # hardware IBM
```
