# MomentumCloud runbook

## Aktiv Core-pappersdrift

Det aktiva workflowet heter `Momentum Core candidate`. PR/push och manuell
start kör utvecklingstestet 2024-01-01–2026-09-01 samt dubbel handelskostnad.
Schemat tisdag–lördag 00:20, 03:20, 06:20 och 09:20 UTC registrerar föregående avslutade USA-session
som framåtriktad pappershandel från 2026-10-29.

`run_momentum_core.py` skriver `Momentum_core_decision.json`. `DATA_BLOCKED`
betyder beräkningsstopp; `NO_GO` betyder ett fullföljt ekonomiskt underkännande.
Ett historiskt `PAPER_ONLY` ger ingen livebehörighet. Läs måtten och gatesen i
`Momentum_Core_evidence`; workflowets färg är inget investeringsbeslut.

Paper-kontot, dess identitet och dubbelkostnadskontot återställs före nästa
session. Ändrad källidentitet eller förlorad ursprunglig checkpoint efter
startfristen blockerar evidensen. Bevara tidigare resultat; rekonstruera
inte gammal paper-historik och kalla den framåtriktad.

Rådatacachen autentiseras och krypteras med befintlig API-credential.
`Momentum_Core_private_inputs` innehåller både mottagarkrypterat forskningsarkiv
och den autentiserade krypterade cachen. Ingen privat nyckel finns i repot.
Den krypterade cachen kan öppnas med `cache_momentum_inputs.py unseal` och den
ursprungliga API-nyckeln i miljövariabeln `POLYGON_API_KEY`; ingen nätkontakt
eller aktiv betalplan behövs för dekrypteringen. Spara nyckeln privat om detta
återställningssätt ska användas efter en nyckelrotation.

Ett fullständigt uppackat underlag körs med `--offline` utan marknadsdata-API.
Workflowet kontrollerar identiska filer och mått vid offlineåterkörning, och
`audit_momentum_core.py` stämmer av kassa, aktier, fordringar, faktiska
öppningskurser, avgifter, SPY och prestationsmått separat från replaymotorn.

Core skickar inga brokerorder och uppdaterar inte gamla Buy Now eller
dashboarden. Dashboarden visar ett historiskt v4-snapshot.

## Historisk v4 — endast manuell drift

Anvisningarna nedan gäller den tidigare v4-implementationen. Dess två workflow
är manuella och ingår inte i Core-pappersdriften.

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

En grön CI och en publicerad snapshot visar produktens drift, inte modellens
GO-status. Före modellgodkännande krävs en fullföljd historisk validering,
granskning av positions- och riskdata samt en beslutsfil vars källversion och
mätvärden stämmer. Backtest och liveflöde måste dessutom pröva samma regler.

Vid `VALIDATION_ERROR` granskas `Momentum_validation_data_errors.json` och
körloggarna. Okända avnoteringar eller saknade priser får inte ersättas med
påhittade affärer. `NO-GO` används för fullföljd validering där något av de
fem fasta prestationskraven fallerar. Båda tillstånden håller Buy Now spärrat.
En positiv historisk avkastning garanteras inte och får inte tillverkas genom
efterhandsoptimering. Systemets aktiva regler ändras endast genom ny explicit
produktversion.


## Bevarad misslyckad första paper-start

Den ursprungliga starten 2026-10-27 fick ingen giltig första checkpoint:
GitHub körde schemat 2026-10-28 13:18 UTC, efter dess startfrist. Den gamla
artifacten bevaras. Ny cohort v2 börjar först med signal 2026-10-29 och
registreras senast 2026-10-30 12:00 UTC. Artefakten heter
`Momentum_Core_paper_v2_evidence`; den gamla cohortens cache eller identitet
får inte användas. Körförsöken sker 01:20, 04:20, 07:20 och 10:20 svensk
vintertid. Upprepade körningar återanvänder samma checkpoint och skapar inte
extra historik. Missas även denna frist ska den riktiga förseningen redovisas.
