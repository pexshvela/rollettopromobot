"""
Telegram Promo Bot
==================
Requirements: python-telegram-bot>=20.0, aiosqlite, python-dotenv
"""

import logging
import asyncio
import aiosqlite
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import Forbidden, BadRequest

# Load environment variables from .env file (local development)
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set. Please set it in your environment or .env file.")
    raise ValueError("BOT_TOKEN environment variable not set")

MIN_AGE_MINUTES: int = 10
MAX_AGE_HOURS: int = 24
DB_PATH: str = os.getenv("DATABASE_URL", "promo_bot.db")

# ---------------------------------------------------------------------------
# Channel IDs per language – replace with your real channel IDs
# ---------------------------------------------------------------------------
CHANNEL_IDS = {
    "en": -1002961190744,
    "it": -1003501534318,
    "fr": -1003889593264,
    "mx": -1003605526750,
}

# ---------------------------------------------------------------------------
# Discussion Group IDs per language – replace with your real group IDs
# ---------------------------------------------------------------------------
DISCUSSION_GROUP_IDS = {
    "en": -1002916936846,
    "it": -1003840150681,
    "fr": -1003891878488,
    "mx": -1003874695773,
}

# ---------------------------------------------------------------------------
# Promo codes per language – replace with your real promo codes
# ---------------------------------------------------------------------------
PROMO_CODES = {
    "en": "ENPROMOCODE",
    "it": "PROMO-IT-2024",
    "fr": "PROMO-FR-2024",
    "mx": "PROMO-MX-2024",
}


# ---------------------------------------------------------------------------
# Language content
# ---------------------------------------------------------------------------

LANG_SELECT_TEXT = (
    "🇬🇧 Hello!\n"
    "🇮🇹 Ciao!\n"
    "🇫🇷 Bonjour!\n"
    "🇲🇽 ¡Hola!\n\n"
    "Please choose your language / Scegli la lingua / Choisissez la langue / Elige tu idioma:"
)

WELCOME_MESSAGES = {
    "en": (
        "👋 Welcome, {name}!\n\n"
        "Thanks for being a member of our channel 🤝\n"
        "Follow Rolletto on our platforms and stay updated with the latest promotions, news, and rewards\n\n"
        "Then go to the discussion group and send the word <b>bonus</b> to claim your promo code.\n\n"
        "✨Join our channel first:\n"
        "👉 <a href='https://t.me/pexshvela1'>Click here to join the channel</a>"
    ),
    "it": (
        "👋 Benvenuto, {name}!\n\n"
        "Grazie per essere un membro del nostro canale 🤝\n"
        "Segui Rolletto sulle nostre piattaforme e rimani aggiornato con le ultime promozioni, notizie e premi\n\n"
        "Poi vai nel gruppo di discussione e invia la parola <b>bonus</b> per ricevere il tuo codice promo.\n\n"
        "✨Unisciti prima al nostro canale:\n"
        "👉 <a href='https://t.me/+OaMmlSD0P4A5ZTky'>Clicca qui per unirti al canale</a>"
    ),
    "fr": (
        "👋 Bienvenue, {name}!\n\n"
        "Merci d'être membre de notre chaîne 🤝\n"
        "Suivez Rolletto sur nos plateformes et restez informé des dernières promotions, actualités et récompenses\n\n"
        "Ensuite, allez dans le groupe de discussion et envoyez le mot <b>bonus</b> pour recevoir votre code promo.\n\n"
        "✨Rejoignez d'abord notre chaîne:\n"
        "👉 <a href='https://t.me/+DwGG1zcvdE1kZmEy'>Cliquez ici pour rejoindre la chaîne</a>"
    ),
    "mx": (
        "👋 ¡Bienvenido, {name}!\n\n"
        "Gracias por ser miembro de nuestro canal 🤝\n"
        "Sigue a Rolletto en nuestras plataformas y mantente al día con las últimas promociones, noticias y recompensas\n\n"
        "Luego ve al grupo de discusión y envía la palabra <b>bonus</b> para reclamar tu código promo.\n\n"
        "✨Únete primero a nuestro canal:\n"
        "👉 <a href='https://t.me/+N762ymdQF0s1MmZi'>Haz clic aquí para unirte al canal</a>"
    ),
}

