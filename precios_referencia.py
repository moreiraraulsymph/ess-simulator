# precios_referencia.py
# v2: Precios de referencia de baterías residenciales (rango € IVA incl., instalación incluida),
# tabla facilitada a Raúl el 29/10/2026 ("Precios de referencia para el simulador.png").
# Para actualizar precios basta con editar esta tabla: la lógica del simulador no tiene precios fijos.

TAMANOS_KWH = [5, 10, 15, 20]

MARCAS = {
    "solis": "Solis (48 V · Pylontech / Dyness)",
    "huawei": "Huawei (LUNA2000)",
}

# Clave: (marca, tamaño kWh) -> {"con_inversor": (min, max), "sin_inversor": (min, max)}
#   con_inversor = el cliente ya tiene inversor híbrido -> solo batería
#   sin_inversor = no tiene inversor híbrido -> batería + inversor híbrido
PRECIOS = {
    ("solis", 5):   {"con_inversor": (1900, 2400), "sin_inversor": (2900, 3600)},
    ("huawei", 5):  {"con_inversor": (2800, 3300), "sin_inversor": (4200, 4900)},
    ("solis", 10):  {"con_inversor": (3000, 3600), "sin_inversor": (4100, 4800)},
    ("huawei", 10): {"con_inversor": (4500, 5200), "sin_inversor": (5900, 6700)},
    ("solis", 15):  {"con_inversor": (4300, 4900), "sin_inversor": (5400, 6100)},
    ("huawei", 15): {"con_inversor": (6100, 6900), "sin_inversor": (7500, 8400)},
    ("solis", 20):  {"con_inversor": (5500, 6400), "sin_inversor": (6600, 7600)},
    ("huawei", 20): {"con_inversor": (8200, 9200), "sin_inversor": (9600, 10700)},
}


def rango_precio(marca, kwh, tiene_inversor):
    """Devuelve (min, max) en € para la configuración elegida."""
    clave = "con_inversor" if tiene_inversor else "sin_inversor"
    return PRECIOS[(marca, kwh)][clave]


def precio_medio(marca, kwh, tiene_inversor):
    lo, hi = rango_precio(marca, kwh, tiene_inversor)
    return round((lo + hi) / 2 / 50) * 50          # redondeado a 50 €
