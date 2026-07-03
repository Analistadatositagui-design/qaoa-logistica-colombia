"""
Q-CARGO-ZAM v1.0 - Fase C: Hardware Cuantico Real (IBM Heron)
China -> Medellin | RCSPP por codificacion binaria (3 qubits)
Autor: Alber Mauricio Marquez Gutierrez

Transferencia de parametros: usa gammas/betas EXACTOS validados
en Fase B v3 (86% de concentracion en simulador). No re-optimiza
en hardware (ahorra minutos IBM). Solo mide 4096 shots.

ANTES DE EJECUTAR:
1) Reemplazar TU_TOKEN_AQUI por el token de quantum.ibm.com
2) Verificar sintaxis:  python -m py_compile qcargo_zam_fase_c.py
3) Verificar token:     Select-String -Path qcargo_zam_fase_c.py -Pattern "TOKEN ="
"""

import json
import numpy as np
from datetime import datetime

from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

AUTOR = "Alber Mauricio Marquez Gutierrez"
PROYECTO = "Q-CARGO-ZAM v1.0"
TOKEN = "TU_TOKEN_AQUI"
SHOTS = 4096


# ============================================================
# CARGAR FASES PREVIAS
# ============================================================
print("=" * 70)
print("  " + PROYECTO + " - FASE C: HARDWARE CUANTICO REAL")
print("  Autor: " + AUTOR)
print("=" * 70)

with open("qcargo_zam_fase_a_resultados.json", "r",
          encoding="utf-8") as f:
    fase_a = json.load(f)

with open("qcargo_zam_fase_b_v3_resultados.json", "r",
          encoding="utf-8") as f:
    fase_b = json.load(f)

RUTAS = fase_a["rutas_factibles"]
T_MAX = fase_a["deadline_experimento_dias"]
NUM_RUTAS = len(RUTAS)
N_QUBITS = fase_b["configuracion_qaoa"]["num_qubits"]
NUM_STATES = 2 ** N_QUBITS
P_LAYERS = fase_b["configuracion_qaoa"]["profundidad_p"]

costos = [r["costo_usd"] for r in RUTAS]
tiempos = [r["tiempo_dias"] for r in RUTAS]
DESCRIPCIONES = [r["descripcion"] for r in RUTAS]

LAM = fase_b["parametros_optimos_para_hardware"]["lambda"]
GAMMAS = fase_b["parametros_optimos_para_hardware"]["gammas"]
BETAS = fase_b["parametros_optimos_para_hardware"]["betas"]
PO_EXACTA = fase_b["prediccion_exacta"]["prob_optimo_pct"]
PO_SIM = fase_b["verificacion_samplerv2"]["prob_optimo_pct"]

ID_OPTIMO = None
for s in range(NUM_RUTAS):
    if tiempos[s] <= T_MAX:
        if ID_OPTIMO is None or costos[s] < costos[ID_OPTIMO]:
            ID_OPTIMO = s
BITS_OPT = format(ID_OPTIMO, "0" + str(N_QUBITS) + "b")

print("\n[REFERENCIAS]")
print("  Rutas: " + str(NUM_RUTAS) + " | Qubits: " + str(N_QUBITS))
print("  Deadline: " + str(T_MAX) + " dias")
print("  Optimo RCSPP: ruta " + str(ID_OPTIMO + 1) +
      " (bits " + BITS_OPT + ", $" + str(costos[ID_OPTIMO]) + ")")
print("  LAMBDA validado: " + "{:.0f}".format(LAM))
print("  Prob(optimo) exacta:    " + "{:.2f}".format(PO_EXACTA) + "%")
print("  Prob(optimo) simulador: " + "{:.2f}".format(PO_SIM) + "%")
print("  Gammas: " + str(np.round(GAMMAS, 4).tolist()))
print("  Betas:  " + str(np.round(BETAS, 4).tolist()))


# ============================================================
# COSTO EFECTIVO Y HAMILTONIANO
# ============================================================
eff = []
for s in range(NUM_STATES):
    if s < NUM_RUTAS:
        exceso = max(0, tiempos[s] - T_MAX)
        eff.append(costos[s] + LAM * exceso)
    else:
        eff.append(max(costos) + LAM * 100)
e = np.array(eff, dtype=float)
ehat = (e - e.min()) / (e.max() - e.min()) * 2.0


