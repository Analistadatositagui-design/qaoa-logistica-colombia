"""
Q-COFFEE v1.0 MaxCut - Fase C: Hardware Cuantico Real
Autor: Alber Mauricio Marquez Gutierrez
"""

import json
import time
import numpy as np
from datetime import datetime

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager


AUTOR = "Alber Mauricio Marquez Gutierrez"
TOKEN = "TU_TOKEN_AQUI"


# ============================================================
# CARGAR DATOS DE FASES PREVIAS
# ============================================================
print("=" * 70)
print("  Q-COFFEE v1.0 MaxCut - FASE C: HARDWARE CUANTICO REAL")
print("  Autor: " + AUTOR)
print("=" * 70)

with open('qcoffee_maxcut_fase_a_resultados.json', 'r', encoding='utf-8') as f:
    fase_a = json.load(f)

with open('qcoffee_maxcut_fase_b_resultados.json', 'r', encoding='utf-8') as f:
    fase_b = json.load(f)

FINCAS = fase_a['configuracion']['fincas']
DISTANCIAS = np.array(fase_a['configuracion']['distancias_inter_fincas_km'])
MAXCUT_OPTIMO = fase_a['mejor_maxcut']['maxcut_km']

# Tabla de costos operativos precalculada (evita bucles anidados)
LOOKUP_OPERATIVO = {}
for item in fase_a['evaluacion_exhaustiva']:
    clave = tuple(item['asignacion'])
    LOOKUP_OPERATIVO[clave] = item['costo_operativo_km']

GAMMAS = fase_b['parametros_optimos_para_hardware']['gammas']
BETAS = fase_b['parametros_optimos_para_hardware']['betas']
PROB_SIM = fase_b['descomposicion_probabilidades']['probabilidad_optimo_pct']

N = len(FINCAS)
P = len(GAMMAS)

print("\n[REFERENCIAS]")
print("  Fincas: " + ", ".join(FINCAS))
print("  MaxCut optimo: " + str(MAXCUT_OPTIMO) + " km")
print("  Prob optimo simulador: " + "{:.2f}".format(PROB_SIM) + "%")
print("  Gammas: " + str(np.round(GAMMAS, 4)))
print("  Betas:  " + str(np.round(BETAS, 4)))


