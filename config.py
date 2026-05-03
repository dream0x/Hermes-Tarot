"""Centralised env-driven config.

Import once at startup, then pass `cfg` around. Never re-read os.environ
from feature code — keeps tests and overrides clean.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on", "y")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _csv_ints(name: str) -> list[int]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    return [int(x) for x in raw.split(",") if x.strip()]


@dataclass
class Config:
    # Kimi
    kimi_api_key: str = field(default_factory=lambda: os.environ.get("KIMI_API_KEY", ""))
    kimi_base_url: str = field(default_factory=lambda: os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1"))
    kimi_model: str = field(default_factory=lambda: os.environ.get("KIMI_MODEL", "kimi-k2.6"))

    # fal.ai
    fal_key: str = field(default_factory=lambda: os.environ.get("FAL_KEY", ""))

    # Pinata
    pinata_jwt: str = field(default_factory=lambda: os.environ.get("PINATA_JWT", ""))

    # Telegram
    telegram_bot_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    telegram_bot_username: str = field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_USERNAME", ""))
    owner_telegram_id: int = field(default_factory=lambda: _int("OWNER_TELEGRAM_ID", 0))
    allowed_telegram_ids: list[int] = field(default_factory=lambda: _csv_ints("ALLOWED_TELEGRAM_IDS"))

    # Rate limits
    public_daily_readings: int = field(default_factory=lambda: _int("PUBLIC_DAILY_READINGS", 3))
    public_lifetime_readings: int = field(default_factory=lambda: _int("PUBLIC_LIFETIME_READINGS", 10))
    allowlist_daily_readings: int = field(default_factory=lambda: _int("ALLOWLIST_DAILY_READINGS", 20))
    max_daily_usd_spend: float = field(default_factory=lambda: _float("MAX_DAILY_USD_SPEND", 5.0))
    public_enabled: bool = field(default_factory=lambda: _bool("PUBLIC_ENABLED", True))

    # Base Sepolia
    base_sepolia_rpc: str = field(default_factory=lambda: os.environ.get("BASE_SEPOLIA_RPC", "https://sepolia.base.org"))
    deployer_private_key: str = field(default_factory=lambda: os.environ.get("DEPLOYER_PRIVATE_KEY", ""))
    oracle_card_contract: str = field(default_factory=lambda: os.environ.get("ORACLE_CARD_CONTRACT", ""))

    # Viewer
    viewer_base_url: str = field(default_factory=lambda: os.environ.get(
        "VIEWER_BASE_URL", "").rstrip("/") + "/" if os.environ.get("VIEWER_BASE_URL") else "")

    # Misc
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))

    # ----- Helpers -----

    def is_owner(self, user_id: int | str) -> bool:
        return int(user_id) == self.owner_telegram_id and self.owner_telegram_id != 0

    def is_allowlisted(self, user_id: int | str) -> bool:
        return int(user_id) in self.allowed_telegram_ids

    def tier_of(self, user_id: int | str) -> str:
        if self.is_owner(user_id):
            return "owner"
        if self.is_allowlisted(user_id):
            return "allowlist"
        return "public"


cfg = Config()


if __name__ == "__main__":
    # Print non-secret view for debugging
    public = {
        "kimi_model": cfg.kimi_model,
        "kimi_base_url": cfg.kimi_base_url,
        "telegram_bot_username": cfg.telegram_bot_username,
        "owner_telegram_id": cfg.owner_telegram_id,
        "allowed_telegram_ids": cfg.allowed_telegram_ids,
        "public_daily_readings": cfg.public_daily_readings,
        "public_lifetime_readings": cfg.public_lifetime_readings,
        "allowlist_daily_readings": cfg.allowlist_daily_readings,
        "max_daily_usd_spend": cfg.max_daily_usd_spend,
        "public_enabled": cfg.public_enabled,
        "base_sepolia_rpc": cfg.base_sepolia_rpc,
        "oracle_card_contract": cfg.oracle_card_contract,
    }
    import json
    print(json.dumps(public, indent=2))
    # Sanity: keys exist (don't print)
    for name in ["kimi_api_key", "fal_key", "pinata_jwt", "telegram_bot_token", "deployer_private_key"]:
        v = getattr(cfg, name)
        print(f"  {name}: {'set' if v else 'MISSING'}")
