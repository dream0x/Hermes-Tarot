# 🔮 Hermes Oracle

> A Hermes Agent skill that turns the agent into a personal divination companion: tarot spreads rendered as a visually consistent FLUX deck, interpreted by Kimi K2.6's 256K context with full memory of your past readings, and delivered on schedule via Telegram. The hero card of each reading mints as an ERC-721 NFT on Base Sepolia.

Built for the [**Hermes Agent Creative Hackathon**](https://hermes-agent.nousresearch.com/) by [Nous Research](https://nousresearch.com/) × [Kimi (Moonshot AI)](https://www.kimi.com/), May 2026.

![demo](docs/demo.gif) <!-- placeholder; will be replaced with the submission video -->

---

## Why this exists

The Hermes Agent ecosystem (see `awesome-hermes-agent`) already has skills for FLUX images, Spotify playback, autonomous novel writing, and TouchDesigner. There was no skill for the **divination / personalization / spiritual companion** space — a category with massive Western mainstream traction (Co-Star: 30M users, WitchTok: billions of views).

Hermes Oracle fills that gap and demonstrates three Hermes-unique strengths in one product:
- **Persistent memory** → every reading you've ever had is in context for the next one
- **Scheduled cron in natural language** → daily horoscope DM at 9 AM
- **Multi-platform** → lives where you already chat (Telegram first, Discord/Slack trivial)

It also showcases **Kimi K2.6's 256K context window** as a personalization engine, not just a long-doc reader.

---

## Architecture

```
┌─ Telegram ───────────────────────────┐
│  user message                        │
└──────────────┬───────────────────────┘
               │
        ┌──────▼──────┐    rate limit + spend ceiling
        │  Hermes     │───►│ ratelimit.py + config.py │
        │  Agent      │
        └──────┬──────┘
               │
   ┌───────────┼─────────────┬──────────────┐
   ▼           ▼             ▼              ▼
┌──────┐  ┌─────────┐   ┌──────────┐  ┌──────────┐
│ tarot│  │ astro   │   │  Kimi    │  │ memory   │
│ deck │  │ natal/  │   │  K2.6    │  │ MEMORY.md│
│  +   │  │ daily   │   │ (256K)   │  │ JSONL    │
│ FLUX │  │         │   │          │  │ history  │
└──┬───┘  └─────────┘   └──────────┘  └──────────┘
   │
   ▼ on "mint"
┌──────────────────┐
│ Pinata (IPFS)    │
│ → Base Sepolia   │
│   ERC-721        │
└──────────────────┘
```

---

## Setup

### Prereqs
- Python 3.11+
- [Hermes Agent](https://hermes-agent.nousresearch.com/) installed (`curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash` then `hermes setup`)
- [Foundry](https://book.getfoundry.sh/) (only if you want to redeploy the contract)

### Install
```bash
git clone https://github.com/dream0x/Hermes-Tarot.git
cd Hermes-Tarot
cp .env.example .env       # then fill in real keys — see .env.example for source URLs
pip install -r requirements.txt
ln -s "$(pwd)" ~/.hermes/skills/Hermes-Tarot
hermes restart
```

In your Hermes chat:
```
/skills
# you should see Hermes-Tarot listed

pull cards for my week, focus on work
```

### Smoke tests
```bash
python -m hermes_oracle.tarot.deck --validate     # asserts 78 cards, no dupes
python -m hermes_oracle.kimi --ping               # round-trips Kimi
python -m hermes_oracle.tarot.render --test fool  # one FLUX image
python -m hermes_oracle.nft.mint --dry-run        # Pinata + tx simulation
```

---

## Powered by
- [**Hermes Agent**](https://hermes-agent.nousresearch.com/) by Nous Research
- [**Kimi K2.6**](https://www.kimi.com/ai-models/kimi-k2-6) by Moonshot AI (256K context)
- [**FLUX**](https://blackforestlabs.ai/) by Black Forest Labs (via fal.ai)
- [**Base**](https://base.org/) Sepolia testnet

---

## Roadmap (post-hackathon v0.2)
- Live **x402** paid premium readings (autonomous USDC microtransactions)
- Autonomous mint per reading (every spread auto-mints as a private NFT)
- Discord & WhatsApp deployments (Hermes makes this ~30 min of config)
- Voice replies via TTS
- Mobile-friendly WebApp inside Telegram

---

## License
MIT — see `LICENSE`.

The live public bot may be offline after hackathon judging concludes; this code is reference and reproducible by anyone with their own API keys.
