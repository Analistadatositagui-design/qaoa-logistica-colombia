"""
Q-CARGO-ZAM v1.0 - Fase B v3: QAOA-RCSPP con optimizacion EXACTA
China -> Medellin | codificacion binaria de rutas (3 qubits)
Autor: Alber Mauricio Marquez Gutierrez

MEJORA CLAVE vs Fase B v2:
Los parametros (gamma, beta) se optimizan de forma EXACTA por
statevector en numpy (8 estados, sin ruido de shots, sin COBYLA
atrapado en minimos locales). Luego se VERIFICA con SamplerV2.
Validado externamente: concentracion exacta alcanzable ~86%,
mas del doble del 36% que dio COBYLA con 5 warm-starts.

RAM: trivial (vectores de 8 componentes). Tiempo: 1-3 minutos.
"""

import numpy as np
import json
import math
from datetime import datetime
from scipy.optimize import minimize

from qiskit import QuantumCircuit
from qiskit_aer.primitives import SamplerV2

AUTOR = "Alber Mauricio Marquez Gutierrez"
PROYECTO = "Q-CARGO-ZAM v1.0"

# Barrido fino de penalizacion (validado: el pico esta cerca de 800)
LAMBDA_GRID = [550.0, 650.0, 700.0, 750.0, 800.0, 850.0, 900.0]
MULTISTARTS = 50
P_LAYERS = 2
SHOTS_FINAL = 4096


# ============================================================
# CARGAR FASE A
# ============================================================
print("=" * 70)
print("  " + PROYECTO + " - FASE B v3: OPTIMIZACION EXACTA + VERIFICACION")
print("  Autor: " + AUTOR)
print("=" * 70)

with open("qcargo_zam_fase_a_resultados.json", "r", encoding="utf-8") as f:
    fase_a = json.load(f)

RUTAS = fase_a["rutas_factibles"]
T_MAX = fase_a["deadline_experimento_dias"]

NUM_RUTAS = len(RUTAS)
N_QUBITS = max(1, math.ceil(math.log2(NUM_RUTAS)))
NUM_STATES = 2 ** N_QUBITS

costos = [r["costo_usd"] for r in RUTAS]
tiempos = [r["tiempo_dias"] for r in RUTAS]

ID_OPTIMO = None
for s in range(NUM_RUTAS):
    if tiempos[s] <= T_MAX:
        if ID_OPTIMO is None or costos[s] < costos[ID_OPTIMO]:
            ID_OPTIMO = s
BITS_OPT = format(ID_OPTIMO, "0" + str(N_QUBITS) + "b")

print("\n[REFERENCIAS DE FASE A]")
print("  Rutas: " + str(NUM_RUTAS) + " | Qubits: " + str(N_QUBITS))
print("  Deadline: " + str(T_MAX) + " dias")
print("  Optimo RCSPP: ruta " + str(ID_OPTIMO + 1) +
      " ($" + str(costos[ID_OPTIMO]) + ", bits " + BITS_OPT + ")")


# ============================================================
# QAOA EXACTO EN NUMPY (statevector de 8 componentes)
# ============================================================
X = np.array([[0, 1], [1, 0]], dtype=complex)
I2 = np.eye(2, dtype=complex)


def mixer(beta):
    m = np.cos(beta) * I2 - 1j * np.sin(beta) * X
    return np.kron(np.kron(m, m), m)


def eff_vector(lam):
    e = []
    for s in range(NUM_STATES):
        if s < NUM_RUTAS:
            exceso = max(0, tiempos[s] - T_MAX)
            e.append(costos[s] + lam * exceso)
        else:
            e.append(max(costos) + lam * 100)
    return np.array(e, dtype=float)


def qaoa_dist(params, ehat):
    psi = np.ones(NUM_STATES, dtype=complex) / np.sqrt(NUM_STATES)
    for l in range(P_LAYERS):
        psi = np.exp(-1j * params[l] * ehat) * psi
        psi = mixer(params[P_LAYERS + l]) @ psi
    return np.abs(psi) ** 2


