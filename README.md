# Houbařský index 🍄

Mapa podmínek pro růst hub v Česku — počítáno ze srážek posledních 14 dní,
půdní vlhkosti a teplot (Open-Meteo), ne z pověr.

- Statická stránka, žádný backend. Prohlížeč nedělá žádné živé API volání —
  čte jen předpočítaný `data.json`.
- ~1470bodová hexagonální mřížka (~7,5 km) nad ČR, MapLibre GL + dark CARTO
- Skóre: 45 % vážený srážkový impuls (lag 5–10 dní), 35 % půdní vlhkost 0–7 cm,
  20 % teplotní pásmo; penalizace mráz/vedro/přísušek
- Výhled Dnes → +6 dní

## Data pipeline

`data.json` je jediný zdroj dat pro mapu a generuje se jednou denně:

- `scripts/build_data.py` postaví mřížku, stáhne Open-Meteo (tempo pod ~600
  volání/min) a zapíše kompaktní `data.json`.
- `.github/workflows/build-data.yml` to spouští cronem (03:30 UTC) a commitne
  `data.json`; commit spustí redeploy na Vercelu.

Proč předpočítávat: hustá mřížka stahovaná přímo z prohlížeče (15 chunků)
naráží na minutový limit Open-Meteo (HTTP 429) → prázdná mapa. Statický
`data.json` limit obchází a umožňuje libovolně malé hexy.

Deploy: statický hosting (Vercel), žádný build step.
