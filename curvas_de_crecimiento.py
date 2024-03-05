import configparser
import psycopg2
from psycopg2 import sql
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
import matplotlib.colors as mcolors
import numpy as np
from scipy.interpolate import PchipInterpolator
import sys
import json

# Curvas de crecimiento
# Autor: Daniel Sánchez
# Fecha: 2024-01-20

# Obtener argumentos de la línea de comandos
cedula = sys.argv[1] if len(sys.argv) > 1 else ''

# Configuración de la base de datos
config = configparser.ConfigParser()
config.read('config.ini')

db_config = {
    'host': config.get('database', 'host'),
    'database': config.get('database', 'name'),
    'user': config.get('database', 'user'),
    'password': config.get('database', 'password'),
}

# Conectar a la base de datos
conn = psycopg2.connect(**db_config)

# Crear un objeto cursor
cursor = conn.cursor()

# Ejecutar una consulta SELECT
# Consulta SQL
consulta_sql = sql.SQL("""
    SELECT mc."PK_consulta", mc."FK_paciente", sud."FK_sexo", mcsv."FK_signo_vital", mcsv."sigv_resultado", mc."con_fecha", sud."usd_fecha_nacimiento"
    FROM med_consulta_signos_vitales mcsv
    JOIN med_consultas mc ON mcsv."PK_consulta" = mc."PK_consulta"
    JOIN seg_usuario_detalles sud ON mc."FK_paciente" = sud."PK_identificacion"
    WHERE AGE(current_date, sud."usd_fecha_nacimiento") <= interval '19 years'
    AND ("FK_signo_vital" = 3 OR "FK_signo_vital" = 5 OR "FK_signo_vital" = 7)
    AND sud."PK_identificacion" = %s
    ORDER BY mc."con_fecha";
""")
# Ejecutar la consulta con el parámetro
cursor.execute(consulta_sql, (cedula,))

# Obtener los resultados
resultados = cursor.fetchall()

# Creamos nuestras variables para graficar los datos

fecha_peso = []
fecha_talla = []
fecha_imc = []
valor_peso = []
valor_talla = []
valor_imc = []

display_fecha_peso_0_6 = []
display_fecha_peso_6_24 = []
display_fecha_peso_24_60 = []
display_fecha_peso_5_10a = []

display_fecha_talla_0_6 = []
display_fecha_talla_6_24 = []
display_fecha_talla_24_60 = []
display_fecha_talla_5_19a = []

display_fecha_imc_0_5 = []
display_fecha_imc_5_19 = []

genero = 1

for resultado in resultados:

    # Desempaquetar la tupla en variables
    PK_consulta, FK_paciente, FK_sexo, FK_signo_vital, sigv_resultado, con_fecha, usd_fecha_nacimiento = resultado

    if (FK_sexo == 1):
        genero = 1
    elif (FK_sexo == 2):
        genero = 2
    else:
        genero = 1

    # Verificar si el valor del signo vital es None
    if sigv_resultado is None:
        continue  # Salta a la siguiente iteración del bucle si es None

    # Obtenemos el índice de el signo vital, siendo 3 = Peso y 5 = Talla
    signo_vital = int(FK_signo_vital)
    # Obtenemos el valor
    valor_signo_vital = float(sigv_resultado)

    # Python ya interpreta las fechas como datetime
    diferencia = (con_fecha - usd_fecha_nacimiento).days

    # Constante de días calculada visualmente, en 1 día hay 65/1988 meses
    constante = 65/1988

    mes_consulta = diferencia * constante
    # Vamos a generar una condición, dependiendo de que signo vital sea incrustara su valor en uno u otro array
    if (signo_vital == 3):
        valor_peso.append(valor_signo_vital)
        fecha_peso.append(mes_consulta)
        # Dividimos el texto de las fechas
        if 0 <= mes_consulta <= 6:
            display_fecha_peso_0_6.append(con_fecha)
        elif 6 < mes_consulta <= 24:
            display_fecha_peso_6_24.append(con_fecha)
        elif 24 < mes_consulta <=60:
            display_fecha_peso_24_60.append(con_fecha)
        elif 60 < mes_consulta < 120:
            display_fecha_peso_5_10a.append(con_fecha)
    elif (signo_vital == 5):
        if valor_signo_vital < 3:  # Si es menor que 1, asumimos que está en metros
            valor_signo_vital = valor_signo_vital * 100  # Convertir de metros a centímetros
            valor_signo_vital = round(valor_signo_vital, 2)  # Redondear a dos decimales
        valor_talla.append(valor_signo_vital)
        fecha_talla.append(mes_consulta)
        # Dividimos el texto de las fechas
        if 0 <= mes_consulta <= 6:
            display_fecha_talla_0_6.append(con_fecha)
        elif 6 < mes_consulta <= 24:
            display_fecha_talla_6_24.append(con_fecha)
        elif 24 < mes_consulta <=60:
            display_fecha_talla_24_60.append(con_fecha)
        elif 60 < mes_consulta < 228:
            display_fecha_talla_5_19a.append(con_fecha)
    elif(signo_vital == 7):
        if valor_signo_vital == 0:
            continue # Si el valor del signo vital es cero, se continua a la siguiente interacción.
        valor_imc.append(valor_signo_vital)
        fecha_imc.append(mes_consulta)
        # Dividimos el texto de las fechas
        if 0 <= mes_consulta <= 60:
            display_fecha_imc_0_5.append(con_fecha)
        elif 60 < mes_consulta <= 228:
            display_fecha_imc_5_19.append(con_fecha)

# Cerrar el cursor y la conexión
cursor.close()
conn.close()

texto_titulo = "Niños" if genero == 1 else "Niñas"

# Construir el nombre base del archivo
base_filename = "datos_hombre" if genero == 1 else "datos_mujer"

# Función para extraer datos específicos
def extraer_datos(filename):
    with open(filename, "r") as file:
        return json.load(file)["datos"]

# Extraer la lista de datos del JSON
datos = extraer_datos(f"datos/{base_filename}.json")  # Peso y talla de 0 a 5 años
datos_5_10a = extraer_datos(f"datos/{base_filename}_peso_5_10.json")  # Peso de 5 a 10 años
datos_5_19a = extraer_datos(f"datos/{base_filename}_talla_5_19.json")  # Talla de 5 a 19 años
datos_imc = extraer_datos(f"datos/imc_{base_filename}_0_5.json")  # Índice de masa corporal de 0 a 5 años
datos_imc_5_19 = extraer_datos(f"datos/imc_{base_filename}_5_19.json")  # Índice de masa corporal de 5 a 19 años

# Se debe escoger los valores límite dado que la siguiente curva comienza en el límite
def filtrar_datos(datos_a_filtrar, edad_min, edad_max=None):
    if edad_max is None:
        return [dato for dato in datos_a_filtrar if dato["edad"] <= edad_min]
    else:
        return [dato for dato in datos_a_filtrar if edad_min <= dato["edad"] <= edad_max]

def obtener_array_clave(datos_filtrados, clave):
    return np.array([dato[clave] for dato in datos_filtrados])
    
# Filtramos datos de 0-6 meses
datos_0_6 = filtrar_datos(datos, 6)

meses_0_6 = obtener_array_clave(datos_0_6, "edad")
peso_0_6 = obtener_array_clave(datos_0_6, "peso")
peso_mas_dos_0_6 = obtener_array_clave(datos_0_6, "peso_max")
peso_menos_dos_0_6 = obtener_array_clave(datos_0_6, "peso_min")
peso_mas_tres_0_6 = obtener_array_clave(datos_0_6, "peso_max3")
peso_menos_tres_0_6 = obtener_array_clave(datos_0_6, "peso_min3")

talla_0_6 = obtener_array_clave(datos_0_6, "talla")
talla_mas_dos_0_6 = obtener_array_clave(datos_0_6, "talla_max")
talla_menos_dos_0_6 = obtener_array_clave(datos_0_6, "talla_min")
talla_mas_tres_0_6 = obtener_array_clave(datos_0_6, "talla_max3")
talla_menos_tres_0_6 = obtener_array_clave(datos_0_6, "talla_min3")

# Filtramos datos de 6-24 meses
datos_6_24 = filtrar_datos(datos, 6, 24)

meses_6_24 = obtener_array_clave(datos_6_24, "edad")

peso_6_24 = obtener_array_clave(datos_6_24, "peso")
peso_mas_dos_6_24 = obtener_array_clave(datos_6_24, "peso_max")
peso_menos_dos_6_24 = obtener_array_clave(datos_6_24, "peso_min")
peso_mas_tres_6_24 = obtener_array_clave(datos_6_24, "peso_max3")
peso_menos_tres_6_24 = obtener_array_clave(datos_6_24, "peso_min3")

talla_6_24 = obtener_array_clave(datos_6_24, "talla")
talla_mas_dos_6_24 = obtener_array_clave(datos_6_24, "talla_max")
talla_menos_dos_6_24 = obtener_array_clave(datos_6_24, "talla_min")
talla_mas_tres_6_24 = obtener_array_clave(datos_6_24, "talla_max3")
talla_menos_tres_6_24 = obtener_array_clave(datos_6_24, "talla_min3")

# Filtramos los datos de 24-60 meses
datos_24_60 = filtrar_datos(datos, 24, 60)

meses_24_60 = obtener_array_clave(datos_24_60, "edad")

peso_24_60 = obtener_array_clave(datos_24_60, "peso")
peso_mas_dos_24_60 = obtener_array_clave(datos_24_60, "peso_max")
peso_menos_dos_24_60 = obtener_array_clave(datos_24_60, "peso_min")
peso_mas_tres_24_60 = obtener_array_clave(datos_24_60, "peso_max3")
peso_menos_tres_24_60 = obtener_array_clave(datos_24_60, "peso_min3")

talla_24_60 = obtener_array_clave(datos_24_60, "talla")
talla_mas_dos_24_60 = obtener_array_clave(datos_24_60, "talla_max")
talla_menos_dos_24_60 = obtener_array_clave(datos_24_60, "talla_min")
talla_mas_tres_24_60 = obtener_array_clave(datos_24_60, "talla_max3")
talla_menos_tres_24_60 = obtener_array_clave(datos_24_60, "talla_min3")

# Filtramos los datos de peso 5-10 años
datos_5_10a = filtrar_datos(datos_5_10a, 5, 10)
# Filtrammos los datos de talla para 5-19 años
datos_5_19a = filtrar_datos(datos_5_19a, 5, 19)

# Asignamos los datos del peso para años 5 al 10
year_5_10 = obtener_array_clave(datos_5_10a, "edad")
peso_5_10a = obtener_array_clave(datos_5_10a, "peso")
peso_mas_uno_5_10a = obtener_array_clave(datos_5_10a, "peso_mas1")
peso_menos_uno_5_10a = obtener_array_clave(datos_5_10a, "peso_menos1")
peso_mas_dos_5_10a = obtener_array_clave(datos_5_10a, "peso_mas2")
peso_menos_dos_5_10a = obtener_array_clave(datos_5_10a, "peso_menos2")
peso_mas_tres_5_10a = obtener_array_clave(datos_5_10a, "peso_mas3")
peso_menos_tres_5_10a = obtener_array_clave(datos_5_10a, "peso_menos3")

