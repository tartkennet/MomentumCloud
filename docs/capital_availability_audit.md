# Kassaflödeskontroll för spärrat kapital

`audit_capital_availability.py` är en fristående kontroll av uttryckliga
kassaflöden. Originalets urval, fasta exitdagar och periodmotor ändras inte.
Modulen är grund för en eventuell senare integrering, inte en färdig
exekveringspolicy eller ett nytt historiskt resultat.

- `BUY` debiterar tillgänglig kassa och öppnar ett separat innehav.
- `EXIT` stänger innehavet och öppnar en fordran i angiven valuta.
- `RECEIVE` krediterar fordrans exakta belopp en enda gång.
- `FX` kräver uttryckliga belopp på båda valutabenen.
- `FEE` kräver tillgänglig kassa; kredit eller belåning antas inte.

Varje händelse kräver unikt ID, tid med tidszon och källreferens. Händelser
med samma tid behåller inmatad ordning. En planerad exit är information;
den skapar varken försäljning eller betalning. Kostnaden för ett öppet innehav
är bokfört inköpsbelopp, inte marknadsvärde. Ingen NAV räknas från det.
Källreferenser är spårbarhet; funktionen bevisar inte att uppgiven källa
styrker en faktisk historisk exekvering. Inga källor hämtas av modulen.

Exempel på manuell körning från projektroten:

```sh
python3 audit_capital_availability.py \
  --input tests/fixtures/capital_availability/late_exit_synthetic.json \
  --output /tmp/late_exit_audit.json
```

Detta syntetiska exempel ska avslutas med kod 1 och
`BLOCKED_CASH_FLOW_AUDIT`: nästa köp saknar finansiering. Filen
`cad_receipt_synthetic.json` ska i stället passera kassaflödeskontrollen,
men behålla 120 CAD och 0 USD. Alla belopp och tidsstämplar i dessa exempel
är syntetiska och beskriver inga historiska SJR- eller FRC-affärer.

För en verklig försenad-exit-simulering återstår koppling till verifierade
positions-/betalningsunderlag, valutariktig daglig värdering och en uttrycklig
regel för nya köp när gammalt kapital fortfarande är bundet. Någon sådan
regel väljs inte genom denna kontroll. Modulen publicerar ingen avkastning,
ändrar inga innehav och startar ingen schemaläggning.
