# calculations.py  -  simple but robust B2C storage simulator (hourly, 8760 h)
# v2 (Carlos, 29/10/2026): perfiles de consumo, tope de ciclos, potencia contratada y criterio año 1. Cambios marcados con '# v2'.
# v2.2 (30/10/2026): solo velocidad (cachés y bucle con floats de Python). Los resultados son idénticos, comprobado con comprobar.py.
# v2.3 (30/10/2026): dos correcciones de criterio, marcadas con '# v2.3' (autosuficiencia y regla "solo año 1").
from dataclasses import dataclass, replace
from functools import lru_cache
import numpy as np

HOURS = 8760
DAYS_IN_MONTH = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


@dataclass(frozen=True)
class Params:
    # --- PV ---
    pv_yield: float = 1500.0          # kWh/kWp/year (Spain: ~1,300 north .. 1,800 south)
    # --- Battery ---
    round_trip: float = 0.90          # AC-AC round-trip efficiency
    dod: float = 0.90                 # usable fraction of nameplate capacity
    c_rate: float = 0.5               # max (dis)charge power = c_rate * capacity [kW]
    margin: float = 0.02              # min €/kWh spread (beyond losses) to bother cycling
    # --- Tariff: FINAL prices incl. peajes/cargos/IEE/IVA, €/kWh ---
    prices: tuple = (0.28, 0.18, 0.10)  # P1 punta, P2 llano, P3 valle
    fixed_price: float = 0.17         # flat-rate tariff, final €/kWh
    export_price: float = 0.06        # simplified surplus compensation €/kWh
    price_scale: float = 1.0          # multiplies ALL prices (sensitivity runs)
    # --- Economics ---
    degradation: float = 0.02         # yearly loss of savings (battery ageing)
    price_escalation: float = 0.02    # yearly growth of electricity prices
    lifetime: int = 15                # years
    seed: int = 42
    # v2: nuevos parámetros (los valores por defecto mantienen el comportamiento de v1 salvo el tope de ciclos)
    contracted_kw: float = float("inf")  # v2: potencia contratada [kW]: la carga desde red no la supera
    max_cycles_day: float = 1.0          # v2: tope de ciclos equivalentes al día (1 ciclo/día por defecto)
    supply_year1_only: bool = False      # v2: True = ahorro por tarifa indexada solo en el año 1 (criterio C&I)
    profile: str = "estandar"            # v2: perfil de consumo: estandar / dia / tarde


# ----------------------------------------------------------------- calendar
def _frozen(*arrays):
    """v2.2: los perfiles se cachean; se marcan de solo lectura para que nadie los modifique por error."""
    for a in arrays:
        a.setflags(write=False)
    return arrays if len(arrays) > 1 else arrays[0]


@lru_cache(maxsize=None)                             # v2.2: mismo calendario siempre -> se calcula una vez
def _calendar():
    idx = np.arange(HOURS)
    hour = idx % 24
    day = idx // 24
    dow = day % 7                                    # 1 Jan assumed Monday
    month = np.repeat(np.arange(12), DAYS_IN_MONTH)[day]
    return _frozen(hour, day, dow, month)


# ----------------------------------------------------------------- profiles
MONTH_SHARE = np.array([5.0, 6.2, 8.5, 9.5, 10.8, 11.5, 12.3, 11.4, 9.3, 7.4, 5.4, 4.4])
DAYLENGTH = np.array([9.8, 10.7, 11.9, 13.1, 14.1, 14.6, 14.3, 13.4, 12.3, 11.1, 10.1, 9.5])


def pv_profile(kwp, p):
    """Hourly kW. Seasonal shape, random-but-reproducible cloudy days,
    scaled so the annual total = kwp * pv_yield."""
    return _pv_profile(float(kwp), float(p.pv_yield), p.seed)   # v2.2: cacheado (mismo resultado)


@lru_cache(maxsize=64)
def _pv_profile(kwp, pv_yield, seed):
    hour, day, _, month = _calendar()
    rng = np.random.default_rng(seed)
    clear = np.clip(rng.beta(5, 2, size=365), 0.25, 1.0)[day]
    t = hour + 0.5 - 13.5                            # hours from solar noon (CET/CEST avg)
    dl = DAYLENGTH[month]
    shape = np.where(np.abs(t) < dl / 2, np.cos(np.pi * t / dl), 0.0) * clear
    shares = MONTH_SHARE / MONTH_SHARE.sum()
    out = np.zeros(HOURS)
    for m in range(12):
        mask = month == m
        out[mask] = shape[mask] / shape[mask].sum() * kwp * pv_yield * shares[m]
    return _frozen(out)