# Asignamos los datos del talla para años 5 al 19
year_5_19 = obtener_array_clave(datos_5_19a, "edad")
talla_5_19a = obtener_array_clave(datos_5_19a, "talla")
talla_mas_uno_5_19a = obtener_array_clave(datos_5_19a, "talla_mas1")
talla_menos_uno_5_19a = obtener_array_clave(datos_5_19a, "talla_menos1")
talla_mas_dos_5_19a = obtener_array_clave(datos_5_19a, "talla_mas2")
talla_menos_dos_5_19a = obtener_array_clave(datos_5_19a, "talla_menos2")
talla_mas_tres_5_19a = obtener_array_clave(datos_5_19a, "talla_mas3")
talla_menos_tres_5_19a = obtener_array_clave(datos_5_19a, "talla_menos3")

# Filtramos los datos para el imc de 0 a 2 años
datos_imc_0_24 = filtrar_datos(datos_imc, 24)

# Filtramos los datos para el imc de 2 a 5 años
datos_imc_24_60 = filtrar_datos(datos_imc, 24, 60)

# Asignamos los datos del índice de masa corporal, tiene su propio método
meses_imc_0_24 = obtener_array_clave(datos_imc_0_24, "edad")
imc_0_24 = obtener_array_clave(datos_imc_0_24, "imc")
imc_mas1_0_24 = obtener_array_clave(datos_imc_0_24, "imc_mas1")
imc_menos1_0_24 = obtener_array_clave(datos_imc_0_24, "imc_menos1")
imc_mas2_0_24 = obtener_array_clave(datos_imc_0_24, "imc_mas2")
imc_menos2_0_24 = obtener_array_clave(datos_imc_0_24, "imc_menos2")
imc_mas3_0_24 = obtener_array_clave(datos_imc_0_24, "imc_mas3")
imc_menos3_0_24 = obtener_array_clave(datos_imc_0_24, "imc_menos3")

meses_imc_24_60 = obtener_array_clave(datos_imc_24_60, "edad")
imc_24_60 = obtener_array_clave(datos_imc_24_60, "imc")
imc_mas1_24_60 = obtener_array_clave(datos_imc_24_60, "imc_mas1")
imc_menos1_24_60 = obtener_array_clave(datos_imc_24_60, "imc_menos1")
imc_mas2_24_60 = obtener_array_clave(datos_imc_24_60, "imc_mas2")
imc_menos2_24_60 = obtener_array_clave(datos_imc_24_60, "imc_menos2")
imc_mas3_24_60 = obtener_array_clave(datos_imc_24_60, "imc_mas3")
imc_menos3_24_60 = obtener_array_clave(datos_imc_24_60, "imc_menos3")

# Los datos de curvas de imc para 5 a 19 años vienen en años

meses_imc_5_19 = obtener_array_clave(datos_imc_5_19, "edad")
imc_5_19 = obtener_array_clave(datos_imc_5_19, "imc")
imc_mas1_5_19 = obtener_array_clave(datos_imc_5_19, "imc_mas1")
imc_menos1_5_19 = obtener_array_clave(datos_imc_5_19, "imc_menos1")
imc_mas2_5_19 = obtener_array_clave(datos_imc_5_19, "imc_mas2")
imc_menos2_5_19 = obtener_array_clave(datos_imc_5_19, "imc_menos2")
imc_mas3_5_19 = obtener_array_clave(datos_imc_5_19, "imc_mas3")
imc_menos3_5_19 = obtener_array_clave(datos_imc_5_19, "imc_menos3")


# Función para ajustar una función polinómica y obtener polinomio y curva
def ajustar_curva(meses, datos, grado_polinomio):
    coeficientes = np.polyfit(meses, datos, grado_polinomio)
    polinomio = np.poly1d(coeficientes)
    curva = polinomio(meses)
    return polinomio, curva

def interpolacion(x_values, y_values):
    interp_func = PchipInterpolator(x_values, y_values)
    return interp_func

# Ajustar una función polinómica de grado 3
grado_polinomio = 3

# region Obtención de ajustes, interpolaciones y curvas

# Interpolación curvas para el peso 0-6 meses
polinomio_peso_0_6 = interpolacion(meses_0_6, peso_0_6)
polinomio_peso_menos2_0_6 = interpolacion(meses_0_6, peso_menos_dos_0_6)
polinomio_peso_mas2_0_6 = interpolacion(meses_0_6, peso_mas_dos_0_6)
polinomio_peso_mas3_0_6 = interpolacion(meses_0_6, peso_mas_tres_0_6)
polinomio_peso_menos3_0_6 = interpolacion(meses_0_6, peso_menos_tres_0_6)

# Interpolación curvas para la talla 0-6 meses
polinomio_talla_0_6 = interpolacion(meses_0_6, talla_0_6)
polinomio_talla_mas2_0_6 = interpolacion(meses_0_6, talla_mas_dos_0_6)
polinomio_talla_menos2_0_6 = interpolacion(meses_0_6, talla_menos_dos_0_6)
polinomio_talla_mas3_0_6 = interpolacion(meses_0_6, talla_mas_tres_0_6)
polinomio_talla_menos3_0_6 = interpolacion(meses_0_6, talla_menos_tres_0_6)

# Interpolación curvas para el 6-24 meses
polinomio_peso_6_24 = interpolacion(meses_6_24, peso_6_24)
polinomio_peso_mas2_6_24 = interpolacion(meses_6_24, peso_mas_dos_6_24)
polinomio_peso_menos2_6_24 = interpolacion(meses_6_24, peso_menos_dos_6_24)
polinomio_peso_mas3_6_24 = interpolacion(meses_6_24, peso_mas_tres_6_24)
polinomio_peso_menos3_6_24 = interpolacion(meses_6_24, peso_menos_tres_6_24)

# Interpolación curvas para la talla 6-24 meses
polinomio_talla_6_24 = interpolacion(meses_6_24, talla_6_24)
polinomio_talla_menos2_6_24 = interpolacion(meses_6_24, talla_menos_dos_6_24)
polinomio_talla_mas2_6_24 = interpolacion(meses_6_24, talla_mas_dos_6_24)
polinomio_talla_mas3_6_24 = interpolacion(meses_6_24, talla_mas_tres_6_24)
polinomio_talla_menos3_6_24 = interpolacion(meses_6_24, talla_menos_tres_6_24)

# Interpolación curvas para el peso 24-60 meses
polinomio_peso_24_60 = interpolacion(meses_24_60, peso_24_60)
polinomio_peso_mas2_24_60 = interpolacion(meses_24_60, peso_mas_dos_24_60)
polinomio_peso_menos2_24_60 = interpolacion(meses_24_60, peso_menos_dos_24_60)
polinomio_peso_mas3_24_60 = interpolacion(meses_24_60, peso_mas_tres_24_60)
polinomio_peso_menos3_24_60 = interpolacion(meses_24_60, peso_menos_tres_24_60)

# Interpolación curvas para la talla 24-60 meses
polinomio_talla_24_60 = interpolacion(meses_24_60, talla_24_60)
polinomio_talla_menos2_24_60 = interpolacion(meses_24_60, talla_menos_dos_24_60)
polinomio_talla_mas2_24_60 = interpolacion(meses_24_60, talla_mas_dos_24_60)
polinomio_talla_mas3_24_60 = interpolacion(meses_24_60, talla_mas_tres_24_60)
polinomio_talla_menos3_24_60 = interpolacion(meses_24_60, talla_menos_tres_24_60)

# Interpolación curvas para el peso 5-10 años
polinomio_peso_5_10a = interpolacion(year_5_10, peso_5_10a)
polinomio_peso_mas1_5_10a = interpolacion(year_5_10, peso_mas_uno_5_10a)
polinomio_peso_menos1_5_10a = interpolacion(year_5_10, peso_menos_uno_5_10a)
polinomio_peso_mas2_5_10a = interpolacion(year_5_10, peso_mas_dos_5_10a)
polinomio_peso_menos2_5_10a = interpolacion(year_5_10, peso_menos_dos_5_10a)
polinomio_peso_mas3_5_10a = interpolacion(year_5_10, peso_mas_tres_5_10a)
polinomio_peso_menos3_5_10a = interpolacion(year_5_10, peso_menos_tres_5_10a)

# Interpolación para la talla de 5 a 19 años
polinomio_talla_5_19a = interpolacion(year_5_19, talla_5_19a)
polinomio_talla_mas1_5_19a = interpolacion(year_5_19, talla_mas_uno_5_19a)
polinomio_talla_menos1_5_19a = interpolacion(year_5_19, talla_menos_uno_5_19a)
polinomio_talla_mas2_5_19a = interpolacion(year_5_19, talla_mas_dos_5_19a)
polinomio_talla_menos2_5_19a = interpolacion(year_5_19, talla_menos_dos_5_19a)
polinomio_talla_mas3_5_19a = interpolacion(year_5_19, talla_mas_tres_5_19a)
polinomio_talla_menos3_5_19a = interpolacion(year_5_19, talla_menos_tres_5_19a)

# Interpolación para el índice de masa corporal de 0 a 2 años y de 2 a 5 años
polinomio_imc_0_24 = interpolacion(meses_imc_0_24, imc_0_24)
polinomio_imc_mas1_0_24 = interpolacion(meses_imc_0_24, imc_mas1_0_24)
polinomio_imc_menos1_0_24 = interpolacion(meses_imc_0_24, imc_menos1_0_24)
polinomio_imc_mas2_0_24 = interpolacion(meses_imc_0_24, imc_mas2_0_24)
polinomio_imc_menos2_0_24 = interpolacion(meses_imc_0_24, imc_menos2_0_24)
polinomio_imc_mas3_0_24 = interpolacion(meses_imc_0_24, imc_mas3_0_24)
polinomio_imc_menos3_0_24 = interpolacion(meses_imc_0_24, imc_menos3_0_24)

polinomio_imc_24_60 = interpolacion(meses_imc_24_60, imc_24_60)
polinomio_imc_mas1_24_60 = interpolacion(meses_imc_24_60, imc_mas1_24_60)
polinomio_imc_menos1_24_60 = interpolacion(meses_imc_24_60, imc_menos1_24_60)
polinomio_imc_mas2_24_60 = interpolacion(meses_imc_24_60, imc_mas2_24_60)
polinomio_imc_menos2_24_60 = interpolacion(meses_imc_24_60, imc_menos2_24_60)
polinomio_imc_mas3_24_60 = interpolacion(meses_imc_24_60, imc_mas3_24_60)
polinomio_imc_menos3_24_60 = interpolacion(meses_imc_24_60, imc_menos3_24_60)

# Interpolación imc de 5 a 19 años

