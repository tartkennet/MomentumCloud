# Production v1 runbook

## Första driftsättning

1. Kontrollera att repository secret `POLYGON_API_KEY` finns.
2. Koppla repots `main`-branch till Vercel; `vercel.json` kräver ingen build.
3. Kör `Production CI` och kräv godkänt resultat före merge.
4. Kör `MomentumCloud Production v1` manuellt en gång.
5. Kontrollera `Momentum_last_run.md`, artefakten och dashboardens systemstatus.
6. Fyll `Momentum_portfolio.csv` först när verkliga affärer har gjorts.

## Normal drift

- Data, regim, stoppar och app uppdateras varje handelskväll.
- Ny portföljrotation skapas en gång per ny kalendermånad.
- Övergång från RISK OFF till RISK ON skapar en ny målportfölj direkt.
- `Momentum_signals.csv` granskas före manuell handel.

## Felhantering

| Fel | Åtgärd |
|---|---|
| Polygon 429 | Workflow retry väntar; starta inte parallella körningar |
| Saknad SPY-historik | Systemet går säkert till RISK OFF |
| Okänd instrumenttyp | Aktien exkluderas |
| Splitbasis-cache underkänns | Cache byggs om från Polygon |
| Outputvalidering misslyckas | Ingen snapshot publiceras |
| Färre än 15 kandidater i RISK ON | Körningen stoppas för datagranskning |

## Produktionsdefinition

Production v1 är tekniskt färdig när CI är grön, första Polygon-körningen
har publicerat en validerad snapshot och Vercel visar samma `market_date`.
En positiv historisk avkastning garanteras inte och får inte tillverkas genom
efterhandsoptimering. Systemets aktiva regler ändras endast genom ny explicit
produktversion.