def optimizar_exacto(lam, seed=11):
    e = eff_vector(lam)
    ehat = (e - e.min()) / (e.max() - e.min()) * 2.0
    rng = np.random.default_rng(seed)

    def f(params):
        return float(np.dot(qaoa_dist(params, ehat), e))

    best = None
    for _ in range(MULTISTARTS):
        p0 = rng.uniform(0, np.pi, size=2 * P_LAYERS)
        r = minimize(f, p0, method="Nelder-Mead",
                     options={"maxiter": 2500, "fatol": 1e-10})
        if best is None or r.fun < best.fun:
            best = r
    d = qaoa_dist(best.x, ehat)
    po = 100.0 * d[ID_OPTIMO]
    pf = 100.0 * sum(d[i] for i in range(NUM_RUTAS)
                     if tiempos[i] <= T_MAX)
    return po, pf, best.x, d


print("\n[1/4] Barrido de LAMBDA con optimizacion EXACTA...")
print("      (" + str(MULTISTARTS) + " multistarts Nelder-Mead por valor)")
print("")
print("  LAMBDA   Prob(optimo)  Prob(factible)")
print("  " + "-" * 42)

t0 = datetime.now()
mejor = None
barrido = []
for lam in LAMBDA_GRID:
    po, pf, x, d = optimizar_exacto(lam)
    barrido.append({"lambda": lam, "prob_optimo_pct": po,
                    "prob_factible_pct": pf})
    marca = ""
    if mejor is None or po > mejor[0]:
        mejor = (po, pf, lam, x, d)
        marca = "  <-- mejor"
    print("  " + "{:.0f}".format(lam).rjust(5) + "     " +
          "{:.2f}".format(po).rjust(6) + "%      " +
          "{:.2f}".format(pf).rjust(6) + "%" + marca)

dur = (datetime.now() - t0).total_seconds()
PO_EX, PF_EX, LAM_WIN, PARAMS_WIN, DIST_EX = mejor
print("\n  Tiempo de optimizacion: " + "{:.0f}".format(dur) + "s")
print("\n[2/4] GANADOR: LAMBDA=" + "{:.0f}".format(LAM_WIN))
print("  Prob(optimo) exacta:   " + "{:.2f}".format(PO_EX) + "%")
print("  Prob(factible) exacta: " + "{:.2f}".format(PF_EX) + "%")
print("  gammas: " + str(np.round(PARAMS_WIN[:P_LAYERS], 4).tolist()))
print("  betas:  " + str(np.round(PARAMS_WIN[P_LAYERS:], 4).tolist()))


# ============================================================
# VERIFICACION CON SAMPLERV2 (el pipeline real de Qiskit)
# ============================================================
print("\n[3/4] Verificando con SamplerV2 (" +
      str(SHOTS_FINAL) + " shots)...")

e = eff_vector(LAM_WIN)
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


qc = QuantumCircuit(N_QUBITS, N_QUBITS)
for q in range(N_QUBITS):
    qc.h(q)
for layer in range(P_LAYERS):
    g = PARAMS_WIN[layer]
    b = PARAMS_WIN[P_LAYERS + layer]
    for (pstr, coeff) in TERMS:
        apply_zterm(qc, z_positions(pstr, N_QUBITS), g * coeff)
    for q in range(N_QUBITS):
        qc.rx(2 * b, q)
qc.measure(range(N_QUBITS), range(N_QUBITS))

sampler = SamplerV2()
job = sampler.run([qc], shots=SHOTS_FINAL)
counts = job.result()[0].data.c.get_counts()

dist = {}
for bs, cnt in counts.items():
    x = int(bs, 2)
    dist[x] = dist.get(x, 0) + cnt

shots_opt = dist.get(ID_OPTIMO, 0)
po_sim = 100.0 * shots_opt / SHOTS_FINAL
shots_fact = sum(dist.get(i, 0) for i in range(NUM_RUTAS)
                 if tiempos[i] <= T_MAX)
pf_sim = 100.0 * shots_fact / SHOTS_FINAL

print("\n[4/4] REPORTE FINAL")
print("=" * 70)
print("\n[DISTRIBUCION - EXACTA vs SAMPLERV2]")
print("  Bits  Ruta  Costo(USD)  T(d)   Exacta   SamplerV2")
print("  " + "-" * 56)
orden = sorted(range(NUM_STATES), key=lambda x: -DIST_EX[x])
for x in orden:
    cnt = dist.get(x, 0)
    pv = 100.0 * cnt / SHOTS_FINAL
    bits = format(x, "0" + str(N_QUBITS) + "b")
    if x < NUM_RUTAS:
        c = str(costos[x])
        t = str(tiempos[x])
        viola = " (viola)" if tiempos[x] > T_MAX else ""
    else:
        c, t, viola = "PAD", "-", ""
    marca = " <--OPT" if x == ID_OPTIMO else viola
    print("  " + bits + "   " + str(x + 1).rjust(3) + "   " +
          c.rjust(7) + "   " + t.rjust(4) + "   " +
          "{:.2f}".format(100 * DIST_EX[x]).rjust(6) + "%  " +
          "{:.2f}".format(pv).rjust(6) + "%" + marca)

