"""
Q-COFFEE v1.0 MaxCut - Fase B: QAOA con 3 Qubits
Autor: Alber Mauricio Marquez Gutierrez

Implementacion canonica QAOA-MaxCut sobre grafo de 3 fincas cafeteras.
Esta formulacion es la mas validada en la literatura cuantica desde Farhi 2014.
"""

import numpy as np
import json
from datetime import datetime

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.primitives import SamplerV2
from scipy.optimize import minimize


AUTOR = "Alber Mauricio Marquez Gutierrez"


# ============================================================
# CARGAR DATOS DE FASE A MAXCUT
# ============================================================
print("=" * 70)
print("  Q-COFFEE v1.0 MaxCut - FASE B: QAOA EN SIMULADOR IDEAL")
print("  Autor: " + AUTOR)
print("=" * 70)

with open('qcoffee_maxcut_fase_a_resultados.json', 'r', encoding='utf-8') as f:
    fase_a = json.load(f)

FINCAS = fase_a['configuracion']['fincas']
DISTANCIAS_FINCAS = np.array(fase_a['configuracion']['distancias_inter_fincas_km'])
MEJOR_MAXCUT_KM = fase_a['mejor_maxcut']['maxcut_km']
ASIGNACION_OPTIMA = fase_a['mejor_maxcut']['asignacion']

N = len(FINCAS)
print("\n[REFERENCIAS DE FASE A]")
print("  MaxCut optimo: " + str(MEJOR_MAXCUT_KM) + " km cortados")
print("  Asignacion optima: " + str(ASIGNACION_OPTIMA))
print("  Qubits requeridos: " + str(N))


# ============================================================
# HAMILTONIANO DE MAXCUT (formulacion canonica)
# H_C = sum_{(i,j) in E} (w_ij / 2) * (1 - Z_i * Z_j)
# Eliminamos la constante y maximizamos sum_{(i,j)} -(w_ij/2) * Z_i * Z_j
# Para QAOA, minimizamos -H_C
# ============================================================
print("\n[1/6] Construyendo Hamiltoniano de MaxCut...")

pauli_terms = []
coeffs = []
offset = 0.0

for i in range(N):
    for j in range(i + 1, N):
        w_ij = DISTANCIAS_FINCAS[i][j]
        # Termino: -w_ij/2 * Z_i * Z_j  (para minimizar, equivale a maximizar maxcut)
        pauli_str = ['I'] * N
        pauli_str[i] = 'Z'
        pauli_str[j] = 'Z'
        pauli_terms.append(''.join(reversed(pauli_str)))
        coeffs.append(-w_ij / 2)
        offset += w_ij / 2

hamiltonian = SparsePauliOp.from_list(list(zip(pauli_terms, coeffs)))
print("      Terminos Pauli: " + str(len(hamiltonian)))
print("      Offset constante: " + "{:.2f}".format(offset))


# ============================================================
# CIRCUITO QAOA
# ============================================================
print("\n[2/6] Construyendo circuito QAOA...")

P_LAYERS = 2

def construir_qaoa(p_layers):
    qc = QuantumCircuit(N, N)
    
    # Estado inicial: superposicion uniforme
    for q in range(N):
        qc.h(q)
    
    gammas = [Parameter('g' + str(i)) for i in range(p_layers)]
    betas = [Parameter('b' + str(i)) for i in range(p_layers)]
    
    for layer in range(p_layers):
        # Operador de costo: exp(-i * gamma * H_C)
        for pauli, coef in zip(hamiltonian.paulis, hamiltonian.coeffs):
            pauli_str = str(pauli)
            qubits_z = [i for i, p in enumerate(reversed(pauli_str)) if p == 'Z']
            
            if len(qubits_z) == 2:
                qc.cx(qubits_z[0], qubits_z[1])
                qc.rz(2 * float(coef.real) * gammas[layer], qubits_z[1])
                qc.cx(qubits_z[0], qubits_z[1])
        
        # Operador de mezcla: exp(-i * beta * sum X_i)
        for q in range(N):
            qc.rx(2 * betas[layer], q)
    
    qc.measure(range(N), range(N))
    return qc, gammas, betas


