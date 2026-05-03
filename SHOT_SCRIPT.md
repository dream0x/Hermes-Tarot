# 🎬 Mnemos demo — shot script

**Length:** 75–90 seconds. **Aspect:** 16:9 horizontal (recommended for X autoplay; 9:16 also works if you'd rather go vertical, just stack instead of split).
**Goal:** prove this is a real Hermes Agent skill driven by real Kimi K2.6 calls minting real on-chain NFTs — not a hand-wavy wrapper.

---

## Pre-flight (5 min, before you hit record)

### Open these windows in this order, leave them ready
1. **Telegram Desktop** (not browser — gives a cleaner screenshot than Web). Chat: `@mnemos_oracle_bot`. Resize to ~520 px wide, place on the LEFT half of the screen.
2. **Terminal #1 (events)** — for the live streamer:
   ```bash
   cd "/Users/alex0x/Desktop/vibecoding/nous hackathon/hermes-oracle"
   python3 scripts/demo_logs.py
   ```
   Set font to **22–26 pt bold**, dark background. Place on the RIGHT half. *Don't run yet — start it during shot 2.*
3. **Browser tab** with: https://dream0x.github.io/Mnemos/?contract=0xa1b9bdeb72aa4f4b86c11234ea6301daa68d2c16&token=2 (placeholder; we'll swap to your fresh token)

### One-time prep
- In Telegram with your test account, run `/start` and complete onboarding so the camera doesn't waste time on it (we'll show a returning user). Do *not* ask any questions yet — we want a clean reading-history slate from your own ID.
- On your Mac terminal, kill any stale streamer: `pkill -f demo_logs.py || true`.

### OBS / screen-recorder settings
- Resolution: 1920×1080 (or 1080×1920 vertical)
- Display capture (whole screen) is fine; you'll crop in post.
- Mic on, voiceover lightweight (3–4 sentences total).

---

## The shots (timing = approximate)

### Shot 1 — cold open (0:00 – 0:08)
**Visual:** full-screen Telegram chat. The user (you) tap `🔮 Pull cards` from the reply keyboard, the bot asks "What question are you bringing to the cards?", you type something punchy:
> *"Will this hackathon project actually ship?"*

You hit send. Hold on the *"🕯️ Drawing the cards…"* status.

**Voice / caption (overlay):**
> "Mnemos — an oracle that remembers every card it's ever pulled for you."

---

### Shot 2 — split-screen reveal (0:08 – 0:25)

The hero moment. Cut to a 50/50 split: Telegram on the left, terminal on the right.

**Action sequence as the reading completes:**
- The 3-card carousel appears in Telegram (≥ 3 seconds hold so the cards register visually).
- **Simultaneously** in the right pane, the streamer prints, line by line:
  ```
  🪞 reading three_card from @doxe01
     ↳ "Will this hackathon project actually ship?"
  ◆ flux  cache hit  the-tower            (no spend)
  ◆ flux  dev        nine-of-pentacles ↻  ·  $0.0250
  ◆ flux  cache hit  the-star             (no spend)
  ◆ kimi  kimi-k2.6  (interpret)  6,142 in → 731 out  ·  $0.00366
  ```
- Then the Kimi prose interpretation scrolls into Telegram below the cards.

**Voice (over the second half):**
> "Real Hermes skill, real Kimi K2.6 calls, real FLUX renders. The 256-K context means every prior reading is in scope."

**Caption (burned in, lower-third, 0:14 – 0:22):**
> `Powered by Kimi K2.6 · 256K context remembers every reading`

---

### Shot 3 — memory call-back (0:25 – 0:42)

**Visual:** stay in split-screen. You ask a *second* question that lets the oracle reference the first:
> *"And what's blocking that ship?"*

Cards appear, streamer fires more events, and — critically — the Kimi prose **explicitly mentions a card from the first reading**. Highlight that sentence with a pulse-zoom or coloured underline in post (CapCut "Beat Underline" effect works).

**Voice:**
> "Watch the second reading. It calls back to the first one — that's the entire history fed into Kimi every turn."

**Caption (burned in):**
> `← oracle references the first reading`

---

### Shot 4 — code reveal (0:42 – 0:50)

A 7-second cut to your code editor (any theme — VS Code dark / Zed / Sublime). Show *three* quick scrolls, each held for 2 seconds:

1. **`SKILL.md`** lines 1–18 (the agentskills.io frontmatter + the "When to use" list).
2. **`kimi.py`** lines 39–60 (the locked-persona system prompt; specifically the "frame → cards as answer → direction" block).
3. **`oracle.py`** lines 49–80 (the `pull_cards` tool definition).

**Voice (whisper-fast):**
> "It's a real Hermes skill: a manifest and a tool surface. Drop it into any Hermes install and the agent calls it natively."

---

### Shot 5 — mint on-chain (0:50 – 1:08)

**Visual:** back to split-screen. In Telegram, tap one of the three mint buttons under the reading — pick the one with the most evocative card name (e.g. *"🔮 Mint Future: The Star"*).

