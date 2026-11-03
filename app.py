# app.py — Simulador de Baterías para Pequeños Consumidores (v2.3)
# v2   (Carlos, 29/10/2026): castellano, tarjetas tipo simulador de Francia, colores Symphonics,
#       recomendación de tamaño con precios de referencia, perfil, potencia contratada, 1 ciclo/día.
# v2.1 (Carlos, 30/10/2026) — revisión de Raúl:
#       logo Symphonics · campos numéricos siempre legibles · traducciones ES/EN/PT recuperadas ·
#       navy #1d3960 · informe HTML descargable · sin pandas (st.dataframe -> tabla HTML) ·
#       FV = 0 -> inversor híbrido "No" · payback: efecto tarifa y efecto optimización separados.
# v2.2 (Carlos, 30/10/2026) — repaso antes de entregar (sin tocar ninguna cifra):
#       nombre del cliente y fecha en el informe · diagnóstico en forma de suma · aviso si ningún tamaño
#       se amortiza · aviso de precios P1/P2/P3 desordenados · ayudas en los campos · restaurar hipótesis ·
#       "Ocultar informe" · sin FV el autoconsumo FV sale "—" · diseño móvil · cálculo ~3x más rápido ·
#       casos de validación de un clic · tema claro aunque no se lea .streamlit/config.toml · versión al pie.
# v2.3 (Carlos, 30/10/2026): autosuficiencia corregida · regla "solo año 1" conservadora · ganancia neta con
#       signo · si la indexada sale más cara, se muestra también el payback manteniendo la tarifa actual.
import base64
import re
import unicodedata
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from calculations import Params, run_simulation, run_range
from precios_referencia import MARCAS, TAMANOS_KWH, rango_precio, precio_medio
from report_generator import (generate_html_report, fmt_payback, eur, eur_signed, fmt_num,
                              comparison_table_html, diagnosis_html, NAVY)
from textos import TEXTOS

POTENCIAS_KW = [3.45, 4.6, 5.75, 6.9, 8.05, 9.2, 10.35, 11.5, 14.49]
PV_OPCIONES = [x / 2 for x in range(0, 31)]
ASSETS = Path(__file__).parent / "assets"


def load_logo():
    """Logo oficial (assets/logo_symphonics.png) en base64; None si no está."""
    f = ASSETS / "logo_symphonics.png"
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else None


LOGO_B64 = load_logo()

# v2.2: tema claro de Symphonics aunque Streamlit no encuentre .streamlit/config.toml
# (pasa si se lanza "streamlit run" desde otra carpeta: Streamlit busca la config en la carpeta actual,
#  no en la de app.py; con el PC en modo oscuro las cajas salían oscuras). Mismos valores que config.toml.
THEME = {"theme.base": "light", "theme.primaryColor": "#e6007e", "theme.backgroundColor": "#fdf0f6",
         "theme.secondaryBackgroundColor": "#ffffff", "theme.textColor": NAVY}


def ensure_theme():
    try:
        from streamlit import config as st_config
        missing = {k: v for k, v in THEME.items() if st_config.get_option(k) != v}
        for k, v in missing.items():
            st_config.set_option(k, v)
        return bool(missing)
    except Exception:        # versión de Streamlit sin esta opción: se queda el CSS de abajo
        return False


# v2.2: valores por defecto de las hipótesis avanzadas, en un solo sitio (son los mismos de la v2.1)
ADV = {"pv_yield": 1500, "rt": 90, "esc": 2.0, "cyc": 1.0, "p1": 0.28, "p2": 0.22, "p3": 0.16,
       "fixed": 0.17, "export": 0.06, "year1": False}


def slug(text):
    """v2.2: nombre de archivo seguro (sin tildes ni símbolos) a partir del nombre del cliente."""
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:40]


def reset_advanced():
    st.session_state.update(ADV)


