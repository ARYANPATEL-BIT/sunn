#!/usr/bin/env python3
"""Sunn Groq Cloud AI Integration Safe Smoke-Test Utility.

Conducts controlled, strictly limited live verification of Groq Cloud AI services.
Features safety gates, credential masking, token counting, and zero retry loops.
Zero Gnani API calls are ever made by this script.

Usage:
    # 1. Dry run (inspect configuration, 0 live requests):
    uv run scripts/groq_live_smoke.py --dry-run

    # 2. Safety stop demonstration (stops without confirmation):
    uv run scripts/groq_live_smoke.py --model-check

    # 3. Live model compatibility verification (exactly 1 Groq request):
    uv run scripts/groq_live_smoke.py --model-check --confirm-live-call

    # 4. Live feature verification (Easier Ways / Judgement, exactly 1 Groq request):
    uv run scripts/groq_live_smoke.py --feature-check --confirm-live-call
"""
import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv
import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "[NOT SET]"
    return f"{key[:4]}...{key[-4:]}"


def load_config():
    load_dotenv(os.path.join(ROOT, ".env"))
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY", "")
    base_url = (os.environ.get("LLM_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
    model = os.environ.get("GROQ_MODEL") or os.environ.get("LLM_MODEL") or "openai/gpt-oss-120b"
    reasoning_effort = os.environ.get("LLM_REASONING_EFFORT", "low").strip()
    timeout_s = float(os.environ.get("LLM_TIMEOUT_S", "3"))
    return {
        "api_key": api_key.strip(),
        "base_url": base_url,
        "model": model.strip(),
        "reasoning_effort": reasoning_effort,
        "timeout_s": timeout_s,
    }


def run_model_check(config: dict, dry_run: bool = False):
    print("\n[Operation 1/1: Model Compatibility Check]")
    print(f"Target URL: {config['base_url']}/chat/completions")
    print(f"Model ID: {config['model']}")
    print(f"Reasoning Effort: {config['reasoning_effort']}")

    test_payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "You are a concise accessibility assistant. Respond in JSON only: {\"status\": \"ok\", \"model\": \"<name>\"}"},
            {"role": "user", "content": "Ping test."},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 120,
    }
    if config["reasoning_effort"] in ("low", "medium", "high"):
        test_payload["reasoning_effort"] = config["reasoning_effort"]

    if dry_run:
        print("[DRY RUN] Request payload preview:")
        print(json.dumps(test_payload, indent=2))
        print("Dry run complete: 0 requests sent, 0 credits consumed.")
        return True

    started = time.monotonic()
    try:
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        resp = httpx.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=config["timeout_s"],
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        print(f"HTTP Status: {resp.status_code} ({elapsed_ms} ms)")

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            choice = data.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason")
            content = choice.get("message", {}).get("content", "")
            print(f"Finish Reason: {finish_reason}")
            print(f"Completion Tokens: {usage.get('completion_tokens')} (prompt: {usage.get('prompt_tokens')}, total: {usage.get('total_tokens')})")
            print(f"Raw Output Content: {content}")
            try:
                parsed = json.loads(content)
                print(f"Parsed JSON successfully: {parsed}")
                print("SUCCESS: Groq model compatibility verified.")
                return True
            except Exception as e:
                print(f"WARNING: Output was not valid JSON ({e})")
                return False
        else:
            print(f"FAILURE: HTTP {resp.status_code} returned:")
            print(resp.text[:300])
            return False
    except httpx.TimeoutException:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        print(f"TIMEOUT: Groq did not answer within {config['timeout_s']}s (took {elapsed_ms} ms)")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return False


def run_feature_check(config: dict, dry_run: bool = False):
    print("\n[Operation 1/1: Feature Verification Check - Phrase Judgement / Alternatives]")
    print(f"Target URL: {config['base_url']}/chat/completions")
    print(f"Model ID: {config['model']}")

    # Synthetic non-sensitive phrase judgement test
    candidates = [
        {"id": "1", "hindi": "पानी चाहिए", "latin": "paani chahiye", "meaning_en": "I need water", "score": 0.82},
        {"id": "2", "hindi": "खाना दे दो", "latin": "khaana de do", "meaning_en": "give me food", "score": 0.70},
    ]
    test_payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "you help a person with unclear speech be understood. pick which candidate they meant. "
                    "reply with json only: {\"choice\": \"<id or none>\", \"confidence\": <0 to 1>, \"reason\": \"<max 12 words>\"}"
                ),
            },
            {
                "role": "user",
                "content": f"the stt registered: baani chaiye. candidates: {json.dumps(candidates, ensure_ascii=False)}.",
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 150,
    }
    if config["reasoning_effort"] in ("low", "medium", "high"):
        test_payload["reasoning_effort"] = config["reasoning_effort"]

    if dry_run:
        print("[DRY RUN] Feature request payload preview:")
        print(json.dumps(test_payload, indent=2))
        print("Dry run complete: 0 requests sent, 0 credits consumed.")
        return True

    started = time.monotonic()
    try:
        headers = {"Authorization": f"Bearer {config['api_key']}"}
        resp = httpx.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=config["timeout_s"],
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        print(f"HTTP Status: {resp.status_code} ({elapsed_ms} ms)")

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            print(f"Completion Tokens: {usage.get('completion_tokens')}")
            print(f"Content: {content}")
            parsed = json.loads(content)
            print(f"Choice: {parsed.get('choice')}, Confidence: {parsed.get('confidence')}, Reason: {parsed.get('reason')}")
            print("SUCCESS: Groq feature workflow verified.")
            return True
        else:
            print(f"FAILURE: HTTP {resp.status_code}: {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sunn Groq Cloud AI Safe Smoke-Test Utility")
    parser.add_argument("--model-check", action="store_true", help="Verify model availability and API compatibility (1 request)")
    parser.add_argument("--feature-check", action="store_true", help="Verify phrase judgement / alternatives workflow (1 request)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without sending any network request")
    parser.add_argument("--confirm-live-call", action="store_true", help="Explicit confirmation gate required to send live requests")

    args = parser.parse_args()
    config = load_config()

    print("=" * 65)
    print("Sunn Groq Cloud AI Controlled Smoke-Test Utility")
    print("=" * 65)
    print(f"Groq API Key Status: {'Configured (' + mask_key(config['api_key']) + ')' if config['api_key'] else 'NOT CONFIGURED'}")
    print(f"Base URL: {config['base_url']}")
    print(f"Configured Model: {config['model']}")
    print(f"Reasoning Effort: {config['reasoning_effort']}")
    print(f"Timeout: {config['timeout_s']}s")
    print("Gnani Credit Impact: ZERO (Gnani services are never invoked)")
    print("=" * 65)

    if not args.model_check and not args.feature_check and not args.dry_run:
        print("\nNo operation specified. Use --model-check, --feature-check, or --dry-run.")
        print("Example: uv run scripts/groq_live_smoke.py --dry-run")
        sys.exit(0)

    if not config["api_key"]:
        print("\n[ERROR] GROQ_API_KEY is not configured in .env or environment.")
        sys.exit(1)

    if not args.dry_run and not args.confirm_live_call:
        print("\n[SAFETY STOP] The --confirm-live-call flag is required to make live requests.")
        print("This safety gate prevents unintended requests during automated test runs.")
        print("To proceed with exactly 1 live request, re-run with: --confirm-live-call")
        sys.exit(1)

    success = True
    if args.model_check or args.dry_run:
        success = run_model_check(config, dry_run=args.dry_run) and success

    if args.feature_check and not args.dry_run:
        success = run_feature_check(config, dry_run=args.dry_run) and success

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
