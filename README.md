# QAOA aplicada a logística en Colombia

**Dos demostraciones reproducibles de QAOA ejecutadas en hardware IBM Quantum Heron r2.**

Autor: **Alber Mauricio Marquez Gutierrez** · Versión 1.0.0 · Julio 2026 · Licencia MIT

<!-- Tras publicar en Zenodo, inserte aquí el badge del DOI:
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

---

## Qué es esto

Este repositorio documenta y hace reproducibles dos experimentos de **QAOA (Quantum
Approximate Optimization Algorithm)** aplicados a problemas de logística, ambos
ejecutados en procesadores cuánticos reales de IBM. El patrón metodológico común es la
**transferencia de parámetros**: los ángulos variacionales (γ, β) se optimizan en un
simulador clásico y luego el circuito de parámetros fijos se ejecuta en hardware, lo que
permite medir con limpieza cuánta concentración de probabilidad pierde la solución por
efecto del ruido.

| Proyecto | Problema | Qubits | Hardware | Job ID |
|---|---|---|---|---|
| **Q-COFFEE** | QAOA-MaxCut, 3 nodos (logística cafetera, Suroeste Antioqueño) | 3 | `ibm_marrakesh` | `d918bteu9n7c73am5nmg` |
| **Q-CARGO-ZAM** | RCSPP, selección de ruta China→Medellín (8 rutas) | 3 | `ibm_fez` | `d92tk17d07jc73dvpnt0` |

---

## Alcance honesto (léase antes de citar)

Este registro está redactado con reclamos deliberadamente acotados. Lo que sigue es tan
importante como los resultados.

**Lo que este trabajo SÍ es:**

- Una implementación **reproducible y verificable** del flujo QAOA de transferencia de
  parámetros sobre hardware NISQ real, con línea base clásica exhaustiva y trayectoria de
  optimización completa —incluidos los intentos fallidos documentados—.
- Una medición limpia de la **degradación por ruido** (simulador → hardware) en dos
  backends Heron distintos: 7.18 puntos en Q-COFFEE, 9.16 puntos en Q-CARGO-ZAM.
- Un ejercicio de **modelado de problemas logísticos regionales** (café del Suroeste
  Antioqueño; importación China→Medellín) como instancias de optimización combinatoria.

**Lo que este trabajo NO es:**

- **No es una demostración de ventaja cuántica.** Ambas instancias son de tamaño trivial
  (≤ 8 estados) y se resuelven de forma **exacta y clásica** por enumeración en los
  scripts de la Fase A. El valor es pedagógico y metodológico, no de aceleración
  computacional.
- **No es una primacía verificada.** No se ha completado una revisión sistemática de
  literatura. Existe trabajo previo relevante: QAOA-MaxCut se formula desde
  Farhi, Goldstone & Gutmann (2014), y hay trabajo académico regional sobre optimización
  cuántica. Cualquier reclamo de "primera implementación" debe considerarse **pendiente de
  verificación**.
- **Los datos de Q-CARGO-ZAM son ILUSTRATIVOS.** Están aproximadamente calibrados contra
  tarifas de flete publicadas, pero no constituyen un conjunto de datos operativo validado.

---

## Resultados verificados

Todas las cifras provienen de los archivos `*_resultados.json` incluidos y fueron
generadas por los scripts de este repositorio.

### Q-COFFEE — QAOA-MaxCut (3 nodos)

Partición óptima del grafo de fincas (Jericó, Jardín, Hispania) que maximiza el corte
= 62 km. La solución es **degenerada** (dos bitstrings óptimos: `100` y `011`), como
corresponde a la simetría Z₂ de MaxCut.

| Nivel | Prob(óptimo) |
|---|---|
| Simulador ideal (SamplerV2) | 61.50 % |
| Hardware `ibm_marrakesh` | **54.32 %** |
| Degradación por ruido | 7.18 pts |

### Q-CARGO-ZAM — RCSPP (8 rutas, penalización por deadline)

Ruta óptima factible = ruta 4 (`011`): 1.580 USD, 26 días, cumple el deadline de 28 días.
Parámetros optimizados por statevector exacto con penalización λ = 800.

| Nivel | Prob(óptimo) |
|---|---|
| Statevector exacto | 85.97 % |
| Simulador (SamplerV2) | 85.52 % |
| Hardware `ibm_fez` | **76.37 %** |
| Degradación por ruido | 9.16 pts |

Ambos experimentos conservan el **orden relativo** de los estados principales bajo ruido:
la mezcla despolarizante eleva de forma pareja los estados de baja probabilidad sin
invertir el ranking, lo que explica que la factibilidad se degrade menos que la
concentración.

---

## Estructura del repositorio

```
.
├── README.md                     ← este archivo
├── LICENSE                       ← MIT
├── CITATION.cff                  ← metadatos de cita (formato Citation File Format)
├── .zenodo.json                  ← metadatos para el DOI de Zenodo
├── .gitignore                    ← excluye credenciales/secretos
├── verificar_paquete.py          ← auditor: comprueba integridad y ausencia de secretos
├── q-coffee-maxcut/
│   ├── README.md
│   ├── qcoffee_maxcut_fase_a.py            + _resultados.json   (línea base clásica)
│   ├── qcoffee_maxcut_fase_b.py            + _resultados.json   (QAOA simulador)
│   └── qcoffee_maxcut_fase_c.py            + _resultados.json   (hardware IBM)
└── q-cargo-zam/
    ├── README.md
    ├── qcargo_zam_fase_a.py                + _resultados.json   (línea base clásica)
    ├── qcargo_zam_fase_b_v3.py             + _resultados.json   (QAOA exacto)
    └── qcargo_zam_fase_c.py                + _resultados.json   (hardware IBM)
```

---

## Reproducibilidad

Requisitos: Python 3.10+ y las dependencias de Qiskit.

```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime scipy numpy
```

**Simulador (no requiere cuenta IBM):** ejecute las Fases A y B de cada proyecto. La
optimización usa semilla fija, por lo que la parte exacta es reproducible bit a bit; la
parte muestreada varía dentro del ruido de shots esperado (~0.5 pts a 4096 shots).

**Hardware (requiere cuenta IBM Quantum):** en los scripts `*_fase_c.py`, reemplace
`TOKEN = "TU_TOKEN_AQUI"` por su token de [quantum.ibm.com](https://quantum.ibm.com).
Los scripts **no re-optimizan** en hardware: transfieren los parámetros ya validados y
miden un solo job de 4096 shots.

> ⚠️ **Seguridad:** nunca suba su token a un repositorio. El `.gitignore` incluido bloquea
> archivos de credenciales, pero verifique manualmente antes de cada push.

---

## Procedencia del hardware

Los resultados de hardware son verificables contra los registros de IBM Quantum mediante
los Job ID publicados arriba. Backends: familia IBM Heron r2, 156 qubits físicos.

---

## Cómo citar

Consulte `CITATION.cff`. Tras la publicación en Zenodo, este registro tendrá un DOI
permanente que debe usarse en la cita.

---

## Licencia

MIT — véase `LICENSE`. Puede reutilizar el código libremente citando la fuente.

---

*Registro de prioridad con fecha. Los reclamos de novedad son conservadores por diseño;
una revisión de literatura posterior podría ampliarlos en una versión v1.1 sobre el mismo
DOI conceptual de Zenodo.*
