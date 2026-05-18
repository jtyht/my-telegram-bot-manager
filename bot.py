import logging
import json
import os
from datetime import datetime
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ChatMemberHandler, CallbackQueryHandler
)
from telegram.constants import ChatMemberStatus
import data_manager as dm

# ─── CHANNEL CONFIG ──────────────────────────────────────────────────────────
REQUIRED_CHANNEL = "@Oencommunity"
CHANNEL_LINK = "https://t.me/Oencommunity"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── HELPERS ────────────────────────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

async def is_member_of_channel(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """User চ্যানেলের member কিনা চেক করে"""
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER
        ]
    except:
        return False

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Channel membership চেক করে, না থাকলে join করতে বলে"""
    user = update.effective_user
    if await is_member_of_channel(user.id, context):
        return True

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 চ্যানেল Join করুন", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Join করেছি — Verify করুন", callback_data="check_membership")]
    ])
    text = (
        f"👋 হ্যালো {user.mention_html()}!\n\n"
        f"🚫 Bot ব্যবহার করতে হলে আমাদের চ্যানেলে Join করতে হবে।\n\n"
        f"👇 নিচের বাটনে ক্লিক করে Join করুন, তারপর Verify করুন।"
    )
    if update.message:
        await update.message.reply_html(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    return False

async def membership_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify button callback"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if await is_member_of_channel(user.id, context):
        await query.message.edit_text(
            f"✅ {user.mention_html()}, আপনি সফলভাবে চ্যানেলে Join করেছেন!\n\n"
            f"এখন Bot ব্যবহার করতে পারবেন। /help দিয়ে সব কমান্ড দেখুন। 🎉",
            parse_mode="HTML"
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 চ্যানেল Join করুন", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Join করেছি — Verify করুন", callback_data="check_membership")]
        ])
        await query.message.edit_text(
            f"❌ {user.mention_html()}, আপনি এখনো চ্যানেলে Join করেননি!\n\n"
            f"👇 আগে Join করুন, তারপর আবার Verify করুন।",
            parse_mode="HTML",
            reply_markup=keyboard
        )

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply থেকে বা username থেকে user বের করে"""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        try:
            username = context.args[0].lstrip("@")
            chat_member = await context.bot.get_chat_member(
                update.effective_chat.id, f"@{username}"
            )
            return chat_member.user
        except:
            pass
    return None

# ─── WELCOME / LEAVE ────────────────────────────────────────────────────────

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        welcome_text = settings.get(
            "welcome_message",
            "👋 স্বাগতম {name}! আমাদের গ্রুপে আপনাকে স্বাগত জানাই।\n/rules টাইপ করে গ্রুপের নিয়মকানুন দেখুন।"
        )
        text = welcome_text.replace("{name}", member.mention_html())
        text = text.replace("{group}", update.effective_chat.title or "")
        await update.message.reply_html(text)

async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    member = update.message.left_chat_member
    if member and not member.is_bot:
        leave_text = settings.get(
            "leave_message",
            "👋 {name} আমাদের গ্রুপ ছেড়ে গেছেন। শুভ বিদায়!"
        )
        text = leave_text.replace("{name}", member.mention_html())
        await update.message.reply_html(text)

# ─── SET WELCOME / LEAVE MESSAGES ───────────────────────────────────────────

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text(
            "📝 ব্যবহার: /setwelcome <message>\n\n"
            "Variables:\n"
            "• {name} — নতুন member এর নাম\n"
            "• {group} — গ্রুপের নাম"
        )
        return
    chat_id = str(update.effective_chat.id)
    msg = " ".join(context.args)
    dm.update_setting(chat_id, "welcome_message", msg)
    await update.message.reply_text("✅ Welcome message সেট হয়েছে!")

async def set_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /setleave <message>\n\nVariables: {name}")
        return
    chat_id = str(update.effective_chat.id)
    msg = " ".join(context.args)
    dm.update_setting(chat_id, "leave_message", msg)
    await update.message.reply_text("✅ Leave message সেট হয়েছে!")