def pauli_terms_from_costs(vec, nq):
    ns = len(vec)
    out = []
    for subset in range(1, ns):
        coeff = 0.0
        for state in range(ns):
            bits = bin(subset & state).count("1")
            sign = 1.0 if (bits % 2 == 0) else -1.0
            coeff += vec[state] * sign
        coeff /= ns
        if abs(coeff) < 1e-9:
            continue
        pauli = ["I"] * nq
        for q in range(nq):
            if (subset >> q) & 1:
                pauli[q] = "Z"
        out.append(("".join(reversed(pauli)), coeff))
    return out


TERMS = pauli_terms_from_costs(ehat.tolist(), N_QUBITS)


def z_positions(pstr, nq):
    out = []
    for q in range(nq):
        if pstr[nq - 1 - q] == "Z":
            out.append(q)
    return out


def apply_zterm(circ, qubits, angle):
    if len(qubits) == 1:
        circ.rz(2 * angle, qubits[0])
        return
    k = len(qubits)
    for i in range(k - 1):
        circ.cx(qubits[i], qubits[i + 1])
    circ.rz(2 * angle, qubits[-1])
    for i in range(k - 1, 0, -1):
        circ.cx(qubits[i - 1], qubits[i])


print("\n[1/6] Construyendo circuito QAOA (parametros fijos)...")
qc = QuantumCircuit(N_QUBITS, N_QUBITS)
for q in range(N_QUBITS):
    qc.h(q)
for layer in range(P_LAYERS):
    g = GAMMAS[layer]
    b = BETAS[layer]
    for (pstr, coeff) in TERMS:
        apply_zterm(qc, z_positions(pstr, N_QUBITS), g * coeff)
    for q in range(N_QUBITS):
        qc.rx(2 * b, q)
qc.measure(range(N_QUBITS), range(N_QUBITS))
print("      Qubits: " + str(qc.num_qubits) +
      " | Profundidad: " + str(qc.depth()))


# ============================================================
# CONEXION Y HARDWARE
# ============================================================
print("\n[2/6] Conectando con IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_quantum_platform",
                               token=TOKEN)
print("      Conexion exitosa")

print("\n[3/6] Seleccionando procesador...")
backend = service.least_busy(operational=True, simulator=False)
print("      Hardware: " + backend.name)
print("      Qubits fisicos: " + str(backend.num_qubits))

print("\n[4/6] Transpilando para " + backend.name + "...")
pm = generate_preset_pass_manager(backend=backend,
                                  optimization_level=1)
isa = pm.run(qc)
print("      Profundidad transpilada: " + str(isa.depth()))


# ============================================================
# ENVIO
# ============================================================
print("\n[5/6] Enviando a hardware real (" + str(SHOTS) + " shots)...")
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
print("\n[6/6] ANALISIS: HARDWARE vs SIMULADOR vs EXACTO")
print("=" * 70)

counts = result[0].data.c.get_counts()
dist = {}
total = 0
for bs, cnt in counts.items():
    x = int(bs, 2)
    dist[x] = dist.get(x, 0) + cnt
    total += cnt

shots_opt = dist.get(ID_OPTIMO, 0)
po_hw = 100.0 * shots_opt / total
shots_fact = 0
for i in range(NUM_RUTAS):
    if tiempos[i] <= T_MAX:
        shots_fact += dist.get(i, 0)
pf_hw = 100.0 * shots_fact / total

mejor_estado = max(dist, key=lambda x: dist[x])
acierto = (mejor_estado == ID_OPTIMO)

print("\n[SOLUCION EN HARDWARE]")
print("  Estado mas medido: " +
      format(mejor_estado, "0" + str(N_QUBITS) + "b") +
      " = ruta " + str(mejor_estado + 1))
if mejor_estado < NUM_RUTAS:
    print("  Ruta: " + DESCRIPCIONES[mejor_estado])
    print("  Costo: $" + str(costos[mejor_estado]) +
          " / " + str(tiempos[mejor_estado]) + " dias")
print("  Coincide con optimo RCSPP: " + ("SI" if acierto else "NO"))

print("\n[DISTRIBUCION HARDWARE]")
print("  Bits  Ruta  Costo(USD)  T(d)  Count   Prob")
print("  " + "-" * 50)
orden = sorted(range(NUM_STATES), key=lambda x: -dist.get(x, 0))
for x in orden:
    cnt = dist.get(x, 0)
    prob = 100.0 * cnt / total
    bits = format(x, "0" + str(N_QUBITS) + "b")
    if x < NUM_RUTAS:
        c = str(costos[x])
        t = str(tiempos[x])
        viola = " (viola)" if tiempos[x] > T_MAX else ""
    else:
        c, t, viola = "PAD", "-", ""
    marca = " <--OPT" if x == ID_OPTIMO else viola
    print("  " + bits + "   " + str(x + 1).rjust(3) + "   " +
          c.rjust(7) + "  " + t.rjust(4) + "  " +
          str(cnt).rjust(5) + "  " +
          "{:.2f}".format(prob).rjust(5) + "%" + marca)

