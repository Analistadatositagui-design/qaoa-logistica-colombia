# Q-CARGO-ZAM v1.0 — QAOA-RCSPP

**Selección de ruta de importación China→Medellín bajo restricción de deadline, resuelta
con QAOA de parámetros exactos transferidos, ejecutada en IBM Quantum `ibm_fez`.**

Autor: Alber Mauricio Marquez Gutierrez

## Problema

Se elige **una entre 8 rutas** multimodales (aéreo / marítimo-express / marítimo) para
llevar carga de China a Medellín, minimizando costo **sujeto a un deadline de 28 días**.
Es un **RCSPP** (Resource-Constrained Shortest Path Problem) reducido a selección de ruta.

- 8 rutas → codificación binaria en **3 qubits**
- Ruta óptima factible: **ruta 4** (`011`) — 1.580 USD, 26 días
- Restricción tratada con **penalización** λ por día de exceso sobre el deadline

## Metodología: penalización y optimización exacta

El valor de λ se fijó mediante **barrido exacto por statevector** (λ = 800 gana con
85.97 %), corrigiendo un diagnóstico previo: el cuello de botella no era la penalización
sino el optimizador clásico (COBYLA atrapado en mínimos locales). La relación
λ→concentración **no es monotónica**: tiene un pico cerca de λ≈800 y decae después porque
una penalización enorme comprime la resolución entre las rutas factibles.

| Fase | Script | Qué hace |
|---|---|---|
| A | `qcargo_zam_fase_a.py` | Línea base clásica RCSPP + análisis de sensibilidad |
| B v3 | `qcargo_zam_fase_b_v3.py` | Optimización **exacta** por statevector + barrido λ |
| C | `qcargo_zam_fase_c.py` | Transferencia de parámetros a hardware IBM (4096 shots) |

## Resultados

| Nivel | Prob(óptimo) | Notas |
|---|---|---|
| Statevector exacto | 85.97 % | λ=800, p=2 |
| Simulador (SamplerV2) | 85.52 % | — |
| Hardware `ibm_fez` | **76.37 %** | Job ID `d92tk17d07jc73dvpnt0` |
| Degradación por ruido | 9.16 pts | Prob(factible) hardware 91.21 % |

Parámetros transferidos: γ = [-1.9580, 1.8911], β = [1.5222, 2.3558].

Trayectoria honesta del proyecto (con fallos incluidos):
**26.27 % → 36.33 % → 85.52 %** (simulador) al pasar de COBYLA mal calibrado a la
optimización exacta.

## Alcance de los datos

Los costos y tiempos son **ILUSTRATIVOS**, aproximadamente calibrados contra tarifas de
flete publicadas (China→Colombia, 2026). No es un conjunto de datos operativo validado.
Un análisis Monte Carlo (documentado en el histórico del proyecto) mostró que la ruta 4
sigue siendo óptima ~62 % de las veces bajo perturbación ±20 % en costos y ±15 % en
tiempos; su rival es la ruta 3 si los tránsitos marítimos se aceleran. Para una v2 con
datos reales, el deadline debe fijarse según el tránsito medido del servicio concreto.

## Hallazgo operativo

Existe un "acantilado" de ~3.170 USD entre 25 y 26 días de plazo: un día de flexibilidad
contractual en el punto correcto de la curva vale ~3× el flete.

## Ejecutar

```bash
python qcargo_zam_fase_a.py         # clásico
python qcargo_zam_fase_b_v3.py      # optimización exacta + simulador
# editar TOKEN en fase_c, luego:
python qcargo_zam_fase_c.py         # hardware IBM
```
