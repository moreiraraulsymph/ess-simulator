# comprobar.py — v2.2: comprobación rápida de que el motor da las cifras validadas (v2.3: + autosuficiencia).
# Uso:  python comprobar.py      (sin dependencias extra; tarda unos segundos)
# Si alguien toca calculations.py y cambia una cifra sin querer, aquí sale FALLO.
import sys
from dataclasses import replace

from calculations import Params, run_simulation, run_range

P = Params(prices=(0.28, 0.22, 0.16))
fallos = 0


def check(nombre, valor, esperado, dec=0):
    global fallos
    v = round(valor, dec) if dec else round(valor)
    ok = v == esperado
    fallos += not ok
    print(f"  {'OK   ' if ok else 'FALLO'} {nombre}: {v} (esperado {esperado})")


print("Caso de referencia residencial (4,5 kWp · 5 kWh · 7.500 kWh · 2.500 €)")
r = run_simulation(4.5, 5, 7500, 2500, P)
s, rng = r["symphonics"], run_range(4.5, 5, 7500, 2500, P)
check("autoconsumo €/año", s["selfcons_part"], 188)
check("arbitraje €/año", s["arbitrage_part"], 15)
check("suministro €/año", s["supply_savings"], 196)
check("ahorro total €/año", s["savings"], 399)
check("payback estándar (años)", r["standard"]["payback"], 10.3, 1)
check("payback Symphonics (años)", s["payback"], 6.3, 1)
check("rango bajo €/año", rng["savings"][0], 363)
check("rango alto €/año", rng["savings"][1], 438)
check("ganancia neta 15 años €", s["lifetime_net"], 3462)
check("ciclos/año", s["cycles"], 357)
check("autosuficiencia % (v2.3)", s["self_sufficiency"] * 100, 60)

print("Caso de Raúl (5,5 kWp · 10 kWh · 9.000 kWh · 8,05 kW · 3.300 €)")
q = replace(P, contracted_kw=8.05)
r = run_simulation(5.5, 10, 9000, 3300, q)
check("payback estándar (años)", r["standard"]["payback"], 8.2, 1)
check("payback Symphonics (años)", r["symphonics"]["payback"], 5.9, 1)
check("efecto tarifa €/año", r["diagnosis"]["tariff_effect"], 128)
check("efecto optimización €/año", r["diagnosis"]["optim_effect"], 31)
r = run_simulation(5.5, 10, 9000, 3300, replace(q, supply_year1_only=True))
check("payback Symphonics, tarifa solo año 1", r["symphonics"]["payback"], 7.3, 1)
r = run_simulation(5.5, 10, 9000, 3300, replace(q, prices=(0.28, 0.18, 0.10)))
check("P2/P3 baratos: efecto tarifa €/año", r["diagnosis"]["tariff_effect"], -9)
check("P2/P3 baratos: payback manteniendo tarifa", r["symphonics_current"]["payback"], 8.8, 1)
r = run_simulation(5.5, 10, 9000, 3300, replace(q, prices=(0.28, 0.18, 0.10), supply_year1_only=True))
check("P2/P3 baratos + solo año 1: payback (v2.3, ya no mejora)", r["symphonics"]["payback"], 9.2, 1)

print("Sin fotovoltaica (0 kWp · 10 kWh · 7.500 kWh)")
r = run_simulation(0, 10, 7500, 4450, P)
check("autosuficiencia % (v2.3, antes 41)", r["symphonics"]["self_sufficiency"] * 100, 0)

print("\nTODO OK" if not fallos else f"\n{fallos} FALLO(S)")
sys.exit(1 if fallos else 0)