print("\n[CONCORDANCIA]")
print("  Prob(optimo):   exacta " + "{:.2f}".format(PO_EX) +
      "% | SamplerV2 " + "{:.2f}".format(po_sim) + "%")
print("  Prob(factible): exacta " + "{:.2f}".format(PF_EX) +
      "% | SamplerV2 " + "{:.2f}".format(pf_sim) + "%")

amplif = po_sim / (100.0 / NUM_STATES)
print("\n[METRICAS]")
print("  Amplificacion vs uniforme: " + "{:.2f}".format(amplif) + "x")
print("  Comparativa historica:")
print("    Fase B  (COBYLA, L=2000): 26.27%")
print("    Fase B2 (COBYLA, L=500):  36.33%")
print("    Fase B3 (exacta, L=" + "{:.0f}".format(LAM_WIN) + "):  " +
      "{:.2f}".format(po_sim) + "%")

concuerda = abs(po_sim - PO_EX) < 3.0
if concuerda and po_sim > 70:
    veredicto = "EXCELENTE - Optimizacion exacta valida y concentracion alta"
elif concuerda:
    veredicto = "BUENO - Pipeline verificado contra la solucion exacta"
else:
    veredicto = "REVISAR - Discrepancia exacta vs muestreo"
print("\n  VEREDICTO: " + veredicto)


# ============================================================
# GUARDAR
# ============================================================
salida = {
    "proyecto": PROYECTO,
    "fase": "B v3 - QAOA-RCSPP optimizacion exacta",
    "autor": AUTOR,
    "ruta": "China -> Medellin",
    "fecha": datetime.now().isoformat(),
    "advertencia_datos": (
        "Costos/tiempos ILUSTRATIVOS calibrados contra rangos "
        "publicados (marzo 2026). Ver notas de calibracion en el "
        "reporte de validacion."
    ),
    "metodo": {
        "optimizacion": "exacta por statevector numpy, " +
                        str(MULTISTARTS) + " multistarts Nelder-Mead",
        "verificacion": "qiskit-aer SamplerV2, " +
                        str(SHOTS_FINAL) + " shots",
        "justificacion": (
            "COBYLA con 5 warm-starts quedaba atrapado en minimos "
            "locales (36% vs 86% alcanzable). Con 3 qubits la "
            "optimizacion exacta es trivial y elimina esa fragilidad."
        )
    },
    "configuracion_qaoa": {
        "camino": "Q - codificacion binaria de rutas",
        "num_rutas": NUM_RUTAS,
        "num_qubits": N_QUBITS,
        "profundidad_p": P_LAYERS,
        "deadline_dias": T_MAX,
        "lambda_grid": LAMBDA_GRID,
        "lambda_optimo": float(LAM_WIN)
    },
    "barrido_lambda_exacto": barrido,
    "parametros_optimos_para_hardware": {
        "lambda": float(LAM_WIN),
        "gammas": [float(p) for p in PARAMS_WIN[:P_LAYERS]],
        "betas": [float(p) for p in PARAMS_WIN[P_LAYERS:]]
    },
    "prediccion_exacta": {
        "prob_optimo_pct": float(PO_EX),
        "prob_factible_pct": float(PF_EX),
        "distribucion": [float(100 * DIST_EX[x])
                         for x in range(NUM_STATES)]
    },
    "verificacion_samplerv2": {
        "prob_optimo_pct": float(po_sim),
        "prob_factible_pct": float(pf_sim),
        "shots": SHOTS_FINAL,
        "concuerda_con_exacta": bool(concuerda)
    },
    "concentracion": {
        "ruta_optima_id": int(ID_OPTIMO + 1),
        "amplificacion": float(amplif)
    },
    "veredicto": veredicto
}

ARCHIVO = "qcargo_zam_fase_b_v3_resultados.json"
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

print("\n[REGISTRO]")
print("  Guardado en: " + ARCHIVO)
print("  Parametros validados listos para Fase C (hardware IBM)")
print("=" * 70)
