import json
from collections import Counter
from pathlib import Path
import pandas as pd
from services.regime_allocation import fit_allocations
root = Path('research/regime_reproduction_2026-10-12')
prices = pd.read_csv(root/'prices.csv', index_col=0, parse_dates=True)
returns = prices.pct_change().dropna()
decisions = json.loads((root/'decisions.json').read_text())
results = []
for d in decisions:
    result = fit_allocations(returns.loc[:d['training_end']])
    results.append({k: result[k] for k in ['training_end','hmm_converged','iterations_used','covariance_type_used']})
summary = {'fits':len(results), 'converged':sum(r['hmm_converged'] for r in results),
           'iteration_caps':sum(r['iterations_used']>=500 and not r['hmm_converged'] for r in results),
           'covariance_types':dict(Counter(r['covariance_type_used'] for r in results)), 'results':results}
Path('research/phase3_convergence_check.json').write_text(json.dumps(summary, indent=2))
print({k:v for k,v in summary.items() if k!='results'})