The streamer fires:
```
◆ ipfs   pinning image  (the-star)
◆ ipfs   pinning metadata  image cid Qm…
◆ chain  tx broadcast  0x47e3f1334dae…
◆ chain  tx confirmed  block 41013240
✨ minted  token #N
   ↳ https://dream0x.github.io/Mnemos/?contract=…&token=N
```

The bot replies in Telegram with the viewer link. **Click it on camera.** Custom viewer page loads — show the card, the title, the attributes, the "Basescan token / Tx" links.

**Voice:**
> "One tap. Pinned to IPFS, minted on Base Sepolia, viewable forever — even after this hackathon ends."

**Caption (burned in 0:55 – 1:05):**
> `ERC-721 on Base Sepolia · custom on-chain viewer`

---

### Shot 6 — daily horoscope cron (1:08 – 1:18)

**Visual:** in Telegram, tap the `☀️ Horoscope` reply-keyboard button. Bot replies (your saved sun sign — Capricorn or whatever). Below it: *"Want this every morning?"* with a `📅 Daily at 9 AM UTC` button. Tap it. Bot confirms.

Streamer shows the kimi event for the horoscope:
```
◆ kimi  kimi-k2.6  (horoscope)  4,318 in → 187 out  ·  $0.00176
```

**Voice:**
> "And it stays with you — Hermes' built-in scheduler delivers your sun-sign reading every morning at nine."

---

### Shot 7 — end card (1:18 – 1:25)

Static end-card, ~5 seconds. Black background, brand text:

```
                            🪞  Mnemos

         a divination companion · built on Hermes Agent
                  voice by Kimi K2.6 · cards by FLUX
                       on-chain on Base Sepolia

                       github.com/dream0x/Mnemos
                       t.me/mnemos_oracle_bot

       Built for the Hermes Agent Creative Hackathon, May 2026
                @NousResearch · @Kimi_Moonshot
```

**No voiceover here.** Let it breathe for the X autoplay.

---

## Editing notes (CapCut / DaVinci / Final Cut)

- **Music:** soft ambient, low BPM. Pixabay's "Mystic" or "Cinematic Documentary Ambient" categories — copyright-free. Duck under voiceover by ~12 dB.
- **Transitions:** none between shots inside the split-screen segment. Hard cuts between the demo and the code reveal. A 0.4s fade to black before the end card.
- **Captions style:** sans-serif (Inter, Helvetica), 32 pt, white with 60% black drop, lower-third positioning. Hold each ≥ 2 s.
- **Cursor:** in Telegram & terminal cuts, set the cursor to a custom highlight (`Cursor Highlighter` on Mac, or just enable system cursor magnification) so judges can follow taps.
- **Speed:** the streamer pace is naturally 1×. If something stretches, speed-ramp to 1.25× *between* events (in the dead time), never *during* an event line.

---

## Voiceover script (full)

If you record VO at the end and overdub:

```
[0:00] Mnemos. An oracle that remembers every card it's ever pulled for you.

[0:14] Real Hermes skill, real Kimi K2.6 calls, real FLUX renders.
        The 256-K context means every prior reading is in scope.

[0:28] Watch the second reading. It calls back to the first one.
        That's the entire history fed into Kimi every turn.

[0:43] It's a real Hermes skill: a manifest and a tool surface.
        Drop it into any Hermes install and the agent calls it natively.

[0:54] One tap. Pinned to IPFS, minted on Base Sepolia,
        viewable forever — even after this hackathon ends.

[1:10] And it stays with you — Hermes' built-in scheduler
        delivers your sun-sign reading every morning at nine.
```

You can pre-record this and lay it over a silent screen-recording. Easier than live-narrating while clicking.

---

## Backup plan

If anything fails on camera:
- **Streamer doesn't connect over SSH** → use `scripts/demo_logs.py --replay logs/sample.txt` (capture a sample first with `ssh root@HETZNER 'journalctl -u hermes-tarot --since "30m ago"' > logs/sample.txt`).
- **A Kimi call fails mid-shot** → just re-run that shot. The streamer also prints failures in red so you can call them out as "oracle stumbled, gracefully" — but better to have a clean take.
- **OpenSea-style viewer doesn't load fast enough** → pre-load it in a tab before recording, then just `Cmd+Tab` to it.
- **You forget which question to ask** → the two questions on this page are good. Use them verbatim.

---

## What makes this different from other hackathon submissions

When you write your tweet copy and Discord post, lean on these in this order:
1. **Memory is the killer feature** — most submissions are stateless wrappers. Mnemos uses Kimi K2.6's 256K window to weave 30 prior readings into every new one.
2. **Real on-chain artifact** — judging from the prize pool (Nous + Kimi + Coinbase / x402 sponsorships in spirit), an actual ERC-721 mint will land. Most submissions won't bother.
3. **Production-grade hosting** — €4.5/mo VPS with systemd hardening, error handling, rate limits, file locks. Not "works on my laptop."
4. **First-class Hermes skill** — SKILL.md manifest, tool surface that the agent itself can call, persistent-memory pattern. Plays the runtime, doesn't just call an LLM behind it.