_WEEKDAY = np.array([.35] * 7 + [.8, .9, .6] + [.5] * 4 + [.7, .6, .45, .5] + [.7, .9, 1.2, 1.4, 1.1, .7])
_WEEKEND = np.array([.35] * 8 + [.5, .8, .9, .9, .9, 1.0, 1.1, .9, .7, .7, .8, .9, 1.2, 1.4, 1.1, .7])
_SEASON = np.array([1.25, 1.15, 1.0, 0.9, 0.85, 0.9, 1.05, 1.05, 0.9, 0.9, 1.05, 1.2])


# v2: perfiles de consumo sencillos para que el instalador elija sin datos horarios
_PROFILE_BOOST = {
    "estandar": None,
    "dia": ((9, 17), 1.6),      # teletrabajo, aerotermia de día, negocio en casa
    "tarde": ((18, 23), 1.6),   # vivienda vacía de día, consumo concentrado al volver a casa
}


@lru_cache(maxsize=64)                               # v2.2: cacheado (mismo resultado)
def load_profile(annual_kwh, profile="estandar"):
    """Hourly kW, weekday/weekend shapes + seasonality, normalised to annual kWh."""
    hour, _, dow, month = _calendar()
    shape = np.where(dow >= 5, _WEEKEND[hour], _WEEKDAY[hour]) * _SEASON[month]
    boost = _PROFILE_BOOST.get(profile)                          # v2
    if boost:
        (h0, h1), k = boost
        shape = shape * np.where((hour >= h0) & (hour < h1), k, 1.0)
    return _frozen(shape / shape.sum() * annual_kwh)          # NB: kWh, not Wh (no *1000!)


def tou_prices(p):
    """2.0TD: weekends/holidays are all P3 (valle)."""
    hour, _, dow, _ = _calendar()
    punta = ((hour >= 10) & (hour < 14)) | ((hour >= 18) & (hour < 22))
    llano = ((hour >= 8) & (hour < 10)) | ((hour >= 14) & (hour < 18)) | (hour >= 22)
    price = np.where(punta, p.prices[0], np.where(llano, p.prices[1], p.prices[2]))
    return np.where(dow >= 5, p.prices[2], price)


@lru_cache(maxsize=None)                             # v2.2: cacheado (mismo resultado)
def synthetic_indexed_prices():
    """PLACEHOLDER duck-curve. Replace with real OMIE/ESIOS hourly data
    (8760 values, final €/kWh incl. tolls and taxes) for credible results."""
    hour, _, _, month = _calendar()
    summerish = np.sin(np.pi * (month + 0.5) / 12) ** 0.5
    spot = (0.08 + 0.07 * ((hour >= 19) & (hour < 23)) + 0.03 * ((hour >= 8) & (hour < 10))
            - 0.07 * summerish * ((hour >= 11) & (hour < 17)))
    tolls = np.where(((hour >= 10) & (hour < 14)) | ((hour >= 18) & (hour < 22)), 0.03,
                     np.where(hour < 8, 0.003, 0.015))
    return _frozen((np.clip(spot, 0.0, None) + tolls) * 1.21)


