# MomentumCloud – kontrollerat urvalstest, uppdaterad 19 oktober 2026

## Färdig samlad lokal verifiering – 19 oktober 2026

**Den tidigare osparade fyrfallsdiagnostiken är nu återskapad genom en ny färdig lokal körning. NO-GO kvarstår.** Hela den redan installerade GOLD/NCR- och efterföljarbatchen kördes med frysta indata och projektets låsta paketversioner. Alla fem steg avslutades utan processfel. Testloggar, full prisförkontroll, urvalspositioner, periodresultat, modellresultat och universumdiagnostik sparas tillsammans i `audit_evidence/replay_20261019/`, med filhashar och körd källkods hashvärden.

| Färskt verifierat resultat | Utfall |
|---|---|
| Regressionstester | **123/123 passerade**, inklusive skydd för oförändrad formationscache och orelaterade tillgångars priser |
| Bred rå/justerad prisförkontroll | **291/291 observerade datumpar, 0 saknade** |
| Urvalsreplay efter hela batchen | **645 positioner, 230 tickers, 43 månader**, exakt samma nycklar, signal-/köp-/exitpriser och köp-/exitdatum som arkivet |
| Oberoende positions- och kapitalaggregering | PASS |
| Nettoavkastning | **−0,5460050227673818 %** |
| Största dagliga nedgång | **−50,38013190677646 %** |
| SPY med samma fasta månadskostnad | **+70,20238513471013 %** |
| Universumdiagnostik | **4 olösta exekveringar, 0 basisavvikelser** |
| Dokumentationstäckning i de ursprungliga fallen | **286/288**, ingen exekveringspassfrekvens |

Arkivets egna pris-, identitets- och NAV-kontroller återverifierades också: 1 935 priser, 645 daterade identiteter och 943 dagliga NAV-punkter passerade. Detta är en kontroll av arkiverat underlag; den separata nya modellkörningen verifierar reproduktion efter hela den nu installerade batchen.

| Kvarvarande modellblockerare | Exakt saknat underlag |
|---|---|
| FRC, signal 2023-03-31 | Observerad exekvering eller verifierat vederlag på fasta exitdagen **2023-05-01**. Senare OTC-kurs får inte bakdateras. |
| SJR, signal 2023-03-31 | Verifierad USD-betalning/valutahantering och daglig värdering av CAD-fordran fram till betalning. Optionsavräkning bevisar inte i sig common-share-betalning. |
| AEPPZ, signal 2023-07-31 | Faktiska per-enhet-villkor för corporate units och dess skuld-/forwardkomponenter vid exit **2023-09-01**. Ingen gissad aktiekvot eller riktad borttagning. |
| RNAZ, signal 2025-10-31 | Observerad kurs på fasta exitdagen **2025-12-01**. Bevarad historik ger först **2025-12-02**, vilket ligger utanför perioden. |

SIVB, NCR, PARA, LNW och HLX finns inte längre i modellens olösta lista efter den samlade batchen. Detta betyder att just dessa resolverhinder inte återkommer, inte att faktisk leverans, fraktionsavräkning eller handelsfyllnad är godkänd. Ingen giltig universumavkastning publiceras och rankningens mervärde är fortfarande obevisat. Daterad emittentidentitet och formationshistorikers kontinuitet behöver fortsatt bedömas separat.

Den nya körningen ändrar inte urvalets negativa resultat. Att stänga dataluckorna kan göra jämförelsen granskbar, men ger inte automatiskt ett GO för modellen. Strategiregler, kostnad, historiska problemaktier och förlorare har bevarats. Inga modellparametrar har optimerats. Inga Actions-jobb, main-merge, produktionsändringar, affärer, dataköp eller automationer startades för den lokala batchen.

Återställningen verifierade tio originalarkiv samt hela den frysta cachen: 507 412 232 byte, 1 230 sessioner, basis 2026-10-06 och SHA-256 `638589917ba5a37c0c69bdd0e057b4fb873618981c286bde3d88488135313ee2`. Två manuellt startade lokala kommandon återställer respektive verifierar underlaget: `restore_verified_audit_inputs.py` och `verify_restored_audit_batch.py`. De skapar ingen schemaläggning eller automation. De daterade äldre avsnitten nedan beskriver tidigare sparlägen; de är inte aktuell körstatus.

## Fördjupad primärkällskontroll av de fyra hindren – 19 oktober 2026

Den avslutande källbatchen ger inga nya verifierade exekveringar att installera. Det finns därför inget nytt prisunderlag som motiverar ännu en oförändrad modellomkörning. Exakta fynd och saknade led finns i `audit_evidence/remaining_blocker_sources_20261019.json` och `fixed_day_price_gaps_20261019.json`.