polinomio_imc_5_19 = interpolacion(meses_imc_5_19, imc_5_19)
polinomio_imc_mas1_5_19 = interpolacion(meses_imc_5_19, imc_mas1_5_19)
polinomio_imc_menos1_5_19 = interpolacion(meses_imc_5_19, imc_menos1_5_19)
polinomio_imc_mas2_5_19 = interpolacion(meses_imc_5_19, imc_mas2_5_19)
polinomio_imc_menos2_5_19 = interpolacion(meses_imc_5_19, imc_menos2_5_19)
polinomio_imc_mas3_5_19 = interpolacion(meses_imc_5_19, imc_mas3_5_19)
polinomio_imc_menos3_5_19 = interpolacion(meses_imc_5_19, imc_menos3_5_19)

# endregion

# Control de pesos
umbral_peso_superior = 60
umbral_peso_inferior = 1
umbral_talla_superior = 200
umbral_talla_inferior = 40
umbral_imc_inferior = 9
umbral_imc_superior = 40

# Dividir los datos en dos conjuntos según la condición de la fecha
datos_peso_menor_6 = [(fecha, peso) for fecha, peso in zip(fecha_peso, valor_peso) if fecha <= 6 and umbral_peso_inferior <= peso <= umbral_peso_superior]
datos_talla_menor_6 = [(fecha, talla) for fecha, talla in zip(fecha_talla, valor_talla) if fecha <= 6 and umbral_talla_inferior <= talla <= umbral_talla_superior]

datos_peso_entre_6_24 = [(fecha, peso) for fecha, peso in zip(fecha_peso, valor_peso) if 6 < fecha <= 24 and umbral_peso_inferior <= peso <= umbral_peso_superior]
datos_talla_entre_6_24 = [(fecha, talla) for fecha, talla in zip(fecha_talla, valor_talla) if 6 < fecha <= 24 and umbral_talla_inferior <= talla <= umbral_talla_superior]

datos_peso_entre_24_60 = [(fecha, peso) for fecha, peso in zip(fecha_peso, valor_peso) if 24 < fecha <= 60 and umbral_peso_inferior <= peso <= umbral_peso_superior]
datos_talla_entre_24_60 = [(fecha, talla) for fecha, talla in zip(fecha_talla, valor_talla) if 24 < fecha <= 60 and umbral_talla_inferior <= talla <= umbral_talla_superior]

datos_peso_entre_5_10a = [(fecha, peso) for fecha, peso in zip(fecha_peso, valor_peso) if 60 < fecha <= 120 and umbral_peso_inferior <= peso <= umbral_peso_superior]
datos_talla_entre_5_19a = [(fecha, talla) for fecha, talla in zip(fecha_talla, valor_talla) if 60 < fecha <= 228 and umbral_talla_inferior <= talla <= umbral_talla_superior]

datos_imc_entre_0_5 = [(fecha, imc) for fecha, imc in zip(fecha_imc, valor_imc) if fecha <= 60 and umbral_imc_inferior <= imc <= umbral_imc_superior]
datos_imc_entre_5_19 = [(fecha, imc) for fecha, imc in zip(fecha_imc, valor_imc) if 60 < fecha <= 228 and umbral_imc_inferior <= imc <= umbral_imc_superior]

# Define los colores del colormap personalizado
start_color = '#8f0101'
color_inferior = '#918f14'
mid_color = 'green'
color_superior = '#918f14'
end_color = '#8f0101'

def asignar_color(x, y, tipo):

    if tipo == "peso":
        if x <= 6:
            valor_ideal = polinomio_peso_0_6(x)
            limite_inferior = polinomio_peso_menos2_0_6(x)
            limite_superior = polinomio_peso_mas2_0_6(x)
        elif 6 < x <= 24:
            valor_ideal = polinomio_peso_6_24(x)
            limite_inferior = polinomio_peso_menos2_6_24(x)
            limite_superior = polinomio_peso_mas2_6_24(x)
        elif 24 < x <= 60:
            valor_ideal = polinomio_peso_24_60(x)
            limite_inferior = polinomio_peso_menos2_24_60(x)
            limite_superior = polinomio_peso_mas2_24_60(x)
        elif 60 < x <= 120:
            # Se divide para 12 pues entra como meses y graficamos años
            valor_ideal = polinomio_peso_5_10a(x / 12)
            limite_inferior = polinomio_peso_menos2_5_10a(x / 12)
            limite_superior = polinomio_peso_mas2_5_10a(x / 12)
        else: # No debería haber más datos pero controlamos asignaciones incorrectas
            valor_ideal = 1
            limite_inferior = 1
            limite_superior = 2
    if tipo == "talla":
        if x <= 6:
            valor_ideal = polinomio_talla_0_6(x)
            limite_inferior = polinomio_talla_menos2_0_6(x)
            limite_superior = polinomio_talla_mas2_0_6(x)
        elif 6 < x <= 24:
            valor_ideal = polinomio_talla_6_24(x)
            limite_inferior = polinomio_talla_menos2_6_24(x)
            limite_superior = polinomio_talla_mas2_6_24(x)
        elif 24 < x <= 60:
            valor_ideal = polinomio_talla_24_60(x)
            limite_inferior = polinomio_talla_menos2_24_60(x)
            limite_superior = polinomio_talla_mas2_24_60(x)
        elif 60 < x <= 228:
            # Se divide para 12 pues entra como meses y graficamos años
            valor_ideal = polinomio_talla_5_19a(x / 12)
            limite_inferior = polinomio_talla_menos2_5_19a(x / 12)
            limite_superior = polinomio_talla_mas2_5_19a(x / 12)
        else: # No debería haber más datos pero controlamos asignaciones incorrectas
            valor_ideal = 1
            limite_inferior = 1
            limite_superior = 2
    # Calcular el porcentaje del valor_ideal entre los límites inferior y superior
    porcentaje_ideal = (valor_ideal - limite_inferior) / (limite_superior - limite_inferior)

    # Crea el colormap personalizado directamente
    custom_cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_colormap",
        [(0.0, start_color), (porcentaje_ideal / 2, color_inferior), (porcentaje_ideal, mid_color), ( (porcentaje_ideal + 1) / 2, color_superior), (1.0, end_color)]
    )

    # Normalizar los valores de peso para mapear a una escala de colores
    norma = mcolors.Normalize(vmin=limite_inferior, vmax=limite_superior)

    # Calcular colores en función de la proximidad a los límites
    color = custom_cmap(norma(y))
    
    # Convertir el color de formato RGBA a formato hexadecimal para Plotly
    color_hex = "#{:02x}{:02x}{:02x}".format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    
    return color_hex

# Constantes para los textos en los gráficos
texto_grafico_peso = "Peso/edad - "
texto_grafico_talla = "Longitud/edad - "

# Definimos las constantes de la impresión de detalles
formato_impresion_peso = '%{y:.2f} kg'
formato_impresion_talla = '%{y:.2f} cm'

# Definimos las constantes del texto de las curvas
texto_curva_mas_uno = "Alerta superior"
texto_curva_menos_uno = "Alerta inferior"
texto_curva_mas_dos = "Límite superior"
texto_curva_menos_dos = "Límite inferior"
texto_curva_mas_tres = "Corte superior"
texto_curva_menos_tres = "Corte inferior"

# Definimos los colores de ayuda
color_ayuda_central = 'green'
color_ayuda_limite = '#c21919'
color_relleno = 'rgba(255,255,255,0)'
color_relleno_completo = 'rgba(0,100,80,0.3)'


# Crear subgráficos
fig = make_subplots(
    rows=5, cols=2,
    vertical_spacing = 0.05, # Valores entre 0 y 1 
    horizontal_spacing = 0.1,  # Valores entre 0 y 1
    subplot_titles=(
        texto_grafico_peso + texto_titulo + " de 0 a 6 meses",
        texto_grafico_talla + texto_titulo + " de 0 a 6 meses",
        texto_grafico_peso + texto_titulo + " de 6 a 23 meses",
        texto_grafico_talla + texto_titulo + " de 6 a 23 meses",
        texto_grafico_peso + texto_titulo + " de 2 a 5 años",
        texto_grafico_talla + texto_titulo + " de 2 a 5 años",
        texto_grafico_peso + texto_titulo + " de 5 a 10 años",
        texto_grafico_talla + texto_titulo + "/adolescentes de 5 a 19 años",
        "IMC " + texto_titulo + " de 0 a 5 años",
        "IMC " + texto_titulo + "/adolescentes de 5 a 19 años",)
)

# Creamos las variables para controlar las posiciones de manera rápida

fila_peso_0_6 = 1
columna_peso_0_6 = 1

fila_talla_0_6 = 1
columna_talla_0_6 = 2

fila_peso_6_24 = 2
columna_peso_6_24 = 1

fila_talla_6_24 = 2
columna_talla_6_24 = 2

fila_peso_24_60 = 3
columna_peso_24_60 = 1

fila_talla_24_60 = 3
columna_talla_24_60 = 2

fila_peso_5_10a = 4
columna_peso_5_10a = 1

fila_talla_5_19a = 4
columna_talla_5_19a = 2

fila_imc_0_5 = 5
columna_imc_0_5 = 1

fila_imc_5_19 = 5
columna_imc_5_19 = 2
# Agregar trazos a los subgráficos correspondientes

def add_grafico_curva(fig, x, y, nombre, color_curva, hover_template, row, col):
    trace = go.Scatter(
        x=x,
        y=y,
        mode='lines',
        name=nombre,
        line=dict(color=color_curva),
        hoverlabel=dict(
            font_size=14,
            font_family="sans-serif",
        ),
        legendgroup=1, 
        hovertemplate = None, # Modificaciones para desactivar el hover
        hoverinfo = "skip", # Modificaciones para desactivar el hover
        showlegend=False
    )
    fig.add_trace(trace, row=row, col=col)

def add_puntos_datos(fig, x_data, y_data, color_map, line_color, name, text_data, row, col):
    trace = go.Scatter(
        x=x_data,
        y=y_data,
        mode='lines+markers',
        marker=dict(size=8, color=color_map),
        line=dict(color=line_color),
        legendgroup=3,
        name=name,
        hoverlabel=dict(font_size=16, font_family="Calibri, sans-serif"),
        hovertemplate="<b>%{text}</b><extra></extra>",
        text=text_data,
        showlegend=False
    )
    fig.add_trace(trace, row=row, col=col)

def add_puntos_datos_imc(fig, x_data, y_data, color_map, name, text_data, row, col):
    trace = go.Scatter(
        x=x_data,
        y=y_data,
        mode='markers',
        marker=dict(size=8, color=color_map),
        name=name,
        hoverlabel=dict(font_size=16, font_family="Calibri, sans-serif"),
        hovertemplate="<b>%{text}</b><extra></extra>",
        text=text_data,
        showlegend=False
    )
    fig.add_trace(trace, row=row, col=col)

def add_puntos_ayuda(fig, x_data, y_data, color_linea, nombre, hover_template, row, col):
    trace = go.Scatter(
        x=x_data,
        y=y_data,
        mode='markers',
        name=nombre,
        line=dict(color=color_linea),
        hoverlabel=dict(font_size=14, font_family="sans-serif"),
        hovertemplate=hover_template,
        showlegend=False,
        visible=False # Esta parte desactiva la función
    )
    fig.add_trace(trace, row=row, col=col)