# ─── WARN / BAN / MUTE ──────────────────────────────────────────────────────

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return

    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /warn @username দিন।")
        return

    chat_id = str(update.effective_chat.id)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "কোনো কারণ উল্লেখ নেই"
    if update.message.reply_to_message:
        reason = " ".join(context.args) if context.args else "কোনো কারণ উল্লেখ নেই"

    warns = dm.add_warn(chat_id, str(target.id))
    max_warns = dm.get_settings(chat_id).get("max_warns", 3)

    text = (
        f"⚠️ <b>Warning!</b>\n"
        f"👤 User: {target.mention_html()}\n"
        f"📌 কারণ: {reason}\n"
        f"🔢 Warning: {warns}/{max_warns}"
    )

    if warns >= max_warns:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        dm.clear_warns(chat_id, str(target.id))
        text += f"\n\n🔨 {warns}টি warning পূর্ণ হয়েছে — ব্যান করা হয়েছে!"

    await update.message.reply_html(text)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /ban @username দিন।")
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"🔨 {target.mention_html()} কে ব্যান করা হয়েছে।")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /unban @username দিন।")
        return
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"✅ {target.mention_html()} কে আনব্যান করা হয়েছে।")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /kick @username দিন।")
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"👢 {target.mention_html()} কে কিক করা হয়েছে।")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /mute @username দিন।")
        return
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
    await update.message.reply_html(f"🔇 {target.mention_html()} কে মিউট করা হয়েছে।")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /unmute @username দিন।")
        return
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
    await update.message.reply_html(f"🔊 {target.mention_html()} এর মিউট তুলে নেওয়া হয়েছে।")

async def warn_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /warns @username দিন।")
        return
    chat_id = str(update.effective_chat.id)
    warns = dm.get_warns(chat_id, str(target.id))
    max_warns = dm.get_settings(chat_id).get("max_warns", 3)
    await update.message.reply_html(
        f"📋 {target.mention_html()} এর Warning: <b>{warns}/{max_warns}</b>"
    )

async def reset_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /resetwarn @username দিন।")
        return
    chat_id = str(update.effective_chat.id)
    dm.clear_warns(chat_id, str(target.id))
    await update.message.reply_html(f"✅ {target.mention_html()} এর সব warning মুছে দেওয়া হয়েছে।")

# ─── ADMIN TOOLS ────────────────────────────────────────────────────────────

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ যে message টি pin করতে চান সেটায় reply করুন।")
        return
    await context.bot.pin_chat_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.reply_text("📌 Message pin করা হয়েছে!")

async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    await context.bot.unpin_all_chat_messages(update.effective_chat.id)
    await update.message.reply_text("📌 সব pin তুলে নেওয়া হয়েছে।")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ যে message টি মুছতে চান সেটায় reply করুন।")
        return
    await context.bot.delete_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.delete()

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /promote @username দিন।")
        return
    await context.bot.promote_chat_member(
        update.effective_chat.id, target.id,
        can_delete_messages=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_invite_users=True
    )
    await update.message.reply_html(f"⬆️ {target.mention_html()} কে অ্যাডমিন করা হয়েছে।")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Reply করুন বা /demote @username দিন।")
        return
    await context.bot.promote_chat_member(
        update.effective_chat.id, target.id,
        can_delete_messages=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_invite_users=False
    )
    await update.message.reply_html(f"⬇️ {target.mention_html()} কে অ্যাডমিন থেকে সরানো হয়েছে।")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        target = update.effective_user
    chat_id = str(update.effective_chat.id)
    warns = dm.get_warns(chat_id, str(target.id))
    member = await context.bot.get_chat_member(update.effective_chat.id, target.id)
    status_map = {
        "creator": "👑 মালিক",
        "administrator": "🛡️ অ্যাডমিন",
        "member": "👤 সদস্য",
        "restricted": "🔇 রেস্ট্রিক্টেড",
        "left": "🚶 চলে গেছে",
        "kicked": "🔨 ব্যান"
    }
    status = status_map.get(member.status, member.status)
    text = (
        f"👤 <b>User Info</b>\n\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"📛 নাম: {target.mention_html()}\n"
        f"🔖 Username: @{target.username or 'নেই'}\n"
        f"📊 Status: {status}\n"
        f"⚠️ Warnings: {warns}"
    )
    await update.message.reply_html(text)

# ─── BAD WORD FILTER ────────────────────────────────────────────────────────

async def check_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    bad_words = settings.get("bad_words", [])

    msg_lower = update.message.text.lower()
    for word in bad_words:
        if word.lower() in msg_lower:
            await update.message.delete()
            warns = dm.add_warn(chat_id, str(update.effective_user.id))
            max_warns = settings.get("max_warns", 3)
            await update.message.reply_html(
                f"🚫 {update.effective_user.mention_html()}, নিষিদ্ধ শব্দ ব্যবহার করা যাবে না!\n"
                f"⚠️ Warning: {warns}/{max_warns}"
            )
            if warns >= max_warns:
                await context.bot.ban_chat_member(update.effective_chat.id, update.effective_user.id)
                dm.clear_warns(chat_id, str(update.effective_user.id))
            return

