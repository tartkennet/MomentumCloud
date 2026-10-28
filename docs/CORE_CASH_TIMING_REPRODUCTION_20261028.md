# Reproducing the fixed cash-timing diagnostic

This dated experiment uses the unchanged frozen Core source. From a fresh
checkout containing `research_cash_timing.py`, place the existing private
data bundle next to the checkout and prepare its previously verified inputs:

```bash
python -m pip install -r requirements.txt
mkdir -p ../final_research/snapshot ../final_research/evidence
unzip -q ../MomentumCloud_Core_data_20261028.zip -d ../core_private_data
cp -a ../core_private_data/cache ../final_research/snapshot/cache
cp -a ../core_private_data/results ../final_research/evidence/core_results
python research_cash_timing.py
```

Use a new checkout/output directory for each repeat to retain prior evidence.
Outputs appear in `cash_timing_results/`. The script refuses any discrepancy
in the frozen model source fingerprint, original metrics, original exports or
saved input fingerprint. The first complete calculation is slower; subsequent
scenarios reuse only pure market-based signals, never portfolio state.
