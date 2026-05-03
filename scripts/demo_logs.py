#!/usr/bin/env python3
"""Mnemos — pretty live-log streamer for the demo recording.

Tails journalctl on the production VPS, filters out polling noise, and
prints a colour-coded one-line-per-event stream that's readable in a
60-pt terminal during a screen-recording.

Usage:
    python3 scripts/demo_logs.py                 # ssh tails the prod VPS
    python3 scripts/demo_logs.py --local         # tail local journalctl
    python3 scripts/demo_logs.py --replay FILE   # replay a saved journal

Recommended terminal setup before recording:
    iTerm2 / WezTerm window
    Font: Menlo / JetBrains Mono Bold, 22-26 pt
    Window dim: ~80 cols x 25 rows
    Background: deep indigo (#0d0a14) to match Mnemos brand
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime

# ----- ANSI colours -----
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Brand-ish palette (true colour)
def rgb(r, g, b):  return f"\033[38;2;{r};{g};{b}m"
GOLD   = rgb(232, 200, 151)
INDIGO = rgb(140, 130, 220)
ROSE   = rgb(229, 110, 130)
TEAL   = rgb(110, 200, 200)
GREEN  = rgb(126, 210, 140)
GREY   = rgb(140, 140, 160)
WHITE  = rgb(243, 234, 214)

# ----- Defaults -----
DEFAULT_HOST = "root@91.99.118.149"
DEFAULT_UNIT = "hermes-tarot"

# Strip the journalctl prefix: "May 03 16:41:27 taligate python[12345]: "
PREFIX_RE = re.compile(
    r"^[A-Z][a-z]{2}\s+\d+\s+\d\d:\d\d:\d\d\s+\S+\s+\S+\[\d+\]:\s*"
)
# Strip Python "2026-05-03 16:41:27,059 INFO    mnemos.bot: " too
PYLOG_RE = re.compile(
    r"^\d{4}-\d\d-\d\d\s+\d\d:\d\d:\d\d,\d+\s+\w+\s+\S+:\s*"
)
# Strip httpx wrapper: "HTTP Request: POST <URL> "HTTP/1.1 NNN ...""
HTTPX_RE = re.compile(r'HTTP Request:\s+(\w+)\s+(\S+)\s+"HTTP/[\d.]+\s+(\d+)')

# Filter: skip pure polling spam
NOISE_SUBSTRINGS = (
    "/getUpdates",
    "deleteWebhook",
    "getMe",
    "Application started",
    "Application is stopping",
    "Application.stop",
    "Scheduler started",
    "BotCommands + descriptions registered",
    "PTBUserWarning",
    "for job in ctx.job_queue",  # warning trace
)


def _now_clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _strip(line: str) -> str:
    line = PREFIX_RE.sub("", line)
    line = PYLOG_RE.sub("", line)
    return line


# ----- Event formatters -----

def fmt_reading_start(m: re.Match) -> str:
    user = m.group("user")
    spread = m.group("spread")
    q = m.group("q").strip("'\"")
    return f"{INDIGO}🪞 reading {WHITE}{spread}{RESET}  {GREY}from{RESET} {GOLD}{user}{RESET}\n   {DIM}↳ “{q}”{RESET}"


def fmt_kimi(m: re.Match) -> str:
    kind = m.group("kind")
    inp = int(m.group("inp"))
    out = int(m.group("out"))
    cost = float(m.group("cost"))
    label = "horoscope" if kind == "horoscope" else "interpret"
    return (f"{INDIGO}◆ kimi {WHITE}kimi-k2.6{RESET}  "
            f"{GREY}({label}){RESET}  "
            f"{WHITE}{inp:>5,}{GREY} in  →  {WHITE}{out:>4,}{GREY} out  ·  "
            f"{GOLD}${cost:.5f}{RESET}")


def fmt_flux(m: re.Match) -> str:
    model = m.group("model")
    card = m.group("card")
    rev = m.group("rev") == "True"
    cost = float(m.group("cost"))
    badge = " ↻" if rev else "  "
    if model == "cache":
        return (f"{TEAL}◆ flux {GREY}cache hit{RESET}  "
                f"{WHITE}{card}{badge}{RESET}  {DIM}(no spend){RESET}")
    return (f"{TEAL}◆ flux {WHITE}{model.split('/')[-1]}{RESET}  "
            f"{WHITE}{card}{badge}{RESET}  ·  {GOLD}${cost:.4f}{RESET}")


def fmt_mint(m: re.Match) -> str:
    stage = m.group("stage")
    rest = m.group("rest")
    if stage == "pin_image":
        card = re.search(r"card=(\S+)", rest).group(1)
        return f"{ROSE}◆ ipfs {WHITE}pinning image{RESET}  {GREY}({card}){RESET}"
    if stage == "pin_meta":
        cid = re.search(r"cid=(\S+)", rest).group(1)[:12]
        return f"{ROSE}◆ ipfs {WHITE}pinning metadata{RESET}  {DIM}image cid {cid}…{RESET}"
    if stage == "tx_sent":
        h = re.search(r"hash=(\S+)", rest).group(1)
        return f"{ROSE}◆ chain {WHITE}tx broadcast{RESET}  {DIM}{h[:18]}…{RESET}"
    if stage == "tx_mined":
        bk = re.search(r"block=(\S+)", rest).group(1)
        return f"{GREEN}◆ chain {WHITE}tx confirmed{RESET}  {GREY}block {bk}{RESET}"
    if stage == "done":
        tid = re.search(r"token_id=(\S+)", rest).group(1)
        viewer = re.search(r"viewer=(\S+)", rest).group(1)
        return (f"{GREEN}{BOLD}✨ minted{RESET}  "
                f"{GOLD}token #{tid}{RESET}\n   {DIM}↳ {viewer}{RESET}")
    return f"{ROSE}◆ mint {stage} {rest}{RESET}"


# Match an inner MNEMOS_EVENT line.
EVENT_RE = re.compile(
    r"MNEMOS_EVENT\s+(?P<kind>reading|kimi|flux|mint)\s+(?P<rest>.*)$"
)
READING_RE = re.compile(r"stage=start user=(?P<user>\S+) spread=(?P<spread>\S+) question=(?P<q>.+)$")
KIMI_RE = re.compile(r"kind=(?P<kind>\S+) in=(?P<inp>\d+) out=(?P<out>\d+) cost_usd=(?P<cost>[\d.]+)")
FLUX_RE = re.compile(r"model=(?P<model>\S+) card=(?P<card>\S+) reversed=(?P<rev>True|False) cost_usd=(?P<cost>[\d.]+)")
MINT_RE = re.compile(r"stage=(?P<stage>\S+)(?:\s+(?P<rest>.+))?")


def transform(raw: str) -> str | None:
    """Turn one journalctl line into a pretty event line, or None to skip."""
    if any(s in raw for s in NOISE_SUBSTRINGS):
        return None
    body = _strip(raw).strip()
    if not body:
        return None

    m = EVENT_RE.search(body)
    if m:
        kind = m.group("kind")
        rest = m.group("rest")
        clock = f"{DIM}{_now_clock()}{RESET}"
        if kind == "reading":
            mm = READING_RE.match(rest)
            return f"\n{clock}  {fmt_reading_start(mm)}" if mm else None
        if kind == "kimi":
            mm = KIMI_RE.match(rest)
            return f"{clock}  {fmt_kimi(mm)}" if mm else None
        if kind == "flux":
            mm = FLUX_RE.match(rest)
            return f"{clock}  {fmt_flux(mm)}" if mm else None
        if kind == "mint":
            mm = MINT_RE.match(rest)
            return f"{clock}  {fmt_mint(mm)}" if mm else None
        return None

    # Non-event httpx call we still want to surface (callbackquery, sendMessage)?
    # Suppress all of them - they would drown the event lines.
    return None


# ----- Source plumbing -----

def stream_remote(host: str, unit: str):
    cmd = ["ssh", host, f"journalctl -fu {shlex.quote(unit)} --no-pager -n 5"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    assert proc.stdout
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.terminate()


def stream_local(unit: str):
    cmd = ["journalctl", "-fu", unit, "--no-pager", "-n", "5"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    assert proc.stdout
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.terminate()


def stream_replay(path: str):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n")
            time.sleep(0.05)  # pace it for visual effect


# ----- Header -----

def banner():
    print()
    print(f"{GOLD}{BOLD}🪞  M N E M O S   ·   live signal{RESET}")
    print(f"{DIM}    streaming Hermes Agent + Kimi K2.6 + Base Sepolia events{RESET}")
    print(f"{DIM}    " + "─" * 56 + RESET)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"SSH target (default: {DEFAULT_HOST})")
    p.add_argument("--unit", default=DEFAULT_UNIT,
                   help=f"systemd unit name (default: {DEFAULT_UNIT})")
    p.add_argument("--local", action="store_true",
                   help="tail local journalctl instead of ssh")
    p.add_argument("--replay", help="replay a saved journal file (for testing)")
    args = p.parse_args()

    banner()

    if args.replay:
        source = stream_replay(args.replay)
    elif args.local:
        source = stream_local(args.unit)
    else:
        source = stream_remote(args.host, args.unit)

    try:
        for raw in source:
            pretty = transform(raw)
            if pretty:
                print(pretty, flush=True)
    except KeyboardInterrupt:
        print(f"\n{DIM}stream closed{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