- **SJR:** [Rogers överlåtelseblankett](https://about.rogers.com/wp-content/uploads/Letter-of-Transmittal-Shaw-Communications-Inc-2023-03-31.pdf), sida 5 och instruktion 12, anger betalning i CAD. [Rogers aktieägarinformation](https://about.rogers.com/investor-relations/shaw/) hänvisar beneficial holders till respektive intermediärs tidsplan. [OCC 52248](https://infomemo.theocc.com/infomemos?number=52248), publicerad 11 april 2023, bekräftar 29,87591536 USD per aktie som underlag för optionsavräkning. Det verifierar beloppet i det sammanhanget, men inte common-share-innehavarens USD-krediteringsdag. CAD-fordrans dagliga USD-värdering och tillgänglighet för återinvestering måste hanteras uttryckligt.
- **AEPPZ:** [AEP:s prospekt](https://docs.aep.com/docs/investors/currentProspectus/AEPEquityUnits-ProspectusSupplement.pdf) ger en justerbar omvandlingsformel baserad på föreskrivna VWAP-observationer. [Den genomförda remarketingen](https://www.aep.com/news/stories/view/8964/AEP-Announces-Remarketing-of-850-Million-in-Aggregate-Principal-Amount-of-Debt-Underlying-its-Equity-Units/) finansierar köpkontraktet via säkerheter. Slutlig kvot och samtliga komponenter per enhet är fortfarande inte verifierade. Varken maximal formelkvot eller totalt emitterade aktier dividerat med ursprungligt antal enheter installeras som gissad kvot; ytterligare 50 USD kontant läggs inte till.
- **FRC:** [FDIC:s besked 1 maj 2023](https://www.fdic.gov/news/press-releases/2023/pr23034.html) verifierar receivership och överföring av insättningar/tillgångar, inte en common-share-kurs eller en kontantlösen på noll. [NYSE:s besked](https://ir.theice.com/press/news-details/2023/NYSE-to-Suspend-Trading-Immediately-in-First-Republic-Bank-FRC-and-Commence-Delisting-Proceedings/default.aspx) är daterat **2 maj**, inte 1 maj. Bevarad rå och justerad FRC-historik slutar 28 april; fast exit 1 maj saknas. Ett generellt regelverk för bundet kapital vid omöjlig exit är en separat redovisnings-/exekveringsutvidgning, ingen återfunnen historisk kurs.
- **RNAZ:** Samtliga 1 249 bevarade observationer per basis kontrollerades. Efter 28 november följer 2 december; 1 december saknas. Detta bevisar en lucka i bevarat underlag, inte att all handel var stoppad. Senare kurs eller senaste tidigare kurs används inte som fast exit.

De avbrutna liveförfrågningarna gav inget bevarat svar. De redovisas därför inte som ny 404-verifikation. Dokumentationstäckningen förblir 286/288, fyra modellerade exekveringar kvarstår, universumavkastning och rankningsmervärde saknas. Urvalsmodellens verifierade negativa resultat kvarstår även om ett framtida underlag skulle stänga de sista luckorna.

## Historik före den färdiga samlade verifieringen


## Aktuell verifierad sparstatus – 19 oktober 2026

**NO-GO kvarstår. Granskningen är inte färdig.** PR 13 var öppen och inte mergad vid återkontrollen. Senaste faktiskt sparade kod-checkpoint var [`3aa19d4cec7c7414c7aec4db8e2c9fe8b884d2fb`](https://github.com/tartkennet/MomentumCloud/commit/3aa19d4cec7c7414c7aec4db8e2c9fe8b884d2fb). Den lokala arbetskatalogen är nu rensad. Senare lokala slutresultat kan därför inte behandlas som återkontrollerade eller återställda slutresultat.

Den sparade urvalsreplayen efter GOLD-rättningen och de fyra fullständiga efterföljarhistorikerna omfattar 645 positioner, 230 tickers och 43 månader. Alla positionsnycklar, priser och köp-/exitdatum anges matcha arkivet exakt, med oberoende kapitalaggregering PASS. Nettoavkastning: **−0,5460050227673818 %**, största dagliga nedgång **−50,38013190677646 %**, SPY med samma fasta månadskostnad **+70,20238513471013 %**. Detta är den sparade körningen från 14 oktober, inte en ny modellkörning den 19 oktober. Den föregår den sista lokala kontrollen efter NCR-installationen.

| Kontroll vid återstart | Verifierat sparläge |
|---|---|
| Dokumentationslista | Omräknad direkt från sparad lista: 286/288 fall; AEPPZ och RNAZ saknar färdig händelselösning |
| Dagsprisbatch | 558 CSV-filer finns i GitHub-trädet: ursprungliga 556 plus TEN:s två basisfiler |
| Rå/justerad förkontroll | Sparad sammanfattning anger 291/291 och 0 saknade; den fullständiga senare kontrollfilen är inte sparad |
| Tester | Sparad checkpoint anger 121 passerade lokala tester; inga nya tester kördes i denna återkontroll |
| Senaste sparade universumdiagnostik | Nio olösta exekveringar och en PARA/PSKY-basisavvikelse, före efterföljarhistorikerna och NCR-rättningen |
| Senare uppgift om fyra olösta fall och 123 tester | Finns i överlämningen, men slutresultatfilerna och de två sista testerna är inte sparade; måste återskapas |
| Giltig universumavkastning / rankningens mervärde | Saknas fortfarande |

Den senast sparade diagnostikens nio tickers är SIVB, FRC, SJR, AEPPZ, NCR, PARA, LNW, RNAZ och HLX. Överlämningen anger att en senare lokal diagnostik reducerade detta till FRC, SJR, AEPPZ och RNAZ utan basisavvikelser. Den senare uppgiften får inte ersätta den sparade diagnostiken innan en samlad lokal körning ger ett sparat resultat. Dokumentationstäckning är ingen godkänd exekveringsfrekvens.

Åtta sparade efterföljar-CSV:er har nu kontrollerats direkt: SIVBQ 407, PSKY 291, LNWO 222 och HOS 22 prisrader per basis. Samtliga åtta äldre manifesthashar visade sig avse CSV-innehållet plus en extra avslutande radbrytning. Manifestet rättas till hash för de faktiskt sparade filernas byte. Prisraderna och de installerade historikerna ändras inte. Detta är en reproducerbarhetsrättning, ingen ny pris- eller avkastningsrättning.

**Nästa konkreta beräkningssteg:** återställ kod och frysta indata från de sparade källorna och kör en samlad lokal verifiering av hela den redan installerade batchen. Spara testlogg, full prisförkontroll, urvalsavstämning och universumdiagnostik tillsammans innan ytterligare händelser installeras. Därefter utreds kvarvarande blockerare i en gemensam källbatch.

Överlämningens fyra kvarvarande utredningsspår är: FRC:s saknade fasta exit 2023-05-01; SJR:s verifierbara betalnings-/valutahantering och daglig värdering fram till betalning; AEPPZ:s faktiska corporate-unit-komponenter; RNAZ:s saknade observation på fasta exitdagen 2025-12-01. Senare kurser får inte bakdateras och inga priser, valutakurser eller rättighetsvärden får gissas. Daterad emittentidentitet, sammanhängande formationshistorik, leverans och verklig exekverbarhet kräver fortsatt granskning även om modellens resolver senare bara rapporterar fyra fall.

Ingen main-merge, produktionsändring, handel, dataköp, parameteroptimering eller automation ingår. Inga modelljobb startades under denna sparåterkontroll. Äldre avsnitt nedan är daterad historik; deras ord som ”körs” eller ”återstår” beskriver respektive checkpoint och är ingen aktuell körstatus.

## Tidigare dokumenterade checkpoints

## Samlad återställnings- och rättningscheckpoint – 14 oktober 2026

**121 lokala regressionstester passerar.** Hela den saknade prisbatchen är nu återhämtad och sparad: 556/556 ursprungliga nya dagsprisfiler, plus två observerade filer för TEN 2024-07-01. Den omräknade breda förkontrollen är **291/291 råa/justerade datumpar, 0 saknade**. Alla 405 fullhistoriker bevaras. De fyra efterföljarhistorikerna och daterad identitet finns säkrade.

GOLD:s återanvändning av Gold.com, CIK 1591588, från 2025-12-02 är rättad. Nya GOLD-innehav får inte spärras av Barricks tidigare symbolbyte till B. Gamla Barrick-innehav följer fortfarande B, och AMRK-innehav följer enbart nya GOLD. Tre nya regressioner passerar. En faktisk ny urvalsreplay efter denna rättning matchar exakt alla 645 positioner, köp-/exitdatum och priser, med oberoende kapitalavstämning PASS: −0,5460050227673818 % netto, −50,38013190677646 % daglig nedgång och +70,20238513471013 % kostnadsjämförbar SPY.

NCR:s 1 VYX+0,5 NATL är nu installerad för de två fasta granskningsscenarierna. Båda aktiekomponenterna värderas på exakt begärd dag och med kompatibel rå/justerad basis för exit och daglig close. Tolv observerade dagar i varje bas och komponent är separata exekveringsunderlag; de ersätter aldrig formationens fullhistorik. Daterade dataposter på första handelsdagen bekräftar CIK 70866 respektive 1974138. Sex nya tester kräver båda benen, rätt datum och originalets basis. Marknadspriserna använder testets kontinuerliga aktieenheter; faktisk kontantavräkning för aktiefraktioner har inte gissats och modellen är ingen bevisad handelsfyllnad.

Den riktade formationskontrollen av återanvända symboler och AEPPZ omfattar 177 poster över 43 signaler och 258 frysta referenssidor. 174 daterade CIK-poster matchar verifierade emittentintervall, inklusive nya Gold.com. AEPPZ är felklassat som CS på tre frysta signaldagar trots att instrumentet är corporate units. Det ligger kvar i granskningen; ingen riktad borttagning används för att förbättra resultatet. Ny DOC:s dagspost 2024-03-04 har en CIK-konflikt, medan frysta månadsreferenser från 2024-03-28 anger rätt Healthpeak-CIK 765880. Dessa kontroller verifierar inte all formationshistories kontinuitet eller en faktiskt möjlig fyllnad.

Den samlade universumdiagnostiken körs lokalt efter denna batch, men dess slutförande är ännu inte verifierat i denna checkpoint. NO-GO och frånvaron av en giltig universumavkastning kvarstår. Ingen main-merge, produktion, handel, dataköp, parameteroptimering eller automation har genomförts.


## Återstart och säkrad återställning – 14 oktober 2026

Arbetet återupptogs på användarens instruktion från verifierad head `3821474`. Den nya körmiljön fungerade men arbetsmappen var tom. Alla 410 textfiler återställdes från GitHub. Tio originalarkiv matchade sparade SHA-256. Den frysta cachen återställdes direkt till mindre delar: 507412232 byte, SHA-256 `638589917ba5a37c0c69bdd0e057b4fb873618981c286bde3d88488135313ee2`, version 3 och basis 2026-10-06. En första lokal extraktion var avklippt och användes inte för körning.

**112/112 regressionstester passerade** på den återställda koden med projektets låsta paketversioner. Alla 405 ursprungliga fullhistoriker bevarades. Fyra kompletta efterföljarhistoriker återhämtades och sparades: SIVBQ 407, PSKY 291, LNWO 222 och HOS 22 observationer i vardera basen. Elva daterade emittentobservationer är sparade. Saknad CIK behålls saknad. En konflikt framkom: datakällans DOC-post 2024-03-04 anger gamla Physicians CIK 1574540 trots Healthpeak-FIGI; juridiskt kvarvarande Healthpeak har CIK 765880. Konflikten får inte tyst godkännas som identitetsbevis.

32 av de 292 saknade dagspris-CSV:erna har nu återhämtats och säkrats: totalt 296/556 nya filer. Resterande 260 finns i återstartslistan. Ingen ny färdig universum- eller urvalskörning påstås i denna mellancheckpoint. Dokumentationstäckningen 286/288 och NO-GO kvarstår tills omräkning/verifiering slutförts.


## Stopp och verifierad sparning – 14 oktober 2026

Arbetet stoppades på användarens begäran. PR 13:s head verifierades som `a1fa847e9ca1103231e43e5af8101bfc04a6bd4a`, öppen och inte mergad. GitHub svarade och hade kvar checkpointen; det finns inget verifierat belägg för att detta avbrott orsakades av GitHub-krediter. Det observerade felet var `environment_offline` / `exec-server transport disconnected` i den lokala körmiljön.

Kodrättningar, händelseunderlag, dokumentation och de senast verifierade resultaten finns i checkpointen. Av 556 nya dagspris-CSV:er finns 264 verifierat i GitHub; 292 saknas där. Den efterföljande prisräddningen gav ingen verifierad ny branch-commit före stoppet. Fyra nya successorhistoriker och elva daterade identitetsobservationer var lokalt färdiga men deras filinnehåll är inte verifierat varaktigt sparat. Deras återställning och en samlad verifiering återstår. Den sista lokala modellomkörningen är inte verifierat slutförd. Inget fortsatt jobb påstås arbeta i bakgrunden.

Detta sparstopp säkrar en exakt återstartslista i `audit_evidence/stopped_checkpoint_20261014.json`; det ersätter inte de saknade prisfilernas innehåll. Den separata rapportfilens senaste bekräftade version är 10; ersättningen misslyckades när körmiljön blev offline. GitHub-rapporten är senare. NO-GO kvarstår, fulluniversumets avkastning och rankningens mervärde är obevisade.


## Senaste verifierade checkpoint – 12 oktober 2026

**NO-GO för köp kvarstår.** Den senaste färdiga urvalskörningen efter 33 nya
händelseinstallationer och daterad kedjehantering matchar exakt alla 645
positionsnycklar, signal-/köp-/exitpriser och köp-/exitdatum i arkivet:
230 tickers, 43 månader, −0,5460050227673818 % netto,
−50,38013190677646 % daglig största nedgång och +70,20238513471013 %
för SPY med samma fasta månadskostnad. Oberoende kapitalavstämning PASS.
112 lokala regressionstester passerade före körmiljöns avbrott.

Dokumentationstäckningen är **286/288** gamla fall. AEPPZ och RNAZ saknar
färdig händelselösning. Dokumenterade fall med okänd valuta-/betalnings-
hantering, spin-off, leverans eller exekvering är fortfarande blockerade.
Dokumentationstäckning är ingen exekveringspassfrekvens.

Den breda lokala prisförkontrollen blev färdig med **291/291 observerade
råa/justerade datumpar**, på exakt begärd dag. ATCO är löst. Den senaste
färdiga universumdiagnostiken hade **nio olösta exekveringar**: SIVB, FRC,
SJR, AEPPZ, NCR, PARA, LNW, RNAZ och HLX. Den publicerar ingen giltig
universumavkastning och inget bevis för rankningens mervärde.

Därefter hämtades fyra individuella successorhistoriker (SIVBQ, PSKY,
LNWO, nya HOS) och elva daterade identitetsobservationer. Båda identifierare
matchar föregångaren för SIVBQ/SIVB, HOS/HLX, Barrick-B/GOLD och nya
FISV/FI. Där leverantörens CIK saknas förblir det fältet saknat; juridisk
CIK från primärkällan redovisas separat. Gamla DOC har CIK 1574540, nya
Healthpeak-DOC CIK 765880; gamla Barnes-B CIK 9984 är inte Barrick CIK 756894.

En omkörning efter de fyra nya historikerna startades men dess slutförande
är **inte verifierat**. Körmiljön tappade anslutningen och rapporterar
`environment_offline` / `exec-server transport disconnected`. Ingen ny
slutavkastning eller pågående bakgrundskörning påstås. Först måste denna
checkpoint återställas i en fungerande körmiljö och den samlade verifieringen
slutföras. Kod och dokumentation säkras direkt i granskningsgrenen; formatering
och kommentarer har normaliserats från de redan lokalt testade patcharna.
Ingen ny lokal testkörning från den återställda GitHub-headen har kunnat göras.

Den befintliga rapportfilens senaste bekräftade version är 10 och ligger efter
denna GitHub-rapport. Försöket att ersätta den med den lokala uppdateringen
misslyckades eftersom miljön är offline. Inga modellparametrar har optimerats,
problemaktier eller förlorare har inte raderats, och ingen main-merge,
produktion, handel, dataköp eller automation har genomförts.



## Beslut och omfattning

**Det isolerade urvalstestet är klart. Bedömning: NO-GO för att godkänna denna urvalsmodell för köp utifrån det här testet.** Det är en granskningsbedömning, inte en ändring av produktionens godkännandestatus. Urvalet gav −0,5460 procent efter kostnader och hade en största daglig nedgång på 50,3801 procent. SPY gav +70,2024 procent med samma fasta månadskostnad.

**Hela universumjämförelsen är fortfarande ofullständig.** Det går därför inte att isolera rankningens mervärde jämfört med alla behöriga kandidater. Inga problemaktier har tagits bort i efterhand för att förbättra avkastningen. Ingen parameteroptimering, handel, main-merge eller produktionsändring ingår.

## Samma fasta regler, kontrollerade priser

Testet omfattar 43 månadskorgar med signaler 2023-02-28–2026-08-31, köp vid nästa öppning och sista exit 2026-10-01. Totalt 645 positioner, 230 unika aktier, 15 lika viktade positioner per månad. Rankningen är ursprungliga simple: 60 procent 12-månadersmomentum och 40 procent 6-månadersmomentum. Pris över 10 USD, rå dollaromsättning över 5 miljoner USD och historikkrav finns kvar. Inga extra trend-, extension-, volatilitet-, regim- eller stoppregler används. Kostnad: 0,30 procentenheter av månadens startkapital, varje månad.

Den historiska grundlistan innehåller 5 053–5 591 börsnoterade stamaktier per signalmånad före pris-, likviditets- och historikfiltrering. Appens 1 759 aktier avser en annan ögonblicksbild och ska inte användas som nämnare för denna historiska granskning.

| Kontrollerad mätning | Resultat |
|---|---:|
| Urval, efter fast månadskostnad | −0,5460 % |
| Urval, före fast månadskostnad | +13,2227 % |
| SPY, samma fasta månadskostnad | +70,2024 % |
| Urval minus kostnadsjämförbar SPY | −70,7484 procentenheter |
| SPY, prisavkastning utan månadskostnad | +93,3082 % |
| Största dagliga nedgång, urval | −50,3801 % |
| Positiva portföljmånader | 25/43, 58,14 % |
| Vinnande/förlorande positioner | 313/332 |

Utdelningar ingår inte i prisavkastningen för vare sig urval eller SPY. SPY-jämförelsen med samma månadskostnad är en standardiserad jämförelse; den beskriver inte kostnaden för en vanlig köp-och-behåll-investering. Ej prissatta CVR-rättigheter ingår inte i fasta kontantvederlag och är inte bevisade värdelösa. Resultaten är därför inte en fullständig totalavkastningsredovisning för sådana rättigheter.

Det tidigare definierade senare testfönstret omfattar 18 perioder: urval +5,2664 procent netto mot SPY +37,1172 procent före jämförelsekostnad. Daglig nedgång där: −42,1915 procent. Detta är samma redan definierade fönster; inga datum valdes för att förbättra resultatet. För hela perioden används den kostnadsjämförbara SPY-siffran ovan som huvudjämförelse.

## Verifiering

- 102 lokala regressionstester passerade, inklusive gemensam prisomräkning för exit och daglig värdering.
- Samtliga 645 positioners signal-, köp- och säljpriser kontrollerades: **1 935/1 935 PASS**, 0 avvikelser. Därav 1 921 prisjämförelser mot individuella endpoint-historiker och 14 kontantvederlag mot verifierade fasta villkor.
- **645/645 daterade emittentposter**, alla med CIK, matchar den frysta historiska referenslistan. Dess 258 paginerade sidor omfattas. Detta kontrollerar identiteten på signaldagen; efterföljande bolagshändelser kräver fortsatt uttryckliga villkor.
- 19 valda positioner berör bolagshändelser: 14 kontantutköp och 5 aktievederlag eller symbolbyten. Juridiska utbyteskvoter bibehålls. Priser konverteras mellan verifierade råa/justerade aktieenheter.
- Oberoende positions- och kapitalaggregering passerade för samtliga 43 perioder.
- En separat daglig värderingsserie byggdes från individuella historiker: **943 värderingspunkter, 0 saknade dagliga priser**. Slutavkastning och största nedgång matchar motorn till flyttalsnoggrannhet.
- Ursprungliga prisfel: 807 gapobservationer klassificerades som 150 verkliga gap och 657 datafel i BCPC/CPK/KW/TPC, 0 oklassificerade. 117 individuella historiker ersatte hela berörda historiken. Ytterligare 308 individuella historiker används för universumdiagnostik. BCPC/CPK finns inte bland de 645 valda positionerna i detta isolerade test.
- De tidigare extrema prisflaggorna har kontrollerats mot individuella priser. Stora vinster eller förluster är inte i sig ett skäl att ta bort en aktie.

Kontrollerna visar intern och individuell prisöverensstämmelse. De är inte en oberoende revision av dataleverantören eller bevis för framtida lönsamhet.

## Felet som gav falsk vinst och fel daglig risk

BREA bytte till SLMT med juridiskt oförändrad 1:1-kvot. Successorns senare omvända split gav annan justerad prisbasis än den gamla symbolens historik. Det tidigare exitpriset 114,10 skulle vara 11,41 i positionens ursprungliga enheter. Med entry 28,06 blir positionens avkastning **−59,3371 procent**, inte +306,63 procent.

Den generella rättningen använder parade råa och justerade priser på båda sidor om bolagshändelsen. Samma omräkning används nu för exit och daglig värdering. Saknad eller oförenlig basis stoppar beräkningen; juridiska kvoter ändras inte för att passa kurserna. Kontantkomponenter skalas till samma ursprungliga enheter.

Den äldre rapporterade urvalsavkastningen +21,3093 procent var ogiltig före basisrättningen. Den korrigerade är −0,5460 procent, en skillnad på −21,8553 procentenheter för samma urval. Även den gamla dagliga riskberäkningen efter exitfixen var fel: −52,5531 procent största nedgång rättas till −50,3801 procent. Äldre körningssiffror får inte återanvändas som slutresultat.

Rättningen, scenariomärkningen och fyra installationsregressionstester är sparade i granskningsgrenen, commit `4b3b86f3b90e04cad8bb5c0a0ff70af123eeb13a`. Kontrollerna kördes lokalt. Committen använder `[skip ci]` för att undvika en ny betald Actions-omkörning. Den är inte mergad eller publicerad i produktion.

## Fördelning och svaga månader

Positionernas största kontrollerade vinster: GRRR +197,13 procent (signal 2025-01-31), AXTI +128,07 procent (2026-01-30), CDTX +103,12 procent (2025-10-31). Största förluster: FTEL −69,97 procent (2024-11-29), CRBP −66,14 procent (2024-08-30), LASE −64,87 procent (2024-09-30). Dessa är enskilda positionsutfall, inte deras bidrag till hela flerårsavkastningen.

| Signal för månadskorg | Portföljens nettoavkastning |
|---|---:|
| 2026-06-30 | −28,70 % |
| 2024-11-29 | −19,89 % |
| 2025-10-31 | −19,85 % |
| 2025-02-28 | −18,44 % |
| 2025-11-28 | −13,89 % |

631 exits är vanlig ombalansering och 14 är kontantutköp. Testet har inga stoppar. Sista historiska korgen, 2026-09-01–2026-10-01: QTTB, ORKA, FCEL, SYRE, MXL, STX, ATEX, SNDK, WDC, MU, TNGX, SLS, HUT, MBX och RLAY. Det är historiska testpositioner, inte ett aktuellt köpförslag.

## Exakt kvarvarande begränsning

Den färska fulluniversumkörningen `37753784684`, jobb `113234457002`, stoppade på **288 signal/ticker-fall, 256 unika tickers i 42 signalperioder**. Det är inte 256 aktier som ska tas bort från nutida handel. Fallen omfattar saknade köp/exit, gamla symboler, återanvända symboler och ofullständiga historiska exekveringsvillkor. Exempel är SIVB/FRC, UMPQ och gamla DICE/EGLE som inte får kopplas till senare bolag eller ETF:er med samma ticker.

Alla 645 valda positioner har full pris- och daterad signalidentitetstäckning. Fulluniversumets framåtriktade exekveringstäckning är däremot inte komplett och dess avkastning kan inte rapporteras. Saknade priser ersätts inte med noll eller godtyckligt sista pris. Historiska förlorare tas inte bort i efterhand.

Det går därmed inte att bevisa rankningens mervärde, sektorneutralitet eller en Shapley-fördelning över enskilda regler. Historisk SIC-täckning var endast cirka 60 procent i tidigare underlag. Turnover kan inte separeras från den fasta månadskostnaden. Övriga tidigare scenarier har inte samtliga genomgått denna nya oberoende dagliga NAV-kontroll och redovisas därför inte här som slutligt granskade.

**Vägval:** använd inte denna testmodell som godkänt köpurval. Den slutförda isolerade kontrollen motiverar att stoppa upprepade oförändrade omkörningar. Ett fullständigt rankningstest kräver att den bifogade återstående exekveringslistan först får verifierbara historiska lösningar; det blir ett separat kompletteringssteg, inte en ny parameterjakt.

## Reproducerbart underlag

Underlagsarkivet innehåller individuella prisserier, parade basispriser, kontrollerade positioner och periodresultat, samtliga pris- och identitetskontroller, den oberoende dagliga NAV-serien samt fulluniversumets kvarvarande fall. Manifestet innehåller filhashar och källa/version.

Frysta modellindata: ursprungsrun `37419651430`, artifact `11393004537`, cachebasis 2026-10-06. Export `37753784722` passerade; alla tre delhashar och arkivhashen verifierades före lokal körning. Prisverifikationer hämtades 2026-10-08 från individuella Massive/Polygon-aggregat för de aktuella historiska datumen. Bolagshändelsernas SEC-/börskällor finns inline i granskningskodens verifierade settlements. Ingen CVR prissätts genom gissning.

- [Gransknings-PR 13](https://github.com/tartkennet/MomentumCloud/pull/13)
- [Sparad daglig basisrättning](https://github.com/tartkennet/MomentumCloud/commit/4b3b86f3b90e04cad8bb5c0a0ff70af123eeb13a)
- [Frysta indata exporterade](https://github.com/tartkennet/MomentumCloud/actions/runs/37753784722)
- [Fulluniversumets kvarvarande blockerare](https://github.com/tartkennet/MomentumCloud/actions/runs/37753784684)

GitHub Actions-budgeten på skärmbilden är 20 USD totalt med stop usage aktiverat, varav 10 USD visades förbrukade. Slutlig debitering har inte kunnat verifieras här. Granskningen ändrar inte budgeten och startar inga fler modelljobb.

## Uppföljning: sparade rättningar och återkontroll 9 oktober 2026

Kalenderfelet för kontantutköp på börshelgdagar är rättat i granskningsgrenen: det juridiska datumet bevaras, medan värderingen hamnar på första tillåtna handelssession. Om ingen session finns i exekveringsfönstret stoppas beräkningen. ICVX-fallet testas nu även genom den verkliga motorns resolver, utöver de fristående installationskontrollerna. 99 regressionstester passerade lokalt med projektets fasta paketversioner.

67 ytterligare tidigare SEC-granskade bolagshändelser är sparade som validation-only settlements, varav 51 kontantvederlag och 16 aktie-/blandvederlag. Juridiska kvoter bevaras och ej prissatta CVR-rättigheter utesluts från fasta vederlag. Barnes-händelsen för B är dokumenterad men inte installerad eftersom symbolen senare återanvänds av Barrick. Fulluniversumets gamla FISV-symbolcykel och andra återanvändningar kräver fortfarande daterad identitetshantering.

Dokumentationslistan innehåller nu 133 tidigare granskade händelser inklusive den karantänlagda B-händelsen. Den motsvarar händelseunderlag för 146 av de 288 tidigare signal/ticker-fallen. **142 fall för 123 tickers saknar fortfarande motsvarande granskad lösning.** Detta är dokumentationstäckning, inte bevis för att exekvering och prisbasis passerar. Inga nya fulluniversumresultat finns efter denna uppdatering.

De 67 installerade händelsedatumen korsar ingen av de 645 sparade innehavsperioderna. En ny oberoende återkontroll av arkivet verifierade filhashar, alla priser och identitetskontroller, 15 positioner per månad, positionsavkastningar, kostnadsjusterad månadsaggregering samt daglig slutvärdering och nedgång. Resultatet förblir −0,5460050228 procent mot SPY +70,2023851347 procent med samma kostnad. Denna kontroll är en återverifiering av arkiverade observationer, inte en ny full modellkörning.

Prisgränsen i urvalstestets simple_builder är 10 USD. Den tidigare rapporttexten 5 USD var fel; inga parametrar ändrades. Korta referensserier för enskilda positioner får inte ersätta hela modellhistoriken. De kompletta individuella överstyrningarna omfattar 405 distinkta tickers, 117 + 308 med 20 överlapp. Ett tidigare återställningsförsök som använde korta referensserier som fullhistoriker ändrade urvalet; dess resultat är ogiltigt och ingår inte i denna rapport.

- [Sparade 67 händelser och full återstående fallista](https://github.com/tartkennet/MomentumCloud/commit/d48adb7b6754c769934ae9da2b0ed1519c0d364f)
- [Sparad kalenderfix](https://github.com/tartkennet/MomentumCloud/commit/0050526478231d0b21ab0a451d8ec2f5d6fe8823)

Alla ändringar ligger i granskningsgrenen. Inga nya GitHub Actions-körningar har begärts. Det isolerade urvalets NO-GO kvarstår; fulluniversumets avkastning och rankningens mervärde är fortfarande obevisade.

## Samlad rättning 9 oktober 2026 – sparad i granskningsgrenen 10 oktober

326 fullständiga primära SEC-texter hämtades för de återstående händelsefallen, med 0 hämtningsfel. Utdragens tidigare saknade inledningar är nu tillgängliga för kontroll av faktiskt slutdatum och vederlag. Det är tillgängligt underlag, inte ett påstående att alla 326 dokument har färdiggranskats.

31 nya bolagshändelser har verifierats och installerats lokalt. Fasta kontantvederlag: SNPO 10,75, CERE 45, JAMF 13,05, HONE 12, AZPN 265, CFLT 31, APLS 41, DCPH 25,60, DOOR 133 och MRUS 97 USD. APLS ej prissatta CVR värderas inte. För MRUS används den faktiska back-end-annulleringen den 30 december 2025, inte den tidigare tenderacceptansen. HONE:s verifierade icke-val är kontantvederlag, inte en gissad aktiekvot.

Aktie-/blandvederlag: LTHM→ALTM, HEES→HRI, CTRA→DVN, MMP→OKE, DEN→XOM, DO→NE, IPG→OMC, SNCY→ALGT, NS→SUN, ESTE→PR, COOP→RKT, HES→CVX, SPR→BA, NSA→PSA och ARIS→WES. Symbolbyten med oförändrade aktieenheter: SIVB→SIVBQ, FRC→FRCB, OSTK→BYON, CHK→EXE, LANC→MZTI och MNMD→DFTX. ARIS använder dokumenterat icke-val om 0,625 WES-enheter. Exakta datum, kvoter, kontantkomponenter och primärkällor finns i det granskade rättningspaketet.

Dokumentationstäckningen har ökat från 146 till **182 av 288 gamla signal/ticker-fall**. **106 fall för 92 tickers saknar fortfarande en motsvarande färdiggranskad händelselösning.** Inte alla dessa är dataleverantörsfel. Varje rättning behöver dessutom kontrolleras mot full historik, daterad emittent och rå/justerad prisbasis. Ingen ny fulluniversumkörning har genomförts efter denna batch; 182/288 är inte en exekveringspassfrekvens.

De 102 lokala regressionstesterna passerar. Tre nya integrationstester kontrollerar att motorn använder den observerade SIVBQ-kursen på rätt dag och att en senare FRCB-kurs inte bakdateras. Rättningspatchen kan appliceras på granskningsgrenens sparade head 691798 dd 8774 ccefab 1796 d 72 e 1 f 33 ea 6 cc 06932; detta kontrollerades med git apply --check. Inga Actions-körningar startades.

SIVB:s oförändrade CUSIP och symbolbyte till SIVBQ den 28 mars 2023 verifieras av OCC-memo 52179. Individuell OTC-data visar öppning 0,877 USD den 3 april 2023, det krävda exitdatumet. FRC:s symbolbyte till FRCB den 3 maj verifieras av OCC-memo 52352. OCC-memo 52358 anger NYSE-handelsstopp den 1 maj och OTC-start den 3 maj. Den första observerade öppningen är 0,396 USD den 3 maj. Parade råa/justerade OTC-serier är identiska i de hämtade fönstren, men originalsymbolens basis måste fortfarande verifieras för full modellintegration.

**FRC kan inte säljas till en observerad öppningskurs den 1 maj enligt det fasta exekveringsfönstret.** En kurs från den 3 maj är inte en kurs från den 1 maj. Den oförändrade modellen stoppar därför det fallet korrekt. En modell som håller spärrat kapital och säljer vid senare återöppning skulle vara en uttrycklig ändring av exekveringshanteringen, med separat redovisning av kapitalbindning och risk; den får inte smygas in som en prisrättning. OTC-prisobservationer bevisar inte heller en faktisk möjlig fyllnad för varje portföljstorlek.

Automatisk godkännandegranskning avvisade sparningen av denna batch till GitHub med hänvisning till den tidigare pausen för nya commits och körningar. Ingen alternativ väg till samma mutation användes. Den här batchen var då lokalt färdig men ännu inte sparad i repo. Blockeringen har därefter lösts och sparningen genomfördes den 10 oktober, se uppföljningen nedan. Fulluniversumets resultat och rankningens mervärde är fortfarande obevisade.

Ingen av de 31 nya händelsedatumen korsar de 645 arkiverade valda innehavsperioderna. Den arkiverade, återverifierade urvalsavkastningen ändras därför inte av dessa installationsposter; detta ersätter inte en full ny modellkörning.

## Återupptaget arbete 10 oktober 2026

Den tidigare GitHub-blockeringen är löst efter användarens nya instruktion att återuppta arbetet och använda GitHub med hänsyn till budgeten. De 31 rättningarna är nu sparade i commit 687 af 6259314698 b 70 c 8 ce 96912 e 4 c 1 e 39620 fd 9. Ingen betald Actions-körning startades; head-kontrollen visade 0 körningar för committen.

Ytterligare sex primärverifierade händelser är sparade i commit 05 ddff 7 ec 1245881 b 829 e 608 e 061333 b 79074554: JBT→JBTM 1:1 den 3 januari 2025, PPBI→COLB 0,9150 med handelsstopp den 2 september 2025 (juridiskt slutdatum 31 augusti), SQ→XYZ 1:1 den 21 januari 2025, GPS→GAP 1:1 den 22 augusti 2024, BRP→BWIN 1:1 den 20 maj 2024 och BOWL→LUCK 1:1 den 12 december 2024.

Individuella råa och justerade successorkurser på planerade exitdatum hämtades för samtliga sex och är identiska inom respektive par. Observerade råa öppningspriser: JBTM 130,88 USD den 3 februari 2025, COLB 26,505 USD den 2 september 2025, XYZ 88,64 USD den 3 februari 2025, GAP 22,19 USD den 3 september 2024, BWIN 33,72 USD den 3 juni 2024 och LUCK 10,08 USD den 2 januari 2025. Detta verifierar tillgängliga successorkurser, men inte originalsymbolens historiska justeringsbasis eller hela innehavsperioden.

Aktuell dokumentationstäckning: **189/288 gamla fall**. **99 fall för 86 tickers** saknar fortfarande granskad händelselösning. Det finns dessutom dokumenterade fall med återstående pris-, identitets- eller exekveringsbegränsningar, inklusive FRC. 102 lokala regressionstester passerade efter den nya batchen. Fulluniversumtestet har inte körts färdigt och rankningens mervärde är fortfarande obevisat. Inga problemaktier har tagits bort och inga parametrar har optimerats.


## Övertagande och ny checkpoint 12 oktober 2026

GitHub-grenens faktiska head kontrollerades både genom PR 13 och direkt branch-ref: `6625c1f5e8a6723ff9d97ab5df8f98335ca98d90`. Den är den tidigare bekräftade sparningen, inte en nyare antagen commit. PR 13 är öppen och inte mergad. Den sparade Library-rapporten var version 7 och låg efter koden: den slutade på 189/288 dokumenterade fall. De 28 händelserna och offlinekoden finns däremot i head. SNV och SMLR saknades där och har återgranskats från primärkällor i denna batch.

### Återställda indata och faktiskt ny lokal körning

De tre frysta indatadelarna återställdes, och den sammanfogade pris-cachefilens SHA-256 är `638589917ba5a37c0c69bdd0e057b4fb873618981c286bde3d88488135313ee2`, samma som offlinekodens låsta hash. Originalarkiven för klassificering, universumhistoriker och rå dollaromsättning hämtades från redan befintliga GitHub-artifacts, utan nya Actions-jobb. Samtliga tio hämtade arkiv matchade GitHubs SHA-256. Fullhistorikerna omfattar 117 klassificerade och 308 universumhistoriker, med 20 överlapp, alltså 405 distinkta tickers.

Det äldre `MomentumCloud_restored_evidence.zip`, Library-ID `libfile_7e4d8024ebdc8191b88d5291f48f0285`, är ofullständigt: ZIP-centralförteckningen saknas och den första komprimerade medlemmen slutar mitt i ML. Det användes inte som modellindata. En komplett ny checkpoint med de tio verifierade originalarkiven är sparad som `MomentumCloud_recovery_checkpoint_20261012.zip`, Library-ID `libfile_865e6eed0fc48191beef2166aa7486a3`. Exakta artifact-ID:n, körningar och hashvärden finns i `audit_evidence/recovery_artifacts_20261012.json`.

En **faktisk lokal offlinekörning** av det oförändrade `momentum_selection_only` genomfördes efter återställningen. Alla 645 positionsnycklar och samtliga signal-, köp- och exitpriser matchar det separat återverifierade arkivet. 230 tickers och 43 månader. Oberoende positions- och kapitalaggregering PASS. Nettoavkastning −0,5460050227673818 %, daglig största nedgång −50,38013190677646 %, SPY med samma fasta månadskostnad +70,20238513471013 %. Detta är en ny körning av urvalet, inte en färdig universumjämförelse. Raden `added_position_keys=645` i körningens generiska jämförelse avser att dess äldre jämförelsefil saknades; den riktiga jämförelsen mot det kontrollerade arkivet visar inga ändrade positionsnycklar.

### Samlad ny händelsebatch

22 ytterligare händelseposter är installerade som validation-only terms. Exakta primärlänkar, juridiskt datum, operativ första session, kvoter och begränsningar finns i `audit_evidence/action_batch_20261012_recovered.json` och settlement-koden.

| Gammal symbol | Operativ händelsedag | Verifierat vederlag/symbolbyte |
|---|---|---|
| SNV | 2026-01-02 | 0,5237 PNFP, ny Georgia-emittent CIK 2082866 |
| SMLR | 2026-01-16 | 21,05 ASST, juridisk kvot bevarad |
| LSXMA, LSXMK | 2024-09-10 | 0,8375 SIRI i den nya emittenten |
| LBRDA, LBRDK | 2026-08-20 | 0,236 CHTR |
| HEP | 2023-12-01 | 0,3150 DINO + 4 USD |
| AZEK | 2025-07-01 | 1,0340 JHX + 26,45 USD |
| WWE | 2023-09-12 | 1 TKO |
| CMPO | 2026-01-23 | GPGI, 1:1 |
| SIX | 2024-07-02 | 0,5800 FUN |
| VSTO | 2024-11-27 | 1 GEAR + 25,75 USD |
| JNVR | 2025-05-05 | DFDV, 1:1 |
| EYEN | 2025-07-03 | HYPD, 1:1 |
| CSWI | 2025-06-09 | CSW, 1:1, samma USA-aktie |
| PX | 2026-02-11 | RPC, 1:1, Ridgepost-emittenten |
| VERB | 2025-09-02 | TONX, 1:1 |
| PSTG | 2026-04-17 | P, 1:1, oförändrad CUSIP |
| DOOO | 2025-12-08 | DOO på Nasdaq, 1:1, inte CAD-kurs på TSX |
| SILV | 2025-02-14 | 1,6022 CDE, inte den avrundade optionskvoten 1,60 |
| SCS | 2025-12-10 | Dokumenterat icke-val: 0,2192 HNI + 7,20 USD |
| DESP | 2025-05-15 | 19,50 USD kontant |

SIX:s separata specialutdelning om 1,53 USD är dokumenterad men utelämnad enligt det oförändrade prisavkastningsmåttet, inte bedömd värdelös. CMPO:s tidigare RHLD-spin-off är en separat händelse. Enkla symbolbyten ändrar inte juridisk aktiekvot för att passa senare splitjusterade priser. SNV:s efterföljare är inte den gamla PNFP-emittenten; LSXMA/LSXMK får inte kopplas till gamla SIRI-aktieenheter. PX:s RPC är Ridgepost, inte bolaget RPC Inc. vars ticker är RES. Dessa observationer ersätter inte daterad emittent- och prisverifiering.

Ingen av de 22 nya händelsedatumen korsar de 645 arkiverade valda innehavsperioderna. Den lokala urvalskörningen utfördes före dessa nya installationer och använder de tidigare sparade händelserna. Ingen ny full modellkörning påstås ha validerat de 22 nya posterna. Efter installation och tre nya fail-closed regressioner passerade **105 lokala tester**.

### Omräknad täckning och kvarvarande hinder

Före denna batch var dokumentationstäckningen faktiskt **222/288**, med **66 fall för 58 tickers** utan granskad händelselösning. Efter de 22 nya tickerposterna täcks ytterligare 25 gamla fall: **247/288**. **41 fall för 36 tickers återstår** utan sådan lösning. Full fallista och kvarvarande exekveringsstatus finns i `audit_evidence/universe_remaining_ledger.json`. Detta är fortfarande dokumentationstäckning, inte godkända exekveringar.

Den breda prisbasisförkontrollen omfattar 268 potentiella datumpar för dokumenterade händelser som inte redan täcks av fulla individuella historiker. 12 par kan besvaras med sparade enskilda observationer, 256 saknas, motsvarande 512 råa/justerade endpoint-förfrågningar. Listan är en bred datainsamlingsbatch, inte bevis för att varje datumpar behövs av en faktisk slutlig universumposition. Förkontrollen samlar båda baserna när de saknas; den kör inte modellen och fyller inte priser. `audit_action_basis_batch.py` och `audit_evidence/action_basis_preflight_20261012.json` innehåller resultatet.

**ATCO 2023-03-27 saknar fortfarande både rått och justerat individuellt prisunderlag.** Den påbörjade äldre batchen kan inte verifieras som sparad. Den nya lokala förkontrollen återbekräftar frånvaron. Ingen ny universumkörning startades efter denna batch eftersom första kända prisbasisblockeraren kvarstår. Lokal Massive/Polygon-nyckel finns inte i den aktuella miljön; GitHub-connectorn kan hämta sparade artifacts men kan inte läsa repo-secrets eller starta en ny datahämtning här. Inga nya Actions-jobb har startats och ingen automation har skapats.

**FRC:s fasta exit 2023-05-01 är ett separat faktiskt exekveringshinder.** Senare FRCB-öppning den 3 maj får inte bakdateras. Mer prisdata i sig bevisar inte en möjlig exit den 1 maj. En eventuell modell som håller kapital spärrat och säljer vid senare återöppning kräver ett uttryckligt separat beslut, redovisning av kapitalbindning och risk, och får inte rapporteras som en rättning av den oförändrade modellen. Daterad identitet för FI/FISV, DOC/PEAK och B/GOLD samt val/proratering och övriga händelser återstår också. Problemaktier och förlorare har inte raderats.

NO-GO för det granskade urvalet kvarstår. Fulluniversumets slutavkastning och rankningens mervärde är fortfarande obevisade. Sparningen sker endast i granskningsgrenen med `[skip ci]`. Ingen main-merge, produktionsändring, handel, dataköp eller parameteroptimering har genomförts.

### Samlad kontroll av de 41 återstående fallen

En separat offlineinventering kontrollerade samtliga 41 återstående fall mot de återställda fulla individuella historikerna. Alla 41 saknar ett komplett observerat rått/justerat prispar för det fasta köp- eller exitdatumet. Detta är inte bevis för att 41 bolagshändelser har inträffat: det kan också röra sig om datatäckning, symbolbyte, emittentbyte, handelsstopp eller andra exekveringsvillkor. En senare observerad kurs användes inte för det fasta datumet. De fasta datumen hämtades från de 43 kontrollerade perioderna, inte från motorns äldre sena fallback-exits.

`audit_remaining_case_prices.py` och `audit_evidence/remaining_cases_price_inventory_20261012.json` sparar hela kontrollen med antal observationer och faktiskt första/sista datum för varje bas. Denna inventering ändrar varken 247/288 dokumentationsfall eller NO-GO, och är ingen ny universumkörning.


## Fortsatt batchgranskning och GO-villkor 12 oktober 2026

Den återupptagna sessionen kontrollerade PR 13:s faktiska head på nytt:
`546e538e84cf09b4a5aa04038abd2419a7e1ae07`, öppen och inte mergad.
Den tidigare nyckelblockeringen har lösts genom den anslutna datatjänsten:
ATCO 2023-03-27 är nu direkt observerad i både rå och justerad basis. Båda
har öppning 15,49, stängning 15,48 och volym 2295603, med tidsstämpel på den
begärda dagen. Detta är ett observerat prispar, inte en godkänd universumexit.
Den samlade hämtningen av återstående prisbasispar körs och sparar enskilda
CSV-observationer löpande. Korta prisfönster ersätter inte formationens 405
kompletta individuella historiker. Slutförandet är ännu inte verifierat i
denna mellancheckpoint; den aktuella manifestfilen anger faktiskt mottagna par.

### Ytterligare samlade rättningar

19 nya händelser har granskats från primärunderlag och installerats för
validering. De elva symbol-/aktieslagsbytena är BK→BNY, EQR→VMRK, LC→HAPN,
MEG→ONT, VSCO→VSXY, SATS→ECHO, KAR→OPLN, CWEN.A→CWEN, FDP→DMC, HLX→HOS
 och TNP→TEN. Samtliga juridiska kvoter är 1:1. EQR:s symbolbyte sker 18 augusti;
AVB:s separata merger sker 17 augusti och får inte ersättas med en direkt
AVB→VMRK-genväg som missar mellanliggande session. HLX:s kvot är 1, inte
legacy Hornbecks 10,27167. Exakta datum och källor finns i
`audit_evidence/action_batch_20261012_symbols.json`.

De åtta övriga posterna är ENFN→CWAN 0,4676 vid dokumenterat icke-val,
PARA→PSKY 1 aktie vid ClassB icke-val, VMW 142,50 USD kontant vid dokumenterat
slutligt icke-val, ERF→CHRD 0,10125+1,84 USD, CADE→HBAN 2,475,
REVG→TEX 0,9809+8,71 USD, PRMW→PRMB 1 aktie och SBOW→CRGY 3,125 vid icke-val.
Valfria alternativa rubrikbelopp eller preliminära prorateringar används
inte som standardvederlag. ERF:s separata extrautdelning 0,232675 USD och
PRMW:s specialutdelning 4,38 USD är dokumenterade men utelämnade enligt
oförändrad prisavkastningsdefinition, inte värderade till noll som rättigheter.
Nya successoremittenter och OTC-instrument kräver fortfarande daterad identitet.
Exakta primärlänkar och begränsningar finns i
`audit_evidence/action_batch_20261012_terms.json`.

Ingen av de 19 nya händelsedatumen korsar någon av de 645 arkiverade valda
innehavsperioderna. Dokumentationstäckningen är nu 270/288 gamla fall;
18 fall för 17 tickers återstår utan färdiggranskad händelselösning.
Detta är fortfarande dokumentationstäckning, inte godkända exekveringar.

### Oberoende avstämning av förlusterna

`analyze_verified_selection_losses.py` räknar dollarbidrag på den faktiska
nettokapitalbanan och stämmer av dem mot både slutkapital och nedgångens
observerade topp/botten. Vid 10000 USD startkapital blev slutkapitalet
9945,399498 USD. Aktievinster/förluster netto på denna kapitalbana var
+1407,624137 USD och faktiska fasta modellavgifter 1462,224639 USD, vilket
stämmer till kapitalförändringen−54,600502 USD.

Utan den fasta avgiften blir samma prisavkastningsserie+13,222697 %.
Skillnaden mot nettoserien är 13,768702 procentenheter inklusive ränta-på-ränta;
den är inte samma mått som avgifternas direkt summerade dollarbidrag.
Den geometriska månatliga bruttoavkastningen är 0,289223 %, under den fasta
månadskostnaden 0,30 %. Kostnaden gör alltså slutresultatet negativt,
men förklarar inte den stora dagliga nedgången.

Största nedgången går från 11 november 2024 till 4 april 2025.
Direkta avgifter bidrar med cirka 2,21 % av kapitalförlusten mellan topp och
botten; aktiebidragen förklarar resten. Ingen registrerad bolagshändelse
finns bland de valda innehaven i denna nedgångsperiod. BREA-händelsen kommer
senare, oktober 2025. De tio största negativa tickerbidragen står för 42,51 %
av summan av negativa aktiebidrag i perioden: FTEL, QUBT, RDW, CAPR, ZETA,
LUNR, RAIL, IONQ, QMCO och RKLB. Det är en koncentrerad riskförlust, inte
bevis för att dessa förlorare får tas bort. Full avstämning finns i
`audit_evidence/selection_loss_attribution_20261012.json` och motsvarande
positions-, avgifts- och nedgångs-CSV-filer.

Alla 645 positioner har faktisk rank 1–15,15 per månad. Ingen framtidsstyrd
backfill till rank 16 eller lägre inträffade i just detta kontrollerade urval.
Det generiska backfill-läget är därmed inte bevis på sådan påverkan här.

### Fortsatt validering och faktiskt GO-beslut

`run_universe_diagnostic_batch.py` samlar kända saknade/motstridiga
bolagshändelsebaser i en enda universumdiagnostik. Dessa exekveringar förblir
olösta; ingen gissad kurs eller avkastning för ett rensat deluniversum
publiceras. Oväntade fel stoppar fortfarande körningen. Scriptet är sparat,
men en färdig diagnostikkörning påstås inte i denna mellancheckpoint.

`docs/GO_validation_protocol.md` låser de återstående bedömningsvillkoren.
Alla 43 analyserade månader är redan sedda data och får inte döpas om till
ny, orörd holdout. Verklig spread/slippage/marknadspåverkan, en i förväg
beslutad riskpolicy och helt nya valideringsdata är inte verifierade.
Ingen framtida paper trading startas utan separat positivt beslut.
Aktuellt beslut är fortsatt **NO-GO för köp**; slutförd granskning kan
fortfarande ge NO-GO. Ingen parameteroptimering har utförts.

### Ytterligare verifierade juridiska villkor och begränsningar

Efter checkpoint `8a410df` tillkom DOC→PEAK 0,674 den 1 mars 2024 och PEAK→DOC 1
den 4 mars 2024, FI→FISV 1 den 11 november 2025, GOLD→B 1 den 9 maj 2025,
AVB→EQR 2,793 den 17 augusti 2026, ISSC→IA 1 den 18 augusti 2026,
LNW→LNWO 1 den 13 november 2025, TRTN→BIPC 0,758545+54,61096 USD
den 28 september 2023, BLD→QXO 20,200 vid icke-val den 1 juli 2026,
MTAL 12,25 USD kontant den 24 oktober 2025, CEPT→SECZ 1 den 2 juli 2026,
IGT→BRSL 1 den 2 juli 2025, MAG→PAAS 0,58844257+4,52847757 USD
den 4 september 2025 och Barnes-B 47,50 USD kontant den 27 januari 2025.

Barnes slutfördes 27 januari, inte vid omröstningen 9 januari. FISV:s
återintroduktion och DOC:s nya emittent hanteras med daterade intervall;
gamla innehav kan följa flera juridiska omvandlingar utan att nya innehav
får en gammal emittents kvot. AVB:s EQR-session 17 augusti bevaras före
VMRK:s första session 18 augusti. Detta ersätter inte en komplett daterad
formationskontroll.

MAG:s slutliga vederlag kommer från den publicerade rättelsen OCC 57233,
inte det felaktiga kontantbeloppet i 57232 eller den avrundade optionskvoten
58/100. Aktiefraktioner rundas enligt villkoren ned till hela aktier;
ingen påhittad likvid tilldelas dem. Leverans var fördröjd genom 8 september.
TRTN:s slutliga icke-val är 0,758545 BIPC+54,61096 USD, inte den valbara
blandningen 0,3895+68,50. Optionsunderlaget beskriver leveransfördröjning
genom 4 oktober, varför faktisk handel på fasta exitdagen 2 oktober fortfarande
måste verifieras. Dessa är juridiska installationsposter, inte exekveringsgodkännanden.

NCR:s rättigheter är 1 VYX+0,5 NATL; en VYX-only-exit har inte installerats.
SJR:s vederlag är 40,50 CAD per publik ClassB-aktie. Betalningsdag och
USD-konvertering har inte gissats. AEPPZ är enligt SEC-underlag före
signalen 6,125% Corporate Units med skulddel och framtida aktieköp, inte
AEP-common. Slutlig individuell kvot och alla komponenter är inte verifierade;
instrumentet har inte tagits bort ur jämförelsen.

RNAZ saknar fortfarande observerad kurs på fasta exitdagen 2025-12-01.
Ny data i båda baserna har första senare observation 2025-12-02.
Den nya responsen hade 1245 rader från 2021-10-13, fyra äldre dagar färre
än den frysta 1249-radshistoriken från 2021-10-07. Gemensamma OHLC-priser
var identiska. Rå volym avvek bara genom heltalstrunkering under en aktie.
Den kortare responsen ersatte inte formationens fullhistorik.
Detta bevisar avsaknad i datakällan, inte säkert att all marknadshandel var stoppad.

Alla 43 månader har redan granskats. Det generiska fältet
`out_of_sample_metrics` för 18 månader är ingen ny orörd holdout.
Verklig spread/slippage/marknadspåverkan och en förhandsbeslutad riskpolicy
är inte verifierade. Ingen paper trading har startats.
