"""
Q-COFFEE v1.0 MaxCut - Fase A: Fundamentos Clasicos
Autor: Alber Mauricio Marquez Gutierrez

Reformulacion del problema cafetero como MaxCut:
"Dividir fincas en 2 grupos (uno por camion) maximizando
viajes cruzados cortados (distancias entre grupos diferentes)."

Hardware: clasico (Python puro), preparacion para QAOA.
"""

from itertools import product
import json
from datetime import datetime


AUTOR = "Alber Mauricio Marquez Gutierrez"


# ============================================================
# DATOS DEL PROBLEMA (subset de las 3 fincas, sin deposito)
# Para MaxCut el deposito NO es nodo - solo las fincas
# ============================================================
FINCAS = ["Jerico", "Jardin", "Hispania"]
NUM_FINCAS = len(FINCAS)

# Matriz de distancias SOLO entre fincas (sin Andes)
# Indices: 0=Jerico, 1=Jardin, 2=Hispania
DISTANCIAS_FINCAS = [
    [0.0,  27.0, 30.0],   # desde Jerico
    [27.0,  0.0, 32.0],   # desde Jardin
    [30.0, 32.0,  0.0],   # desde Hispania
]

# Tambien necesitamos las distancias finca-Andes para
# calcular el costo TOTAL operativo despues
DISTANCIAS_A_ANDES = [24.0, 22.0, 11.0]  # Andes a Jerico, Jardin, Hispania


def costo_maxcut(asignacion):
    """
    asignacion: lista [a1, a2, a3] donde ai in {0, 1}
                0 = camion A, 1 = camion B
    
    Retorna: suma de distancias entre fincas en GRUPOS DIFERENTES
    (esto es lo que queremos MAXIMIZAR)
    """
    total = 0.0
    for i in range(NUM_FINCAS):
        for j in range(i + 1, NUM_FINCAS):
            if asignacion[i] != asignacion[j]:
                total += DISTANCIAS_FINCAS[i][j]
    return total


def costo_operativo_total(asignacion):
    """
    Calcula el costo total operativo real (km recorridos por ambos camiones).
    Cada camion sale de Andes, visita sus fincas en orden optimo, vuelve.
    """
    grupo_a = [i for i in range(NUM_FINCAS) if asignacion[i] == 0]
    grupo_b = [i for i in range(NUM_FINCAS) if asignacion[i] == 1]
    
    total = 0.0
    
    for grupo in [grupo_a, grupo_b]:
        if len(grupo) == 0:
            continue
        elif len(grupo) == 1:
            # Andes -> Finca -> Andes
            total += 2 * DISTANCIAS_A_ANDES[grupo[0]]
        elif len(grupo) == 2:
            # Andes -> F1 -> F2 -> Andes (probar ambos ordenes)
            f1, f2 = grupo[0], grupo[1]
            ruta_a = DISTANCIAS_A_ANDES[f1] + DISTANCIAS_FINCAS[f1][f2] + DISTANCIAS_A_ANDES[f2]
            ruta_b = DISTANCIAS_A_ANDES[f2] + DISTANCIAS_FINCAS[f2][f1] + DISTANCIAS_A_ANDES[f1]
            total += min(ruta_a, ruta_b)
        elif len(grupo) == 3:
            # Andes -> F1 -> F2 -> F3 -> Andes (probar todos los ordenes)
            from itertools import permutations
            mejor_costo = float('inf')
            for orden in permutations(grupo):
                costo = DISTANCIAS_A_ANDES[orden[0]]
                for k in range(len(orden) - 1):
                    costo += DISTANCIAS_FINCAS[orden[k]][orden[k+1]]
                costo += DISTANCIAS_A_ANDES[orden[-1]]
                if costo < mejor_costo:
                    mejor_costo = costo
            total += mejor_costo
    
    return total


def describir_asignacion(asignacion):
    grupo_a = [FINCAS[i] for i in range(NUM_FINCAS) if asignacion[i] == 0]
    grupo_b = [FINCAS[i] for i in range(NUM_FINCAS) if asignacion[i] == 1]
    return "Camion A: " + str(grupo_a) + " | Camion B: " + str(grupo_b)


# ============================================================
# FUERZA BRUTA: Evaluar todas las 2^3 = 8 asignaciones
# ============================================================
print("=" * 70)
print("  Q-COFFEE v1.0 MaxCut - FASE A: FUNDAMENTOS CLASICOS")
print("  Autor: " + AUTOR)
print("  Region: Suroeste Antioqueno, Colombia")
fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
print("  Fecha: " + fecha_str)
print("=" * 70)

print("\n[CONFIGURACION]")
print("  Fincas:    " + str(NUM_FINCAS) + " (" + ", ".join(FINCAS) + ")")
print("  Deposito:  Andes (central de beneficio)")
print("  Camiones:  2 (A y B)")
print("  Problema:  MaxCut sobre grafo de fincas")
print("  Objetivo:  Maximizar suma de distancias 'cortadas'")
print("             entre grupos diferentes")


# Evaluacion exhaustiva
print("\n[EVALUACION EXHAUSTIVA - 2^3 = 8 asignaciones]")
print("")
print("  Asignacion (J,Jd,H)  | Maxcut | Costo Operativo | Descripcion")
print("  " + "-" * 76)

resultados_completos = []