circuit, gammas, betas = construir_qaoa(P_LAYERS)
print("      Qubits: " + str(circuit.num_qubits))
print("      Profundidad: " + str(circuit.depth()))
print("      P-layers: " + str(P_LAYERS))


# ============================================================
# FUNCIONES DE EVALUACION
# ============================================================
sampler = SamplerV2()
NUM_SHOTS_OPT = 1024
NUM_SHOTS_FINAL = 4096


def costo_maxcut(bitstring):
    """Calcula el corte de MaxCut para una asignacion binaria."""
    asignacion = [int(b) for b in reversed(bitstring)]
    total = 0.0
    for i in range(N):
        for j in range(i + 1, N):
            if asignacion[i] != asignacion[j]:
                total += DISTANCIAS_FINCAS[i][j]
    return total


def funcion_objetivo(params, num_shots=NUM_SHOTS_OPT):
    """QAOA minimiza esto, asi que negamos el maxcut (queremos maximizar)."""
    g_vals = params[:P_LAYERS]
    b_vals = params[P_LAYERS:]
    
    bound_circuit = circuit.assign_parameters(
        {gammas[i]: g_vals[i] for i in range(P_LAYERS)} |
        {betas[i]: b_vals[i] for i in range(P_LAYERS)}
    )
    
    job = sampler.run([bound_circuit], shots=num_shots)
    result = job.result()
    counts = result[0].data.c.get_counts()
    
    # Maxcut promedio (queremos maximizarlo)
    maxcut_promedio = 0
    for bitstring, count in counts.items():
        maxcut_promedio += costo_maxcut(bitstring) * count
    maxcut_promedio /= num_shots
    
    # Retornamos el negativo porque scipy minimiza
    return -maxcut_promedio


# ============================================================
# WARM-STARTS DE LITERATURA
# ============================================================
WARM_STARTS = [
    np.array([0.4, 0.8, 0.6, 0.3]),
    np.array([0.5, 1.0, 0.5, 0.25]),
    np.array([0.3, 0.6, 0.8, 0.4]),
    np.array([0.7, 0.4, 0.5, 0.6]),
    np.array([0.2, 1.2, 0.9, 0.3])
]


# ============================================================
# MULTI-RESTART
# ============================================================
print("\n[3/6] Ejecutando 5 restarts QAOA-MaxCut...")
print("      Shots por evaluacion: " + str(NUM_SHOTS_OPT))
print("")

NUM_RESTARTS = 5
restarts_results = []
fecha_inicio_total = datetime.now()

for restart_idx in range(NUM_RESTARTS):
    print("  --- Restart " + str(restart_idx + 1) + "/" + str(NUM_RESTARTS) + " ---")
    
    params_iniciales = WARM_STARTS[restart_idx].copy()
    print("    Warm-start: " + str(np.round(params_iniciales, 3)))
    
    fecha_inicio = datetime.now()
    
    resultado_opt = minimize(
        funcion_objetivo,
        params_iniciales,
        method='COBYLA',
        options={'maxiter': 100, 'rhobeg': 0.3, 'disp': False}
    )
    
    duracion = (datetime.now() - fecha_inicio).total_seconds()
    maxcut_alcanzado = -resultado_opt.fun
    
    print("    Iteraciones: " + str(resultado_opt.nfev) + 
          " | MaxCut promedio alcanzado: " + 
          "{:.2f}".format(maxcut_alcanzado) + " km" +
          " | Tiempo: " + "{:.1f}".format(duracion) + "s")
    
    restarts_results.append({
        'restart_idx': restart_idx,
        'params_iniciales': params_iniciales.tolist(),
        'params_finales': resultado_opt.x.tolist(),
        'maxcut_alcanzado': float(maxcut_alcanzado),
        'iteraciones': int(resultado_opt.nfev),
        'duracion_s': duracion
    })
    print("")

duracion_total = (datetime.now() - fecha_inicio_total).total_seconds()
print("  TIEMPO TOTAL: " + "{:.1f}".format(duracion_total) + "s")


# ============================================================
# MEJOR RESTART
# ============================================================
print("\n[4/6] Seleccionando mejor configuracion...")

mejor_restart = max(restarts_results, key=lambda r: r['maxcut_alcanzado'])
print("      Mejor restart: #" + str(mejor_restart['restart_idx'] + 1))
print("      MaxCut promedio: " + 
      "{:.2f}".format(mejor_restart['maxcut_alcanzado']) + " km")