# --------------------------------------------------------------------------------- 1. PÁGINA Y ESTILO
st.set_page_config(page_title="Simulador baterías · Symphonics", page_icon="🔋", layout="wide")
if ensure_theme() and not st.session_state.get("_theme_rerun"):
    st.session_state["_theme_rerun"] = True   # como mucho una vez por sesión: nunca entra en bucle
    st.rerun()               # el tema se aplica en la siguiente ejecución
st.markdown(f"""
<style>
:root {{ --navy:{NAVY}; --magenta:#e6007e; --teal:#2ec4b6; --yellow:#fff3c4; --lime:#c5e86c; --pink:#fdf0f6;
         color-scheme: light; }}
.stApp {{ background: var(--pink); }}
.block-container {{ padding-top: 2.2rem; max-width: 1200px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none; }}
h1, h2, h3, h4, p, label, span, div {{ color: var(--navy); }}
/* v2.1: campos numéricos y selectores siempre legibles (también si el navegador está en modo oscuro) */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div {{
    background: #f6f7fb !important; border: 1px solid #d9dee8 !important; border-radius: 10px !important; }}
[data-baseweb="input"] input, [data-baseweb="base-input"] input, [data-testid="stNumberInput"] input {{
    color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important;
    background: #f6f7fb !important; font-weight: 600; opacity: 1 !important; }}
/* v2.2: caja de texto (nombre del cliente) con el mismo aspecto que las numéricas */
[data-testid="stTextInputRootElement"] {{ background: #f6f7fb !important; border: 1px solid #d9dee8 !important;
    border-radius: 10px !important; }}
[data-testid="stTextInputRootElement"] input {{ color: var(--navy) !important; -webkit-text-fill-color: var(--navy) !important; }}
input::placeholder {{ color: #9aa5b8 !important; -webkit-text-fill-color: #9aa5b8 !important; font-weight: 400; }}
/* v2.2: solo los botones − / + (antes también pintaba el icono de ayuda "?" como un punto negro) */
[data-testid="stNumberInput"] button[data-testid^="stNumberInputStep"] {{ background: #eef1f7 !important; color: var(--navy) !important; }}
[data-testid="stNumberInput"] button[data-testid^="stNumberInputStep"] svg {{ fill: var(--navy) !important; }}
[class*="st-key-card"] {{ background: #ffffff; border-radius: 18px; padding: 22px 24px;
    box-shadow: 0 4px 14px rgba(29,57,96,0.06); border: none !important; }}
.sy-badge {{ background: var(--magenta); color: #fff !important; padding: 3px 12px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; margin-left: 12px; vertical-align: middle; }}
.sy-logo {{ height: 38px; vertical-align: middle; }}
.sy-brand {{ font-weight: 800; letter-spacing: 3px; color: var(--navy); font-size: 0.9rem; }}
.sy-icon {{ display:inline-flex; align-items:center; justify-content:center; width:42px; height:42px;
    border-radius: 12px; margin-right: 12px; font-size: 1.3rem; }}
.sy-card-title {{ display:flex; align-items:center; font-weight: 700; font-size: 1.15rem; margin-bottom: 8px; }}
.sy-reco-circle {{ width: 84px; height: 84px; border-radius: 50%; background: var(--yellow); margin: 8px auto;
    display:flex; align-items:center; justify-content:center; font-size: 2.2rem; }}
.sy-reco-value {{ text-align:center; font-size: 2.6rem !important; font-weight: 800; color: #a86400 !important; margin: 0; line-height: 1.1; }}
.sy-reco-sub {{ text-align:center; color: #5c7088 !important; margin: 0 0 10px; }}
.sy-summary {{ background: #f6f7fb; border-radius: 12px; padding: 12px 16px; font-size: 0.92rem; }}
.sy-summary div {{ display:flex; justify-content: space-between; padding: 3px 0; }}
.sy-row {{ display:flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid #eee; }}
.sy-row b {{ white-space: nowrap; }}
.sy-big {{ font-size: 2rem !important; font-weight: 800; color: var(--magenta) !important; margin: 6px 0 0; }}
.sy-pill {{ border-radius: 10px; padding: 9px 14px; font-weight: 700; color: #fff !important; font-size: 1.15rem; }}
.sy-kpi {{ text-align:center; }}
.sy-kpi b {{ font-size: 1.5rem; display:block; }}
.sy-kpi span {{ color: #5c7088 !important; font-size: 0.85rem; }}
div.stButton > button, div.stDownloadButton > button {{ background: var(--magenta); color: #fff; border: none;
    border-radius: 10px; font-weight: 700; }}
div.stButton > button p, div.stDownloadButton > button p {{ color: #fff; }}
/* v2.2: botón secundario (restaurar) discreto */
.st-key-reset_adv button {{ background: #ffffff !important; color: var(--navy) !important; border: 1px solid #d9dee8 !important; }}
.st-key-reset_adv button p {{ color: var(--navy) !important; }}
.st-key-case_ref button, .st-key-case_raul button {{ background: #ffffff !important; border: 1px solid #d9dee8 !important; }}
.st-key-case_ref button p, .st-key-case_raul button p {{ color: var(--navy) !important; }}
.sy-reco-warn {{ background: #fdecc8 !important; color: #a86400 !important; }}
.sy-note {{ text-align:center; font-size: 0.85rem; color: #a86400 !important; margin: 0 0 8px; }}
/* v2.2: móvil */
@media (max-width: 640px) {{
  h1 {{ font-size: 1.9rem !important; }}
  [class*="st-key-card"] {{ padding: 16px 14px; }}
  .sy-reco-value {{ font-size: 2.1rem !important; }}
}}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------- 2. CABECERA + IDIOMA
h1, h2 = st.columns([6, 1])
with h2:
    lang = st.selectbox("Idioma", list(TEXTOS), index=0, label_visibility="collapsed", key="lang")
t = TEXTOS[lang]
with h1:
    logo = (f'<img class="sy-logo" src="data:image/png;base64,{LOGO_B64}" alt="Symphonics">' if LOGO_B64
            else '<span class="sy-brand">SYMPHONICS</span>')
    st.markdown(f'{logo}<span class="sy-badge">{t["badge"]}</span>', unsafe_allow_html=True)
st.title(t["title"])
st.write(t["subtitle"])


def num(x, dec=2):
    return fmt_num(x, t, dec)


def keep(widget, label, options, base_key, default, **kw):
    """v2.1: widget con textos traducidos que conserva su valor al cambiar de idioma.
    La clave incluye el idioma (Streamlit reinicia el widget si cambia el texto de las opciones);
    el último valor elegido se guarda aparte y se reaplica en el idioma nuevo."""
    store, key = f"_v_{base_key}", f"{base_key}_l{list(TEXTOS).index(lang)}"
    if st.session_state.get(key) not in options:          # v2.2: valor inicial vía session_state
        value = st.session_state.get(store, default)
        st.session_state[key] = value if value in options else default
    out = widget(label, options, key=key, **kw)
    st.session_state[store] = out
    return out


def set_kept(base_key, value):
    """v2.2: fija el valor de un widget creado con keep() en todos los idiomas."""
    st.session_state[f"_v_{base_key}"] = value
    for i in range(len(TEXTOS)):
        st.session_state[f"{base_key}_l{i}"] = value


# v2.2: casos de validación (mismas cifras que README y comprobar.py)
CASOS = {
    "ref": {"consumo": 7500, "potencia": 5.75, "pv": 4.5, "kwh": 5, "coste": 2500},
    "raul": {"consumo": 9000, "potencia": 8.05, "pv": 5.5, "kwh": 10, "coste": 3300},
}


def load_case(name):
    c = CASOS[name]
    st.session_state.update(ADV)
    st.session_state["consumo"] = c["consumo"]
    st.session_state["marca"] = "solis"
    for base, v in [("potencia", c["potencia"]), ("pv", c["pv"]), ("perfil", "estandar"),
                    ("tarifa", "2.0TD"), ("inversor_confv", True)]:
        set_kept(base, v)
    st.session_state["kwh"] = c["kwh"]
    st.session_state["_keep_kwh"] = True
    st.session_state[f"coste_solis_{c['kwh']}_True"] = c["coste"]


# --------------------------------------------------------------------------------- 3. SIMULACIÓN (cacheada)
@st.cache_data(show_spinner=False)
def simulate(pv, batt, cons, cost, tariff, p):
    return run_simulation(pv, batt, cons, cost, p, tariff), run_range(pv, batt, cons, cost, p, tariff)


@st.cache_data(show_spinner=False)
def recommend(pv, cons, tariff, marca, tiene_inv, p):
    """Simula los 4 tamaños con su precio medio de referencia y elige el de mayor ganancia neta
    en la vida útil entre los que se amortizan (a igualdad, el más pequeño)."""
    filas = []
    for kwh in TAMANOS_KWH:
        coste = precio_medio(marca, kwh, tiene_inv)
        r = run_simulation(pv, kwh, cons, coste, p, tariff)["symphonics"]
        filas.append({"kwh": kwh, "coste": coste, "ahorro": r["savings"], "payback": r["payback"],
                      "neta": r["lifetime_net"], "ciclos": r["cycles"]})
    validas = [f for f in filas if f["payback"] != float("inf")]
    mejor = max(validas, key=lambda f: (round(f["neta"], -1), -f["kwh"])) if validas else filas[0]
    return mejor["kwh"], filas


# --------------------------------------------------------------------------------- 4. ENTRADAS + RECOMENDACIÓN
col_in, col_reco = st.columns([1.05, 1], gap="large")

with col_in:
    with st.container(key="card_inputs"):
        st.markdown(f'<div class="sy-card-title"><span class="sy-icon" style="background:#fde3f0;">🏠</span>'
                    f'{t["card_client"]}</div>', unsafe_allow_html=True)
        cliente = st.text_input(t["client_name"], max_chars=60, placeholder=t["client_ph"],
                                help=t["client_help"], key="cliente").strip()
        st.session_state.setdefault("consumo", 7500)
        consumo = st.number_input(t["consumption"], 1500, 20000, step=250, help=t["consumption_help"], key="consumo")
        potencia = keep(st.select_slider, t["contracted"], POTENCIAS_KW, "potencia", 5.75, format_func=lambda x: num(x),
                        help=t["contracted_help"])
        pv = keep(st.select_slider, t["pv"], PV_OPCIONES, "pv", 4.5, format_func=lambda x: f"{num(x, 1)} kWp",
                  help=t["pv_help"])
        perfil = keep(st.radio, t["profile_q"], list(t["profiles"]), "perfil", list(t["profiles"])[0],
                      format_func=t["profiles"].get, horizontal=True)
        c1, c2 = st.columns(2)
        with c1:
            # v2.1: sin fotovoltaica -> "No" por defecto (la clave cambia al cruzar 0 para reiniciar el valor)
            tiene_inv = keep(st.radio, t["inverter_q"], [True, False], f"inversor_{'sinfv' if pv == 0 else 'confv'}",
                             pv != 0, format_func=lambda x: t["yes"] if x else t["no"], help=t["inverter_help"],
                             horizontal=True)
        with c2:
            tarifa = keep(st.radio, t["tariff_q"], ["2.0TD", "fixed"], "tarifa", "2.0TD", horizontal=True,
                          format_func=lambda k: t["tariff_2td"] if k == "2.0TD" else t["tariff_fixed"])
        marca = st.radio(t["brand_q"], list(MARCAS), format_func=MARCAS.get, horizontal=True, key="marca")

    with st.expander(t["advanced"]):
        a1, a2 = st.columns(2)
        # v2.2: el valor inicial sale de ADV vía session_state (así "Restaurar" también actualiza la pantalla)
        for k, v in ADV.items():
            st.session_state.setdefault(k, v)
        with a1:
            pv_yield = st.number_input(t["adv_yield"], 1000, 2000, step=50, key="pv_yield")
            round_trip = st.slider(t["adv_rt"], 80, 98, step=1, key="rt")
            escalation = st.slider(t["adv_esc"], 0.0, 6.0, step=0.5, key="esc")
            max_cyc = st.number_input(t["adv_cyc"], 0.5, 2.0, step=0.1, help=t["adv_cyc_help"], key="cyc")
        with a2:
            p1 = st.number_input(t["adv_p1"], 0.05, 0.60, step=0.01, format="%.2f", key="p1")
            p2 = st.number_input(t["adv_p2"], 0.05, 0.60, step=0.01, format="%.2f", key="p2")
            p3 = st.number_input(t["adv_p3"], 0.03, 0.60, step=0.01, format="%.2f", key="p3")
            fixed = st.number_input(t["adv_fixed"], 0.05, 0.60, step=0.01, format="%.2f", key="fixed")
            export = st.number_input(t["adv_export"], 0.0, 0.30, step=0.01, format="%.2f", key="export")
        year1 = st.checkbox(t["adv_year1"], help=t["adv_year1_help"], key="year1")
        st.button(t["reset_adv"], on_click=reset_advanced, key="reset_adv")

params = Params(pv_yield=float(pv_yield), round_trip=round_trip / 100, prices=(p1, p2, p3),
                fixed_price=fixed, export_price=export, price_escalation=escalation / 100,
                contracted_kw=float(potencia), max_cycles_day=float(max_cyc),
                supply_year1_only=bool(year1), profile=perfil)

reco_kwh, tabla = recommend(pv, consumo, tarifa, marca, tiene_inv, params)
conf = t["only_battery"] if tiene_inv else t["battery_inverter"]

with col_reco:
    with st.container(key="card_reco"):
        st.markdown(f'<div class="sy-card-title"><span class="sy-icon" style="background:#c9f3ee;">🔋</span>'
                    f'{t["card_reco"]}</div>', unsafe_allow_html=True)
        lo_r, hi_r = rango_precio(marca, reco_kwh, tiene_inv)
        ninguno = all(f["payback"] == float("inf") for f in tabla)     # v2.2: ningún tamaño se amortiza
        st.markdown(f"""
            <div class="sy-reco-circle{' sy-reco-warn' if ninguno else ''}">{'!' if ninguno else '✓'}</div>
            <div class="sy-reco-value">{reco_kwh} kWh</div>
            {f'<p class="sy-note">{t["reco_none"].format(n=params.lifetime)}</p>' if ninguno else ''}
            <p class="sy-reco-sub">{MARCAS[marca]} · {conf}<br>
            {t['ref_price']}: <b>{eur(lo_r, t)} – {eur(hi_r, t)} €</b></p>""", unsafe_allow_html=True)
        # el tamaño vuelve a la recomendación cada vez que esta cambia (salvo al cargar un caso de validación)
        if st.session_state.get("_reco_seen") != reco_kwh or "kwh" not in st.session_state:
            if not st.session_state.get("_keep_kwh"):
                st.session_state["kwh"] = reco_kwh
            st.session_state["_reco_seen"] = reco_kwh
        st.session_state["_keep_kwh"] = False
        kwh = st.select_slider(t["size_sim"], TAMANOS_KWH, key="kwh")
        lo, hi = rango_precio(marca, kwh, tiene_inv)
        ckey = f"coste_{marca}_{kwh}_{tiene_inv}"         # cambia de marca/tamaño/inversor -> precio de referencia
        st.session_state.setdefault(ckey, precio_medio(marca, kwh, tiene_inv))
        coste = st.number_input(t["investment"].format(lo=eur(lo, t), hi=eur(hi, t)), 500, 30000, step=50, key=ckey)
        st.markdown(f"""
            <div class="sy-summary">
              <div><span>{t['sum_consumption']}</span><b>{eur(consumo, t)} kWh</b></div>
              <div><span>{t['sum_contracted']}</span><b>{num(potencia)} kW</b></div>
              <div><span>{t['sum_pv']}</span><b>{num(pv, 1)} kWp</b></div>
              <div><span>{t['sum_profile']}</span><b>{t['profiles'][perfil]}</b></div>
            </div>""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------- 5. RESULTADOS
results, rng = simulate(pv, kwh, consumo, coste, tarifa, params)
sym, std = results["symphonics"], results["standard"]
life = params.lifetime

# v2.3: si la tarifa indexada sale más cara, tercera barra con Symphonics manteniendo la tarifa actual
keep_pill = ""
if results["diagnosis"]["tariff_effect"] < 0:
    keep_pill = (f'<p style="margin:12px 0 4px;color:#5c7088;">{t["with_symphonics_current"]}</p>'
                 f'<div class="sy-pill" style="background:{NAVY};">'
                 f'{fmt_payback(results["symphonics_current"]["payback"], t, life)}</div>')

st.write("")
r1, r2, r3 = st.columns(3, gap="medium")
with r1:
    with st.container(key="card_savings"):
        st.markdown(f"""
            <div class="sy-card-title"><span class="sy-icon" style="background:#fde3f0;">€</span>{t['card_savings']}</div>
            <div class="sy-row"><span>{t['row_selfcons']}</span><b>~{eur(sym['selfcons_part'], t)} {t['per_year']}</b></div>
            <div class="sy-row"><span>{t['row_arbitrage']}</span><b>~{eur(sym['arbitrage_part'], t)} {t['per_year']}</b></div>
            <div class="sy-row" style="border:none;"><span>{t['row_supply']}</span><b>~{eur(sym['supply_savings'], t)} {t['per_year']}</b></div>
            <div class="sy-big">~{eur(sym['savings'], t)} {t['per_year']}</div>
            <p style="color:#5c7088;margin:0;">{t['range']}: {eur(rng['savings'][0], t)} – {eur(rng['savings'][1], t)} {t['per_year']}</p>
            """, unsafe_allow_html=True)
with r2:
    with st.container(key="card_payback"):
        st.markdown(f"""
            <div class="sy-card-title"><span class="sy-icon" style="background:#fff3c4;">⏱</span>{t['card_payback']}</div>
            <p style="margin:6px 0 4px;color:#5c7088;">{t['standard_battery']}</p>
            <div class="sy-pill" style="background:#5c7088;">{fmt_payback(std['payback'], t, life)}</div>
            <p style="margin:12px 0 4px;color:#5c7088;">{t['with_symphonics']}</p>
            <div class="sy-pill" style="background:#e6007e;">{fmt_payback(sym['payback'], t, life)}</div>
            {keep_pill}
            <p style="color:#888;font-size:0.85rem;margin:10px 0 0;">{t['investment_line'].format(cost=eur(coste, t))}</p>
            """, unsafe_allow_html=True)
with r3:
    with st.container(key="card_kpis"):
        st.markdown(f"""
            <div class="sy-card-title"><span class="sy-icon" style="background:#e9f7c8;">📈</span>{t['card_kpis']}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:8px;">
              <div class="sy-kpi"><b>{sym['self_sufficiency']*100:.0f} %</b><span>{t['kpi_selfsuff']}</span></div>
              <div class="sy-kpi"><b>{'—' if pv == 0 else f"{sym['self_consumption']*100:.0f} %"}</b><span>{t['kpi_selfcons']}</span></div>
              <div class="sy-kpi"><b>{sym['cycles']:.0f}</b><span>{t['kpi_cycles']}</span></div>
              <div class="sy-kpi"><b>{eur_signed(sym['lifetime_net'], t)} €</b><span>{t['lifetime_gain'].format(n=life)}</span></div>
            </div>""", unsafe_allow_html=True)

# v2.1: diagnóstico del payback — efecto de la optimización (>= 0) y efecto de la tarifa, por separado
# v2.2: presentado como suma: estándar + tarifa + optimización = total con Symphonics
with st.container(key="card_diag"):
    st.markdown(f'<div class="sy-card-title" style="font-size:1rem;">{t["diag_title"]}</div>'
                f'{diagnosis_html(results, t, life)}', unsafe_allow_html=True)
if tarifa == "2.0TD" and not (p1 >= p2 >= p3):
    st.warning(t["warn_price_order"])
if sym["payback"] > std["payback"] and std["payback"] != float("inf"):
    st.warning(t["warn_payback_tariff"])
if sym["payback"] == float("inf"):
    st.warning(t["warn_no_payback"].format(n=life))

# --------------------------------------------------------------------------------- 6. COMPARATIVA DE TAMAÑOS
with st.expander(t["compare"]):
    # v2.1: tabla HTML en lugar de st.dataframe (evita importar pandas, bloqueado en algunos PCs)
    st.markdown(comparison_table_html(tabla, reco_kwh, t, life), unsafe_allow_html=True)
    st.caption(t["compare_note"])

# --------------------------------------------------------------------------------- 7. ESTUDIOS TIPO E INFORME
st.write("")
e1, e2 = st.columns(2, gap="medium")
with e1:
    with st.container(key="card_studies"):
        st.markdown(f'<div class="sy-card-title"><span class="sy-icon" style="background:#e9f7c8;">📖</span>'
                    f'{t["card_studies"]}</div>', unsafe_allow_html=True)
        ref = ASSETS / "Caso_de_Referencia_Residencial.pdf"
        if ref.exists():
            st.download_button(t["study_btn"], ref.read_bytes(), file_name=ref.name, mime="application/pdf",
                               key="study")
        else:
            st.caption(t["study_missing"])
with e2:
    with st.container(key="card_offer"):
        st.markdown(f'<div class="sy-card-title"><span class="sy-icon" style="background:#fde3f0;">📄</span>'
                    f'{t["card_report"]}</div>', unsafe_allow_html=True)
        tariff_label = "2.0TD" if tarifa == "2.0TD" else t["tariff_fixed"]
        assumptions = t["assumptions_line"].format(y=eur(pv_yield, t), rt=round_trip, p1=num(p1), p2=num(p2),
                                                   p3=num(p3), fx=num(fixed), esc=num(escalation, 1),
                                                   cyc=num(max_cyc, 1))
        config_line = t["config_line"].format(brand=MARCAS[marca], kwh=kwh, conf=conf,
                                              lo=eur(lo, t), hi=eur(hi, t))
        html_report = generate_html_report(pv, kwh, consumo, results, rng, t, tariff_label, coste, life,
                                           assumptions, config_line, logo_b64=LOGO_B64,
                                           tabla=tabla, reco_kwh=reco_kwh, client=cliente,
                                           date_str=date.today().strftime("%d/%m/%Y"))
        nombre = "_".join(x for x in ["informe_symphonics", slug(cliente), f"{kwh}kWh"] if x)
        b1, b2 = st.columns(2)
        with b1:
            st.download_button(t["btn_download"], html_report, file_name=f"{nombre}.html", mime="text/html", key="dl")
        with b2:
            st.button(t["btn_hide"] if st.session_state.get("show_report") else t["btn_view"], key="view",
                      on_click=lambda: st.session_state.update(show_report=not st.session_state.get("show_report")))

if st.session_state.get("show_report"):
    components.html(html_report, height=1300, scrolling=True)
    st.caption(t["pdf_tip"])

# --------------------------------------------------------------------------------- 8. VALIDACIÓN (v2.2)
st.write("")
with st.expander(t["val_title"]):
    st.caption(t["val_intro"])
    v1, v2 = st.columns(2)
    with v1:
        st.button(t["val_ref_btn"], on_click=load_case, args=("ref",), key="case_ref")
        st.caption(t["val_ref_expect"])
    with v2:
        st.button(t["val_raul_btn"], on_click=load_case, args=("raul",), key="case_raul")
        st.caption(t["val_raul_expect"])
st.caption(f"{t['version']} 2.3 · 30/10/2026")
