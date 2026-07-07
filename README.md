# Houbařský index 🍄

Mapa podmínek pro růst hub v Česku — počítáno ze srážek posledních 14 dní,
půdní vlhkosti a teplot (Open-Meteo), ne z pověr.

- Statická stránka, žádný backend — data se stahují client-side z Open-Meteo
- 92bodová hexagonální mřížka nad ČR, MapLibre GL + dark CARTO
- Skóre: 45 % vážený srážkový impuls (lag 5–10 dní), 35 % půdní vlhkost 0–7 cm,
  20 % teplotní pásmo; penalizace mráz/vedro/přísušek
- Výhled Dnes → +6 dní, localStorage cache per den

Deploy: statický hosting (Vercel), žádný build step.
