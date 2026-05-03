"""Smoke-test all external services. Run before any real dev.

Usage: python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OK = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, fn) -> None:
    try:
        msg = fn()
        results.append((name, True, msg or ""))
        print(f"{OK} {name}: {msg or 'ok'}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, str(e)))
        print(f"{FAIL} {name}: {e}")


def kimi() -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["KIMI_API_KEY"],
        base_url=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1"),
    )
    resp = client.chat.completions.create(
        model=os.environ.get("KIMI_MODEL", "kimi-k2.6"),
        messages=[{"role": "user", "content": "Reply with exactly one word: 'pong'."}],
        max_tokens=20,
    )
    text = (resp.choices[0].message.content or "").strip()
    return f"model said: {text!r}"


def fal() -> str:
    import requests

    key = os.environ["FAL_KEY"]
    r = requests.get(
        "https://queue.fal.run/fal-ai/flux/dev/requests",
        headers={"Authorization": f"Key {key}"},
        timeout=10,
    )
    # Accept any non-401/403 (auth-shape) response; the endpoint returns 4xx
    # for missing request id but 401/403 for bad creds.
    if r.status_code in (401, 403):
        raise RuntimeError(f"auth failed: HTTP {r.status_code}")
    return f"auth ok (HTTP {r.status_code})"


def pinata() -> str:
    import requests

    jwt = os.environ["PINATA_JWT"]
    r = requests.get(
        "https://api.pinata.cloud/data/testAuthentication",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return "auth ok"


def telegram() -> str:
    import requests

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    bot = data["result"]
    return f"@{bot['username']} (id={bot['id']})"


def base_sepolia() -> str:
    import requests

    rpc = os.environ.get("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
    pk = os.environ["DEPLOYER_PRIVATE_KEY"]
    if not pk.startswith("0x") or len(pk) != 66:
        raise RuntimeError(f"private key shape wrong (len={len(pk)})")
    # Eth balance via raw JSON-RPC. Derive address with simple keccak — but
    # without web3 installed in the smoke env, just check the RPC is reachable.
    r = requests.post(
        rpc,
        json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
        timeout=10,
    )
    data = r.json()
    chain_id = int(data["result"], 16)
    if chain_id != 84532:  # Base Sepolia
        raise RuntimeError(f"unexpected chainId {chain_id}, expected 84532")
    return f"chainId={chain_id} (Base Sepolia)"


if __name__ == "__main__":
    print("Hermes Oracle — smoke test\n")
    check("Kimi K2.6", kimi)
    check("fal.ai", fal)
    check("Pinata", pinata)
    check("Telegram bot", telegram)
    check("Base Sepolia RPC + key shape", base_sepolia)
    print()
    failed = [n for n, ok, _ in results if not ok]
    if failed:
        print(f"\n{len(failed)} failed: {failed}")
        sys.exit(1)
    print("All services healthy. Ready to build.")