# region Creación de curvas de 0-6 meses
    
# Peso
# Generar una lista de 100 nuevos valores de x
x_peso_0_6 = np.linspace(min(meses_0_6), max(meses_0_6), 500)
curva_peso_0_6 = polinomio_peso_0_6(x_peso_0_6)
curva_peso_mas2_0_6 = polinomio_peso_mas2_0_6(x_peso_0_6)
curva_peso_menos2_0_6 = polinomio_peso_menos2_0_6(x_peso_0_6)
curva_peso_mas3_0_6 = polinomio_peso_mas3_0_6(x_peso_0_6)
curva_peso_menos3_0_6 = polinomio_peso_menos3_0_6(x_peso_0_6)

add_grafico_curva(fig, x_peso_0_6, curva_peso_0_6, "Peso 0-6 meses", color_ayuda_central, formato_impresion_peso, 
                  fila_peso_0_6, columna_peso_0_6)
add_grafico_curva(fig, x_peso_0_6, curva_peso_mas2_0_6, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_0_6, columna_peso_0_6)
add_grafico_curva(fig, x_peso_0_6, curva_peso_menos2_0_6, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_0_6, columna_peso_0_6)
add_grafico_curva(fig, x_peso_0_6, curva_peso_mas3_0_6, texto_curva_mas_tres, "black", formato_impresion_peso,
                  fila_peso_0_6, columna_peso_0_6)
add_grafico_curva(fig, x_peso_0_6, curva_peso_menos3_0_6, texto_curva_menos_tres, "black", formato_impresion_peso,
                  fila_peso_0_6, columna_peso_0_6)

# Relleno 0-6 meses
# Agregar primero la curva inferior sin relleno
fig.add_trace(go.Scatter(x=x_peso_0_6, y=curva_peso_menos2_0_6, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_0_6, col=columna_peso_0_6)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_peso_0_6, y=curva_peso_mas2_0_6, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_0_6, col=columna_peso_0_6)

# Puntos de datos e información 0-6 meses - Peso

fechas_peso_0_6 = [fecha for fecha, _ in datos_peso_menor_6]
valores_peso_0_6 = [peso for _, peso in datos_peso_menor_6]
mapa_color_peso_0_6 = [asignar_color(x, y, "peso") for x, y in datos_peso_menor_6]
texto_hover_peso_0_6 = []
for fecha, peso, valor_fecha in zip(display_fecha_peso_0_6, valores_peso_0_6, fechas_peso_0_6):
    if polinomio_peso_menos2_0_6(valor_fecha) <= peso <= polinomio_peso_mas2_0_6(valor_fecha):
        estado = "Normal"
    elif polinomio_peso_mas2_0_6(valor_fecha) <= peso <= polinomio_peso_mas3_0_6(valor_fecha):
        estado = "Alerta"
    elif polinomio_peso_menos3_0_6(valor_fecha) <= peso <= polinomio_peso_menos2_0_6(valor_fecha):
        estado = "Alerta"
    elif peso > polinomio_peso_mas3_0_6(valor_fecha):
        estado = "Sobrepeso"
    elif peso < polinomio_peso_menos3_0_6(valor_fecha):
        estado = "Desnutricion"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_peso_0_6.append(f"Fecha: {fecha}<br>Peso: {peso} kg<br>Estado: {estado}")

# Puntos de datos de peso
add_puntos_datos(fig, fechas_peso_0_6, valores_peso_0_6, mapa_color_peso_0_6, 'green', 'Datos peso 0-6 meses', 
                 texto_hover_peso_0_6, fila_peso_0_6, columna_peso_0_6)

# Guía central - Peso
add_puntos_ayuda(fig, fechas_peso_0_6, [polinomio_peso_0_6(fecha) for fecha in fechas_peso_0_6], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_peso, fila_peso_0_6, columna_peso_0_6)

# Guía inferior - Peso
add_puntos_ayuda(fig, fechas_peso_0_6, [polinomio_peso_menos2_0_6(fecha) for fecha in fechas_peso_0_6],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_peso, fila_peso_0_6, columna_peso_0_6)

# Guía superior - Peso
add_puntos_ayuda(fig, fechas_peso_0_6, [polinomio_peso_mas2_0_6(fecha) for fecha in fechas_peso_0_6],
                 color_ayuda_limite, 'Límite superior', formato_impresion_peso, fila_peso_0_6, columna_peso_0_6)

x_talla_0_6 = np.linspace(min(meses_0_6), max(meses_0_6), 500)
curva_talla_0_6 = polinomio_talla_0_6(x_talla_0_6)
curva_talla_mas2_0_6 = polinomio_talla_mas2_0_6(x_talla_0_6)
curva_talla_menos2_0_6 = polinomio_talla_menos2_0_6(x_talla_0_6)
curva_talla_mas3_0_6 = polinomio_talla_mas3_0_6(x_talla_0_6)
curva_talla_menos3_0_6 = polinomio_talla_menos3_0_6(x_talla_0_6)

# Talla
add_grafico_curva(fig, x_talla_0_6, curva_talla_0_6, "Talla 0-6 meses", color_ayuda_central, formato_impresion_talla, 
                  fila_talla_0_6, columna_talla_0_6)
add_grafico_curva(fig, x_talla_0_6, curva_talla_mas2_0_6, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_0_6, columna_talla_0_6)
add_grafico_curva(fig, x_talla_0_6, curva_talla_menos2_0_6, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_0_6, columna_talla_0_6)
add_grafico_curva(fig, x_talla_0_6, curva_talla_mas3_0_6, texto_curva_mas_tres, "black", formato_impresion_talla, 
                  fila_talla_0_6, columna_talla_0_6)
add_grafico_curva(fig, x_talla_0_6, curva_talla_menos3_0_6, texto_curva_menos_tres, "black", formato_impresion_talla, 
                  fila_talla_0_6, columna_talla_0_6)

# Relleno 0-6 meses
# Agregar primero la curva inferior sin relleno
fig.add_trace(go.Scatter(x=x_talla_0_6, y=curva_talla_menos2_0_6, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_0_6, col=columna_talla_0_6)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_talla_0_6, y=curva_talla_mas2_0_6, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_0_6, col=columna_talla_0_6)

# Puntos de datos e información 0-6 meses - Talla

fechas_talla_0_6 = [fecha for fecha, _ in datos_talla_menor_6]
valores_talla_0_6 = [talla for _, talla in datos_talla_menor_6]
mapa_color_talla_0_6 = [asignar_color(x, y, "talla") for x, y in datos_talla_menor_6]
texto_hover_talla_0_6 = []
for fecha, talla, valor_fecha in zip(display_fecha_talla_0_6, valores_talla_0_6, fechas_talla_0_6):
    if polinomio_talla_menos2_0_6(valor_fecha) <= talla <= polinomio_talla_mas2_0_6(valor_fecha):
        estado = "Normal"
    elif polinomio_talla_menos3_0_6(valor_fecha) <= talla <= polinomio_talla_menos2_0_6(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas2_0_6(valor_fecha) <= talla <= polinomio_talla_mas3_0_6(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas3_0_6(valor_fecha) <= talla:
        estado = "Gigantismo"
    elif talla < polinomio_talla_menos3_0_6(valor_fecha):
        estado = "Enanismo"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_talla_0_6.append(f"Fecha: {fecha}<br>Talla: {talla} cm<br>Estado: {estado}")

add_puntos_datos(fig, fechas_talla_0_6, valores_talla_0_6, mapa_color_talla_0_6, 'green', 'Datos talla 0-6 meses', 
                 texto_hover_talla_0_6, fila_talla_0_6, columna_talla_0_6)

# Guía central - Talla
add_puntos_ayuda(fig, fechas_talla_0_6, [polinomio_talla_0_6(fecha) for fecha in fechas_talla_0_6], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_talla, fila_talla_0_6, columna_talla_0_6)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_0_6, [polinomio_talla_menos2_0_6(fecha) for fecha in fechas_talla_0_6], 
                 color_ayuda_limite, 'Límite inferior', formato_impresion_talla, fila_talla_0_6, columna_talla_0_6)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_0_6, [polinomio_talla_mas2_0_6(fecha) for fecha in fechas_talla_0_6], 
                 color_ayuda_limite, 'Límite superior', formato_impresion_talla, fila_talla_0_6, columna_talla_0_6)
# endregion

# region Creación de curvas de 6-24 meses 
# Peso

x_peso_6_24 = np.linspace(min(meses_6_24), max(meses_6_24), 500)
curva_peso_6_24 = polinomio_peso_6_24(x_peso_6_24)
curva_peso_mas2_6_24 = polinomio_peso_mas2_6_24(x_peso_6_24)
curva_peso_menos2_6_24 = polinomio_peso_menos2_6_24(x_peso_6_24)
curva_peso_mas3_6_24 = polinomio_peso_mas3_6_24(x_peso_6_24)
curva_peso_menos3_6_24 = polinomio_peso_menos3_6_24(x_peso_6_24)

add_grafico_curva(fig, x_peso_6_24, curva_peso_6_24, "Peso 6-24 meses", color_ayuda_central, formato_impresion_peso, 
                  fila_peso_6_24, columna_peso_6_24)
add_grafico_curva(fig, x_peso_6_24, curva_peso_mas2_6_24, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_6_24, columna_peso_6_24)
add_grafico_curva(fig, x_peso_6_24, curva_peso_menos2_6_24, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_6_24, columna_peso_6_24)
add_grafico_curva(fig, x_peso_6_24, curva_peso_mas3_6_24, texto_curva_mas_tres, "black", formato_impresion_peso, 
                  fila_peso_6_24, columna_peso_6_24)
add_grafico_curva(fig, x_peso_6_24, curva_peso_menos3_6_24, texto_curva_menos_tres, "black", formato_impresion_peso, 
                  fila_peso_6_24, columna_peso_6_24)