print("\n[COMPARACION TRIPLE]")
print("  Prob(optimo) exacta:     " + "{:.2f}".format(PO_EXACTA) + "%")
print("  Prob(optimo) simulador:  " + "{:.2f}".format(PO_SIM) + "%")
print("  Prob(optimo) HARDWARE:   " + "{:.2f}".format(po_hw) + "%")
degrad = PO_SIM - po_hw
print("  Degradacion por ruido:   " + "{:.2f}".format(degrad) +
      "% absoluto")
print("  Prob(factible) hardware: " + "{:.2f}".format(pf_hw) + "%")

if acierto and po_hw >= 60:
    veredicto = "EXCELENTE - Hardware mantiene concentracion alta"
elif acierto and po_hw >= 40:
    veredicto = "BUENO - Hardware funciona, ruido moderado"
elif acierto:
    veredicto = "ACEPTABLE - Optimo dominante bajo ruido"
else:
    veredicto = "REVISAR - Ruido altero el estado dominante"
print("\n  VEREDICTO: " + veredicto)


# ============================================================
# GUARDAR
# ============================================================
salida = {
    "proyecto": PROYECTO,
    "fase": "C - Hardware Cuantico Real",
    "titulo_formal": (
        "Q-CARGO-ZAM v1.0 - RCSPP multimodal China-Medellin "
        "resuelto con QAOA de parametros exactos transferidos, "
        "ejecutado en hardware IBM Quantum Heron."
    ),
    "autor": AUTOR,
    "fecha": datetime.now().isoformat(),
    "hardware": {
        "backend": backend.name,
        "qubits_fisicos": backend.num_qubits,
        "job_id": JOB_ID,
        "shots": SHOTS,
        "tiempo_espera_s": float(espera),
        "profundidad_transpilada": int(isa.depth())
    },
    "parametros_transferidos": {
        "lambda": float(LAM),
        "gammas": GAMMAS,
        "betas": BETAS,
        "profundidad_p": P_LAYERS,
        "origen": "Fase B v3 (optimizacion exacta statevector)"
    },
    "solucion_hardware": {
        "estado_bits": format(mejor_estado,
                              "0" + str(N_QUBITS) + "b"),
        "ruta_id": int(mejor_estado + 1),
        "coincide_con_optimo": bool(acierto)
    },
    "comparacion_triple": {
        "prob_optimo_exacta_pct": float(PO_EXACTA),
        "prob_optimo_simulador_pct": float(PO_SIM),
        "prob_optimo_hardware_pct": float(po_hw),
        "degradacion_pct": float(degrad),
        "prob_factible_hardware_pct": float(pf_hw)
    },
    "distribucion_hardware": [
        {"ruta_id": int(x + 1),
         "bits": format(x, "0" + str(N_QUBITS) + "b"),
         "count": int(dist.get(x, 0)),
         "prob_pct": float(100.0 * dist.get(x, 0) / total)}
        for x in orden
    ],
    "veredicto": veredicto
}

ARCHIVO = "qcargo_zam_fase_c_resultados.json"
with open(ARCHIVO, "w", encoding="utf-8") as f:
    json.dump(salida, f, indent=2, ensure_ascii=False)

print("\n[VERIFICACION DEL NOMBRE Y PROYECTO]")
with open(ARCHIVO, "r", encoding="utf-8") as f:
    contenido = f.read()
if "Alber Mauricio" in contenido and "Alberto" not in contenido:
    print("  [OK] Nombre correcto: 'Alber Mauricio Marquez Gutierrez'")
elif "Alberto" in contenido:
    print("  [ERROR] Aparece 'Alberto'")
if "Q-CARGO-ZAM v1.0" in contenido:
    print("  [OK] Proyecto correcto: 'Q-CARGO-ZAM v1.0'")
else:
    print("  [ERROR] Proyecto no encontrado")

print("\n" + "=" * 70)
print("  " + PROYECTO + " EJECUTADO EN HARDWARE CUANTICO REAL")
print("  Autor: " + AUTOR)
print("  Hardware: " + backend.name + " | Job ID: " + JOB_ID)
print("  Registro: " + ARCHIVO)
print("=" * 70)
                               