# Fullständig repo-audit

Audit utförd mot 195 filer i PR 2:s senaste träd: 38 aktiva filer och 157
dagliga Excelkopior under `backups/`. Git-historiken är arkivet; binära
dagkopior ska inte ligga i den aktiva produktgrenen.

## KEEP — befintliga filer

| Fil | Beslut |
|---|---|
| `.gitignore` | Repareras; var tidigare en trasig Markdown-kodruta |
| `Momentum mall fil.xlsx` | Enda inmatningsmall och befintligt universum |
| `Momentum.xlsx` | Genererad produktarbetsbok |
| `Momentum_buy_history.csv` | Produktionssignalhistorik; tidigare forskningsrader nollställs vid lansering |
| `Momentum_last_run.md` | Senaste verifierade körstatus |
| `Momentum_portfolio.csv` | Faktiska innehav |
| `backtest_momentum_v3.py` | Befintlig exekveringsmotor; produktionsingången låser v4 |
| `momentum_master_v3.py` | Polygon/cache/split/Excel-infrastruktur och fryst historisk jämförelse |
| `public/data/buynow.json` | Byts till genererad Production v1-payload |
| `requirements.txt` | Låsta Python-beroenden |
| `tests/test_backtest_cache_split_basis.py` | Cache/split-regression |
| `tests/test_backtest_configuration_v3.py` | Frysta historiska exekverings- och corporate-action-regressioner |
| `tests/test_history_cache_split_basis.py` | Live-cache/split-regression |
| `tests/test_momentum_master_v3.py` | Gemensam data-/portföljinfrastruktur |
| `tests/test_point_in_time_universe.py` | Historisk backtestinfrastruktur; påverkar inte produktion |

## ARCHIVE — kvar endast genom Git-historiken

| Fil/grupp | Orsak |
|---|---|
| `momentum_master_v2.py` | Ersatt modellimplementation |
| `Momentum_template.xlsx` | Dubblett av mall |
| `momentum backup.xlsx` | Dubblett av mall |
| `sector_map.csv` | Statiskt och oanvänt experimentunderlag |
| `tickers.csv` | Ersatt av arbetsbokens universum + Polygon-instrumentmaster |
| `polygon_fetch_incremental.py` | Duplicerar produktionsklient/cache |
| `polygon_fetch_sectors.py` | Oanvänd produktionsväg |
| `send_email.py` | Oanvänd leveranskanal |

## DELETE — tas bort från aktiv gren

| Fil/grupp | Orsak |
|---|---|
| `.github/workflows/momentum_backtest.yml` | Forskningsworkflow ersatt av låst validering |
| `.github/workflows/momentum_exit_research.yml` | Stop-loss-forskning är avslutad |
| `.github/workflows/momentum_legacy_comparison.yml` | Modelljämförelse är avslutad |
| `.github/workflows/momentum_production_candidate.yml` | Ersatt av Production v1 |
| `.github/workflows/momentum_robustness.yml` | Parameterforskning är avslutad |
| `.github/workflows/momentum_usa_quarterly.yml` | Fel produktfrekvens/portfölj |
| `.github/workflows/momentum_v3.yml` | Ersatt av Production v1 |
| `.github/workflows/momentum_walk_forward.yml` | Parameterforskning är avslutad |
| `robustness_report_v3.py` | Tillhör borttagen forskning |
| `walkforward_report_v3.py` | Tillhör borttagen forskning |
| `tests/test_momentum_selection_v4.py` | Ersatt av rena produktionsregressioner |
| `tests/test_robustness_report_v3.py` | Tillhör borttagen forskning |
| `tests/test_walkforward_report_v3.py` | Tillhör borttagen forskning |
| `MomentumCloud.zip` | Föråldrad zip inuti Git |
| `backups/*.xlsx` — samtliga 157 filer | Identiska/återkommande dagkopior; Git-historiken bevarar dem |

## CREATE — nya produktionsfiler

| Fil | Syfte |
|---|---|
| `.github/workflows/ci.yml` | Snabb produkt-CI |
| `.github/workflows/momentum_production.yml` | Enda schemalagda produktkörning |
| `.github/workflows/momentum_validation.yml` | Enda manuella modellvalidering |
| `momentum_config.py` | Låst konfiguration |
| `momentum_strategy.py` | Enda aktiva strategi |
| `momentum_production.py` | Produktorkestrering |
| `validate_production_backtest.py` | Låst backtestingång |
| `Momentum_signals.csv` | Genererad köp/säljfil |
| `api/dashboard.js` | Snapshot-API utan tunga Python-beroenden i Vercel |
| `api/health.js` | Hälsokontroll utan tunga Python-beroenden i Vercel |
| `public/index.html` | Mobile-first dashboard |
| `public/styles.css` | Färgstarkt responsivt UI |
| `public/app.js` | Dashboardrendering |
| `public/icon.svg` | Appikon |
| `public/manifest.webmanifest` | Installerbar mobilwebbapp |
| `public/data/dashboard.json` | Kanonisk snapshot |
| `vercel.json` | Hosting/API-routing |
| `tests/test_production_strategy.py` | Regel- och rankinglås |
| `tests/test_production_outputs.py` | Signal- och payloaddrift |
| `docs/ARCHITECTURE.md` | Produktionsarkitektur |
| `docs/REPOSITORY_AUDIT.md` | Filklassificering |
| `docs/RUNBOOK.md` | Drift och incidenthantering |

## Ändrade filer

- `.gitignore`: giltig ignorefil.
- `README.md`: Production v1 i stället för forskningsstatus.
- `momentum_master_v3.py`: senaste handelsdatum kontrolleras först.
- `backtest_momentum_v3.py`: exakt 5 MUSD, 10 USD prisgolv,
  v4-regim och current-template-validering.
- `public/data/buynow.json`: ersatt schema, genereras från samma snapshot som appen.
