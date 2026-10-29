"""Verify and deliver completed risk research without the interactive runtime."""
import ast, hashlib, json, os, shutil, subprocess, zipfile
from pathlib import Path
from audit_core_stop_policy import audit
from run_momentum_core import source_fingerprint
root, prior, cache, original = map(Path, ("current_evidence","previous_evidence",".momentum_core_cache",".original_core_cache"))
out=Path("report_out"); out.mkdir(exist_ok=True)
cur=json.loads((root/"attempts.json").read_text()); old=json.loads((prior/"attempts.json").read_text())
assert cur["all_attempts_completed"] and len(cur["attempts"])==60
assert all(a["status"]=="COMPLETE" and a["accounting_audit"]=="PASS" and a["max_nav_error_usd"]==0 for a in cur["attempts"])
assert not cur["live_approved"] and not cur["broker_orders_enabled"]
manifest=json.loads(Path("risk_release/Momentum_core_risk_manifest.json").read_text())
for name,h in manifest["input_files"].items():
 p=cache/name
 assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h,name
orig=[p for p in original.rglob("*") if p.is_file()]
assert len(orig)==957 and len(manifest["input_files"])==1001
for p in orig: assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest["input_files"][str(p.relative_to(original))]
lookup={(a["phase"],a["name"]):a for a in old["attempts"]}
same=0; fixes=0; policies=[]
for a in cur["attempts"]:
 b=lookup[(a["phase"],a["name"])]
 for k in ("metrics","gates","input_fingerprint","decision_status"): assert a[k]==b[k],(a["name"],k)
 phase="historical" if a["phase"]=="historical" else "extended"
 p,q=root/phase/a["name"],prior/phase/a["name"]
 for suffix in ("daily.csv","trades.csv","periods.csv","targets.json","state.json","checkpoint.json"):
  name=suffix if suffix=="checkpoint.json" else "Momentum_core_"+suffix
  assert (p/name).read_bytes()==(q/name).read_bytes(),(phase,a["name"],name)
  same+=1
 if a["phase"]=="extension":
  x,y=dict(b["extension_metrics"]),dict(a["extension_metrics"]); x.pop("ActualFees_USD"); value=y.pop("ActualFees_USD"); assert x==y
  state=json.loads((p/"Momentum_core_state.json").read_text()); start=next(r for r in state["equity"] if r["date"]=="2026-09-01")
  assert value==state["fees"]-start["fees_cumulative"] and value>0; fixes+=1
 if not a["name"].startswith("baseline_"): policies.append(audit(cache,p))
assert len(policies)==40 and all(a["status"]=="PASS" for a in policies)
for name in ("research_core_stop.py","research_core_trailing.py"):
 assert subprocess.check_output(["git","show","19032b041a972f5b6916c13ef60bdd8feb1ab022:"+name])==Path(name).read_bytes()
