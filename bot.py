"""Hermes Oracle — standalone Telegram bot transport.

This is a thin wrapper around `oracle.py`: it owns the Telegram UX
(media-groups, inline buttons, JobQueue for daily horoscopes) and
delegates all real work to the skill module. The same `oracle.py` is
also discoverable to Hermes Agent itself via SKILL.md — this bot is
just the demo-friendly entry point.

Run:
    python bot.py
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from datetime import time as dtime
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import oracle as oracle_mod
from config import cfg
from memory import Profile, find_reading, recent_readings
from ratelimit import can_mint, check_can_read, commit_read, todays_spend

logging.basicConfig(
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    level=getattr(logging, cfg.log_level.upper(), logging.INFO),
)
log = logging.getLogger("hermes_oracle.bot")

WELCOME = (
    "🔮 *The Hermes Oracle is listening.*\n\n"
    "Send a question — anything sitting on your chest — and the cards will answer.\n\n"
    "Or try:\n"
    "  • `/pull <your question>` — pull a 3-card spread\n"
    "  • `/single <your question>` — pull one card\n"
    "  • `/horoscope <sign>` — daily horoscope (e.g. `/horoscope leo`)\n"
    "  • `/profile` — set your sun sign, birth date, wallet\n"
    "  • `/history` — see your last readings\n\n"
    "_For reflection, not prescription._"
)

THINKING = "🕯️ _Drawing the cards..._"
INTERPRETING = "🌙 _The Oracle is reading..._"


# ---------- Helpers ----------

def _user_id(update: Update) -> int:
    assert update.effective_user is not None
    return update.effective_user.id


def _user_label(update: Update) -> str:
    u = update.effective_user
    if not u:
        return "anon"
    return f"@{u.username}" if u.username else f"id={u.id}"


def _gate(update: Update) -> tuple[bool, str | None]:
    """Return (allowed, refusal_message_or_none)."""
    decision = check_can_read(_user_id(update))
    if not decision.allowed:
        return False, decision.user_message
    return True, None


def _reading_keyboard(user_id: int, reading_id: str) -> InlineKeyboardMarkup:
    """Buttons shown under a reading."""
    rows: list[list[InlineKeyboardButton]] = []
    if cfg.is_owner(user_id):
        rows.append([
            InlineKeyboardButton("🔮 Mint hero card on-chain", callback_data=f"mint:{reading_id}:0"),
        ])
    rows.append([
        InlineKeyboardButton("🪞 Pull again", callback_data="pull_again"),
        InlineKeyboardButton("📅 Daily at 9 AM UTC", callback_data="schedule_daily"),
    ])
    return InlineKeyboardMarkup(rows)


# ---------- Commands ----------

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("/start from %s", _user_label(update))
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)


async def cmd_pull(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(ctx.args) if ctx.args else ""
    await _do_reading(update, ctx, question or "Speak to me about this moment.", spread="three_card")


async def cmd_single(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(ctx.args) if ctx.args else "What does this moment ask of me?"
    await _do_reading(update, ctx, question, spread="single")


async def cmd_horoscope(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    sign = (ctx.args[0] if ctx.args else "").strip().capitalize()
    profile = Profile.load(user_id)
    sign = sign or (profile.sun_sign or "")
    if not sign:
        await update.message.reply_text(
            "Tell me your sun sign first: `/horoscope leo` (or set it with `/profile sign leo`).",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    ok, refusal = _gate(update)
    if not ok:
        await update.message.reply_text(refusal or "Not now.", parse_mode=ParseMode.MARKDOWN)
        return

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        text = await asyncio.to_thread(oracle_mod.daily_horoscope, sign, user_id)
    except Exception as e:  # noqa: BLE001
        log.exception("horoscope failed")
        await update.message.reply_text(f"The Oracle stumbled: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return
    commit_read(user_id)
    await update.message.reply_text(f"☀️ *{sign} — today*\n\n{text}", parse_mode=ParseMode.MARKDOWN)


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    profile = Profile.load(user_id)

    # Usage forms:
    #   /profile                                 -> show current
    #   /profile sign leo
    #   /profile dob 1995-04-12
    #   /profile place "Kyiv, Ukraine"
    #   /profile wallet 0xabc...
    if not ctx.args:
        await update.message.reply_text(
            "Your profile:\n```\n" + "\n".join(
                f"{k}: {v}" for k, v in asdict(profile).items() if v
            ) + "\n```\nSet fields like:\n"
            "  `/profile sign leo`\n"
            "  `/profile dob 1995-04-12`\n"
            "  `/profile place \"Kyiv, Ukraine\"`\n"
            "  `/profile wallet 0xabc...`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    field, _, value = " ".join(ctx.args).partition(" ")
    field = field.lower().strip()
    value = value.strip().strip('"').strip("'")
    mapping = {
        "sign": "sun_sign",
        "dob": "dob",
        "place": "birth_place",
        "time": "birth_time",
        "name": "display_name",
        "wallet": "wallet_address",
        "tone": "tone_preference",
    }
    attr = mapping.get(field)
    if not attr:
        await update.message.reply_text(f"Unknown field `{field}`.", parse_mode=ParseMode.MARKDOWN)
        return
    setattr(profile, attr, value)
    profile.save()
    await update.message.reply_text(f"✓ {attr} = {value}", parse_mode=ParseMode.MARKDOWN)


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    rs = recent_readings(user_id, limit=5)
    if not rs:
        await update.message.reply_text("No readings yet. Ask the cards a question.")
        return
    lines = ["🕯️ *Your last readings:*\n"]
    for r in rs:
        ts = time.strftime("%Y-%m-%d", time.gmtime(r.timestamp))
        cards = ", ".join(c["name"] for c in r.cards)
        lines.append(f"`{ts}` — _{r.question[:60]}_\n      {cards}\n")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner-only. Shows spend + active limits."""
    user_id = _user_id(update)
    if not cfg.is_owner(user_id):
        return
    g = todays_spend()
    msg = (
        f"*Hermes Oracle — status*\n"
        f"Today's spend: ${g.spent_usd:.4f} / ${cfg.max_daily_usd_spend}\n"
        f"Breakdown: {g.breakdown}\n"
        f"Public enabled: {cfg.public_enabled}\n"
        f"Public daily / lifetime: {cfg.public_daily_readings} / {cfg.public_lifetime_readings}\n"
        f"Allowlist daily: {cfg.allowlist_daily_readings}\n"
        f"Owner: {cfg.owner_telegram_id}\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ---------- Free-form text -> reading ----------

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    q = update.message.text.strip()
    if q.startswith("/"):
        return
    await _do_reading(update, ctx, q, spread="three_card")


# ---------- Reading flow ----------

async def _do_reading(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    question: str,
    *,
    spread: str = "three_card",
) -> None:
    user_id = _user_id(update)
    chat_id = update.effective_chat.id

    ok, refusal = _gate(update)
    if not ok:
        await update.message.reply_text(refusal or "Not now.", parse_mode=ParseMode.MARKDOWN)
        return

    log.info("reading: user=%s spread=%s q=%r", _user_label(update), spread, question[:80])
    await ctx.bot.send_chat_action(chat_id, ChatAction.TYPING)
    progress_msg = await update.message.reply_text(THINKING, parse_mode=ParseMode.MARKDOWN)

    try:
        # Pull (cheap) + render (FLUX)
        drawn = await asyncio.to_thread(oracle_mod.pull_cards, user_id, question, spread)
        rendered = await asyncio.to_thread(oracle_mod.render_cards, drawn["cards"])
    except Exception as e:  # noqa: BLE001
        log.exception("pull/render failed")
        await progress_msg.edit_text(f"The cards are uncooperative: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return

    # Send the cards as a media-group with question as caption on the first card.
    caption = f"*“{question}”*\n_{spread.replace('_', ' ')}_"
    media: list[InputMediaPhoto] = []
    for i, c in enumerate(rendered):
        path = Path(c["image_path"])
        with path.open("rb") as f:
            data = f.read()
        if i == 0:
            media.append(InputMediaPhoto(media=data, caption=caption, parse_mode=ParseMode.MARKDOWN,
                                         filename=path.name))
        else:
            media.append(InputMediaPhoto(media=data, filename=path.name))
    try:
        sent = await ctx.bot.send_media_group(chat_id=chat_id, media=media)
    except Exception:
        log.exception("media_group failed; falling back to single sends")
        for c in rendered:
            with Path(c["image_path"]).open("rb") as f:
                await ctx.bot.send_photo(chat_id=chat_id, photo=f.read())
        sent = []

    # Now interpret + save
    await progress_msg.edit_text(INTERPRETING, parse_mode=ParseMode.MARKDOWN)
    try:
        interpretation = await asyncio.to_thread(
            oracle_mod.interpret_reading, user_id, question, rendered, spread
        )
    except Exception as e:  # noqa: BLE001
        log.exception("interpret failed")
        await progress_msg.edit_text(f"The Oracle is silent: `{e}`", parse_mode=ParseMode.MARKDOWN)
        return

    # Persist as a Reading and surface buttons keyed by its id
    from memory import Reading, append_reading
    reading = Reading(
        id=Reading.new_id(),
        user_id=str(user_id),
        timestamp=time.time(),
        question=question,
        spread=spread,
        cards=rendered,
        interpretation=interpretation,
    )
    append_reading(reading)
    commit_read(user_id)

    await progress_msg.delete()
    # Send the interpretation with action buttons
    await ctx.bot.send_message(
        chat_id=chat_id,
        text=interpretation,
        reply_markup=_reading_keyboard(user_id, reading.id),
    )


# ---------- Inline buttons ----------

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "pull_again":
        msg = update.effective_message
        if not msg:
            return
        # Best-effort: re-use the previous question if we can find the most recent
        last = recent_readings(user_id, limit=1)
        question = last[-1].question if last else "Pull again."
        # Build a synthetic Update for the reading flow by reusing this chat
        await ctx.bot.send_message(chat_id=msg.chat_id, text="🕯️ _New cards..._", parse_mode=ParseMode.MARKDOWN)
        # We can't easily forge an Update; just call the orchestration directly.
        try:
            ok, refusal = _gate(update)
            if not ok:
                await ctx.bot.send_message(msg.chat_id, refusal or "Not now.")
                return
            drawn = await asyncio.to_thread(oracle_mod.pull_cards, user_id, question, "three_card")
            rendered = await asyncio.to_thread(oracle_mod.render_cards, drawn["cards"])
            interpretation = await asyncio.to_thread(
                oracle_mod.interpret_reading, user_id, question, rendered, "three_card"
            )
            from memory import Reading, append_reading
            r = Reading(id=Reading.new_id(), user_id=str(user_id), timestamp=time.time(),
                        question=question, spread="three_card",
                        cards=rendered, interpretation=interpretation)
            append_reading(r)
            commit_read(user_id)
            media = []
            for i, c in enumerate(rendered):
                with open(c["image_path"], "rb") as f:
                    data_b = f.read()
                if i == 0:
                    media.append(InputMediaPhoto(media=data_b, caption=f"*“{question}”*", parse_mode=ParseMode.MARKDOWN))
                else:
                    media.append(InputMediaPhoto(media=data_b))
            await ctx.bot.send_media_group(msg.chat_id, media=media)
            await ctx.bot.send_message(msg.chat_id, interpretation,
                                       reply_markup=_reading_keyboard(user_id, r.id))
        except Exception as e:  # noqa: BLE001
            log.exception("pull_again failed")
            await ctx.bot.send_message(msg.chat_id, f"The cards resist: `{e}`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "schedule_daily":
        # Ensure profile has a sun sign first
        profile = Profile.load(user_id)
        if not profile.sun_sign:
            await ctx.bot.send_message(query.message.chat_id,
                "Set your sun sign first: `/profile sign leo`", parse_mode=ParseMode.MARKDOWN)
            return
        chat_id = query.message.chat_id
        # Remove any prior job
        for job in ctx.job_queue.get_jobs_by_name(f"daily-{user_id}"):
            job.schedule_removal()
        ctx.job_queue.run_daily(
            _job_daily_horoscope,
            time=dtime(hour=9, minute=0),  # UTC
            data={"user_id": user_id, "chat_id": chat_id},
            name=f"daily-{user_id}",
        )
        await ctx.bot.send_message(chat_id,
            f"📅 _Done. The {profile.sun_sign} horoscope will arrive each morning at 9:00 UTC._",
            parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("mint:"):
        _, reading_id, idx = data.split(":", 2)
        decision = can_mint(user_id)
        if not decision.allowed:
            await ctx.bot.send_message(query.message.chat_id, decision.user_message,
                                        parse_mode=ParseMode.MARKDOWN)
            return
        await ctx.bot.send_message(query.message.chat_id, "⛓️ _Pinning to IPFS and minting on Base Sepolia..._",
                                    parse_mode=ParseMode.MARKDOWN)
        try:
            result = await asyncio.to_thread(oracle_mod.mint_card, user_id, reading_id, int(idx))
        except Exception as e:  # noqa: BLE001
            log.exception("mint failed")
            await ctx.bot.send_message(query.message.chat_id, f"Mint failed: `{e}`",
                                        parse_mode=ParseMode.MARKDOWN)
            return
        await ctx.bot.send_message(
            query.message.chat_id,
            f"✨ *Minted on Base Sepolia.*\nToken #{result['token_id']}\n"
            f"[View your card]({result['viewer_url']})\n"
            f"[Basescan token]({result['basescan_token_url']}) · [Tx]({result['tx_url']})",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )


# ---------- Scheduled job ----------

async def _job_daily_horoscope(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    data = ctx.job.data or {}
    user_id = int(data["user_id"])
    chat_id = int(data["chat_id"])
    profile = Profile.load(user_id)
    sign = profile.sun_sign or "Aries"
    try:
        text = await asyncio.to_thread(oracle_mod.daily_horoscope, sign, user_id)
    except Exception as e:  # noqa: BLE001
        log.exception("scheduled horoscope failed for %s", user_id)
        await ctx.bot.send_message(chat_id, f"_Today's horoscope stumbled: {e}_",
                                    parse_mode=ParseMode.MARKDOWN)
        return
    await ctx.bot.send_message(chat_id, f"☀️ *{sign} — today*\n\n{text}",
                                parse_mode=ParseMode.MARKDOWN)


# ---------- Wiring ----------

def build_app() -> Application:
    if not cfg.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    app = ApplicationBuilder().token(cfg.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pull", cmd_pull))
    app.add_handler(CommandHandler("single", cmd_single))
    app.add_handler(CommandHandler("horoscope", cmd_horoscope))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


def main() -> None:
    app = build_app()
    log.info("Starting Hermes Oracle bot @%s ...", cfg.telegram_bot_username or "<unknown>")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
