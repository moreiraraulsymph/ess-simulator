# Simulador de Baterías para Pequeños Consumidores · v2.3

Versión 2 (29/10/2026, Carlos Peña) construida sobre una **copia** del simulador B2C de Raúl Moreira.
El original de Raúl (`Simulator B2C.zip` en Drive) no se ha modificado. Su código exacto está en el
primer commit de git (`v1 original Raúl`).

## Cómo arrancarlo

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador, en http://localhost:8501.

## Qué cambia respecto a la v1

| Tema | v1 (Raúl) | v2 |
|---|---|---|
| Idioma | Selector EN / ES / PT; por defecto en inglés | Selector ES / EN / PT (v2.1), textos en `textos.py`; por defecto en español |
| Diseño | Barra lateral, métricas estándar de Streamlit | Tarjetas al estilo del simulador de Francia, con los colores de Symphonics |
| Tamaño de batería | Lo elige el usuario a mano | **Recomendación automática** entre 5 / 10 / 15 / 20 kWh, con opción de cambiarla |
| Precios | Coste introducido a mano (4.500 € por defecto) | **Precios de referencia integrados** (Solis / Huawei, con o sin inversor híbrido) en `precios_referencia.py`; se pueden editar en pantalla |
| Datos del cliente | FV, batería, consumo, tarifa | Además: potencia contratada, perfil de consumo (estándar / día / tarde-noche), inversor híbrido sí/no y marca |
| Ciclado | Sin límite | **Tope de 1 ciclo/día** por defecto (configurable), mismo criterio que la calculadora C&I |
| Potencia contratada | No se usaba | La carga desde red nunca supera la potencia contratada |
| Ahorro por tarifa indexada | Se cuenta todos los años | Igual por defecto, con la opción "solo el primer año" (criterio de la calculadora C&I) |
| Sin FV | Fallaba (división por cero) | Funciona con 0 kWp |
| Formato | 3,543 € · 10.3 años | Formato español: 3.543 € · 10,3 años. Sin cifras negativas, salvo la ganancia neta cuando hay pérdida (v2.3) |
| Oferta HTML | Diseño básico | Colores Symphonics, configuración recomendada, ciclos/año, lista para imprimir en PDF |
| Extras | — | Comparativa de tamaños y descarga del estudio tipo residencial |

Todos los cambios del código llevan la marca `# v2`.

## Cambios v2.1 (30/10/2026, revisión de Raúl `Comentarios_Simulador.pdf`)

Copia de seguridad previa: carpeta de backup del 30/10/2026 en Drive y tag git `backup-2026-10-30-antes-cambios-raul`.

1. **Logo Symphonics** en la cabecera de la app y del informe (`assets/logo_symphonics.png`; si falta, se muestra el texto SYMPHONICS).
2. **Cajas de números siempre visibles**: fondo claro y texto navy forzados por CSS, aunque el ordenador esté en modo oscuro.
3. **Idiomas ES / EN / PT** recuperados. Al cambiar de idioma se conservan los datos introducidos.
4. **Navy corporativo `#1d3960`** en app, informe y `.streamlit/config.toml`.
5. **Descarga del informe en HTML** (botón "Descargar informe"), además de "Ver informe".
6. **Error de pandas (DLL bloqueada por Application Control)**: la tabla comparativa ya no usa `st.dataframe`; se pinta en HTML. La app no necesita pandas para nada.
7. **Sin FV → "¿Tiene ya inversor híbrido?" = No** automáticamente (se puede cambiar a mano).
8. **Payback separado en sus dos causas**:
   - *Optimización Symphonics* = coste con batería en indexada sin optimizar − con optimización. Nunca es negativa: si no genera ahorro, no se envían consignas y la batería funciona como una estándar.
   - *Cambio de tarifa* = coste con batería estándar en la tarifa actual − con batería estándar en indexada. **Es la única que puede ser negativa** (indexada no competitiva).
   - Si el cambio de tarifa resta, la app lo avisa y muestra también el payback con Symphonics **manteniendo la tarifa actual**.
   - La regla "solo año 1" ahora quita solo el efecto tarifa a partir del año 2; antes quitaba todo el ahorro de suministro y por eso el payback salía peor que el estándar (el 9,4 años que vio Raúl).

