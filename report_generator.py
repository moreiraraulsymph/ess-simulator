# report_generator.py
# v2.3 (Carlos, 30/10/2026): la ganancia neta muestra el signo (una pérdida ya no sale como 0 €).
# v2.2 (Carlos, 30/10/2026): diagnóstico en forma de suma, cliente y fecha, impresión en A4 sin cortes.
# v2.1 (Carlos, 30/10/2026): informe HTML descargable, multidioma, con logo Symphonics,
# navy corporativo #1d3960, diagnóstico del payback y comparativa de tamaños. Cifras siempre en positivo.
from html import escape

INF = float("inf")

# Paleta Symphonics
NAVY = "#1d3960"      # v2.1: navy corporativo confirmado por Raúl
MAGENTA = "#e6007e"
TEAL = "#2ec4b6"
YELLOW = "#fff3c4"
LIME = "#c5e86c"
PINK_BG = "#fdf0f6"
GREY = "#5c7088"


def fmt_num(x, t, dec=0):
    """Número con los separadores del idioma (t['dec'], t['thou'])."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", t.get("dec", ",")).replace("§", t.get("thou", "."))


def eur(x, t):
    """Importe redondeado, nunca negativo en pantalla."""
    return fmt_num(max(x, 0), t)


def eur_signed(x, t):
    """v2.3: importe con signo para la ganancia neta: una pérdida se muestra como pérdida (−359), no como 0."""
    return ("−" if round(x) < 0 else "") + fmt_num(abs(x), t)


def fmt_payback(x, t, lifetime):
    """'6,3 años' o '> 15 años' cuando la batería no se amortiza en su vida útil."""
    return t["never"].format(n=lifetime) if x == INF else f"{fmt_num(x, t, 1)} {t['years']}"


def _row(label, value, t, border=True):
    line = "border-bottom:1px solid #eee;" if border else ""
    return (
        f'<div style="display:flex;justify-content:space-between;gap:12px;{line}padding:10px 0;">'
        f'<span>{escape(label)}</span>'
        f'<span style="font-weight:bold;white-space:nowrap;">~{eur(value, t)} {t["per_year"]}</span></div>'
    )


def diagnosis_html(results, t, lifetime):
    """v2.2: el diagnóstico como una suma que cuadra con el ahorro total:
    batería estándar + cambio de tarifa + optimización = total con Symphonics.
    Solo presenta cifras que ya calcula calculations.py (no cambia ningún número)."""
    d, py = results["diagnosis"], t["per_year"]
    te = d["tariff_effect"]
    tariff_val = f"+{eur(te, t)} {py}" if te >= 0 else t["subtracts"].format(x=eur(-te, t))
    rows = [(t["bridge_std"], f"~{eur(d['standard_savings'], t)} {py}", None, ""),
            (t["diag_tariff_gain"], tariff_val, None, "" if te >= 0 else f"color:{MAGENTA};"),
            (t["diag_optim"], f"+{eur(d['optim_effect'], t)} {py}", t["diag_optim_note"], "")]
    cell = "padding:7px 0;border-bottom:1px solid #eee;"
    html = ""
    for label, val, note, extra in rows:
        sub = f'<div style="font-size:0.82em;color:{GREY};">({escape(note)})</div>' if note else ""
        html += (f'<div style="display:flex;justify-content:space-between;gap:12px;{cell}">'
                 f'<div>{escape(label)}{sub}</div><b style="white-space:nowrap;{extra}">{escape(val)}</b></div>')
    html += (f'<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0 0;">'
             f'<b>{escape(t["bridge_total"])}</b><b style="white-space:nowrap;color:{MAGENTA};">'
             f'~{eur(results["symphonics"]["savings"], t)} {py}</b></div>')
    html += f'<div style="font-size:0.78em;color:{GREY};margin-top:4px;">{escape(t["rounding_note"])}</div>'
    if te < 0:
        html += (f'<p style="margin:10px 0 0;font-size:0.88em;color:{NAVY};">'
                 f'{escape(t["diag_tariff_loss"].format(x=eur(-te, t)))}. '
                 f'{escape(t["diag_keep_current"].format(pb=fmt_payback(results["symphonics_current"]["payback"], t, lifetime)))}.</p>')
    return html


def comparison_table_html(tabla, reco_kwh, t, lifetime, header_bg=NAVY):
    """v2.1: tabla de tamaños en HTML (sustituye a st.dataframe, que necesitaba pandas)."""
    th = f'style="background:{header_bg};color:#fff;text-align:left;padding:8px 10px;font-weight:600;"'
    td = 'style="padding:8px 10px;border-bottom:1px solid #eee;white-space:nowrap;"'
    head = "".join(f"<th {th}>{escape(h)}</th>" for h in
                   [t["col_size"], t["col_price"], t["col_savings"], t["col_payback"],
                    t["col_net"].format(n=lifetime), t["col_cycles"]])
    rows = ""
    for f in tabla:
        reco = f["kwh"] == reco_kwh
        style = f' style="background:{YELLOW};font-weight:600;"' if reco else ""
        label = f"{f['kwh']} kWh" + (f" ← {t['recommended']}" if reco else "")
        cells = [label, eur(f["coste"], t), eur(f["ahorro"], t), fmt_payback(f["payback"], t, lifetime),
                 eur_signed(f["neta"], t), f"{f['ciclos']:.0f}"]
        rows += f"<tr{style}>" + "".join(f"<td {td}>{escape(c)}</td>" for c in cells) + "</tr>"
    return (f'<table style="border-collapse:collapse;width:100%;font-size:0.92em;background:#fff;'
            f'border-radius:10px;overflow:hidden;"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')


def generate_html_report(pv_power, battery_capacity, annual_consumption, results, rng, t,
                         tariff_label, battery_cost, lifetime, assumptions, config_line="",
                         logo_b64=None, tabla=None, reco_kwh=None, client="", date_str=""):
    """
    results : output of calculations.run_simulation
    rng     : output of calculations.run_range
    t       : diccionario de textos del idioma (textos.TEXTOS[lang])
    Everything shown comes from the simulation: no hardcoded splits or ranges.
    """
    sym, std = results["symphonics"], results["standard"]
    lo, hi = rng["savings"]

    subtitle = t["report_subtitle"].format(
        pv=fmt_num(pv_power, t, 1 if pv_power % 1 else 0), batt=f"{battery_capacity:g}",
        cons=fmt_num(annual_consumption, t), tariff=escape(tariff_label))

    rows = _row(t["row_selfcons"], sym["selfcons_part"], t)
    rows += _row(t["row_arbitrage"], sym["arbitrage_part"], t)
    rows += _row(t["row_supply"], sym["supply_savings"], t, border=False)

    config_html = (f'<p style="margin:6px 0 0;color:{GREY};font-size:0.9em;">{escape(config_line)}</p>'
                   if config_line else "")
    # v2.2: cliente y fecha en la cabecera
    meta = " · ".join(x for x in [f"{t['report_client']}: {client}" if client else "",
                                   f"{t['report_date']}: {date_str}" if date_str else ""] if x)
    meta_html = f'<p style="margin:4px 0 0;color:{GREY};font-size:0.9em;">{escape(meta)}</p>' if meta else ""
    brand = (f'<img src="data:image/png;base64,{logo_b64}" alt="Symphonics" style="height:34px;">'
             if logo_b64 else f'<span style="font-weight:800;letter-spacing:3px;color:{NAVY};">SYMPHONICS</span>')
    diag = diagnosis_html(results, t, lifetime)
    table_html = ""
    if tabla:
        table_html = (f'<div class="sy-block" style="margin-top:20px;"><h3 style="color:{NAVY};margin:0 0 10px;">{escape(t["compare"])}</h3>'
                      f'{comparison_table_html(tabla, reco_kwh, t, lifetime)}</div>')

    # v2.3: si la indexada sale más cara, se enseña también el payback manteniendo la tarifa actual
    keep_html = ""
    if results["diagnosis"]["tariff_effect"] < 0:
        keep_html = (f'<p style="color:{GREY};margin:15px 0 5px;">{escape(t["with_symphonics_current"])}</p>'
                     f'<div style="background-color:{NAVY};color:white;padding:10px 14px;border-radius:10px;'
                     f'font-weight:bold;font-size:1.2em;">{fmt_payback(results["symphonics_current"]["payback"], t, lifetime)}</div>')

    card = "flex:1;min-width:300px;background:white;padding:22px;border-radius:16px;box-shadow:0 4px 14px rgba(29,57,96,0.06);"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(t['report_title'])}{(' · ' + escape(client)) if client else ''} · Symphonics</title>
<style>
@page {{ size: A4; margin: 10mm; }}
@media print {{
  body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .sy-block, table, tr {{ break-inside: avoid; page-break-inside: avoid; }}
}}
</style>
</head>
<body style="margin:0;background:#ffffff;">
<div style="font-family:Arial,Helvetica,sans-serif;background-color:{PINK_BG};padding:30px;border-radius:16px;color:{NAVY};max-width:900px;margin:auto;">

  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
    {brand}
    <span style="background:{MAGENTA};color:white;padding:4px 12px;border-radius:20px;font-size:0.8em;font-weight:bold;">{escape(t['badge'])}</span>
  </div>
  <h2 style="color:{NAVY};margin:16px 0 4px;">{escape(t['report_title'])}</h2>
  <p style="color:{GREY};margin:0;">{subtitle}</p>
  {config_html}
  {meta_html}

  <div style="display:flex;gap:20px;margin-top:20px;flex-wrap:wrap;">
    <div class="sy-block" style="{card}">
      <h3 style="color:{NAVY};margin-top:0;">{escape(t['estimated_savings'])}</h3>
      {rows}
      <h4 style="color:{MAGENTA};margin:18px 0 5px;">{escape(t['total_savings'])}</h4>
      <h2 style="color:{MAGENTA};margin:0;">~{eur(sym['savings'], t)} {t['per_year']}</h2>
    </div>
    <div class="sy-block" style="{card}">
      <h3 style="color:{NAVY};margin-top:0;">{escape(t['payback_title'])}</h3>
      <p style="color:{GREY};margin-bottom:5px;">{escape(t['standard_battery'])}</p>
      <div style="background-color:{GREY};color:white;padding:10px 14px;border-radius:10px;font-weight:bold;font-size:1.2em;margin-bottom:15px;">
        {fmt_payback(std['payback'], t, lifetime)}
      </div>
      <p style="color:{GREY};margin-bottom:5px;">{escape(t['with_symphonics'])}</p>
      <div style="background-color:{MAGENTA};color:white;padding:10px 14px;border-radius:10px;font-weight:bold;font-size:1.2em;">
        {fmt_payback(sym['payback'], t, lifetime)}
      </div>
      {keep_html}
      <p style="color:#888;font-size:0.85em;margin-bottom:0;">{t['investment_line'].format(cost=eur(battery_cost, t))}</p>
    </div>
  </div>

  <div class="sy-block" style="margin-top:20px;background:white;padding:18px 22px;border-radius:16px;">
    <h3 style="color:{NAVY};margin:0 0 6px;font-size:1.05em;">{escape(t['diag_title'])}</h3>
    <div style="color:{NAVY};font-size:0.92em;">{diag}</div>
  </div>

  <div class="sy-block" style="margin-top:20px;background:{NAVY};color:white;padding:25px;border-radius:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;">
      <div>
        <span style="background:{TEAL};color:{NAVY};padding:4px 10px;border-radius:20px;font-size:0.8em;font-weight:bold;text-transform:uppercase;">Symphonics</span>
        <h3 style="margin:10px 0 5px;color:#fff;">{escape(t['col_symphonics'])}</h3>
        <p style="color:#c9d3e3;margin-top:0;">{escape(t['smart_storage'])}</p>
      </div>
      <div style="text-align:right;">
        <p style="margin:0;font-size:0.9em;color:#fff;">{escape(t['savings_range'])}</p>
        <h2 style="margin:0;color:{LIME};">{eur(lo, t)} – {eur(hi, t)} {t['per_year']}</h2>
      </div>
    </div>
    <hr style="border:none;border-top:1px solid #34507a;margin:15px 0;">
    <div style="display:flex;gap:30px;flex-wrap:wrap;font-size:0.95em;color:#fff;">
      <div><span style="color:#c9d3e3;">{escape(t['kpi_selfsuff'])}</span><br><b>{sym['self_sufficiency']*100:.0f} %</b></div>
      <div><span style="color:#c9d3e3;">{escape(t['kpi_selfcons'])}</span><br><b>{'—' if pv_power == 0 else f"{sym['self_consumption']*100:.0f} %"}</b></div>
      <div><span style="color:#c9d3e3;">{escape(t['kpi_cycles'])}</span><br><b>{sym['cycles']:.0f}</b></div>
      <div><span style="color:#c9d3e3;">{escape(t['lifetime_gain'].format(n=lifetime))}</span><br><b>{eur_signed(sym['lifetime_net'], t)} €</b></div>
    </div>
    <p style="font-size:0.9em;color:#c9d3e3;margin-bottom:0;">
      <b>{escape(t['smart_charging'])}</b><br>{escape(t['maximize_self'])}
    </p>
  </div>
  {table_html}

  <p style="font-size:0.75em;color:#888;margin-top:20px;">{escape(assumptions)}</p>
  <p style="font-size:0.7em;color:#888;">{escape(t['disclaimer'])}</p>
</div>
</body></html>"""
    return html
