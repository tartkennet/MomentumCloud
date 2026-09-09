# MomentumCloud v3

MomentumCloud är ett USA-momentumsystem med Polygon som enda marknadsdatakälla.

## Status

Den verifierade jämförelsen mellan den gamla v1-modellen och v3, med samma 15 lika viktade aktier, månadsvis omallokering, 6 % stop-loss, signal vid stängning och order nästa börsdags öppning, gav v3 bäst resultat.

- v3 med 6 % stop-loss: −5,19 % totalt, −20,97 procentenheter mot SPY
- legacy v1 med 6 % stop-loss: −13,09 %
- legacy v1 med 8 % stop-loss: −10,18 %
- SPY: +15,77 %

v1 används därför inte längre som modellkandidat. v3 med 6 % stop-loss är den enda kvarvarande kandidaten, men är **inte produktionsgodkänd**: den senaste 12-månadersjämförelsen är negativ och aktieuniversumet har `CURRENT_TEMPLATE_SURVIVORSHIP_BIAS`.

## Vad systemet gör

- Läser aktieuniversum från `Momentum mall fil.xlsx`, fliken `Universe`, kolumnen `Ticker`.
- Hämtar daglig OHLCV-data från Polygon.
- Tillämpar kvalitetsfilter:
  - kurs minst 5 USD
  - genomsnittlig dollarlikviditet, 20 dagar, minst 20 000 000 USD
  - trend: kurs > SMA50 > SMA200
  - momentum: avkastning 3, 6 och 12 månader över 0
- Poängsätter aktier med viktat momentum och acceleration.
- Väljer topp 15 och markerar topp 10 köp.
- Läser portföljvärde från `Parametrar!B1`.
- Räknar ut lika viktad kvantitet för de 10 främsta positionerna.
- Skriver resultat till `Momentum.xlsx` och `BuyNow`.

## Krävd miljövariabel

- `POLYGON_API_KEY`: Polygon API-nyckel.

## Lokal körning

```bash
pip install pandas numpy requests openpyxl
python momentum_master_v3.py
```
