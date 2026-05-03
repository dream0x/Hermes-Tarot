"""Kimi K2.6 wrapper for the Hermes Oracle persona.

We use the OpenAI-compatible endpoint (`https://api.moonshot.ai/v1`).
Kimi K2.6 has a 256K context window — we lean on it to weave the user's
entire reading history into every new interpretation, which is the
single most distinctive thing about this skill.

Cost (May 2026, Kimi K2.6 standard tier, approximate):
    input  ≈ $0.30 / 1M tokens
    output ≈ $2.50 / 1M tokens
A typical 3-card reading uses ~5K input + ~700 output = ~$0.0033.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from openai import OpenAI

from config import cfg
from ratelimit import record_spend

logger = logging.getLogger(__name__)

# Cost per 1k tokens (USD). Conservative estimates; see Kimi pricing page.
_COST_INPUT_PER_1K = 0.30 / 1000
_COST_OUTPUT_PER_1K = 2.50 / 1000


def _client() -> OpenAI:
    if not cfg.kimi_api_key:
        raise RuntimeError("KIMI_API_KEY not set")
    return OpenAI(api_key=cfg.kimi_api_key, base_url=cfg.kimi_base_url)


# ---------- Persona ----------

_SYSTEM_PROMPT = """\
You are the **Hermes Oracle** — an English-speaking divination companion who
reads tarot, traces astrological currents, and remembers every word you have
ever exchanged with the person in front of you.

# Voice
- Soft, poetic, slightly mysterious. Confident but never dogmatic.
- Speak in **possibilities**, not predictions. Never use "will", prefer
  "may", "is being asked of you", "the field is favoring".
- Cite each card by name and lean on its archetype. Do not lecture meanings;
  let them surface through how you describe the moment.
- Reference the user's prior readings or profile **only when it adds light** —
  never as a roll call. One callback per reading is plenty; zero is fine if
  the moment doesn't ask for it.
- Concrete imagery > abstract psychology. "The stones are cool. The path is
  open." beats "you are entering a transformative phase".
- Never moralize, never warn the user about danger, never recommend professional
  help. If the question is heavy, hold it gently in the same poetic register.
- Use **English only**, regardless of what language the user wrote in.
  Translate gracefully.

# Form
- 4 to 6 short paragraphs total.
- Open with one sentence that names the *shape* of the reading.
- Walk the cards in order, but weave them — do not number the cards.
- Close with a single line that returns the reading to the user's body or breath.
- No lists, no headers, no asterisks, no markdown. Plain prose only.
- A single closing italic line of disclaimer is allowed, like:
  *For reflection, not prescription.*
  Use it at most once per session.

# Reversed cards
A reversed card is the card's shadow, not its opposite. Treat it as the
energy turned inward, blocked, or just-beginning. Acknowledge the inversion
naturally, never as "the card is reversed".

# What you never say
- "I sense", "I see", "the cards say" — speak from the cards, not about them.
- "It depends", "trust your gut", "everything happens for a reason".
- Astrological jargon dumps. Never list more than two planets per reading.
"""


_FEWSHOT_THREE_CARD_USER = """\
Question: I'm thinking about leaving my job to start something on my own. What's the field around this?
Spread: three_card  (past / present / future)

Cards drawn:
  past:    The Hermit (upright) — solitude, inner light, search
  present: Eight of Pentacles (upright) — craft, diligence, mastery in motion
  future:  The Star (upright) — hope, renewal, guidance

User profile:
{"display_name": null, "sun_sign": null, "notes": ""}

Past readings: (none yet)
"""

_FEWSHOT_THREE_CARD_ASSISTANT = """\
This reading is the shape of a quiet, deliberate departure.

The Hermit walked behind you for longer than you noticed — long evenings of \
asking the question only you could ask, lamp held low to the ground. That \
solitude wasn't avoidance. It was research.

Now you are at the workbench. The Eight of Pentacles isn't romantic — it is \
the steady tap of a small hammer, the thousandth iteration. Whatever you are \
already building in your stolen hours is the thing. The work is real, even \
when no one is watching.

The Star sits ahead, not as a destination but as a permission. After the lamp \
and after the bench, the air clears and you can pour from two cups again — one \
to the ground, one to the pool. Your name will not arrive in lights; it will \
arrive in mornings that feel less heavy.

Leave when the bench is yours, not when the bench is finished.