async def add_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /addbadword <word1> <word2> ...")
        return
    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    bad_words = settings.get("bad_words", [])
    added = []
    for word in context.args:
        if word.lower() not in bad_words:
            bad_words.append(word.lower())
            added.append(word)
    dm.update_setting(chat_id, "bad_words", bad_words)
    await update.message.reply_text(f"✅ Bad word যোগ হয়েছে: {', '.join(added)}")

async def remove_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /rmbadword <word>")
        return
    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    bad_words = settings.get("bad_words", [])
    word = context.args[0].lower()
    if word in bad_words:
        bad_words.remove(word)
        dm.update_setting(chat_id, "bad_words", bad_words)
        await update.message.reply_text(f"✅ '{word}' সরিয়ে দেওয়া হয়েছে।")
    else:
        await update.message.reply_text(f"❌ '{word}' তালিকায় নেই।")

async def list_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    chat_id = str(update.effective_chat.id)
    bad_words = dm.get_settings(chat_id).get("bad_words", [])
    if not bad_words:
        await update.message.reply_text("📋 কোনো bad word নেই।")
        return
    await update.message.reply_text("📋 Bad words:\n" + "\n".join(f"• {w}" for w in bad_words))

# ─── ANTI-LINK ──────────────────────────────────────────────────────────────

async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    if not settings.get("antilink", False):
        return

    text = update.message.text
    link_patterns = ["http://", "https://", "t.me/", "www.", ".com", ".net", ".org"]
    has_link = any(p in text.lower() for p in link_patterns)
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type in ["url", "text_link"]:
                has_link = True
                break

    if has_link:
        await update.message.delete()
        warns = dm.add_warn(chat_id, str(update.effective_user.id))
        max_warns = settings.get("max_warns", 3)
        await context.bot.send_message(
            update.effective_chat.id,
            f"🔗 {update.effective_user.mention_html()}, লিংক পাঠানো নিষিদ্ধ!\n"
            f"⚠️ Warning: {warns}/{max_warns}",
            parse_mode="HTML"
        )
        if warns >= max_warns:
            await context.bot.ban_chat_member(update.effective_chat.id, update.effective_user.id)
            dm.clear_warns(chat_id, str(update.effective_user.id))

async def toggle_antilink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    chat_id = str(update.effective_chat.id)
    current = dm.get_settings(chat_id).get("antilink", False)
    dm.update_setting(chat_id, "antilink", not current)
    status = "✅ চালু" if not current else "❌ বন্ধ"
    await update.message.reply_text(f"🔗 Anti-link {status} করা হয়েছে।")

# ─── ANTI-SPAM (FLOOD) ──────────────────────────────────────────────────────

async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    settings = dm.get_settings(chat_id)

    if not settings.get("antiflood", False):
        return

    flood_limit = settings.get("flood_limit", 5)
    flood_count = dm.increment_flood(chat_id, user_id)

    if flood_count >= flood_limit:
        perms = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(update.effective_chat.id, int(user_id), perms)
        dm.reset_flood(chat_id, user_id)
        await update.message.reply_html(
            f"🌊 {update.effective_user.mention_html()}, অনেক বেশি message করছেন! 5 মিনিটের জন্য মিউট।"
        )

async def toggle_antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    chat_id = str(update.effective_chat.id)
    current = dm.get_settings(chat_id).get("antiflood", False)
    dm.update_setting(chat_id, "antiflood", not current)
    status = "✅ চালু" if not current else "❌ বন্ধ"
    await update.message.reply_text(f"🌊 Anti-flood {status} করা হয়েছে।")

# ─── RULES ──────────────────────────────────────────────────────────────────

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    rules = dm.get_settings(chat_id).get("rules", None)
    if not rules:
        await update.message.reply_text(
            "📋 এই গ্রুপে এখনো কোনো নিয়ম সেট করা হয়নি।\n"
            "অ্যাডমিন /setrules দিয়ে নিয়ম সেট করতে পারবেন।"
        )
        return
    await update.message.reply_html(f"📋 <b>গ্রুপের নিয়মকানুন:</b>\n\n{rules}")

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /setrules <নিয়মগুলো লিখুন>")
        return
    chat_id = str(update.effective_chat.id)
    rules = " ".join(context.args)
    dm.update_setting(chat_id, "rules", rules)
    await update.message.reply_text("✅ গ্রুপের নিয়ম সেট হয়েছে!")