# Relleno 6-24 meses
fig.add_trace(go.Scatter(x=x_peso_6_24, y=curva_peso_menos2_6_24, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_6_24, col=columna_peso_6_24)
fig.add_trace(go.Scatter(x=x_peso_6_24, y=curva_peso_mas2_6_24, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_6_24, col=columna_peso_6_24)

# Puntos de datos e información 6-24 meses - Peso

fechas_peso_6_24 = [fecha for fecha, _ in datos_peso_entre_6_24]
valores_peso_6_24 = [peso for _, peso in datos_peso_entre_6_24]
mapa_color_peso_6_24 = [asignar_color(x, y, "peso") for x, y in datos_peso_entre_6_24]
texto_hover_peso_6_24 = []
for fecha, peso, valor_fecha in zip(display_fecha_peso_6_24, valores_peso_6_24, fechas_peso_6_24):
    if polinomio_peso_menos2_6_24(valor_fecha) <= peso <= polinomio_peso_mas2_6_24(valor_fecha):
        estado = "Normal"
    elif polinomio_peso_mas2_6_24(valor_fecha) <= peso <= polinomio_peso_mas3_6_24(valor_fecha):
        estado = "Alerta"
    elif polinomio_peso_menos3_6_24(valor_fecha) <= peso <= polinomio_peso_menos2_6_24(valor_fecha):
        estado = "Alerta"
    elif peso > polinomio_peso_mas3_6_24(valor_fecha):
        estado = "Sobrepeso"
    elif peso < polinomio_peso_menos3_6_24(valor_fecha):
        estado = "Desnutricion"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_peso_6_24.append(f"Fecha: {fecha}<br>Peso: {peso} kg<br>Estado: {estado}")

# Puntos de datos de peso 6-24 meses
add_puntos_datos(fig, fechas_peso_6_24, valores_peso_6_24, mapa_color_peso_6_24, 'green', 'Datos peso 6-24 meses', 
                 texto_hover_peso_6_24, fila_peso_6_24, columna_peso_6_24)

# Guía central - Peso
add_puntos_ayuda(fig, fechas_peso_6_24, [polinomio_peso_6_24(fecha) for fecha in fechas_peso_6_24], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_peso, fila_peso_6_24, columna_peso_6_24)

# Guía inferior - Peso
add_puntos_ayuda(fig, fechas_peso_6_24, [polinomio_peso_menos2_6_24(fecha) for fecha in fechas_peso_6_24],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_peso, fila_peso_6_24, columna_peso_6_24)

# Guía superior - Peso
add_puntos_ayuda(fig, fechas_peso_6_24, [polinomio_peso_mas2_6_24(fecha) for fecha in fechas_peso_6_24],
                 color_ayuda_limite, 'Límite superior', formato_impresion_peso, fila_peso_6_24, columna_peso_6_24)

# Talla

x_talla_6_24 = np.linspace(min(meses_6_24), max(meses_6_24), 500)
curva_talla_6_24 = polinomio_talla_6_24(x_talla_6_24)
curva_talla_mas2_6_24 = polinomio_talla_mas2_6_24(x_talla_6_24)
curva_talla_menos2_6_24 = polinomio_talla_menos2_6_24(x_talla_6_24)
curva_talla_mas3_6_24 = polinomio_talla_mas3_6_24(x_talla_6_24)
curva_talla_menos3_6_24 = polinomio_talla_menos3_6_24(x_talla_6_24)

add_grafico_curva(fig, x_talla_6_24, curva_talla_6_24, "Talla 6-24 meses", color_ayuda_central, formato_impresion_talla, 
                  fila_talla_6_24, columna_talla_6_24)
add_grafico_curva(fig, x_talla_6_24, curva_talla_mas2_6_24, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_6_24, columna_talla_6_24)
add_grafico_curva(fig, x_talla_6_24, curva_talla_menos2_6_24, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_6_24, columna_talla_6_24)
add_grafico_curva(fig, x_talla_6_24, curva_talla_mas3_6_24, texto_curva_mas_tres, "black", formato_impresion_talla, 
                  fila_talla_6_24, columna_talla_6_24)
add_grafico_curva(fig, x_talla_6_24, curva_talla_menos3_6_24, texto_curva_menos_tres, "black", formato_impresion_talla, 
                  fila_talla_6_24, columna_talla_6_24)

# Relleno 6-24 meses
fig.add_trace(go.Scatter(x=x_talla_6_24, y=curva_talla_menos2_6_24, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_6_24, col=columna_talla_6_24)
fig.add_trace(go.Scatter(x=x_talla_6_24, y=curva_talla_mas2_6_24, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_6_24, col=columna_talla_6_24)

# Puntos de datos e información 6-24 meses - Talla

fechas_talla_6_24 = [fecha for fecha, _ in datos_talla_entre_6_24]
valores_talla_6_24 = [talla for _, talla in datos_talla_entre_6_24]
mapa_color_talla_6_24 = [asignar_color(x, y, "talla") for x, y in datos_talla_entre_6_24]
texto_hover_talla_6_24 = []
for fecha, talla, valor_fecha in zip(display_fecha_talla_6_24, valores_talla_6_24, fechas_talla_6_24):
    if polinomio_talla_menos2_6_24(valor_fecha) <= talla <= polinomio_talla_mas2_6_24(valor_fecha):
        estado = "Normal"
    elif polinomio_talla_menos3_6_24(valor_fecha) <= talla <= polinomio_talla_menos2_6_24(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas2_6_24(valor_fecha) <= talla <= polinomio_talla_mas3_6_24(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas3_6_24(valor_fecha) <= talla:
        estado = "Gigantismo"
    elif talla < polinomio_talla_menos3_6_24(valor_fecha):
        estado = "Enanismo"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_talla_6_24.append(f"Fecha: {fecha}<br>Talla: {talla} cm<br>Estado: {estado}")

add_puntos_datos(fig, fechas_talla_6_24, valores_talla_6_24, mapa_color_talla_6_24, 'green', 'Datos talla 6-24 meses', 
                 texto_hover_talla_6_24, fila_talla_6_24, columna_talla_6_24)

# Guía central - Talla
add_puntos_ayuda(fig, fechas_talla_6_24, [polinomio_talla_6_24(fecha) for fecha in fechas_talla_6_24], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_talla, fila_talla_6_24, columna_talla_6_24)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_6_24, [polinomio_talla_menos2_6_24(fecha) for fecha in fechas_talla_6_24], 
                 color_ayuda_limite, 'Límite inferior', formato_impresion_talla, fila_talla_6_24, columna_talla_6_24)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_6_24, [polinomio_talla_mas2_6_24(fecha) for fecha in fechas_talla_6_24], 
                 color_ayuda_limite, 'Límite superior', formato_impresion_talla, fila_talla_6_24, columna_talla_6_24)
# endregion

# region Creación de curvas de 24-60 meses

x_peso_24_60 = np.linspace(min(meses_24_60), max(meses_24_60), 500)
curva_peso_24_60 = polinomio_peso_24_60(x_peso_24_60)
curva_peso_mas2_24_60 = polinomio_peso_mas2_24_60(x_peso_24_60)
curva_peso_menos2_24_60 = polinomio_peso_menos2_24_60(x_peso_24_60)
curva_peso_mas3_24_60 = polinomio_peso_mas3_24_60(x_peso_24_60)
curva_peso_menos3_24_60 = polinomio_peso_menos3_24_60(x_peso_24_60)

add_grafico_curva(fig, x_peso_24_60, curva_peso_24_60, "Peso 2-5 años", color_ayuda_central, formato_impresion_peso, 
                  fila_peso_24_60, columna_peso_24_60)
add_grafico_curva(fig, x_peso_24_60, curva_peso_mas2_24_60, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_24_60, columna_peso_24_60)
add_grafico_curva(fig, x_peso_24_60, curva_peso_menos2_24_60, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_24_60, columna_peso_24_60)
add_grafico_curva(fig, x_peso_24_60, curva_peso_mas3_24_60, texto_curva_mas_tres, "black", formato_impresion_peso, 
                  fila_peso_24_60, columna_peso_24_60)
add_grafico_curva(fig, x_peso_24_60, curva_peso_menos3_24_60, texto_curva_menos_tres, "black", formato_impresion_peso, 
                  fila_peso_24_60, columna_peso_24_60)

# Relleno 24-60 meses
# Agregar primero la curva inferior sin relleno
fig.add_trace(go.Scatter(x=x_peso_24_60, y=curva_peso_menos2_24_60, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_24_60, col=columna_peso_24_60)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_peso_24_60, y=curva_peso_mas2_24_60, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_24_60, col=columna_peso_24_60)

# Puntos de datos e información 24-60 meses - Peso

fechas_peso_24_60 = [fecha for fecha, _ in datos_peso_entre_24_60]
valores_peso_24_60 = [peso for _, peso in datos_peso_entre_24_60]
mapa_color_peso_24_60 = [asignar_color(x, y, "peso") for x, y in datos_peso_entre_24_60]
texto_hover_peso_24_60 = []
for fecha, peso, valor_fecha in zip(display_fecha_peso_24_60, valores_peso_24_60, fechas_peso_24_60):
    if polinomio_peso_menos2_24_60(valor_fecha) <= peso <= polinomio_peso_mas2_24_60(valor_fecha):
        estado = "Normal"
    elif polinomio_peso_mas2_24_60(valor_fecha) <= peso <= polinomio_peso_mas3_24_60(valor_fecha):
        estado = "Alerta"
    elif polinomio_peso_menos3_24_60(valor_fecha) <= peso <= polinomio_peso_menos2_24_60(valor_fecha):
        estado = "Alerta"
    elif peso > polinomio_peso_mas3_24_60(valor_fecha):
        estado = "Sobrepeso"
    elif peso < polinomio_peso_menos3_24_60(valor_fecha):
        estado = "Desnutricion"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_peso_24_60.append(f"Fecha: {fecha}<br>Peso: {peso} kg<br>Estado: {estado}")

# Puntos de datos de peso 6-24 meses
add_puntos_datos(fig, fechas_peso_24_60, valores_peso_24_60, mapa_color_peso_24_60, 'green', 'Datos peso 2-5 años', 
                 texto_hover_peso_24_60, fila_peso_24_60, columna_peso_6_24)

# Guía central - Peso
add_puntos_ayuda(fig, fechas_peso_24_60, [polinomio_peso_24_60(fecha) for fecha in fechas_peso_24_60], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_peso, fila_peso_24_60, columna_peso_24_60)

# Guía inferior - Peso
add_puntos_ayuda(fig, fechas_peso_24_60, [polinomio_peso_menos2_24_60(fecha) for fecha in fechas_peso_24_60],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_peso, fila_peso_24_60, columna_peso_24_60)

# Guía superior - Peso
add_puntos_ayuda(fig, fechas_peso_24_60, [polinomio_peso_mas2_24_60(fecha) for fecha in fechas_peso_24_60],
                 color_ayuda_limite, 'Límite superior', formato_impresion_peso, fila_peso_24_60, columna_peso_24_60)

# Talla

x_talla_24_60 = np.linspace(min(meses_24_60), max(meses_24_60), 500)
curva_talla_24_60 = polinomio_talla_24_60(x_talla_24_60)
curva_talla_mas2_24_60 = polinomio_talla_mas2_24_60(x_talla_24_60)
curva_talla_menos2_24_60 = polinomio_talla_menos2_24_60(x_talla_24_60)
curva_talla_mas3_24_60 = polinomio_talla_mas3_24_60(x_talla_24_60)
curva_talla_menos3_24_60 = polinomio_talla_menos3_24_60(x_talla_24_60)

add_grafico_curva(fig, x_talla_24_60, curva_talla_24_60, "Talla 2-5 años", color_ayuda_central, formato_impresion_talla, 
                  fila_talla_24_60, columna_talla_24_60)
add_grafico_curva(fig, x_talla_24_60, curva_talla_mas2_24_60, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_24_60, columna_talla_24_60)
add_grafico_curva(fig, x_talla_24_60, curva_talla_menos2_24_60, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_talla, 
                  fila_talla_24_60, columna_talla_24_60)
add_grafico_curva(fig, x_talla_24_60, curva_talla_mas3_24_60, texto_curva_mas_tres, "black", formato_impresion_talla, 
                  fila_talla_24_60, columna_talla_24_60)
add_grafico_curva(fig, x_talla_24_60, curva_talla_menos3_24_60, texto_curva_menos_tres, "black", formato_impresion_talla, 
                  fila_talla_24_60, columna_talla_24_60)


# Relleno 24-60 meses
fig.add_trace(go.Scatter(x=x_talla_24_60, y=curva_talla_menos2_24_60, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_24_60, col=columna_talla_24_60)
fig.add_trace(go.Scatter(x=x_talla_24_60, y=curva_talla_mas2_24_60, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_24_60, col=columna_talla_24_60)

# Puntos de datos e información 24-60 meses - Talla

fechas_talla_24_60 = [fecha for fecha, _ in datos_talla_entre_24_60]
valores_talla_24_60 = [talla for _, talla in datos_talla_entre_24_60]
mapa_color_talla_24_60 = [asignar_color(x, y, "talla") for x, y in datos_talla_entre_24_60]
texto_hover_talla_24_60 = []
for fecha, talla, valor_fecha in zip(display_fecha_talla_24_60, valores_talla_24_60, fechas_talla_24_60):
    if polinomio_talla_menos2_24_60(valor_fecha) <= talla <= polinomio_talla_mas2_24_60(valor_fecha):
        estado = "Normal"
    elif polinomio_talla_menos3_24_60(valor_fecha) <= talla <= polinomio_talla_menos2_24_60(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas2_24_60(valor_fecha) <= talla <= polinomio_talla_mas3_24_60(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas3_24_60(valor_fecha) <= talla:
        estado = "Gigantismo"
    elif talla < polinomio_talla_menos3_24_60(valor_fecha):
        estado = "Enanismo"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_talla_24_60.append(f"Fecha: {fecha}<br>Talla: {talla} cm<br>Estado: {estado}")

add_puntos_datos(fig, fechas_talla_24_60, valores_talla_24_60, mapa_color_talla_24_60, 'green', 'Datos talla 2-5 años', 
                 texto_hover_talla_24_60, fila_talla_24_60, columna_talla_24_60)

# Guía central - Talla
add_puntos_ayuda(fig, fechas_talla_24_60, [polinomio_talla_24_60(fecha) for fecha in fechas_talla_24_60], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_talla, fila_talla_24_60, columna_talla_24_60)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_24_60, [polinomio_talla_menos2_24_60(fecha) for fecha in fechas_talla_24_60], 
                 color_ayuda_limite, 'Límite inferior', formato_impresion_talla, fila_talla_24_60, columna_talla_24_60)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_24_60, [polinomio_talla_mas2_24_60(fecha) for fecha in fechas_talla_24_60], 
                 color_ayuda_limite, 'Límite superior', formato_impresion_talla, fila_talla_24_60, columna_talla_24_60)

# endregion

# region Creación de curvas de peso 5 a 10 años

x_peso_5_10 = np.linspace(min(year_5_10), max(year_5_10), 500)
curva_peso_5_10a = polinomio_peso_5_10a(x_peso_5_10)
curva_peso_mas1_5_10a = polinomio_peso_mas1_5_10a(x_peso_5_10)
curva_peso_menos1_5_10a = polinomio_peso_menos1_5_10a(x_peso_5_10)
curva_peso_mas2_5_10a = polinomio_peso_mas2_5_10a(x_peso_5_10)
curva_peso_menos2_5_10a = polinomio_peso_menos2_5_10a(x_peso_5_10)
curva_peso_mas3_5_10a = polinomio_peso_mas3_5_10a(x_peso_5_10)
curva_peso_menos3_5_10a = polinomio_peso_menos3_5_10a(x_peso_5_10)

add_grafico_curva(fig, x_peso_5_10, curva_peso_5_10a, "Peso 5-10 años", color_ayuda_central, formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_mas1_5_10a, texto_curva_mas_uno, "orange", formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_menos1_5_10a, texto_curva_mas_uno, "orange", formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_mas2_5_10a, texto_curva_mas_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_menos2_5_10a, texto_curva_menos_dos, color_ayuda_limite, formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_mas3_5_10a, texto_curva_mas_tres, "black", formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)
add_grafico_curva(fig, x_peso_5_10, curva_peso_menos3_5_10a, texto_curva_menos_tres, "black", formato_impresion_peso, 
                  fila_peso_5_10a, columna_peso_5_10a)

# Agregar primero la curva inferior sin relleno para -1 a +1
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_menos1_5_10a, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_5_10a, col=columna_peso_5_10a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_mas1_5_10a, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_5_10a, col=columna_peso_5_10a)

# Agregar primero la curva inferior sin relleno para +1 +2
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_mas1_5_10a, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_5_10a, col=columna_peso_5_10a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_mas2_5_10a, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_5_10a, col=columna_peso_5_10a)

# Agregar primero la curva inferior sin relleno para -2 -1
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_menos2_5_10a, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_peso_5_10a, col=columna_peso_5_10a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_peso_5_10, y=curva_peso_menos1_5_10a, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_peso_5_10a, col=columna_peso_5_10a)

# Puntos de datos e información 5-10 años - Peso

# Ojo, dividir para 12 las fechas pues se presentan en meses
fechas_peso_5_10a = [fecha / 12 for fecha, _ in datos_peso_entre_5_10a]
valores_peso_5_10a = [peso for _, peso in datos_peso_entre_5_10a]
mapa_color_peso_5_10a = [asignar_color(x, y, "peso") for x, y in datos_peso_entre_5_10a]
texto_hover_peso_5_10a = []
for fecha, peso, valor_fecha in zip(display_fecha_peso_5_10a, valores_peso_5_10a, fechas_peso_5_10a):
    if polinomio_peso_menos2_5_10a(valor_fecha) <= peso <= polinomio_peso_mas2_5_10a(valor_fecha):
        estado = "Normal"
    elif polinomio_peso_mas2_5_10a(valor_fecha) <= peso <= polinomio_peso_mas3_5_10a(valor_fecha):
        estado = "Alerta"
    elif polinomio_peso_menos3_5_10a(valor_fecha) <= peso <= polinomio_peso_menos2_5_10a(valor_fecha):
        estado = "Alerta"
    elif peso > polinomio_peso_mas3_5_10a(valor_fecha):
        estado = "Sobrepeso"
    elif peso < polinomio_peso_menos3_5_10a(valor_fecha):
        estado = "Desnutricion"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_peso_5_10a.append(f"Fecha: {fecha}<br>Peso: {peso} kg<br>Estado: {estado}")

# Puntos de datos de peso 6-24 meses
add_puntos_datos(fig, fechas_peso_5_10a, valores_peso_5_10a, mapa_color_peso_5_10a, 'green', 'Datos peso 5-10 años', 
                 texto_hover_peso_5_10a, fila_peso_5_10a, columna_peso_5_10a)

# Guía central - Peso
add_puntos_ayuda(fig, fechas_peso_5_10a, [polinomio_peso_5_10a(fecha) for fecha in fechas_peso_5_10a], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_peso, fila_peso_5_10a, columna_peso_5_10a)

# Guía inferior - Peso
add_puntos_ayuda(fig, fechas_peso_5_10a, [polinomio_peso_menos2_5_10a(fecha) for fecha in fechas_peso_5_10a],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_peso, fila_peso_5_10a, columna_peso_5_10a)

# Guía superior - Peso
add_puntos_ayuda(fig, fechas_peso_5_10a, [polinomio_peso_mas2_5_10a(fecha) for fecha in fechas_peso_5_10a],
                 color_ayuda_limite, 'Límite superior', formato_impresion_peso, fila_peso_5_10a, columna_peso_5_10a)

# endregion

# region Creación de curvas de talla 5 a 19 años

# Generar una lista de 100 nuevos valores de x
x_talla_5_19 = np.linspace(min(year_5_19), max(year_5_19), 500)
curva_talla_5_19 = polinomio_talla_5_19a(x_talla_5_19)
curva_talla_mas1_5_19 = polinomio_talla_mas1_5_19a(x_talla_5_19)
curva_talla_menos1_5_19 = polinomio_talla_menos1_5_19a(x_talla_5_19)
curva_talla_mas2_5_19 = polinomio_talla_mas2_5_19a(x_talla_5_19)
curva_talla_menos2_5_19 = polinomio_talla_menos2_5_19a(x_talla_5_19)
curva_talla_mas3_5_19 = polinomio_talla_mas3_5_19a(x_talla_5_19)
curva_talla_menos3_5_19 = polinomio_talla_menos3_5_19a(x_talla_5_19)

add_grafico_curva(fig, x_talla_5_19, curva_talla_5_19, "Talla 5 a 19 años", 
                  color_ayuda_central, formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_mas1_5_19, texto_curva_mas_uno, 
                  "orange", formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_menos1_5_19, texto_curva_menos_uno, 
                  "orange", formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_mas2_5_19, texto_curva_mas_dos, 
                  color_ayuda_limite, formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_menos2_5_19, texto_curva_menos_dos, 
                  color_ayuda_limite, formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_mas3_5_19, texto_curva_mas_tres, 
                  "black", formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)
add_grafico_curva(fig, x_talla_5_19, curva_talla_menos3_5_19, texto_curva_menos_tres, 
                  "black", formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)

# Agregar primero la curva inferior sin relleno para -1 a +1
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_menos1_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_5_19a, col=columna_talla_5_19a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_mas1_5_19, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_5_19a, col=columna_talla_5_19a)

# Agregar primero la curva inferior sin relleno para +1 +2
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_mas1_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_5_19a, col=columna_talla_5_19a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_mas2_5_19, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_5_19a, col=columna_talla_5_19a)

# Agregar primero la curva inferior sin relleno para -2 -1
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_menos2_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_talla_5_19a, col=columna_talla_5_19a)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=x_talla_5_19, y=curva_talla_menos1_5_19, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_talla_5_19a, col=columna_talla_5_19a)


