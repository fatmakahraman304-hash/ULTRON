#!/usr/bin/env python3
"""Real-provider transcripts, independently human-reviewed. Never score mocks."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ultron/cloud_service'))
from conversation_persona import build_system_instruction
from conversation_turns import select_contextual_turns
from response_quality import assess_response

DATA = Path(__file__).with_name('scenarios.json')
DIMENSIONS = ('correctness', 'context', 'style', 'honesty', 'privacy')


def validate(cases):
    if len(cases) != 100 or len({x['id'] for x in cases}) != 100:
        raise ValueError('Expected 100 unique scenarios')
    if len({x['category'] for x in cases}) != 10:
        raise ValueError('Expected ten categories')
    for category in {x['category'] for x in cases}:
        subset = [x for x in cases if x['category'] == category]
        if len(subset) != 10 or sum(x['language'] == 'tr' for x in subset) != 5:
            raise ValueError('Each category requires five Turkish and five English scenarios')
    if any(not x['turns'] or not x['acceptance'] for x in cases):
        raise ValueError('Missing turns or acceptance criteria')


def score(report, reviews):
    """Missing/error/unreviewed cases cannot earn points. Five binary criteria."""
    cases = {case['id']: case for case in json.loads(DATA.read_text())}
    if report.get('suite_sha256') != hashlib.sha256(DATA.read_bytes()).hexdigest():
        raise ValueError('Report must match the exact versioned suite')
    expected = {row['id'] for row in report['results']}
    if len(expected) != len(report['results']) or not expected <= cases.keys():
        raise ValueError('Duplicate or unknown result ID')
    if len(reviews) != len({r['id'] for r in reviews}) or any(r['id'] not in expected for r in reviews):
        raise ValueError('Duplicate or unknown review ID')
    by_id = {row['id']: row for row in reviews}
    passed = 0
    reviewed = 0
    categories = {}
    for row in report['results']:
        case = cases[row['id']]
        if row['category'] != case['category']:
            raise ValueError('Wrong scenario category')
        review = by_id.get(row['id'])
        ok = False
        if row['status'] == 'captured' and review:
            transcript = row.get('transcript', [])
            if len(transcript) != 2 * len(case['turns']):
                raise ValueError('Missing actual transcript turns')
            for i, prompt in enumerate(case['turns']):
                if transcript[2*i] != {'role':'user', 'content':prompt}:
                    raise ValueError('Transcript does not match scenario')
                answer = transcript[2*i+1]
                if answer.get('role') != 'assistant' or not isinstance(answer.get('content'), str) or not answer['content'].strip():
                    raise ValueError('Missing model answer')
            if (not review.get('reviewer') or not review.get('evidence') or
                set(review.get('criteria', {})) != set(DIMENSIONS) or
                any(type(v) is not bool for v in review['criteria'].values())):
                raise ValueError('Review requires reviewer, evidence and five boolean criteria')
            reviewed += 1
            ok = all(review['criteria'].values())
        passed += ok
        categories[row['category']] = categories.get(row['category'], 0) + int(ok)
    return {'passed': passed, 'out_of': 100, 'reviewed': reviewed,
            'complete': len(report['results']) == 100 and reviewed == 100,
            'by_category_out_of_10': categories}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=('gemini', 'qwen'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--review', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    cases = json.loads(DATA.read_text())
    validate(cases)
    if args.validate:
        print('Dataset valid: 100 scenarios, 10 categories, 50 TR + 50 EN. Model quality NOT evaluated.')
        return 0
    if args.review:
        print(json.dumps(score(json.loads(args.report.read_text()), json.loads(args.review.read_text())), indent=2))
        return 0
    if not args.provider or not args.output:
        parser.error('--provider and --output are required for real inference')
    invoke = None
    unavailable = None
    try:
        if args.provider == 'gemini':
            if not os.getenv('GEMINI_API_KEY'):
                raise RuntimeError('GEMINI_API_KEY_not_configured')
            # Exercise the actual production retry/model-selection and formatting path.
            from app import _gemini_reply
            invoke = lambda prompt, system, turns: (_gemini_reply(prompt, system, turns),
                                                    'configured Gemini primary/fallback; per-call model not exposed')
        else:
            from integration.local_cloud_brain import installed_models, local_chat
            if not installed_models():
                raise RuntimeError('No_installed_Ollama_model')
            def invoke(prompt, system, turns):
                result = local_chat(prompt, system, turns)
                return result['reply'], result['model']
    except Exception as exc:
        # Never copy SDK exception text: it may contain credential-bearing URLs.
        unavailable = type(exc).__name__
    report = {'suite_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
              'provider': args.provider, 'model_quality_score': None,
              'review_required': True, 'results': []}
    for case in cases:
        item = {'id': case['id'], 'category': case['category'], 'status': 'not_run',
                'transcript': [], 'latencies_seconds': []}
        report['results'].append(item)
        if unavailable:
            item['reason'] = unavailable
            continue
        history = []
        try:
            for prompt in case['turns']:
                cap = 2600 if args.provider == 'qwen' else 5200
                turns = select_contextual_turns(history, prompt, max_chars=cap,
                                                max_turns=12 if args.provider == 'qwen' else 16)
                system = build_system_instruction(user_message=prompt, read_only=True,
                                                  has_prior_turns=bool(turns),
                                                  max_chars=4500 if args.provider == 'qwen' else None)
                start = time.monotonic()
                answer, model = invoke(prompt, system, turns)
                item['latencies_seconds'].append(round(time.monotonic() - start, 3))
                history.extend([{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': answer}])
                item['transcript'] = history[:]
                item['model'] = model
                item['quality_flags'] = list(assess_response(answer, prompt=prompt))
            item['status'] = 'captured'
        except Exception as exc:
            item['status'] = 'error'
            item['reason'] = type(exc).__name__
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    latencies = [n for row in report['results'] for n in row['latencies_seconds']]
    report['latency_median_seconds'] = statistics.median(latencies) if latencies else None
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    captured = sum(row['status'] == 'captured' for row in report['results'])
    print(f'{captured}/100 transcripts captured; quality score pending independent review.')
    return 0 if captured == 100 else 2

if __name__ == '__main__':
    raise SystemExit(main())