# ─── BROADCAST ──────────────────────────────────────────────────────────────

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /broadcast <message>")
        return
    msg = " ".join(context.args)
    await update.message.reply_html(
        f"📢 <b>Broadcast Message:</b>\n\n{msg}"
    )

# ─── HELP ───────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🤖 <b>Group Management Bot — সকল কমান্ড</b>

<b>👋 Welcome/Leave</b>
/setwelcome — Welcome message সেট করুন
/setleave — Leave message সেট করুন

<b>⚠️ Warn সিস্টেম</b>
/warn — User কে warn করুন (reply করে)
/warns — কতটি warn আছে দেখুন
/resetwarn — Warn রিসেট করুন

<b>🔨 Ban/Kick/Mute</b>
/ban — User ব্যান করুন
/unban — ব্যান তুলুন
/kick — User কিক করুন
/mute — User মিউট করুন
/unmute — মিউট তুলুন

<b>🛡️ Admin Tools</b>
/promote — অ্যাডমিন করুন
/demote — অ্যাডমিন থেকে সরান
/pin — Message pin করুন (reply করে)
/unpin — সব pin তুলুন
/del — Message মুছুন (reply করে)
/info — User তথ্য দেখুন

<b>🚫 Anti-spam/Link</b>
/antilink — Anti-link চালু/বন্ধ
/antiflood — Anti-flood চালু/বন্ধ
/addbadword — Bad word যোগ করুন
/rmbadword — Bad word সরান
/badwords — Bad word তালিকা

<b>📋 Rules/Broadcast</b>
/rules — গ্রুপের নিয়ম দেখুন
/setrules — নিয়ম সেট করুন
/broadcast — সবাইকে message পাঠান
"""
    await update.message.reply_html(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Channel membership চেক
    if not await is_member_of_channel(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 চ্যানেল Join করুন", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Join করেছি — Verify করুন", callback_data="check_membership")]
        ])
        await update.message.reply_html(
            f"👋 হ্যালো {user.mention_html()}! আমি <b>Group Management Bot</b>।\n\n"
            f"🚫 Bot ব্যবহার করতে হলে আমাদের Official চ্যানেলে Join করতে হবে।\n\n"
            f"👇 নিচের বাটনে ক্লিক করে Join করুন, তারপর Verify করুন।",
            reply_markup=keyboard
        )
        return

    # Channel member হলে স্বাগত বার্তা
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 আমাদের চ্যানেল", url=CHANNEL_LINK)]
    ])
    await update.message.reply_html(
        f"👋 স্বাগতম {user.mention_html()}! আমি <b>Group Management Bot</b>!\n\n"
        f"✅ আপনি আমাদের চ্যানেলের সদস্য।\n\n"
        f"আমাকে গ্রুপে অ্যাডমিন করুন এবং /help দিয়ে সব কমান্ড দেখুন।",
        reply_markup=keyboard
    )

# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    TOKEN = os.environ.get("BOT_TOKEN", "8702706418:AAHQ37uqiSRrRcTzbNFeTT5kNbcOjKPqxwE")
    app = Application.builder().token(TOKEN).build()

    # Start & Help
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(membership_verify_callback, pattern="^check_membership$"))

    # Welcome/Leave
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setleave", set_leave))

    # Warn/Ban/Mute
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("warns", warn_list))
    app.add_handler(CommandHandler("resetwarn", reset_warns))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))

    # Admin Tools
    app.add_handler(CommandHandler("promote", promote_user))
    app.add_handler(CommandHandler("demote", demote_user))
    app.add_handler(CommandHandler("pin", pin_message))
    app.add_handler(CommandHandler("unpin", unpin_message))
    app.add_handler(CommandHandler("del", delete_message))
    app.add_handler(CommandHandler("info", user_info))

    # Bad words
    app.add_handler(CommandHandler("addbadword", add_bad_word))
    app.add_handler(CommandHandler("rmbadword", remove_bad_word))
    app.add_handler(CommandHandler("badwords", list_bad_words))

    # Anti-link/flood toggles
    app.add_handler(CommandHandler("antilink", toggle_antilink))
    app.add_handler(CommandHandler("antiflood", toggle_antiflood))

    # Rules & Broadcast
    app.add_handler(CommandHandler("rules", show_rules))
    app.add_handler(CommandHandler("setrules", set_rules))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Auto message filter (bad words, links, flood) — order matters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_bad_words))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_links))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_flood))

    print("✅ Bot চালু হয়েছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