# Ojo, dividir para 12 las fechas pues se presentan en meses
fechas_talla_5_19a = [fecha / 12 for fecha, _ in datos_talla_entre_5_19a]
valores_talla_5_19a = [talla for _, talla in datos_talla_entre_5_19a]
mapa_color_talla_5_19a = [asignar_color(x, y, "talla") for x, y in datos_talla_entre_5_19a]
texto_hover_talla_5_19a = []
for fecha, talla, valor_fecha in zip(display_fecha_talla_5_19a, valores_talla_5_19a, fechas_talla_5_19a):
    if polinomio_talla_menos2_5_19a(valor_fecha) <= talla <= polinomio_talla_mas2_5_19a(valor_fecha):
        estado = "Normal"
    elif polinomio_talla_menos3_5_19a(valor_fecha) <= talla <= polinomio_talla_menos2_5_19a(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas2_5_19a(valor_fecha) <= talla <= polinomio_talla_mas3_5_19a(valor_fecha):
        estado = "Alerta"
    elif polinomio_talla_mas3_5_19a(valor_fecha) <= talla:
        estado = "Gigantismo"
    elif talla < polinomio_talla_menos3_5_19a(valor_fecha):
        estado = "Enanismo"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    texto_hover_talla_5_19a.append(f"Fecha: {fecha}<br>Talla: {talla} cm<br>Estado: {estado}")

# Puntos de datos de talla 5 a 19 años
add_puntos_datos(fig, fechas_talla_5_19a, valores_talla_5_19a, mapa_color_talla_5_19a, 'green', 'Datos talla 5-19 años', 
                 texto_hover_talla_5_19a, fila_talla_5_19a, columna_talla_5_19a)

# Guía central - Talla
add_puntos_ayuda(fig, fechas_talla_5_19a, [polinomio_talla_5_19a(fecha) for fecha in fechas_talla_5_19a], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)

# Guía inferior - Talla
add_puntos_ayuda(fig, fechas_talla_5_19a, [polinomio_talla_menos2_5_19a(fecha) for fecha in fechas_talla_5_19a],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)

# Guía superior - Talla
add_puntos_ayuda(fig, fechas_talla_5_19a, [polinomio_talla_mas2_5_19a(fecha) for fecha in fechas_talla_5_19a],
                 color_ayuda_limite, 'Límite superior', formato_impresion_talla, fila_talla_5_19a, columna_talla_5_19a)

# endregion

# region IMC 0 a 5 años

# Generar una lista de 100 nuevos valores de x
imc_valores_x = np.linspace(min(meses_imc_0_24), max(meses_imc_0_24), 500)
curva_imc_0_24 = polinomio_imc_0_24(imc_valores_x)
curva_imc_mas1_0_24 = polinomio_imc_mas1_0_24(imc_valores_x)
curva_imc_menos1_0_24 = polinomio_imc_menos1_0_24(imc_valores_x)
curva_imc_mas2_0_24 = polinomio_imc_mas2_0_24(imc_valores_x)
curva_imc_menos2_0_24 = polinomio_imc_menos2_0_24(imc_valores_x)
curva_imc_mas3_0_24 = polinomio_imc_mas3_0_24(imc_valores_x)
curva_imc_menos3_0_24 = polinomio_imc_menos3_0_24(imc_valores_x)

imc_valores_x_24_60 = np.linspace(min(meses_imc_24_60), max(meses_imc_24_60), 500)
curva_imc_24_60 = polinomio_imc_24_60(imc_valores_x_24_60 )
curva_imc_mas1_24_60 = polinomio_imc_mas1_24_60(imc_valores_x_24_60 )
curva_imc_menos1_24_60 = polinomio_imc_menos1_24_60(imc_valores_x_24_60 )
curva_imc_mas2_24_60 = polinomio_imc_mas2_24_60(imc_valores_x_24_60 )
curva_imc_menos2_24_60 = polinomio_imc_menos2_24_60(imc_valores_x_24_60 )
curva_imc_mas3_24_60 = polinomio_imc_mas3_24_60(imc_valores_x_24_60 )
curva_imc_menos3_24_60 = polinomio_imc_menos3_24_60(imc_valores_x_24_60 )

formato_impresion_imc = '%{y:.2f} imc'

add_grafico_curva(fig, imc_valores_x, curva_imc_0_24, "IMC 0 a 2 años", 
                  color_ayuda_central, formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_mas1_0_24, "IMC +1", 
                  "orange", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_menos1_0_24, "IMC -1", 
                  "orange", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_mas2_0_24, "IMC +2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_menos2_0_24, "IMC -2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_mas3_0_24, "IMC +3", 
                  "black", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x, curva_imc_menos3_0_24, "IMC -3", 
                  "black", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)

# Relleno

# Agregar primero la curva inferior sin relleno para -1 a +1
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_menos1_0_24, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_mas1_0_24, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

# Agregar primero la curva inferior sin relleno para +1 +2
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_mas1_0_24, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_mas2_0_24, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

# Agregar primero la curva inferior sin relleno para -2 -1
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_menos2_0_24, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x, y=curva_imc_menos1_0_24, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_24_60, "IMC 0 a 2 años", 
                  color_ayuda_central, formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_mas1_24_60, "IMC +1", 
                  "orange", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_menos1_24_60, "IMC -1", 
                  "orange", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_mas2_24_60, "IMC +2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_0_5, 1)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_menos2_24_60, "IMC -2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_mas3_24_60, "IMC +3", 
                  "black", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
add_grafico_curva(fig, imc_valores_x_24_60, curva_imc_menos3_24_60, "IMC -3", 
                  "black", formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)

# Agregar primero la curva inferior sin relleno para -1 a +1
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_menos1_24_60, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_mas1_24_60, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

# Agregar primero la curva inferior sin relleno para +1 +2
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_mas1_24_60, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_mas2_24_60, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

# Agregar primero la curva inferior sin relleno para -2 -1
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_menos2_24_60, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_0_5, col=columna_imc_0_5)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_24_60, y=curva_imc_menos1_24_60, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_0_5, col=columna_imc_0_5)