# ----------------------------------------------------------------- dispatch
def dispatch(load, pv, price, cap, p, grid_charge):
    """One hourly battery engine for every scenario.
    grid_charge=False -> pure self-consumption (charge from PV surplus only)
    grid_charge=True  -> also charges from the grid in the day's cheapest hours,
                         only as much as it expects to use, leaving room for PV."""
    n = len(load)
    if cap <= 0:                                 # v2.2: sin batería -> resultado directo, sin bucle (idéntico)
        net = np.asarray(load) - np.asarray(pv)
        imp = np.where(net >= 0, net, 0.0)
        exp = np.where(net < 0, -net, 0.0)
        cost = float((imp * price).sum() - (exp * p.export_price * p.price_scale).sum())
        return {"cost": cost, "imp": imp, "exp": exp, "grid_chg": np.zeros(n), "cycles": 0.0}
    usable = cap * p.dod
    pmax = cap * p.c_rate
    eta = p.round_trip ** 0.5
    imp, exp, grid_chg = [0.0] * n, [0.0] * n, [0.0] * n   # v2.2: listas de Python (3-4x más rápido)
    load_l, pv_l, price_l = np.asarray(load).tolist(), np.asarray(pv).tolist(), np.asarray(price).tolist()
    soc = throughput = 0.0
    day_cap = p.max_cycles_day * usable          # v2: energía máxima descargable al día (tope de ciclos)

    days = n // 24
    if grid_charge:                              # v2.2: percentil y máximo de todos los días de una vez (idéntico)
        price_days = np.asarray(price)[:days * 24].reshape(days, 24)
        p25_days, max_days = np.percentile(price_days, 25, axis=1), price_days.max(axis=1)

    for d in range(days):
        a, b = d * 24, (d + 1) * 24
        day_out = 0.0                            # v2
        floor, cheap, target = -np.inf, -np.inf, 0.0     # defaults: discharge always
        if grid_charge and usable > 0:
            dp = price[a:b]
            c = p25_days[d]
            f = c / p.round_trip + p.margin              # min price worth discharging into
            if max_days[d] >= f:                         # there is a real spread today
                floor, cheap = f, c + 1e-9
                net = load[a:b] - pv[a:b]
                need = np.clip(net, 0, None)[dp >= f].sum() / eta   # stored kWh needed
                from_pv = np.clip(-net, 0, None).sum() * eta        # PV will refill this much
                target = float(np.clip(min(need, usable) - from_pv, 0, usable))

        for h in range(a, b):
            net = load_l[h] - pv_l[h]
            if net < 0:                                  # PV surplus -> battery, rest exported
                c_in = min(-net, pmax, (usable - soc) / eta)
                soc += c_in * eta
                exp[h] = -net - c_in
            else:                                        # deficit
                dis = 0.0
                if price_l[h] >= floor:
                    dis = min(net, pmax, soc * eta, max(day_cap - day_out, 0.0) * eta)   # v2: tope de ciclos
                    soc -= dis / eta
                    throughput += dis / eta
                    day_out += dis / eta
                imp[h] = net - dis
                if price_l[h] <= cheap and soc < target:   # cheap hour -> top up from grid
                    g = min(pmax, (target - soc) / eta, max(p.contracted_kw - imp[h], 0.0))   # v2: potencia contratada
                    soc += g * eta
                    imp[h] += g
                    grid_chg[h] = g

    imp, exp, grid_chg = np.array(imp), np.array(exp), np.array(grid_chg)
    cost = float((imp * price).sum() - (exp * p.export_price * p.price_scale).sum())
    return {"cost": cost, "imp": imp, "exp": exp, "grid_chg": grid_chg,
            "cycles": throughput / usable if usable > 0 else 0.0}


# ----------------------------------------------------------------- economics
def payback_and_net(investment, year1_saving, p, supply_part=0.0):
    """Payback (years, inf if never within lifetime) and net lifetime gain.
    v2.1: si p.supply_year1_only, la parte del ahorro debida al cambio de tarifa (supply_part) solo cuenta en el año 1."""
    cum, payback = 0.0, float("inf")
    for y in range(1, p.lifetime + 1):
        base = year1_saving - (supply_part if (p.supply_year1_only and y > 1) else 0.0)   # v2
        s = base * (1 - p.degradation) ** (y - 1) * (1 + p.price_escalation) ** (y - 1)
        if payback == float("inf") and cum + s >= investment and s > 0:
            payback = (y - 1) + (investment - cum) / s
        cum += s
    return payback, cum - investment


def _price_curves(p, tariff, indexed_prices):
    base = tou_prices(p) if tariff == "2.0TD" else np.full(HOURS, p.fixed_price)
    idx = indexed_prices if indexed_prices is not None else synthetic_indexed_prices()
    return base * p.price_scale, np.asarray(idx) * p.price_scale