# ============================================================
# CONEXION
# ============================================================
print("\n[1/7] Conectando con IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN)
print("      Conexion exitosa")


# ============================================================
# SELECCION DE HARDWARE
# ============================================================
print("\n[2/7] Seleccionando procesador...")
backend = service.least_busy(operational=True, simulator=False)
print("      Hardware: " + backend.name)
print("      Qubits fisicos: " + str(backend.num_qubits))


# ============================================================
# HAMILTONIANO MAXCUT
# ============================================================
print("\n[3/7] Construyendo Hamiltoniano...")
pauli_terms = []
coeffs = []

for i in range(N):
    for j in range(i + 1, N):
        w = DISTANCIAS[i][j]
        s = ['I'] * N
        s[i] = 'Z'
        s[j] = 'Z'
        pauli_terms.append(''.join(reversed(s)))
        coeffs.append(-w / 2)

hamiltonian = SparsePauliOp.from_list(list(zip(pauli_terms, coeffs)))
print("      Terminos Pauli: " + str(len(hamiltonian)))


# ============================================================
# CIRCUITO QAOA CON PARAMETROS FIJOS
# ============================================================
print("\n[4/7] Construyendo circuito QAOA...")
qc = QuantumCircuit(N, N)

for q in range(N):
    qc.h(q)

for layer in range(P):
    g = GAMMAS[layer]
    b = BETAS[layer]
    
    for pauli, coef in zip(hamiltonian.paulis, hamiltonian.coeffs):
        ps = str(pauli)
        zq = [i for i, p in enumerate(reversed(ps)) if p == 'Z']
        if len(zq) == 2:
            qc.cx(zq[0], zq[1])
            qc.rz(2 * float(coef.real) * g, zq[1])
            qc.cx(zq[0], zq[1])
    
    for q in range(N):
        qc.rx(2 * b, q)

qc.measure(range(N), range(N))
print("      Qubits: " + str(qc.num_qubits))
print("      Profundidad: " + str(qc.depth()))


# ============================================================
# TRANSPILACION
# ============================================================
print("\n[5/7] Transpilando para " + backend.name + "...")
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
isa = pm.run(qc)
print("      Profundidad transpilada: " + str(isa.depth()))


# ============================================================
# ENVIO DEL JOB
# ============================================================
SHOTS = 4096
print("\n[6/7] Enviando a hardware real...")
sampler = Sampler(mode=backend)
job = sampler.run([isa], shots=SHOTS)

JOB_ID = job.job_id()
print("      Job ID: " + JOB_ID)
print("      Monitorea en quantum.ibm.com > Cargas de trabajo")
print("      Esperando ejecucion fisica...")

t0 = datetime.now()
result = job.result()
espera = (datetime.now() - t0).total_seconds()
print("      Recibido en " + "{:.1f}".format(espera) + "s")


# ============================================================
# ANALISIS
# ============================================================
print("\n[7/7] ANALISIS HARDWARE vs SIMULADOR")
print("=" * 70)

counts = result[0].data.c.get_counts()


def maxcut(bitstring):
    a = [int(b) for b in reversed(bitstring)]
    t = 0.0
    for i in range(N):
        for j in range(i + 1, N):
            if a[i] != a[j]:
                t += DISTANCIAS[i][j]
    return t


dist = {}
total = 0
for bs, cnt in counts.items():
    mc = maxcut(bs)
    a = [int(b) for b in reversed(bs)]
    dist[bs] = {'count': cnt, 'maxcut': mc, 'asig': a}
    total += cnt

mejor_bs = max(dist, key=lambda b: dist[b]['maxcut'])
mejor_mc = dist[mejor_bs]['maxcut']
mejor_a = dist[mejor_bs]['asig']

shots_opt = sum(d['count'] for b, d in dist.items()
                if abs(d['maxcut'] - MAXCUT_OPTIMO) < 0.1)
prob_hw = 100 * shots_opt / total

ga = [FINCAS[i] for i in range(N) if mejor_a[i] == 0]
gb = [FINCAS[i] for i in range(N) if mejor_a[i] == 1]

print("\n[SOLUCION EN HARDWARE]")
print("  Bitstring: " + mejor_bs)
print("  Asignacion: " + str(mejor_a))
print("  MaxCut: " + "{:.2f}".format(mejor_mc) + " km")
print("  Camion A: " + str(ga))
print("  Camion B: " + str(gb))

print("\n[DISTRIBUCION HARDWARE - TODOS LOS ESTADOS]")
print("  Bitstring   Asignacion   MaxCut   Count   Prob")
print("  " + "-" * 52)
ordenados = sorted(dist.items(), key=lambda x: -x[1]['count'])
for bs, d in ordenados:
    prob = 100 * d['count'] / total
    print("  " + bs + "        " + str(d['asig']).ljust(11) +
          " " + "{:.1f}".format(d['maxcut']).rjust(5) +
          "    " + str(d['count']).rjust(4) +
          "  " + "{:.2f}".format(prob).rjust(5) + "%")

print("\n[COMPARACION]")
print("  Prob optimo simulador: " + "{:.2f}".format(PROB_SIM) + "%")
print("  Prob optimo hardware:  " + "{:.2f}".format(prob_hw) + "%")
degrad = PROB_SIM - prob_hw
print("  Degradacion por ruido: " + "{:.2f}".format(degrad) + "% absoluto")

if prob_hw >= 40:
    veredicto = "EXCELENTE - Hardware mantiene concentracion alta"
elif prob_hw >= 25:
    veredicto = "BUENO - Hardware funciona, ruido moderado"
elif prob_hw >= 12.5:
    veredicto = "ACEPTABLE - Mejor que aleatorio"
else:
    veredicto = "MEJORABLE - Ruido dominante"
print("\n  VEREDICTO: " + veredicto)

# Costo operativo desde lookup (sin recalcular)
costo_op = LOOKUP_OPERATIVO.get(tuple(mejor_a), None)
print("\n[IMPACTO OPERATIVO - ILUSTRATIVO]")
if costo_op is not None:
    print("  Ruta operativa: " + "{:.2f}".format(costo_op) + " km")
    print("  Costo estimado: " + "{:,.0f}".format(costo_op * 5000) + " COP/dia")


# ============================================================
# GUARDAR
# ============================================================
salida = {
    'proyecto': 'Q-COFFEE v1.0 MaxCut',
    'fase': 'C - Hardware Cuantico Real',
    'titulo_formal': (
        'Q-COFFEE v1.0 - Primera implementacion documentada de '
        'QAOA-MaxCut aplicada a la cadena cafetera del Suroeste '
        'Antioqueno, ejecutada en hardware IBM Quantum Heron.'
    ),
    'autor': AUTOR,
    'region': 'Suroeste Antioqueno, Colombia',
    'fecha': datetime.now().isoformat(),
    'hardware': {
        'backend': backend.name,
        'qubits_fisicos': backend.num_qubits,
        'job_id': JOB_ID,
        'shots': SHOTS,
        'tiempo_espera_s': float(espera)
    },
    'parametros_transferidos': {
        'gammas': GAMMAS,
        'betas': BETAS,
        'profundidad_p': P
    },
    'solucion_hardware': {
        'bitstring': mejor_bs,
        'asignacion': mejor_a,
        'maxcut_km': float(mejor_mc),
        'camion_A': ga,
        'camion_B': gb,
        'costo_operativo_km': costo_op
    },
    'distribucion_hardware': [
        {'bitstring': b, 'asignacion': d['asig'],
         'maxcut_km': float(d['maxcut']), 'count': d['count'],
         'prob_pct': float(100 * d['count'] / total)}
        for b, d in ordenados
    ],
    'comparacion': {
        'prob_optimo_simulador_pct': float(PROB_SIM),
        'prob_optimo_hardware_pct': float(prob_hw),
        'degradacion_pct': float(degrad),
        'veredicto': veredicto
    }
}

with open('qcoffee_maxcut_fase_c_resultados.json', 'w', encoding='utf-8') as f:
    json.dump(salida, f, indent=2, ensure_ascii=False)

print("\n[VERIFICACION DEL NOMBRE]")
with open('qcoffee_maxcut_fase_c_resultados.json', 'r', encoding='utf-8') as f:
    c = f.read()
if 'Alber Mauricio' in c and 'Alberto' not in c:
    print("  [OK] Nombre correcto: 'Alber Mauricio Marquez Gutierrez'")
elif 'Alberto' in c:
    print("  [ERROR] Aparece 'Alberto'")

print("\n" + "=" * 70)
print("  Q-COFFEE v1.0 EJECUTADO EN HARDWARE CUANTICO REAL")
print("  Autor: " + AUTOR)
print("  Hardware: " + backend.name + " | Job ID: " + JOB_ID)
print("  Registro: qcoffee_maxcut_fase_c_resultados.json")
print("=" * 70)                               