Verificación (5,5 kWp · 10 kWh · 9.000 kWh · 3.300 €):

| Precios P1/P2/P3 | Estándar | Symphonics | Optimización | Efecto tarifa | Symphonics sin cambiar tarifa |
|---|---|---|---|---|---|
| 0,28 / 0,22 / 0,16 | 8,2 años | 5,9 años | +31 €/año | +128 €/año | 8,0 años |
| 0,28 / 0,18 / 0,10 | 9,8 años | 9,2 años | +31 €/año | −9 €/año | 8,8 años |

Conclusión: cuando el payback optimizado sale peor, **la causa es siempre la tarifa indexada, nunca la optimización**.

Nota: el desglose "Autoconsumo / Arbitraje / Suministro" del ahorro compara con la casa **sin batería**; el diagnóstico compara con la **batería estándar**. Por eso la cifra de suministro (p. ej. 196 €) no coincide con el "cambio de tarifa" del diagnóstico (p. ej. 91 €).

## Cambios v2.2 (30/10/2026, repaso completo antes de entregar — ninguna cifra cambia)

- **Más rápido (~3x)**: cachés de perfiles y bucle de la batería con números de Python. Resultados idénticos bit a bit a la v2.1 en 72 casos de prueba. `python comprobar.py` comprueba las cifras validadas en segundos.
- **Informe**: nombre del cliente (opcional) y fecha en la cabecera; el archivo se llama `informe_symphonics_<cliente>_<kWh>kWh.html`. Al imprimir en PDF sale en A4 sin cortar tarjetas ni filas.
- **Diagnóstico en forma de suma**: batería estándar + cambio de tarifa + optimización = total con Symphonics (cuadra con el ahorro de la tarjeta).
- **Avisos nuevos**: si ningún tamaño se amortiza, la recomendación lo dice en vez de mostrar ✓; si P1 / P2 / P3 no van de mayor a menor, se avisa.
- **Uso**: ayudas en los campos, botón "Restaurar valores por defecto" en hipótesis avanzadas, "Ver / Ocultar informe", importes con €/año, sin FV el autoconsumo FV sale "—", diseño adaptado a móvil, icono de ayuda corregido.
- **Lanzador**: ya no se queda parado en la pregunta del email de Streamlit la primera vez.
- **Casos de validación** (desplegable al final de la app): un clic carga el caso de referencia (debe dar ~399 €/año y 10,3 → 6,3 años) o el caso de la revisión de Raúl (~563 €/año, 8,2 → 5,9 años; con "solo el primer año", 7,3 en vez de los 9,4 de antes).
- **Tema claro garantizado**: aunque se lance `streamlit run` desde otra carpeta (Streamlit solo lee `.streamlit/config.toml` de la carpeta actual), la app aplica el tema de Symphonics. Con el PC en modo oscuro y sin esa config, las cajas se veían oscuras: probablemente era el problema de "las cajas solo se ven cuando se pincha".
- Versión visible al pie de la app.
- **Probado** con pandas y pyarrow bloqueados a propósito (como la política de Application Control): la app no los importa en ningún momento. Funciona con Streamlit 1.40 y 1.66. Dependencias: solo `streamlit` y `numpy`, sin cambios.

## Cambios v2.3 (30/10/2026) — correcciones de criterio

Ninguna toca el ahorro, el payback de los casos validados, los ciclos, la degradación, los precios de referencia ni la tarifa: `comprobar.py` sigue dando las mismas cifras.

| Qué | Antes | Ahora | Por qué |
|---|---|---|---|
| **Autosuficiencia** | 1 − (compras a red − carga desde red) / consumo | 1 − compras a red / consumo | La energía de red guardada en la batería contaba como "autosuficiente": sin FV salía un 41 %. Caso de referencia: 63 % → 60 %; caso de la revisión: 70 % → 65 %; sin FV: 41 % → 0 % |
| **Regla "solo el primer año"** | Quitaba el efecto tarifa a partir del año 2, también cuando era negativo | Solo quita la *ventaja* de la tarifa | Si la indexada sale más cara, marcar la opción mejoraba el payback (9,2 → 9,0 años). Ahora se mantiene en 9,2 |
| **Ganancia neta** | Una pérdida salía como "0 €" | Sale con signo (p. ej. −359 €) | Era una cifra falsa; el payback ya decía "> 15 años" |
| **Indexada más cara** | Solo se veía en el diagnóstico | Tercera barra en el retorno: "Con Symphonics BTM manteniendo la tarifa actual" (app e informe) | Se puede ofrecer solo la optimización sin cambiar de tarifa; el titular sigue siendo BTM + Suministro |