def run_simulation(pv_power, battery_capacity, annual_consumption, battery_cost,
                   p=Params(), tariff="2.0TD", indexed_prices=None):
    """tariff: "2.0TD" (peak/flat/valley) or "fixed" (single price) = customer's CURRENT tariff.
    Reference for all savings = same house, PV but NO battery, on the current tariff.
    Coherence: savings = supply_savings + battery_savings, and
    battery_savings = selfcons_part + arbitrage_part (symphonics scenario)."""
    pv = pv_profile(pv_power, p)
    load = load_profile(annual_consumption, p.profile)          # v2: perfil elegido
    base, idx = _price_curves(p, tariff, indexed_prices)

    ref = dispatch(load, pv, base, 0, p, False)          # PV only, current tariff
    pv_idx = dispatch(load, pv, idx, 0, p, False)        # PV only, indexed tariff
    r_std = dispatch(load, pv, base, battery_capacity, p, False)
    r_idx = dispatch(load, pv, idx, battery_capacity, p, False)
    r_sym = dispatch(load, pv, idx, battery_capacity, p, True)
    if r_sym["cost"] > r_idx["cost"]:                    # optimiser never does worse than no optimiser
        r_sym = r_idx
    # v2.1 (criterio Raúl): si la optimización no genera ahorro no se envían consignas, así que la
    # batería optimizada nunca puede ser peor que la estándar EN LA MISMA TARIFA. Escenario extra:
    # optimización Symphonics manteniendo la tarifa actual del cliente.
    r_cur = dispatch(load, pv, base, battery_capacity, p, True)
    if r_cur["cost"] > r_std["cost"]:
        r_cur = r_std

    # v2.1: descomposición separada del ahorro de Symphonics frente a la batería estándar
    #   tariff_effect = cambio a tarifa indexada (con batería sin optimizar)  -> puede ser negativo
    #   optim_effect  = optimización Symphonics sobre la tarifa indexada      -> siempre >= 0
    tariff_effect = r_std["cost"] - r_idx["cost"]
    optim_effect = r_idx["cost"] - r_sym["cost"]

    # (resultado, parte del ahorro debida al cambio de tarifa)
    # v2.3: la regla "solo año 1" es conservadora: retira la VENTAJA de la tarifa a partir del año 2.
    # Si la tarifa indexada sale más cara (efecto negativo), esa desventaja se mantiene todos los años
    # (antes se quitaba y el payback mejoraba al marcar la opción, que no tiene sentido).
    tariff_part = max(tariff_effect, 0.0)
    scen = {"standard": (r_std, 0.0), "indexed": (r_idx, tariff_part),
            "symphonics": (r_sym, tariff_part), "symphonics_current": (r_cur, 0.0)}
    out = {}
    for name, (r, tariff_part) in scen.items():
        total = ref["cost"] - r["cost"]
        on_idx = name in ("indexed", "symphonics")
        supply = (ref["cost"] - pv_idx["cost"]) if on_idx else 0.0
        # v2.1: con el criterio "solo año 1" se descuenta a partir del año 2 SOLO el efecto del
        # cambio de tarifa (no el ahorro de suministro sin batería), para no penalizar la optimización.
        pb, net = payback_and_net(battery_cost, max(total, 0.0), p, tariff_part)
        out[name] = {
            "savings": float(total),
            "supply_savings": float(supply),
            "battery_savings": float(total - supply),
            "payback": float(pb),
            "lifetime_net": float(net),
            "cycles": float(r["cycles"]),
            "self_consumption": float(1 - r["exp"].sum() / pv.sum()) if pv.sum() > 0 else 0.0,   # v2: sin FV
            # v2.3: parte del consumo que NO se compra a la red. Antes se restaba la carga desde red, así que la
            # energía de red guardada en la batería contaba como "autosuficiente" (sin FV salía un 41 %).
            "self_sufficiency": float(max(0.0, 1 - r["imp"].sum() / load.sum())),
        }
    out["symphonics"]["selfcons_part"] = float(pv_idx["cost"] - r_idx["cost"])
    out["symphonics"]["arbitrage_part"] = float(r_idx["cost"] - r_sym["cost"])
    out["diagnosis"] = {                                                      # v2.1
        "standard_savings": float(ref["cost"] - r_std["cost"]),
        "tariff_effect": float(tariff_effect),
        "optim_effect": float(optim_effect),
        "optim_current_effect": float(r_std["cost"] - r_cur["cost"]),
    }
    out["context"] = {"pv_kwh": float(pv.sum()), "load_kwh": float(load.sum()),
                      "bill_no_pv": float((load * base).sum()), "bill_pv_only": float(ref["cost"])}
    return out


def run_range(pv_power, battery_capacity, annual_consumption, battery_cost,
              p=Params(), tariff="2.0TD", indexed_prices=None, spread=0.10):
    """Sensitivity: PV yield and prices both -/+ spread. Returns the Symphonics
    total savings (low, high) and payback (best, worst)."""
    lo = replace(p, pv_yield=p.pv_yield * (1 - spread), price_scale=p.price_scale * (1 - spread))
    hi = replace(p, pv_yield=p.pv_yield * (1 + spread), price_scale=p.price_scale * (1 + spread))
    a = run_simulation(pv_power, battery_capacity, annual_consumption, battery_cost, lo, tariff, indexed_prices)["symphonics"]
    b = run_simulation(pv_power, battery_capacity, annual_consumption, battery_cost, hi, tariff, indexed_prices)["symphonics"]
    return {"savings": (a["savings"], b["savings"]), "payback": (b["payback"], a["payback"])}