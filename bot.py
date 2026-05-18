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
    """Check if user is a member of the channel"""
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
    """Check channel membership, prompt to join if not a member"""
    user = update.effective_user
    if await is_member_of_channel(user.id, context):
        return True

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined — Verify", callback_data="check_membership")]
    ])
    text = (
        f"👋 Hello {user.mention_html()}!\n\n"
        f"🚫 You must join our channel to use this bot.\n\n"
        f"👇 Click the button below to join, then verify."
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
            f"✅ {user.mention_html()}, you have successfully joined the channel!\n\n"
            f"You can now use the bot. Type /help to see all commands. 🎉",
            parse_mode="HTML"
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I've Joined — Verify", callback_data="check_membership")]
        ])
        await query.message.edit_text(
            f"❌ {user.mention_html()}, you have not joined the channel yet!\n\n"
            f"👇 Please join first, then verify again.",
            parse_mode="HTML",
            reply_markup=keyboard
        )

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user from reply or username"""
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
            "👋 Welcome {name}! We're glad to have you in our group.\nType /rules to see the group rules."
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
            "👋 {name} has left the group. Goodbye!"
        )
        text = leave_text.replace("{name}", member.mention_html())
        await update.message.reply_html(text)

# ─── SET WELCOME / LEAVE MESSAGES ───────────────────────────────────────────

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text(
            "📝 Usage: /setwelcome <message>\n\n"
            "Variables:\n"
            "• {name} — new member's name\n"
            "• {group} — group name"
        )
        return
    chat_id = str(update.effective_chat.id)
    msg = " ".join(context.args)
    dm.update_setting(chat_id, "welcome_message", msg)
    await update.message.reply_text("✅ Welcome message has been set!")

async def set_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("📝 Usage: /setleave <message>\n\nVariables: {name}")
        return
    chat_id = str(update.effective_chat.id)
    msg = " ".join(context.args)
    dm.update_setting(chat_id, "leave_message", msg)
    await update.message.reply_text("✅ Leave message has been set!")

# ─── WARN / BAN / MUTE ──────────────────────────────────────────────────────

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /warn @username.")
        return

    chat_id = str(update.effective_chat.id)
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason provided"
    if update.message.reply_to_message:
        reason = " ".join(context.args) if context.args else "No reason provided"

    warns = dm.add_warn(chat_id, str(target.id))
    max_warns = dm.get_settings(chat_id).get("max_warns", 3)

    text = (
        f"⚠️ <b>Warning!</b>\n"
        f"👤 User: {target.mention_html()}\n"
        f"📌 Reason: {reason}\n"
        f"🔢 Warnings: {warns}/{max_warns}"
    )

    if warns >= max_warns:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        dm.clear_warns(chat_id, str(target.id))
        text += f"\n\n🔨 {warns} warnings reached — user has been banned!"

    await update.message.reply_html(text)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /ban @username.")
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"🔨 {target.mention_html()} has been banned.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /unban @username.")
        return
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"✅ {target.mention_html()} has been unbanned.")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /kick @username.")
        return
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_html(f"👢 {target.mention_html()} has been kicked.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /mute @username.")
        return
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
    await update.message.reply_html(f"🔇 {target.mention_html()} has been muted.")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /unmute @username.")
        return
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, perms)
    await update.message.reply_html(f"🔊 {target.mention_html()} has been unmuted.")

async def warn_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /warns @username.")
        return
    chat_id = str(update.effective_chat.id)
    warns = dm.get_warns(chat_id, str(target.id))
    max_warns = dm.get_settings(chat_id).get("max_warns", 3)
    await update.message.reply_html(
        f"📋 {target.mention_html()} Warnings: <b>{warns}/{max_warns}</b>"
    )

async def reset_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /resetwarn @username.")
        return
    chat_id = str(update.effective_chat.id)
    dm.clear_warns(chat_id, str(target.id))
    await update.message.reply_html(f"✅ All warnings for {target.mention_html()} have been cleared.")

# ─── ADMIN TOOLS ────────────────────────────────────────────────────────────

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the message you want to pin.")
        return
    await context.bot.pin_chat_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.reply_text("📌 Message has been pinned!")

async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    await context.bot.unpin_all_chat_messages(update.effective_chat.id)
    await update.message.reply_text("📌 All pinned messages have been unpinned.")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to the message you want to delete.")
        return
    await context.bot.delete_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.delete()

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /promote @username.")
        return
    await context.bot.promote_chat_member(
        update.effective_chat.id, target.id,
        can_delete_messages=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_invite_users=True
    )
    await update.message.reply_html(f"⬆️ {target.mention_html()} has been promoted to admin.")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = await get_target_user(update, context)
    if not target:
        await update.message.reply_text("⚠️ Please reply to a user or use /demote @username.")
        return
    await context.bot.promote_chat_member(
        update.effective_chat.id, target.id,
        can_delete_messages=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_invite_users=False
    )
    await update.message.reply_html(f"⬇️ {target.mention_html()} has been demoted from admin.")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target_user(update, context)
    if not target:
        target = update.effective_user
    chat_id = str(update.effective_chat.id)
    warns = dm.get_warns(chat_id, str(target.id))
    member = await context.bot.get_chat_member(update.effective_chat.id, target.id)
    status_map = {
        "creator": "👑 Owner",
        "administrator": "🛡️ Admin",
        "member": "👤 Member",
        "restricted": "🔇 Restricted",
        "left": "🚶 Left",
        "kicked": "🔨 Banned"
    }
    status = status_map.get(member.status, member.status)
    text = (
        f"👤 <b>User Info</b>\n\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"📛 Name: {target.mention_html()}\n"
        f"🔖 Username: @{target.username or 'None'}\n"
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
                f"🚫 {update.effective_user.mention_html()}, use of banned words is not allowed!\n"
                f"⚠️ Warning: {warns}/{max_warns}"
            )
            if warns >= max_warns:
                await context.bot.ban_chat_member(update.effective_chat.id, update.effective_user.id)
                dm.clear_warns(chat_id, str(update.effective_user.id))
            return

async def add_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("📝 Usage: /addbadword <word1> <word2> ...")
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
    await update.message.reply_text(f"✅ Bad word(s) added: {', '.join(added)}")

async def remove_bad_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("📝 Usage: /rmbadword <word>")
        return
    chat_id = str(update.effective_chat.id)
    settings = dm.get_settings(chat_id)
    bad_words = settings.get("bad_words", [])
    word = context.args[0].lower()
    if word in bad_words:
        bad_words.remove(word)
        dm.update_setting(chat_id, "bad_words", bad_words)
        await update.message.reply_text(f"✅ '{word}' has been removed.")
    else:
        await update.message.reply_text(f"❌ '{word}' is not in the list.")

async def list_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    chat_id = str(update.effective_chat.id)
    bad_words = dm.get_settings(chat_id).get("bad_words", [])
    if not bad_words:
        await update.message.reply_text("📋 No bad words have been set.")
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
            f"🔗 {update.effective_user.mention_html()}, sending links is not allowed!\n"
            f"⚠️ Warning: {warns}/{max_warns}",
            parse_mode="HTML"
        )
        if warns >= max_warns:
            await context.bot.ban_chat_member(update.effective_chat.id, update.effective_user.id)
            dm.clear_warns(chat_id, str(update.effective_user.id))

async def toggle_antilink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    chat_id = str(update.effective_chat.id)
    current = dm.get_settings(chat_id).get("antilink", False)
    dm.update_setting(chat_id, "antilink", not current)
    status = "✅ Enabled" if not current else "❌ Disabled"
    await update.message.reply_text(f"🔗 Anti-link {status}.")

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
            f"🌊 {update.effective_user.mention_html()}, you are sending too many messages! Muted for 5 minutes."
        )

async def toggle_antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    chat_id = str(update.effective_chat.id)
    current = dm.get_settings(chat_id).get("antiflood", False)
    dm.update_setting(chat_id, "antiflood", not current)
    status = "✅ Enabled" if not current else "❌ Disabled"
    await update.message.reply_text(f"🌊 Anti-flood {status}.")

# ─── RULES ──────────────────────────────────────────────────────────────────

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    rules = dm.get_settings(chat_id).get("rules", None)
    if not rules:
        await update.message.reply_text(
            "📋 No rules have been set for this group yet.\n"
            "An admin can set rules using /setrules."
        )
        return
    await update.message.reply_html(f"📋 <b>Group Rules:</b>\n\n{rules}")

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("📝 Usage: /setrules <write the rules here>")
        return
    chat_id = str(update.effective_chat.id)
    rules = " ".join(context.args)
    dm.update_setting(chat_id, "rules", rules)
    await update.message.reply_text("✅ Group rules have been set!")

# ─── BROADCAST ──────────────────────────────────────────────────────────────

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("📝 Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    await update.message.reply_html(
        f"📢 <b>Broadcast Message:</b>\n\n{msg}"
    )

# ─── HELP ───────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🤖 <b>Group Management Bot — All Commands</b>

<b>👋 Welcome/Leave</b>
/setwelcome — Set welcome message
/setleave — Set leave message

<b>⚠️ Warn System</b>
/warn — Warn a user (reply to their message)
/warns — Check how many warnings a user has
/resetwarn — Reset a user's warnings

<b>🔨 Ban/Kick/Mute</b>
/ban — Ban a user
/unban — Unban a user
/kick — Kick a user
/mute — Mute a user
/unmute — Unmute a user

<b>🛡️ Admin Tools</b>
/promote — Promote to admin
/demote — Demote from admin
/pin — Pin a message (reply to it)
/unpin — Unpin all messages
/del — Delete a message (reply to it)
/info — View user info

<b>🚫 Anti-spam/Link</b>
/antilink — Toggle anti-link on/off
/antiflood — Toggle anti-flood on/off
/addbadword — Add a bad word
/rmbadword — Remove a bad word
/badwords — List bad words

<b>📋 Rules/Broadcast</b>
/rules — View group rules
/setrules — Set group rules
/broadcast — Send a message to everyone
"""
    await update.message.reply_html(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Check channel membership
    if not await is_member_of_channel(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I've Joined — Verify", callback_data="check_membership")]
        ])
        await update.message.reply_html(
            f"👋 Hello {user.mention_html()}! I am <b>Group Management Bot</b>.\n\n"
            f"🚫 You must join our official channel to use this bot.\n\n"
            f"👇 Click the button below to join, then verify.",
            reply_markup=keyboard
        )
        return

    # Welcome message for channel members
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Our Channel", url=CHANNEL_LINK)]
    ])
    await update.message.reply_html(
        f"👋 Welcome {user.mention_html()}! I am <b>Group Management Bot</b>!\n\n"
        f"✅ You are a member of our channel.\n\n"
        f"Add me to your group as an admin and type /help to see all commands.",
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

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