def functions(s): return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=functions(subprocess.check_output(["git","show","c919bff42fdc49cb1d2aeebb4656ca1c87e3b0cb:run_core_risk_research.py"]))
b=functions(Path("run_core_risk_research.py").read_text())
assert a.keys()==b.keys() and [n for n in a if a[n]!=b[n]]==["extension_metrics"]
rank=[r for r in json.loads((root/"extended/baseline_assumed_5_15bps/Momentum_core_targets.json").read_text()) if r["risk_on"]]
meta={"status":"PASS","financial_GO":False,"live_approved":False,"broker_orders_enabled":False,"research_run":40791570390,"earlier_complete_run":40788221889,"export_run":int(os.environ["GITHUB_RUN_ID"]),"export_source":os.environ["GITHUB_SHA"],"source_fingerprint":source_fingerprint(),"study_fingerprint":cur["study_fingerprint"],"completed_accounts":60,"unit_tests":163,"input_files_verified":1001,"original_input_files_unchanged":957,"new_input_files":44,"accounting_audits_passed":60,"maximum_nav_error_usd":0,"independent_stop_policy_accounts":40,"independent_stop_signals":sum(p["signals_checked"] for p in policies),"next_session_stop_fills":sum(p["next_session_stop_fills_checked"] for p in policies),"identical_economic_files":same,"corrected_fee_metadata_accounts":fixes,"only_runner_function_changed":"extension_metrics","frozen_risk_modules_unchanged":True,"market_data_API_used":False,"risk_on_rankings":len(rank),"eligible_min":min(r["eligible_count"] for r in rank),"eligible_max":max(r["eligible_count"] for r in rank),"target_min":min(len(r["targets"]) for r in rank),"target_max":max(len(r["targets"]) for r in rank),"raw_first_session":min(p.stem.split(".")[0] for p in (cache/"raw-v1").glob("*.json.gz")),"raw_last_session":max(p.stem.split(".")[0] for p in (cache/"raw-v1").glob("*.json.gz")),"release_tag":"core-risk-research-20261029"}
assert meta["independent_stop_signals"]==11630 and meta["next_session_stop_fills"]==11610
cases=[{k:a[k] for k in ("phase","name","delay","cost","metrics","gates","input_fingerprint","decision_status")} | ({"extension_metrics":a["extension_metrics"]} if a["phase"]=="extension" else {}) for a in cur["attempts"]]
summary={"verification":meta,"cases":cases}; index={(a["phase"],a["name"]):a for a in cases}
Path("docs").mkdir(exist_ok=True)
Path("docs/CORE_RISK_RESULTS_20261029.json").write_text(json.dumps(summary,indent=2))
families=[("baseline","Core original"),("stop10","10 % inköpsstopp"),("trailing10","10 % rörligt stopp")]
def pct(x): return f"{x:.2f}".replace(".",",")+" %"
def table(phase):
 rows=["| Modell, 15 bp/sida | Netto | SPY | Maximal nedgång | Missade krav |","|---|---:|---:|---:|---|"]
 for family,label in families:
  a=index[(phase,family+"_assumed_5_15bps")]; m=a["metrics"]; fail=", ".join(g["gate"] for g in a["gates"] if not g["pass"])
  rows.append(f"| {label} | {pct(m['TotalReturn_pct'])} | {pct(m['SPYTotalReturn_pct'])} | {pct(m['DailyMaxDrawdown_pct'])} | {fail} |")
 return "\n".join(rows)
ext=["| Modell, 15 bp/sida | Netto 2 sep–28 okt | SPY | Faktiska simuleringsavgifter |","|---|---:|---:|---:|"]
for family,label in families:
 m=index[("extension",family+"_assumed_5_15bps")]["extension_metrics"]
 ext.append(f"| {label} | {pct(m['TotalReturn_pct'])} | {pct(m['SPYTotalReturn_pct'])} | {m['ActualFees_USD']:.2f} USD |")
all_rows=["| Fas | Variant/policy | Kostnad/sida | Netto | Maximal nedgång | Missade krav |","|---|---|---:|---:|---:|---|"]
for a in cases:
 m=a["metrics"]; fail=", ".join(g["gate"] for g in a["gates"] if not g["pass"])
 all_rows.append(f"| {a['phase']} | {a['name']} | {a['cost']*10000:.0f} bp | {pct(m['TotalReturn_pct'])} | {pct(m['DailyMaxDrawdown_pct'])} | {fail} |")