for asignacion in product([0, 1], repeat=NUM_FINCAS):
    maxcut = costo_maxcut(asignacion)
    operativo = costo_operativo_total(asignacion)
    desc = describir_asignacion(asignacion)
    
    resultados_completos.append({
        'asignacion': list(asignacion),
        'maxcut_km': maxcut,
        'costo_operativo_km': operativo,
        'descripcion': desc
    })
    
    asig_str = str(list(asignacion)).ljust(12)
    mc_str = "{:.1f}".format(maxcut).rjust(6)
    op_str = "{:.1f}".format(operativo).rjust(8)
    print("  " + asig_str + "        | " + mc_str + " | " + op_str + 
          "        | " + desc)


# Encontrar el mejor MaxCut
mejor_maxcut = max(resultados_completos, key=lambda r: r['maxcut_km'])

# Encontrar el mejor costo operativo (esto es el TSP-equivalente)
mejor_operativo = min(resultados_completos, key=lambda r: r['costo_operativo_km'])

# Encontrar el peor (asignacion trivial: todos al mismo camion)
peor_maxcut = min(resultados_completos, key=lambda r: r['maxcut_km'])


print("\n[ANALISIS]")
print("\n  SOLUCION MAXCUT (lo que QAOA intentara encontrar):")
print("    Asignacion: " + str(mejor_maxcut['asignacion']))
print("    MaxCut: " + "{:.2f}".format(mejor_maxcut['maxcut_km']) + " km cortados")
print("    " + mejor_maxcut['descripcion'])
print("    Costo operativo equivalente: " + 
      "{:.2f}".format(mejor_maxcut['costo_operativo_km']) + " km")

print("\n  SOLUCION OPERATIVA OPTIMA (TSP real):")
print("    Asignacion: " + str(mejor_operativo['asignacion']))
print("    Costo operativo: " + 
      "{:.2f}".format(mejor_operativo['costo_operativo_km']) + " km")
print("    " + mejor_operativo['descripcion'])

print("\n  PEOR ASIGNACION (un solo camion hace todo):")
print("    Asignacion: " + str(peor_maxcut['asignacion']))
print("    MaxCut: " + "{:.2f}".format(peor_maxcut['maxcut_km']) + " km")
print("    Costo operativo: " + 
      "{:.2f}".format(peor_maxcut['costo_operativo_km']) + " km")
print("    " + peor_maxcut['descripcion'])


# Verificar alineacion: MaxCut optimo coincide con TSP optimo?
if mejor_maxcut['asignacion'] == mejor_operativo['asignacion']:
    print("\n  [OK] MaxCut optimo COINCIDE con TSP operativo optimo")
    print("       MaxCut es proxy valido del problema real de logistica")
elif mejor_maxcut['costo_operativo_km'] <= mejor_operativo['costo_operativo_km'] * 1.1:
    print("\n  [OK] MaxCut optimo cercano al TSP optimo (dentro del 10%)")
    print("       MaxCut sirve como aproximacion industrial")
else:
    print("\n  [WARNING] MaxCut y TSP optimo difieren significativamente")
    print("           Esto requeriria documentacion adicional")


# ============================================================
# GUARDAR RESULTADOS
# ============================================================
resultados_json = {
    'proyecto': 'Q-COFFEE v1.0 MaxCut',
    'fase': 'A - Fundamentos Clasicos (MaxCut)',
    'autor': AUTOR,
    'region': 'Suroeste Antioqueno, Colombia',
    'fecha': datetime.now().isoformat(),
    'justificacion_pivote': (
        'Pivote de formulacion TSP/VRP a MaxCut para alinearse con '
        'el caso canonico de QAOA sobre hardware NISQ. MaxCut tiene '
        'formulacion validada en literatura desde Farhi 2014.'
    ),
    'configuracion': {
        'fincas': FINCAS,
        'num_fincas': NUM_FINCAS,
        'distancias_inter_fincas_km': DISTANCIAS_FINCAS,
        'distancias_finca_andes_km': DISTANCIAS_A_ANDES,
        'num_camiones': 2,
        'qubits_requeridos': NUM_FINCAS,
        'fuente_datos': 'Google Maps - rutas vehiculares, junio 2026'
    },
    'evaluacion_exhaustiva': resultados_completos,
    'mejor_maxcut': mejor_maxcut,
    'mejor_operativo': mejor_operativo,
    'peor_caso': peor_maxcut
}

with open('qcoffee_maxcut_fase_a_resultados.json', 'w', encoding='utf-8') as f:
    json.dump(resultados_json, f, indent=2, ensure_ascii=False)


# Verificacion del nombre
print("\n[VERIFICACION DEL NOMBRE EN EL JSON]")
with open('qcoffee_maxcut_fase_a_resultados.json', 'r', encoding='utf-8') as f:
    contenido = f.read()

if 'Alber Mauricio' in contenido and 'Alberto' not in contenido:
    print("  [OK] Nombre correcto: 'Alber Mauricio Marquez Gutierrez'")
elif 'Alberto' in contenido:
    print("  [ERROR] Aparece 'Alberto'")


print("\n[REGISTRO]")
print("  Guardado en: qcoffee_maxcut_fase_a_resultados.json")
print("  Listo para alimentar a Fase B (QAOA-MaxCut)")
print("=" * 70)