# ============================================================
# EXTRACCION FINAL
# ============================================================
print("\n[5/6] Extraccion final con " + str(NUM_SHOTS_FINAL) + " shots...")

params_opt = np.array(mejor_restart['params_finales'])
bound_circuit = circuit.assign_parameters(
    {gammas[i]: params_opt[i] for i in range(P_LAYERS)} |
    {betas[i]: params_opt[P_LAYERS + i] for i in range(P_LAYERS)}
)

job = sampler.run([bound_circuit], shots=NUM_SHOTS_FINAL)
result = job.result()
counts = result[0].data.c.get_counts()

# Analizar distribucion completa
distribuciones = {}
for bitstring, count in counts.items():
    maxcut = costo_maxcut(bitstring)
    asignacion = [int(b) for b in reversed(bitstring)]
    distribuciones[bitstring] = {
        'count': count,
        'maxcut': maxcut,
        'asignacion': asignacion
    }

# Mejor solucion (max MaxCut)
mejor_bitstring = max(distribuciones, key=lambda b: distribuciones[b]['maxcut'])
mejor_maxcut = distribuciones[mejor_bitstring]['maxcut']
mejor_asignacion = distribuciones[mejor_bitstring]['asignacion']


# ============================================================
# REPORTE FINAL
# ============================================================
print("\n[6/6] REPORTE FINAL Q-COFFEE MAXCUT QAOA")
print("=" * 70)

print("\n[SOLUCION QAOA-MAXCUT]")
print("  Mejor bitstring: " + mejor_bitstring)
print("  Asignacion: " + str(mejor_asignacion))
print("  MaxCut alcanzado: " + "{:.2f}".format(mejor_maxcut) + " km")

# Describir la asignacion
grupo_a = [FINCAS[i] for i in range(N) if mejor_asignacion[i] == 0]
grupo_b = [FINCAS[i] for i in range(N) if mejor_asignacion[i] == 1]
print("  Camion A: " + str(grupo_a))
print("  Camion B: " + str(grupo_b))


print("\n[COMPARACION CON OPTIMO]")
print("  MaxCut optimo (fuerza bruta): " + "{:.2f}".format(MEJOR_MAXCUT_KM) + " km")
print("  MaxCut QAOA:                  " + "{:.2f}".format(mejor_maxcut) + " km")

brecha = MEJOR_MAXCUT_KM - mejor_maxcut
brecha_pct = (brecha / MEJOR_MAXCUT_KM) * 100 if MEJOR_MAXCUT_KM > 0 else 0

print("  Brecha:                       " + "{:.2f}".format(brecha) + " km (" + 
      "{:.2f}".format(brecha_pct) + "%)")


# ============================================================
# DESCOMPOSICION DE PROBABILIDADES COMPLETA
# (Para 3 qubits son solo 8 estados - mostramos TODOS)
# ============================================================
print("\n[DESCOMPOSICION DE PROBABILIDADES - TODOS LOS 8 ESTADOS]")
print("  Bitstring   Asignacion   MaxCut(km)   Count   Probabilidad")
print("  " + "-" * 60)

todos_ordenados = sorted(distribuciones.items(), 
                         key=lambda x: -x[1]['count'])

for bs, d in todos_ordenados:
    prob = 100 * d['count'] / NUM_SHOTS_FINAL
    asig_str = str(d['asignacion'])
    print("  " + bs + "        " + asig_str.ljust(11) + 
          "  " + "{:.1f}".format(d['maxcut']).rjust(6) + 
          "      " + str(d['count']).rjust(4) + 
          "    " + "{:.2f}".format(prob).rjust(5) + "%")


# Concentracion en optimo
shots_optimo = sum(d['count'] for b, d in distribuciones.items() 
                   if abs(d['maxcut'] - MEJOR_MAXCUT_KM) < 0.1)
prob_optimo = 100 * shots_optimo / NUM_SHOTS_FINAL

print("\n[CONCENTRACION EN EL OPTIMO]")
print("  Shots en el optimo (" + str(MEJOR_MAXCUT_KM) + " km): " + 
      str(shots_optimo) + "/" + str(NUM_SHOTS_FINAL))