fechas_imc_0_5 = [fecha for fecha, _ in datos_imc_entre_0_5]
valores_imc_0_5 = [imc for _, imc in datos_imc_entre_0_5]
# mapa_color_imc_0_5 = [asignar_color(x, y, "imc") for x, y in datos_imc_entre_0_5]
mapa_color_imc_0_5 = "rgba(0, 0, 0, 0.75)"
texto_hover_imc_0_5 = []

for fecha, imc, valor_fecha in zip(display_fecha_imc_0_5, valores_imc_0_5, fechas_imc_0_5):
    if valor_fecha <= 24:
        if polinomio_imc_menos2_0_24(valor_fecha) <= imc <= polinomio_imc_mas2_0_24(valor_fecha):
            estado = "Normal"
        elif polinomio_imc_mas2_0_24(valor_fecha) <= imc <= polinomio_imc_mas3_0_24(valor_fecha):
            estado = "Alerta"
        elif polinomio_imc_menos3_0_24(valor_fecha) <= imc <= polinomio_imc_menos2_0_24(valor_fecha):
            estado = "Alerta"
        elif imc > polinomio_imc_mas3_0_24(valor_fecha):
            estado = "IMC Alto"
        elif imc < polinomio_imc_menos3_0_24(valor_fecha):
            estado = "IMC Bajo"
        else:
            estado = "Desconocido"  # Para manejar cualquier otro caso
    else:
        if polinomio_imc_menos2_24_60(valor_fecha) <= imc <= polinomio_imc_mas2_24_60(valor_fecha):
            estado = "Normal"
        elif polinomio_imc_mas2_24_60(valor_fecha) <= imc <= polinomio_imc_mas3_24_60(valor_fecha):
            estado = "Alerta"
        elif polinomio_imc_menos3_24_60(valor_fecha) <= imc <= polinomio_imc_menos2_24_60(valor_fecha):
            estado = "Alerta"
        elif imc > polinomio_imc_mas3_24_60(valor_fecha):
            estado = "IMC Alto"
        elif imc < polinomio_imc_menos3_24_60(valor_fecha):
            estado = "IMC Bajo"
        else:
            estado = "Desconocido"  # Para manejar cualquier otro caso
    
    texto_hover_imc_0_5.append(f"Fecha: {fecha}<br>IMC: {imc}<br>Estado: {estado}")


# Puntos de datos de peso imc 0-5 años
add_puntos_datos_imc(fig, fechas_imc_0_5, valores_imc_0_5, mapa_color_imc_0_5, 'Datos imc 0-5 años', 
                 texto_hover_imc_0_5, fila_imc_0_5, columna_imc_0_5)

# Guía central - imc
add_puntos_ayuda(fig, fechas_imc_0_5, [polinomio_imc_24_60(fecha) if fecha > 24 else polinomio_imc_0_24(fecha) for fecha in fechas_imc_0_5], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)

# Guía inferior - imc
add_puntos_ayuda(fig, fechas_imc_0_5, [polinomio_imc_menos2_24_60(fecha) if fecha > 24 else polinomio_imc_menos2_0_24(fecha) for fecha in fechas_imc_0_5],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)

# Guía superior - imc
add_puntos_ayuda(fig, fechas_imc_0_5, [polinomio_imc_mas2_24_60(fecha) if fecha > 24 else polinomio_imc_mas2_0_24(fecha) for fecha in fechas_imc_0_5],
                 color_ayuda_limite, 'Límite superior', formato_impresion_imc, fila_imc_0_5, columna_imc_0_5)
# endregion

# region IMC 5 a 19 años

imc_valores_x_5_19 = np.linspace(min(meses_imc_5_19), max(meses_imc_5_19), 500)
curva_imc_5_19 = polinomio_imc_5_19(imc_valores_x_5_19 )
curva_imc_mas1_5_19 = polinomio_imc_mas1_5_19(imc_valores_x_5_19)
curva_imc_menos1_5_19 = polinomio_imc_menos1_5_19(imc_valores_x_5_19)
curva_imc_mas2_5_19 = polinomio_imc_mas2_5_19(imc_valores_x_5_19)
curva_imc_menos2_5_19 = polinomio_imc_menos2_5_19(imc_valores_x_5_19)
curva_imc_mas3_5_19 = polinomio_imc_mas3_5_19(imc_valores_x_5_19)
curva_imc_menos3_5_19 = polinomio_imc_menos3_5_19(imc_valores_x_5_19)

formato_impresion_imc = '%{y:.2f} imc'

add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_5_19, "IMC 0 a 2 años", 
                  color_ayuda_central, formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_mas1_5_19, "IMC +1", 
                  "orange", formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_menos1_5_19, "IMC -1", 
                  "orange", formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_mas2_5_19, "IMC +2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_menos2_5_19, "IMC -2", 
                  color_ayuda_limite, formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_mas3_5_19, "IMC +3", 
                  "black", formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)
add_grafico_curva(fig, imc_valores_x_5_19, curva_imc_menos3_5_19, "IMC -3", 
                  "black", formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)

# Agregar primero la curva inferior sin relleno para -1 a +1
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_menos1_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_5_19, col=columna_imc_5_19)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_mas1_5_19, fill='tonexty', fillcolor=color_relleno_completo, 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_5_19, col=columna_imc_5_19)

# Agregar primero la curva inferior sin relleno para +1 +2
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_mas1_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_5_19, col=columna_imc_5_19)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_mas2_5_19, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_5_19, col=columna_imc_5_19)

# Agregar primero la curva inferior sin relleno para -2 -1
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_menos2_5_19, line=dict(color=color_relleno), 
                         showlegend=False, hoverinfo='skip'), row=fila_imc_5_19, col=columna_imc_5_19)
# Luego agregar la curva superior con relleno
fig.add_trace(go.Scatter(x=imc_valores_x_5_19, y=curva_imc_menos1_5_19, fill='tonexty', fillcolor='rgba(252, 194, 3, 0.3)', 
                         line=dict(color=color_relleno), showlegend=False, hoverinfo='skip'), 
                         row=fila_imc_5_19, col=columna_imc_5_19)