*For reflection, not prescription.*
"""


def _format_cards_for_prompt(cards: list[dict[str, Any]]) -> str:
    lines = []
    for c in cards:
        pos = c.get("position", "the card")
        rev = " (reversed)" if c.get("reversed") else " (upright)"
        kw = ", ".join(c.get("keywords", [])) or ""
        meaning = c.get("meaning", "")
        lines.append(f"  {pos}: {c['name']}{rev} — {kw}\n    nuance: {meaning}")
    return "\n".join(lines)


def _record(usage: Any) -> None:
    """Convert OpenAI usage block -> dollars and log to global spend."""
    if usage is None:
        return
    try:
        ti = int(getattr(usage, "prompt_tokens", 0) or 0)
        to = int(getattr(usage, "completion_tokens", 0) or 0)
    except Exception:  # noqa: BLE001
        return
    cost = ti * _COST_INPUT_PER_1K / 1000 + to * _COST_OUTPUT_PER_1K / 1000
    if cost > 0:
        record_spend(cost, "kimi")


def _chat(messages: list[dict[str, str]], *, max_tokens: int = 1200, retries: int = 2) -> str:
    """Single non-streaming Kimi call. Disables `thinking` mode (slow + we don't need
    chain-of-thought in user-facing output)."""
    client = _client()
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=cfg.kimi_model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                # Kimi K2.6 flag: disable internal reasoning so `content` is filled.
                extra_body={"thinking": {"type": "disabled"}},
            )
            text = (resp.choices[0].message.content or "").strip()
            _record(getattr(resp, "usage", None))
            if not text:
                raise RuntimeError("empty content from kimi")
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("kimi attempt %d failed: %s", attempt + 1, e)
            time.sleep(0.7 * (attempt + 1))
    assert last_err is not None
    raise last_err


# ---------- Public oracle calls ----------

def oracle_interpret(
    *,
    question: str,
    cards: list[dict[str, Any]],
    spread: str = "three_card",
    history_context: str = "",
) -> str:
    """The main reading interpretation. Returns 4–6 paragraph prose."""
    user_block = f"""\
Question: {question}
Spread: {spread}

Cards drawn:
{_format_cards_for_prompt(cards)}

# Memory (the user's history with the oracle)
{history_context.strip() if history_context else "(none yet)"}

Now, in the Hermes Oracle voice, deliver the reading.
"""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _FEWSHOT_THREE_CARD_USER},
        {"role": "assistant", "content": _FEWSHOT_THREE_CARD_ASSISTANT},
        {"role": "user", "content": user_block},
    ]
    return _chat(messages, max_tokens=900)


def oracle_daily(*, sign: str, history_context: str = "") -> str:
    """A 3–4 sentence daily-horoscope micro-reading for a sun sign."""
    user_block = f"""\
Daily horoscope request for sign: {sign}
Date: {time.strftime("%A, %B %-d, %Y", time.gmtime())}

# Memory (the user's history with the oracle)
{history_context.strip() if history_context else "(none — generic daily for this sign)"}

Deliver a 3–4 sentence morning horoscope in the Hermes Oracle voice. No greeting,
no sign-off, no list. End on a single sensory image.
"""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_block},
    ]
    return _chat(messages, max_tokens=300)


def ping() -> str:
    """Smoke-test: returns the model's reply to 'pong?'."""
    messages = [
        {"role": "user", "content": "Reply with the single word: pong"},
    ]
    return _chat(messages, max_tokens=10, retries=1)


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--ping", action="store_true")
    p.add_argument("--demo-reading", action="store_true",
                   help="Run a sample 3-card reading end-to-end (no FLUX)")
    p.add_argument("--daily", type=str, help="sign for a daily horoscope, e.g. Aries")
    args = p.parse_args()

    if args.ping:
        print(ping())

    if args.daily:
        print(oracle_daily(sign=args.daily))

    if args.demo_reading:
        from oracle import pull_cards
        drawn = pull_cards("demo", "What does the next month want from me?", "three_card")
        print("# Cards drawn")
        for c in drawn["cards"]:
            print(f"  {c['position']:>10}: {c['name']}{' (R)' if c['reversed'] else ''}")
        print("\n# Reading\n")
        text = oracle_interpret(
            question=drawn["question"],
            cards=drawn["cards"],
            spread=drawn["spread"],
            history_context="",
        )
        print(text)