## Validación con el caso de referencia

Caso: 4,5 kWp · 5 kWh · 7.500 kWh/año · 2.0TD · 2.500 € · precios P1 / P2 / P3 0,28 / 0,22 / 0,16 €/kWh.

| | PDF de referencia (v1) | v2 sin tope de ciclos | v2 (1 ciclo/día) |
|---|---|---|---|
| Autoconsumo | 188 € | 188 € | 188 € |
| Arbitraje | 20 € | 20 € | 15 € |
| Suministro (indexada) | 196 € | 196 € | 196 € |
| **Total** | **404 €/año** | **404 €/año** | **399 €/año** |
| Payback sin optimizar → con Symphonics | 10,3 → 6,2 años | 10,3 → 6,2 años | 10,3 → 6,3 años |
| Rango | 368 – 443 € | 368 – 443 € | 363 – 438 € |
| Ganancia neta 15 años | 3.543 € | 3.543 € | 3.462 € |

Sin el tope de ciclos, v2 reproduce el PDF exactamente. La pequeña diferencia viene solo del tope de 1 ciclo/día.

## Puntos para Raúl

1. **Los precios P2/P3 mandan en el ahorro de "suministro".** El PDF usa 0,22 / 0,16 €/kWh, pero la app v1 traía 0,18 / 0,10 por defecto. Con estos últimos, la línea de suministro baja de 196 a 27 €/año (total 235 €/año, payback 10,7 años). v2 usa los del PDF. Hay que confirmar cuáles son los buenos.
2. **Precios indexados sintéticos.** La curva indexada sigue siendo la de ejemplo de la v1. Para cifras defendibles hay que cargar precios reales de OMIE/ESIOS en el formato ya preparado (`indexed_prices`).
3. **Criterio "solo año 1".** Corregido en v2.1 (ver arriba): ahora solo afecta al efecto tarifa y ya no puede dejar el payback optimizado peor que el estándar por culpa de la optimización. Sigue como opción, no por defecto.
4. **Precio de 5 kWh.** El caso de referencia usa 2.500 €. La tabla da 1.900 – 2.400 € para Solis solo batería y 2.900 – 3.600 € con inversor.
5. **Resolución horaria.** El modelo residencial sigue siendo horario (8.760 h), mientras que el mercado liquida cada 15 minutos. Para 2.0TD el impacto es pequeño, y así se indica en el aviso legal.
6. **Festivos y calendario de 2.0TD (propuesta, no aplicada).** El calendario supone que el 1 de enero es lunes y no tiene festivos nacionales (que en 2.0TD son P3). Con el calendario de 2026 y festivos: payback estándar 10,3 → 10,9 años (caso de referencia) y 8,2 → 8,6 (caso de la revisión); Symphonics no cambia (6,3 y 5,9). No se aplica para no romper la coincidencia con el estudio tipo en PDF.
7. **Criterio de recomendación.** Se elige el tamaño con mayor ganancia neta en 15 años entre los que se amortizan. Con 4,5 kWp y 7.500 kWh recomienda 10 kWh, y no 5. Si se prefiere el payback más corto, es un cambio de una línea en `recommend()`.

## Estructura

- `app.py`: interfaz (Streamlit).
- `calculations.py`: motor de simulación horaria de Raúl, más los parámetros v2.
- `precios_referencia.py`: tabla de precios Solis / Huawei, editable.
- `report_generator.py`: informe HTML para el cliente (descargable).
- `textos.py`: textos ES / EN / PT (v2.1).
- `comprobar.py`: comprueba que el motor da las cifras validadas (v2.2).
- `assets/`: logo Symphonics y estudio tipo residencial en PDF.
- `.streamlit/config.toml`: colores Symphonics.