print("  Probabilidad: " + "{:.2f}".format(prob_optimo) + "%")
print("  vs aleatorio uniforme: " + "{:.2f}".format(100 * 2 / 8) + "%")
print("  (2 asignaciones optimas degeneradas sobre 8 totales = 25%)")

factor = prob_optimo / 25.0
print("  Factor de amplificacion vs aleatorio: " + 
      "{:.2f}".format(factor) + "x")


# Veredicto
if mejor_maxcut >= MEJOR_MAXCUT_KM * 0.95 and prob_optimo > 40:
    veredicto = "EXCELENTE - QAOA encuentra y concentra el optimo"
elif mejor_maxcut >= MEJOR_MAXCUT_KM * 0.95:
    veredicto = "BUENO - QAOA encuentra el optimo (probabilidad baja)"
elif mejor_maxcut >= MEJOR_MAXCUT_KM * 0.85:
    veredicto = "ACEPTABLE - QAOA dentro del 15% del optimo"
else:
    veredicto = "MEJORABLE - QAOA lejos del optimo"

print("\n  VEREDICTO: " + veredicto)


# ============================================================
# GUARDAR RESULTADOS
# ============================================================
resultados_b = {
    'proyecto': 'Q-COFFEE v1.0 MaxCut',
    'fase': 'B - QAOA-MaxCut Simulador Ideal',
    'autor': AUTOR,
    'region': 'Suroeste Antioqueno, Colombia',
    'fecha': datetime.now().isoformat(),
    'configuracion_qaoa': {
        'profundidad_p': P_LAYERS,
        'num_qubits': N,
        'shots_optimizacion': NUM_SHOTS_OPT,
        'shots_extraccion_final': NUM_SHOTS_FINAL,
        'num_restarts': NUM_RESTARTS,
        'iteraciones_cobyla_max': 100,
        'hardware': 'qiskit_aer.primitives.SamplerV2 (simulador ideal)'
    },
    'restarts_completos': restarts_results,
    'mejor_restart': mejor_restart,
    'parametros_optimos_para_hardware': {
        'gammas': [float(p) for p in params_opt[:P_LAYERS]],
        'betas': [float(p) for p in params_opt[P_LAYERS:]]
    },
    'solucion_qaoa': {
        'bitstring': mejor_bitstring,
        'asignacion': mejor_asignacion,
        'maxcut_km': float(mejor_maxcut),
        'camion_A': grupo_a,
        'camion_B': grupo_b
    },
    'comparacion': {
        'maxcut_optimo_km': MEJOR_MAXCUT_KM,
        'maxcut_qaoa_km': float(mejor_maxcut),
        'brecha_pct': float(brecha_pct)
    },
    'descomposicion_probabilidades': {
        'todos_estados': [
            {'bitstring': b, 'asignacion': d['asignacion'],
             'maxcut_km': float(d['maxcut']), 'count': d['count'],
             'probabilidad_pct': float(100 * d['count'] / NUM_SHOTS_FINAL)}
            for b, d in todos_ordenados
        ],
        'shots_en_optimo': shots_optimo,
        'probabilidad_optimo_pct': float(prob_optimo),
        'factor_amplificacion_vs_aleatorio': float(factor)
    },
    'tiempo_total_segundos': float(duracion_total),
    'veredicto': veredicto
}

with open('qcoffee_maxcut_fase_b_resultados.json', 'w', encoding='utf-8') as f:
    json.dump(resultados_b, f, indent=2, ensure_ascii=False)


# Verificacion del nombre
print("\n[VERIFICACION DEL NOMBRE EN EL JSON]")
with open('qcoffee_maxcut_fase_b_resultados.json', 'r', encoding='utf-8') as f:
    contenido = f.read()
if 'Alber Mauricio' in contenido and 'Alberto' not in contenido:
    print("  [OK] Nombre correcto: 'Alber Mauricio Marquez Gutierrez'")
elif 'Alberto' in contenido:
    print("  [ERROR] Aparece 'Alberto'")


print("\n[REGISTRO]")
print("  Resultados guardados en: qcoffee_maxcut_fase_b_resultados.json")
print("  Listo para Fase C (hardware real ibm_kingston)")
print("=" * 70)