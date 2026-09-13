# MomentumCloud Production v1 — arkitektur

## Produktionsflöde

1. GitHub Actions startar efter USA-börsens stängning.
2. `momentum_production.py` hämtar aktuell instrumentmaster, USDSEK, SPY och
   justerad OHLCV från Polygon.
3. Universumet korsas med aktiva USA-noterade common stocks. ETF, ADR,
   preferensaktier, OTC och namn som tydligt identifierar SPAC exkluderas.
4. `momentum_strategy.py` räknar exakt en modell: `v4-balanced`.
5. `SPY > SMA200` avgör RISK ON/RISK OFF. RISK OFF ger tom målportfölj och
   säljsignal för registrerade innehav.
6. Månadsskifte skapar omallokeringssignaler. Det fasta 10 %-stoppet
   kontrolleras varje handelsdag.
7. Samma snapshot valideras och skrivs till JSON, CSV och Excel.
8. Vercel serverar dashboard och två läs-API:er. Ingen handelsintegration finns.

## Komponenter

| Komponent | Ansvar |
|---|---|
| `momentum_config.py` | Oföränderlig produktionskonfiguration |
| `momentum_strategy.py` | Ren filtrering, regim, ranking och stopplogik |
| `momentum_production.py` | Polygon, state, signaler, Excel och dashboarddata |
| `momentum_master_v3.py` | Beprövad Polygon-, cache-, split- och portföljinfrastruktur; äldre urvalslogik är historisk |
| `backtest_momentum_v3.py` | Befintlig exekveringsmotor; produktion kör endast v4 via wrappern |
| `validate_production_backtest.py` | Låst valideringsingång utan modellalternativ |
| `api/` | Read-only dashboard- och health-API |
| `public/` | Mobil dashboard/PWA |

## State och data

- `.momentum_production_state.json` låser senaste urvalsmånad och föregående
  regim så att dagliga körningar inte omallokerar portföljen varje dag.
- `.momentum_history_cache.json` har versionsmärkt splitbasis.
- `.momentum_splits_cache.json` innehåller verifierade bolagshändelser.
- `Momentum_portfolio.csv` är enda källan för faktiska innehav.
- `public/data/dashboard.json` är den kanoniska publicerade snapshoten.

## Säkerhetsgränser

- Ingen orderläggning eller mäklaranslutning.
- Saknad SPY-historik ger RISK OFF.
- Saknad eller okänd instrumentklass exkluderas.
- Konfigurationsdrift stoppar CI/körning.
- En produktionssnapshot publiceras först efter unit-test och outputvalidering.
- `Current limitation: survivorship bias` visas i alla produktionsytor.