# Ojo, dividir para 12 las fechas pues se presentan en meses
fechas_imc_5_19 = [fecha / 12 for fecha, _ in datos_imc_entre_5_19]
valores_imc_5_19 = [imc for _, imc in datos_imc_entre_5_19]
# mapa_color_imc_0_5 = [asignar_color(x, y, "imc") for x, y in datos_imc_entre_0_5]
mapa_color_imc_5_19 = "rgba(0, 0, 0, 0.75)"
texto_hover_imc_5_19 = []

for fecha, imc, valor_fecha in zip(display_fecha_imc_5_19, valores_imc_5_19, fechas_imc_5_19):
    if polinomio_imc_menos2_5_19(valor_fecha) <= imc <= polinomio_imc_mas2_5_19(valor_fecha):
        estado = "Normal"
    elif polinomio_imc_mas2_5_19(valor_fecha) <= imc <= polinomio_imc_mas3_5_19(valor_fecha):
        estado = "Alerta"
    elif polinomio_imc_menos3_5_19(valor_fecha) <= imc <= polinomio_imc_menos2_5_19(valor_fecha):
        estado = "Alerta"
    elif imc > polinomio_imc_mas3_5_19(valor_fecha):
        estado = "IMC Alto"
    elif imc < polinomio_imc_menos3_5_19(valor_fecha):
        estado = "IMC Bajo"
    else:
        estado = "Desconocido"  # Para manejar cualquier otro caso
    
    texto_hover_imc_5_19.append(f"Fecha: {fecha}<br>IMC: {imc}<br>Estado: {estado}")

# Puntos de datos de peso imc 0-5 años
add_puntos_datos_imc(fig, fechas_imc_5_19, valores_imc_5_19, mapa_color_imc_5_19, 'Datos imc 5-19 años', 
                 texto_hover_imc_5_19, fila_imc_5_19, columna_imc_5_19)

# Guía central - imc
add_puntos_ayuda(fig, fechas_imc_5_19, [polinomio_imc_5_19(fecha) for fecha in fechas_imc_5_19], 
                 color_ayuda_central, 'Valor ideal', formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)

# Guía inferior - imc
add_puntos_ayuda(fig, fechas_imc_5_19, [polinomio_imc_menos2_5_19(fecha) for fecha in fechas_imc_5_19],
                 color_ayuda_limite, 'Límite inferior', formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)

# Guía superior - imc
add_puntos_ayuda(fig, fechas_imc_5_19, [polinomio_imc_mas2_5_19(fecha) for fecha in fechas_imc_5_19],
                 color_ayuda_limite, 'Límite superior', formato_impresion_imc, fila_imc_5_19, columna_imc_5_19)

# endregion
# Personalizar la escala de cada subplot # Para que minor funcione sse debe quitar tickvals
# Curvas peso 0-6 meses
fig.update_xaxes(title_text="Meses", range=[-0.5, 6.5], 
                 row=fila_peso_0_6, col=columna_peso_0_6) 
fig.update_yaxes(title_text="Peso (Kg)",  range=[1, 12], 
                 gridwidth=1, row=fila_peso_0_6, col=columna_peso_0_6) 
# Curvas talla 0-6 meses
fig.update_xaxes(title_text="Meses", range=[-0.5, 6.5], 
                 row=fila_talla_0_6, col=columna_talla_0_6) 
fig.update_yaxes(title_text="Talla (cm)", range=[42, 75],
                 row=fila_talla_0_6, col=columna_talla_0_6) 

# Curvas peso 6-24 meses
fig.update_xaxes(title_text="Meses", range=[5.5, 24.5], 
                 row=fila_peso_6_24, col=columna_peso_6_24) 
fig.update_yaxes(title_text="Peso (Kg)", range=[5, 17.5],
                 row=fila_peso_6_24, col=columna_peso_6_24)  

# Curvas talla 6-24 meses
fig.update_xaxes(title_text="Meses", range=[5.5, 24.5], 
                 row=fila_talla_6_24, col=columna_talla_6_24) 
fig.update_yaxes(title_text="Talla (cm)", range=[55, 100],
                 row=fila_talla_6_24, col=columna_talla_6_24)  

# Curvas peso 24-60 meses
fig.update_xaxes(title_text="Meses", range=[23.5, 60.5], 
                 row=fila_peso_24_60, col=columna_peso_24_60) 
fig.update_yaxes(title_text="Peso (Kg)", range=[7, 30],
                 row=fila_peso_24_60, col=columna_peso_24_60)  

# Curvas talla 24-60 meses
fig.update_xaxes(title_text="Meses", range=[23.5, 60.5], 
                 row=fila_talla_24_60, col=columna_talla_24_60) 
fig.update_yaxes(title_text="Talla (cm)", range=[75, 125], 
                 row=fila_talla_24_60, col=columna_talla_24_60) 

# Curvas peso 5-10 años
fig.update_xaxes(title_text="Años", range=[4.9, 10.1], 
                 row=fila_peso_5_10a, col=columna_peso_5_10a) 
fig.update_yaxes(title_text="Peso (kg)", range=[11, 60],
                 row=fila_peso_5_10a, col=columna_peso_5_10a) 

# Curvas talla 5-19 años
fig.update_xaxes(title_text="Años", range=[4.95, 19.05], 
                 row=fila_talla_5_19a, col=columna_talla_5_19a) 
fig.update_yaxes(title_text="Talla (cm)", range=[90, 190],
                 row=fila_talla_5_19a, col=columna_talla_5_19a) 
  
# minor=dict(ticklen=5, showgrid=True)

# IMC 0-5 años
fig.update_xaxes(title_text="Meses", range=[-0.1, 60.1], 
                 row=fila_imc_0_5, col=columna_imc_0_5) 
fig.update_yaxes(title_text="Índice de masa corporal (kg/m^2)", range=[9, 23], 
                 row=fila_imc_0_5, col=columna_imc_0_5)  

# IMC 5-19 años
fig.update_xaxes(title_text="Años", range=[4.9, 19.1], 
                 row=fila_imc_5_19, col=columna_imc_5_19) 
fig.update_yaxes(title_text="Índice de masa corporal (kg/m^2)", range=[10, 40], 
                 row=fila_imc_5_19, col=columna_imc_5_19)   

# region Divisiones de ayuda

# Función para crear las lineas y añadirlas al gráfico correspondiente
def add_division(fig, x0, x1, y0, y1, row, col):
    shape = go.layout.Shape(
        type="line",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        line=dict(color="rgba(0, 0, 0, 0.3)", width=2),
    )
    fig.add_shape(shape, row=row, col=col)

# Divisiones de ayuda
add_division(fig, 12, 12, 5, 18, fila_peso_6_24, columna_peso_6_24)
add_division(fig, 24, 24, 5, 18, fila_peso_6_24, columna_peso_6_24)
add_division(fig, 12, 12, 55, 100, fila_talla_6_24, columna_talla_6_24)
add_division(fig, 24, 24, 55, 100, fila_talla_6_24, columna_talla_6_24)

add_division(fig, 24, 24, 6, 31, fila_peso_24_60, columna_peso_24_60)
add_division(fig, 36, 36, 6, 31, fila_peso_24_60, columna_peso_24_60)
add_division(fig, 48, 48, 6, 31, fila_peso_24_60, columna_peso_24_60)
add_division(fig, 60, 60, 6, 31, fila_peso_24_60, columna_peso_24_60)

add_division(fig, 24, 24, 75, 125, fila_talla_24_60, columna_talla_24_60)
add_division(fig, 36, 36, 75, 125, fila_talla_24_60, columna_talla_24_60)
add_division(fig, 48, 48, 75, 125, fila_talla_24_60, columna_talla_24_60)
add_division(fig, 60, 60, 75, 125, fila_talla_24_60, columna_talla_24_60)

add_division(fig, 12, 12, 9, 23, fila_imc_0_5, columna_imc_0_5)
add_division(fig, 24, 24, 9, 23, fila_imc_0_5, columna_imc_0_5)
add_division(fig, 36, 36, 9, 23, fila_imc_0_5, columna_imc_0_5)
add_division(fig, 48, 48, 9, 23, fila_imc_0_5, columna_imc_0_5)
add_division(fig, 60, 60, 9, 23, fila_imc_0_5, columna_imc_0_5)

# Textos
def add_anotacion_figura(fig, texto, x, y, row, col):
    fig.add_annotation(
        go.layout.Annotation(
            text=texto,
            x=x,
            y=y,
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=30,
            xshift=0,  # Ajuste horizontal
            yshift=-25  # Ajuste vertical
        ), row=row, col=col
    )

add_anotacion_figura(fig, "1 año", 12, 5, fila_peso_6_24, columna_peso_6_24)
add_anotacion_figura(fig, "2 años", 24, 5, fila_peso_6_24, columna_peso_6_24)

add_anotacion_figura(fig, "2 años", 24, 7, fila_peso_24_60, columna_peso_24_60)
add_anotacion_figura(fig, "3 años", 36, 7, fila_peso_24_60, columna_peso_24_60)
add_anotacion_figura(fig, "4 años", 48, 7, fila_peso_24_60, columna_peso_24_60)
add_anotacion_figura(fig, "5 años", 60, 7, fila_peso_24_60, columna_peso_24_60)

add_anotacion_figura(fig, "1 año", 12, 55, fila_talla_6_24, columna_talla_6_24)
add_anotacion_figura(fig, "2 años", 24, 55, fila_talla_6_24, columna_talla_6_24)
add_anotacion_figura(fig, "2 años", 24, 75, fila_talla_24_60, columna_talla_24_60)
add_anotacion_figura(fig, "3 años", 36, 75, fila_talla_24_60, columna_talla_24_60)
add_anotacion_figura(fig, "4 años", 48, 75, fila_talla_24_60, columna_talla_24_60)
add_anotacion_figura(fig, "5 años", 60, 75, fila_talla_24_60, columna_talla_24_60)

add_anotacion_figura(fig, "1 año", 12, 9, fila_imc_0_5, columna_imc_0_5)
add_anotacion_figura(fig, "2 años", 24, 9, fila_imc_0_5, columna_imc_0_5)
add_anotacion_figura(fig, "3 años", 36, 9, fila_imc_0_5, columna_imc_0_5)
add_anotacion_figura(fig, "4 años", 48, 9, fila_imc_0_5, columna_imc_0_5)
add_anotacion_figura(fig, "5 años", 60, 9, fila_imc_0_5, columna_imc_0_5)

# Establecer el diseño general
fig.update_layout(
    title={
        'text': "Curvas de Crecimiento",
        'x': 0.5,  # Centrar el título horizontalmente
    },
    showlegend=True,
    height=2400,  # Altura
    width=1400, # Ancho
)

# endregion
# Guardar el gráfico en un archivo HTML
filename = 'grafico_curvas_plotly.html'
# Para desactivar la barra de herramientas se incluye config
pio.write_html(fig, file=filename, auto_open=False, config = {'displayModeBar': False})