BONUS_MESSAGES = {
    "already_claimed": {
        "en": "You have already claimed this promotion.",
        "it": "Hai già riscattato questa promozione.",
        "fr": "Vous avez déjà réclamé cette promotion.",
        "mx": "Ya has reclamado esta promoción.",
    },
    "not_subscribed": {
        "en": "You must join the channel first to receive the bonus.",
        "it": "Devi prima unirti al canale per ricevere il bonus.",
        "fr": "Vous devez d'abord rejoindre la chaîne pour recevoir le bonus.",
        "mx": "Debes unirte al canal primero para recibir el bono.",
    },
    "too_old": {
        "en": "This promotion is only available for new members (within 24 hours).",
        "it": "Questa promozione è disponibile solo per i nuovi membri (entro 24 ore).",
        "fr": "Cette promotion est uniquement disponible pour les nouveaux membres (dans les 24 heures).",
        "mx": "Esta promoción solo está disponible para nuevos miembros (dentro de las 24 horas).",
    },
    "too_new": {
        "en": "You should be a member for at least 10 minutes – try again in about {mins} minute(s).",
        "it": "Devi essere membro da almeno 10 minuti – riprova tra circa {mins} minuto/i.",
        "fr": "Vous devez être membre depuis au moins 10 minutes – réessayez dans environ {mins} minute(s).",
        "mx": "Debes ser miembro por al menos 10 minutos – inténtalo de nuevo en {mins} minuto(s).",
    },
    "no_dm": {
        "en": "⚠️ I could not send you a DM. Please start a private conversation with me first (@rollettopromobot), then type 'bonus' here again.",
        "it": "⚠️ Non riesco a inviarti un messaggio privato. Avvia prima una conversazione privata con me (@rollettopromobot), poi scrivi 'bonus' qui.",
        "fr": "⚠️ Je ne peux pas vous envoyer de message privé. Commencez d'abord une conversation privée avec moi (@rollettopromobot), puis tapez 'bonus' ici.",
        "mx": "⚠️ No pude enviarte un mensaje privado. Primero inicia una conversación privada conmigo (@rollettopromobot), luego escribe 'bonus' aquí.",
    },
    "sent": {
        "en": "✅ Promo code sent to your direct messages.",
        "it": "✅ Codice promo inviato ai tuoi messaggi diretti.",
        "fr": "✅ Code promo envoyé dans vos messages privés.",
        "mx": "✅ Código promo enviado a tus mensajes directos.",
    },
    "promo_dm": {
        "en": "🎉 Congratulations! Here is your exclusive promo code:\n\n<code>{code}</code>\n\nUse it before it expires. Enjoy!",
        "it": "🎉 Congratulazioni! Ecco il tuo codice promo esclusivo:\n\n<code>{code}</code>\n\nUsalo prima che scada. Buon divertimento!",
        "fr": "🎉 Félicitations! Voici votre code promo exclusif:\n\n<code>{code}</code>\n\nUtilisez-le avant qu'il n'expire. Profitez-en!",
        "mx": "🎉 ¡Felicidades! Aquí está tu código promo exclusivo:\n\n<code>{code}</code>\n\nÚsalo antes de que expire. ¡Disfrútalo!",
    },
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                first_seen    REAL NOT NULL,
                claimed       INTEGER NOT NULL DEFAULT 0,
                language      TEXT NOT NULL DEFAULT 'en'
            )
            """
        )
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, first_seen, claimed, language FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def upsert_user(user_id: int) -> dict:
    now = datetime.now(timezone.utc).timestamp()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, first_seen, claimed, language) VALUES (?, ?, 0, 'en')",
            (user_id, now),
        )
        await db.commit()
    return await get_user(user_id)


async def set_user_language(user_id: int, language: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (language, user_id),
        )
        await db.commit()


async def mark_claimed(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET claimed = 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def get_user_language(user_id: int) -> str:
    user = await get_user(user_id)
    if user:
        return user.get("language", "en")
    return "en"


# ---------------------------------------------------------------------------
# Subscription check – checks the correct channel for the user's language
# ---------------------------------------------------------------------------

async def is_subscribed_to_channel(bot, user_id: int, lang: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_IDS[lang], user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except (Forbidden, BadRequest) as exc:
        logger.warning("Could not check channel membership for %s: %s", user_id, exc)
        return False


# ---------------------------------------------------------------------------
# /start command – show language selection buttons
# ---------------------------------------------------------------------------

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await upsert_user(user.id)

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
            InlineKeyboardButton("🇲🇽 Español", callback_data="lang_mx"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        LANG_SELECT_TEXT,
        reply_markup=reply_markup,
    )


# ---------------------------------------------------------------------------
# Callback handler – language button pressed
# ---------------------------------------------------------------------------

async def handle_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    lang = query.data.replace("lang_", "")  # "lang_en" → "en"

    await upsert_user(user.id)
    await set_user_language(user.id, lang)

    welcome_text = WELCOME_MESSAGES[lang].format(name=user.first_name)

    await query.edit_message_text(
        text=welcome_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    logger.info("User %s chose language: %s", user.id, lang)


# ---------------------------------------------------------------------------
# Core handler – "bonus" keyword in any discussion group
# ---------------------------------------------------------------------------

async def handle_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    # Only act inside one of the registered discussion groups
    if chat.id not in DISCUSSION_GROUP_IDS.values():
        return

    logger.info("'bonus' received from user %s (%s)", user.id, user.full_name)

    # Auto-detect language based on which group the message was sent in
    # This means it always works correctly regardless of user's saved language
    lang = next((l for l, gid in DISCUSSION_GROUP_IDS.items() if gid == chat.id), "en")

    # Save detected language to user's profile
    await upsert_user(user.id)
    await set_user_language(user.id, lang)

    # Step 1 – Check subscription to the correct channel for this language
    if not await is_subscribed_to_channel(context.bot, user.id, lang):
        await message.reply_text(BONUS_MESSAGES["not_subscribed"][lang])
        return

    # Step 2 – Record first interaction
    user_record = await upsert_user(user.id)

    # Step 4 – Already claimed?
    if user_record["claimed"]:
        await message.reply_text(BONUS_MESSAGES["already_claimed"][lang])
        return

    # Step 3 – Timing checks
    now = datetime.now(timezone.utc)
    first_seen = datetime.fromtimestamp(user_record["first_seen"], tz=timezone.utc)
    age: timedelta = now - first_seen

    if age > timedelta(hours=MAX_AGE_HOURS):
        await message.reply_text(BONUS_MESSAGES["too_old"][lang])
        return

    if age < timedelta(minutes=MIN_AGE_MINUTES):
        remaining = timedelta(minutes=MIN_AGE_MINUTES) - age
        mins_left = int(remaining.total_seconds() // 60) + 1
        await message.reply_text(
            BONUS_MESSAGES["too_new"][lang].format(mins=mins_left)
        )
        return

    # Eligible – send promo code via DM in user's language
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=BONUS_MESSAGES["promo_dm"][lang].format(code=PROMO_CODES[lang]),
            parse_mode="HTML",
        )
    except Forbidden:
        await message.reply_text(BONUS_MESSAGES["no_dm"][lang])
        return

    await mark_claimed(user.id)
    logger.info("Promo code delivered to user %s in language %s", user.id, lang)
    await message.reply_text(BONUS_MESSAGES["sent"][lang])


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception: %s", context.error, exc_info=context.error)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_language_choice, pattern="^lang_"))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"(?i)\bbonus\b"),
            handle_bonus,
        )
    )
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