text=f"""# MomentumCloud — avslutad riskprövning, 29 oktober 2026

**Ingen prövad modell uppfyller samtliga oförändrade GO-krav. Två konkreta riskändringar är byggda och genomprövade. Förbättringar i utvecklingstestet höll inte i den senare kontrollperioden. Ingen modell för riktiga pengar är godkänd.**

Kod: [PR 20](https://github.com/tartkennet/MomentumCloud/pull/20).
Fullföljd prövning: [Actions 40791570390](https://github.com/tartkennet/MomentumCloud/actions/runs/40791570390).
Separat evidensexport: [Actions {meta['export_run']}](https://github.com/tartkennet/MomentumCloud/actions/runs/{meta['export_run']}).

## Faktiska ändringar och flaskhals

research_core_stop.py testar v4:s befintliga 10-procentiga stopp mot viktat faktiskt inköpspris. research_core_trailing.py testar samma tröskel mot högsta observerade stängning sedan köp. Signalen bildas vid stängning och försäljningen sker vid nästa verkliga öppning. Sålda kapitalandelar lämnas i kassa och återköp samma månad blockeras. Splitar, tickerbyten, stock/cash mergers och hela aktier hanteras i handelsboken.

Urval, 12–2-rankning, universum, pris- och likviditetsgränser, SPY-regim, viktning och godkännandekrav har inte lättats. Core fyllde alla 15 målplatser vid samtliga 34 RISK ON-rankningar i den förlängda baslinjen, med 845–1 713 kvalificerade kandidater. Tomt urval är inte flaskhalsen i Core. Den äldre dashboardens Buy Now är en separat kedja.

Första riskvarianten frystes i 93e06fd79610a1c08984b93d2bf387859dce8af6. Den andra hypotesen och jämförelsen frystes i 19032b041a972f5b6916c13ef60bdd8feb1ab022 före granskning av förlängningens utfall. Inga riskparametrar ändrades för att passa den senare perioden.

## Utvecklingsperioden: 2024-01-01–2026-09-01

Tabellen använder samma **antagna fem handelssessioners betalningsfördröjning** för alla modeller. Det är inte verifierade verkliga betalningsdagar. Alla fem betalningspolicyer och båda kostnaderna redovisas också.

{table("historical")}

Vid dubbla kostnader, 30 baspunkter per sida, fallerar även SPY-jämförelsen för båda riskvarianterna i detta femsessionsfall. Ingen betalningspolicy väljs ut för att få grönt resultat.

## Senare kontrollperiod: 2 september–28 oktober 2026

Samma konton återstartades från sparat tillstånd den 1 september, utan nytt kapital eller nollställda innehav. 40 nya observerade sessioner ingår.

{chr(10).join(ext)}

Perioden är inte certifierat orörd holdout och inte framåtriktad paper. Tidigare projektarbete såg aktuella marknadssnapshots. Här finns bara ett komplett månadsintervall och en ofullständig slutmånad, inte 30 nya oberoende observationer. Riskändringarna gav inget robust godkännande i denna kontroll.

## Sammanhängande konto till 28 oktober 2026

709 dagsvärden och 33 kompletta månadsintervall:

{table("extension")}

Gränserna i momentum_core.py::gates är oförändrade: minst 30 kompletta perioder, positiv nettoavkastning, positiv avkastningsskillnad mot SPY, daglig maximal nedgång minst −20 %, och minst 50 % positiva månadsperioder. run_core_risk_research.py skriver separata beslutsfiler. Historiska pass skulle vara PAPER_ONLY. live_approved=false och broker_orders_enabled=false kvarstår.

## Konkreta riskorsaker

Oberoende P&L-attribution av den tidigare baslinjens femsessionsfall stämmer av topp-till-botten-förlusten 68 692,86 USD. RNA, EBS, CATX, RDW och RKLB är exempel på negativa bidrag. Dessa namn utesluts inte i efterhand.

Stoppnivån är inget garanterat pris. LUNR gick från signalstängning 11,26 USD den 6 mars 2025 till nästa observerade öppning 7,26 USD, cirka 35,52 % lägre. ERAS gick i den rörliga varianten från signalstängning 19,15 USD till öppning 10,51 USD den 28 april 2026, cirka 45,12 % lägre. Handelsboken använder de observerade öppningspriserna. [SEC beskriver denna begränsning med stoporder](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15).

## Verifiering och rättningar

- 163 funktionstester passerar.
- 60 konton/scenarier är fullföljda: tre modellfamiljer × fem betalningspolicyer × två kostnader i två faser. Detta är inte 60 oberoende marknadsurval.
- Samtliga 60 har separat kass-/aktie-/fordrings-/avgiftskontroll, med 0 USD största NAV-avvikelse.
- Separat policykontroll importerar inte riskmotorerna och verifierar 40 riskkonton, 11 630 signaler och 11 610 försäljningar vid nästa session.
- Offlineåterkörningen reproducerar ekonomiska mått och gates; 360 dags-/affärs-/period-/mål-/tillstånds-/checkpointfiler är identiska med den första fullständiga prövningen.
- Ett rapportfel rättades: förlängningens separata avgiftsfält hade blivit noll genom en temporär måttbehållare. Fältet visar nu verklig avgiftsökning. Nettoavkastning, hela kontots avgifter, affärer och gates ändrades inte. Alla andra runnerfunktioner och båda frysta riskmodulerna är oförändrade.
- En senare utdelningscache stoppades av indatahashkontrollen trots identiska grundmått. Originalvintagen återställdes. PR-scopade cacher ersätts som långtidskälla av ett opublicerat krypterat forskningspaket.

1 001 indatafiler är hashverifierade. Samtliga 957 ursprungliga filer är oförändrade; 44 filer har tillkommit. Sparade råprissessioner omfattar {meta['raw_first_session']}–{meta['raw_last_session']}. Detta är inte en export av alla oanvända fem abonnemangsår.

Ursprungligt källfingeravtryck: {meta['source_fingerprint']}.
Forskningsfingeravtryck: {meta['study_fingerprint']}.

## Kvarstående blockerare och A–F

A. **Tekniskt färdigt för riktiga pengar: NEJ.** Forskningsmotor, bevarande och kontroller fungerar. Ekonomiskt godkännande och verklig exekvering saknas.

B. **PIT-universum:** datumstyrda common-stock-register används. Leverantörens ursprungliga historiska datavintage och alla instrumentidentiteter är inte oberoende certifierade.

C. **Survivorship bias:** dagens Excel-lista används inte som historiskt universum. Senare avnoterade innehav ingår. Leverantörsbackfill kvarstår som begränsning.

D. **Corporate actions:** observerade händelser är bokförda och avstämda. Faktiska betalningsdagar för åtta mergerfordringar är fortfarande inte verifierade. 0/1/5/20-sessionsscenarierna är antaganden.

E. **Likviditet:** 5 miljoner USD i ADV20 och antagen 15/30 bp-kostnad bevisar inte öppningslikviditet eller faktisk slippage.

F. **Logisk felräkning:** ingen separat avstämd NAV-avvikelse undanröjer kraven. Avgiftsrapportfältet är rättat. Risk och senare underprestation kvarstår.

Core-paper-identiteten och v4-dashboarden är inte omdöpta till godkända signaler. Riskvarianterna är forskningskod. Alla försök och missade gates bevaras. Inga krav sänks i efterhand för att kalla modellen GO.

## Bevarade filer

Det opublicerade forskningspaketet core-risk-research-20261029 bevarar krypterade indata, exakt kod, resultat och hashmanifest. Exporten kompletterar det med mottagarkrypterade indata och verifierade resultat. Ingen API-nyckel publiceras. Det tidigare privata datapaketet i ChatGPT innehåller mottagarnyckeln för att öppna mottagarkrypterade exporter. Själva offlineberäkningen kräver inget nytt historikabonnemang.

## Alla fasta scenarier

{chr(10).join(all_rows)}
"""
Path("docs/CORE_RISK_REVIEW_20261029.md").write_text(text)
(out/"verification.json").write_text(json.dumps(meta,indent=2))
shutil.copyfile("docs/CORE_RISK_REVIEW_20261029.md",out/"MomentumCloud_riskrapport_20261029.md")
shutil.copyfile("docs/CORE_RISK_RESULTS_20261029.json",out/"summary.json")
with zipfile.ZipFile(out/"Momentum_core_risk_verified_results.zip","w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(root.rglob("*")):
  if p.is_file():z.write(p,"results/"+str(p.relative_to(root)))
 for p in sorted(Path(".canonical_baseline/core_results").rglob("*")):
  if p.is_file():z.write(p,"baseline_reference/"+str(p.relative_to(".canonical_baseline/core_results")))
 z.write(prior/"attempts.json","prior_attempts/40788221889_attempts.json")
 z.write(out/"verification.json","verification.json")
 z.writestr("README_sv.md","Alla 60 scenarier och kontroller. Inget godkännande för riktiga pengar. Betalningsdagar är antaganden. Kod och krypterade rådata finns i forskningspaketet. baseline_reference används vid offlineåterkörning.")
for a in cases:print("FINAL_RISK_EXPORT_CASE "+json.dumps(a,separators=(",",":")))
print("FINAL_RISK_EXPORT_META "+json.dumps(meta,separators=(",",":")))
