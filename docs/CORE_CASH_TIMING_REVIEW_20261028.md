# Core — kassaflödeskontroll

## 10. Kompletterande kassaflödeskontroll, 28 oktober 2026

**Den genomförda känslighetsanalysen ger inget stöd för att upplåsta uppköpslikvider ensamma skulle lösa prestationsproblemen. I samtliga fyra prövade betalningsscenarier blev avkastningen lägre och nedgången större än i originalkörningen. Detta är hypotetiska scenarier, inte verifierade historiska betalningsdagar.**

Två oförändrade grundkörningar och åtta scenariokörningar har genomförts helt offline. Betalningsfördröjningarna 0, 1, 5 och 20 observerade handelssessioner fastställdes skriftligen innan scenarioutfallen beräknades. Samma antagande tillämpades på alla verifierade kontantuppköp som saknar betalningsdag, inte bara vissa innehav. CVR förblev osäker och värderad till noll. Ingen vinnande betalningsregel valdes ut.

| Antagen likviddag | Kostnad per sida | Netto | SPY | Skillnad, pp | Maximal nedgång | Positiva månader | Ekonomiska krav |
|---|---:|---:|---:|---:|---:|---:|---|
| Ingen återinvestering, original | 15 bp | +44.3054 % | +65.4425 % | -21.1371 | -37.5238 % | 56.250 % | 3/5 PASS |
| Ingen återinvestering, original | 30 bp | +39.5403 % | +64.9849 % | -25.4446 | -37.8683 % | 56.250 % | 3/5 PASS |
| Effektivdag + 0 handelssessioner | 15 bp | +25.4550 % | +65.4425 % | -39.9875 | -47.3877 % | 53.125 % | 3/5 PASS |
| Effektivdag + 0 handelssessioner | 30 bp | +19.6860 % | +64.9849 % | -45.2990 | -47.9546 % | 50.000 % | 3/5 PASS |
| Effektivdag + 1 handelssessioner | 15 bp | +25.5111 % | +65.4425 % | -39.9314 | -47.3774 % | 53.125 % | 3/5 PASS |
| Effektivdag + 1 handelssessioner | 30 bp | +19.5816 % | +64.9849 % | -45.4034 | -47.9624 % | 50.000 % | 3/5 PASS |
| Effektivdag + 5 handelssessioner | 15 bp | +25.5111 % | +65.4425 % | -39.9314 | -47.3774 % | 53.125 % | 3/5 PASS |
| Effektivdag + 5 handelssessioner | 30 bp | +19.5816 % | +64.9849 % | -45.4034 | -47.9624 % | 50.000 % | 3/5 PASS |
| Effektivdag + 20 handelssessioner | 15 bp | +26.7342 % | +65.4425 % | -38.7083 | -47.3386 % | 53.125 % | 3/5 PASS |
| Effektivdag + 20 handelssessioner | 30 bp | +21.6293 % | +64.9849 % | -43.3556 | -47.9523 % | 50.000 % | 3/5 PASS |

Alla tio fall innehåller 32 kompletta månadsintervall. Samtliga fall klarar positiv nettoavkastning och minst 50 % positiva månader. Samtliga fall fallerar jämförelsen med SPY och nedgångsgränsen på 20 %. Ingen signal, urvalsgräns, marknadsregel, portföljvikt eller prestationsgräns ändrades.

Vid grundkostnaden ger de fyra antagna betalningsfördröjningarna cirka **25,45–26,73 %** nettoavkastning och **47,34–47,39 %** maximal nedgång. Originalets motsvarande värden är **44,31 %** och **37,52 %**. Det är alltså fel att förutsätta att betalningskompletteringen kommer att förbättra resultatet. I dessa scenarier möjliggör den mer aktieexponering och större förluster. Verkliga betalningsdagar kan skilja sig mellan uppköpen; deras exakta utfall är fortfarande inte verifierat.

### Kontroller och bevis

- Originalets grund- och dubbelkostnadsmått reproduceras exakt. Fem grundfiler, inklusive hela dagsboken och slutligt tillstånd, är byte-identiska med den tidigare verifierade körningen.
- Samma målfil och samma 957-filers indatafingeravtryck används i samtliga tio fall. Varje scenario får dessutom ett eget fingeravtryck som inkluderar betalningsantaganden, kostnad och det förhandsskrivna protokollet.
- Alla fem grundkostnadsfall har kontrollerats separat med den befintliga redovisningsrevisorn: **PASS**, med **0 USD** största NAV-avvikelse. Kontroll av antagen bokföring verifierar inte att betalningsantagandet inträffade i verkligheten.
- Samtliga **129 funktionstester** passerar även lokalt. Den separata huvudgrenskörningen [40774263229](https://github.com/tartkennet/MomentumCloud/actions/runs/40774263229) har också avslutats framgångsrikt.
- Alla tio försök, fullständiga resultat, antagna betalningsdagar och kontrollrapporter sparas. Inga nya marknadsdata hämtades och inget abonnemang köptes.

### Vad källgranskningen faktiskt visar

Stängningsrapporterna från SEC bekräftar kontantvillkor och bolagshändelser för IMGN, AMAM, ALPN, FUSN, LBPH, CDTX, VTYX och TERN. De fastställer inte de kontospecifika likviddagarna som saknas. Exempelvis beskriver FUSN:s [stängningsmeddelande](https://www.sec.gov/Archives/edgar/data/1805890/000119312524154275/d827973dex991.htm) att pengarna lämnats till betalningsförmedlaren, medan vidare leverans till aktieägarna anges utan en exakt genomförd betalningsdag. TERN:s [8-K](https://www.sec.gov/Archives/edgar/data/1831363/000119312526205305/d70112d8k.htm) beskriver en kommande snabb betalning. Inget av detta ska felmärkas som en verifierad mäklarkreditering samma morgon.

Det som återstår är verifierbara likviduppgifter, rimlig exekvering och oberoende framtida evidens. Den sparade historiken har nu granskats upprepade gånger och är utvecklingsdata. Att ändra regler eller GO-gränser tills just denna historik passerar skulle inte skapa ett verifierat godkännande. Det finns därför fortfarande ingen godkänd modell för riktiga pengar att leverera.
