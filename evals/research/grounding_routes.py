"""Deterministic router measurement only. NOT a model intelligence benchmark."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source-root', type=Path, default=HERE.parents[1])
args = parser.parse_args()
sys.path.insert(0, str(args.source_root / 'ultron/cloud_service'))
from conversation_persona import classify_model_task
cases = json.loads((HERE/'grounding_routes.json').read_text())
results = []
latencies = []
for case in cases:
    actual = classify_model_task(case['message'])
    results.append({**case,'actual':actual,'pass':actual == case['task']})
for _ in range(100):
    for case in cases:
        start = time.perf_counter_ns()
        classify_model_task(case['message'])
        latencies.append((time.perf_counter_ns()-start)/1e6)
print(json.dumps({'scope':'lexical router only; 100 timing repetitions per scenario',
                  'passed':sum(x['pass'] for x in results),'total':len(results),
                  'latency_ms_p50':statistics.median(latencies),
                  'latency_ms_p95':sorted(latencies)[int(len(latencies)*.95)],
                  'model_quality':'NOT_RUN','live_response_latency':'NOT_RUN',
                  'extra_model_calls':0,'results':results},ensure_ascii=False,indent=2))

raise SystemExit(0 if all(x['pass'] for x in results) else 1)
