import re
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1003799272783
MUTE_DAYS = 7

BANNED_WORDS = {
    # alkohol
    "wódka", "wodka", "vodka", "piwo", "whisky",
    "whiskey", "rum", "gin", "wino", "tequila",
    "bimber", "alkohol",

    # marihuana
    "buch", "buu", "weed", "marihuana",
    "marihuana", "trawa", "zioło", "ziolo",
    "ganja", "joint", "blant", "blunt",
    "thc", "cbd", "hasz", "haszysz",

    # stymulanty
    "amfa", "amfetamina", "speed",
    "feta", "mefedron", "mefa",
    "4mmc", "4-mmc", "3cmc", "3-cmc",
    "4cmc", "4-cmc", "klef", "krysztal",
    "crystal", "ice",

    # kokaina
    "koks", "kokaina", "coke",
    "coca", "snow",

    # opio
    "opio", "opioid", "opioidy",
    "heroina", "hera", "oxy",
    "oxycodon", "oxycodone",
    "morfina", "morfina",
    "fentanyl", "tramal",
    "tramadol", "metadon",

    # psychodeliki
    "lsd", "kwas", "acid",
    "grzyby", "grzybki",
    "psylocybina",

    # mdma
    "mdma", "ecstasy", "xtc",
    "molly",

    # benzodiazepiny
    "xanax", "alpra",
    "alprazolam", "clonazepam",
    "klony", "diazepam",
}

LINK_PATTERN = re.compile(
    r"(https?:\/\/|www\.|t\.me\/|telegram\.me\/|discord\.gg\/|"
    r"bit\.ly\/|tinyurl\.com\/|\.pl\b|\.com\b|\.net\b|\.org\b)",
    re.IGNORECASE,
)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001FFFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "]",
    flags=re.UNICODE,
)


def normalize(text: str):
    return re.sub(
        r"[^a-zA-Z0-9ąćęłńóśżź]",
        "",
        text.lower(),
    )


async def is_admin(chat, user_id):
    member = await chat.get_member(user_id)
    return member.status in ["administrator", "creator"]


async def mute_user(update, context, reason):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    try:
        await message.delete()
    except:
        pass

    until_date = (
        datetime.now(timezone.utc)
        + timedelta(days=MUTE_DAYS)
    )

    await context.bot.restrict_chat_member(
        chat_id=chat.id,
        user_id=user.id,
        permissions=ChatPermissions(
            can_send_messages=False
        ),
        until_date=until_date,
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Unmute",
                    callback_data=f"unmute:{user.id}"
                )
            ]
        ]
    )

    username = (
        f"@{user.username}"
        if user.username
        else user.full_name
    )

    await chat.send_message(
        f"🚫 MODERATION SYSTEM\n\n"
        f"👤 User: {username} [{user.id}]\n\n"
        f"📋 Reason:\n{reason}\n\n"
        f"🔇 Action: Muted\n\n"
        f"📅 Until:\n"
        f"{until_date.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=keyboard,
    )


async def check_message(update, context):
    chat = update.effective_chat

    if not chat:
        return

    if chat.id != GROUP_ID:
        return

    user = update.effective_user

    if await is_admin(chat, user.id):
        return

    message = update.effective_message

    if not message:
        return

    text = message.text or message.caption or ""

    if not text:
        return

    if "#" in text:
        await mute_user(
            update,
            context,
            "Hashtag detected (#)"
        )
        return

    if LINK_PATTERN.search(text):
        await mute_user(
            update,
            context,
            "Link detected"
        )
        return

    if EMOJI_PATTERN.search(text):
        await mute_user(
            update,
            context,
            "Emoji detected"
        )
        return

    lower_text = text.lower()
    normalized = normalize(text)

    for word in BANNED_WORDS:

        if word.lower() in lower_text:
            await mute_user(
                update,
                context,
                f"Banned word: {word}"
            )
            return

        if normalize(word) in normalized:
            await mute_user(
                update,
                context,
                f"Banned word: {word}"
            )
            return


async def unmute_callback(update, context):
    query = update.callback_query

    await query.answer()

    member = await context.bot.get_chat_member(
        query.message.chat.id,
        query.from_user.id,
    )

    if member.status not in [
        "administrator",
        "creator",
    ]:
        await query.answer(
            "Only admins can unmute.",
            show_alert=True,
        )
        return

    user_id = int(
        query.data.split(":")[1]
    )

    await context.bot.restrict_chat_member(
        chat_id=query.message.chat.id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        ),
    )

    await query.edit_message_text(
        f"✅ User {user_id} unmuted."
    )


def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.CaptionRegex(".*"),
            check_message,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            unmute_callback,
            pattern="^unmute:"
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
