"""Read-only research readiness. Never generates tokens or prints credentials.

--list-models performs only the official model metadata request. A model listing
is not proof of grounding support, response quality, quota or paid-use approval.
"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ultron.cloud_service.grounded_search import provider_failure


def check(*, list_models=False):
    model = os.getenv('GEMINI_SEARCH_MODEL', '').strip()
    approved = os.getenv('GOLGE_GOOGLE_SEARCH_BUDGET_APPROVED', '').lower() == 'true'
    enabled = os.getenv('GOLGE_GOOGLE_SEARCH_ENABLED', '').lower() == 'true'
    key = os.getenv('GEMINI_API_KEY', '')
    result = {
        'google_search': 'READY_FOR_OWNER_TEST' if all((model,approved,enabled,key)) else 'BLOCKED',
        'key_present': bool(key), 'enabled':enabled, 'budget_approved':approved,
        'model_configured': bool(model), 'model_inventory':'NOT_RUN',
        'generation':'NOT_RUN', 'quota':'NOT_VERIFIED', 'physical_devices':'NOT_RUN',
        'pricing_reference':'https://ai.google.dev/gemini-api/docs/pricing',
    }
    if not list_models:
        return result
    if not key:
        result['model_inventory'] = 'BLOCKED_KEY_MISSING'
        return result
    client = None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=5000, retry_options=types.HttpRetryOptions(attempts=1)))
        found = False
        count = 0
        for item in client.models.list(config={'page_size':100}):
            count += 1
            if str(item.name).removeprefix('models/') == model.removeprefix('models/'):
                found = True
            if count >= 100:
                break
        result.update(model_inventory='PASS_METADATA_ONLY', listed_count=count,
                      configured_model_in_first_100=found)
    except Exception as exc:
        result.update(model_inventory='BLOCKED', failure_kind=provider_failure(exc))
    finally:
        if client is not None:
            try: client.close()
            except Exception: pass
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-models', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(list_models=args.list_models), ensure_ascii=False, indent=2))
