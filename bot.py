import sys
import asyncio
import os
import random
import sqlite3
from datetime import datetime

# --- FIX FOR EVENT LOOP ERROR ---
# This must be run before importing pyrogram
if sys.version_info >= (3, 10):
    try:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    except:
        pass

from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, 
    Message, CallbackQuery
)

# --- CONFIGURATION ---
API_ID = 37502609
API_HASH = "cd4e39a4344aad8946b904292abbdf14"
BOT_TOKEN = "8211174189:AAHPSlr9tjlxYARlaTkz78EqIOpZILi2cgc"
ADMIN_ID = 6068463116

# --- DATABASE SETUP ---
DB_NAME = "anonymous_chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            age INTEGER,
            hobby TEXT,
            bio TEXT,
            photo_file_id TEXT,
            is_banned INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pairs (
            user1 INTEGER,
            user2 INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- BOT CLIENT ---
app = Client("anon_chat_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- HELPER FUNCTIONS ---
def get_db_connection():
    return sqlite3.connect(DB_NAME)

def is_user_banned(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def get_user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, age, hobby, bio, photo_file_id FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

def save_user_profile(user_id, **kwargs):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, joined_date) VALUES (?, ?)", (user_id, str(datetime.now())))
    
    for key, value in kwargs.items():
        cursor.execute(f"UPDATE users SET {key}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def add_to_queue(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO queue (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_from_queue(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM queue WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_partner(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user1, user2 FROM pairs WHERE user1=? OR user2=?", (user_id, user_id))
    res = cursor.fetchone()
    conn.close()
    if res:
        return res[1] if res[0] == user_id else res[0]
    return None

def create_pair(user1_id, user2_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pairs (user1, user2) VALUES (?, ?)", (user1_id, user2_id))
    cursor.execute("DELETE FROM queue WHERE user_id IN (?, ?)", (user1_id, user2_id))
    conn.commit()
    conn.close()

def delete_pair(user_id):
    partner_id = get_partner(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pairs WHERE user1=? OR user2=?", (user_id, user_id))
    conn.commit()
    conn.close()
    return partner_id

# --- KEYBOARDS ---
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🔍 Find Partner", "👤 My Profile"],
        ["✏️ Setup Profile", "🛑 Stop Chat"]
    ],
    resize_keyboard=True
)

PROFILE_MENU = ReplyKeyboardMarkup(
    [
        ["🖼 Set Photo", "✏️ Set Username"],
        ["🎂 Set Age", "🎯 Set Hobby"],
        ["📝 Set Bio", "🔙 Back"]
    ],
    resize_keyboard=True
)

ADMIN_PANEL = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_prompt")],
        [InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_prompt")]
    ]
)

# --- STATES MANAGEMENT ---
user_states = {}

# --- HANDLERS ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    user_id = message.from_user.id
    save_user_profile(user_id, username=message.from_user.first_name)
    
    if user_id == ADMIN_ID:
        await message.reply("Welcome Admin!\nUser Count Control Panel:", reply_markup=ADMIN_PANEL)
    
    await message.reply(
        "Welcome to **Anonymous Chat Bot**!\n"
        "Your identity is safe here.\n\n"
        "Use the menu below to find a partner or setup your profile.",
        reply_markup=MAIN_MENU
    )

@app.on_message(filters.private & filters.text("🔙 Back"))
async def back_to_main(client, message):
    user_states[message.from_user.id] = None
    await message.reply("Main Menu", reply_markup=MAIN_MENU)

# --- PROFILE SYSTEM ---
@app.on_message(filters.private & filters.text("✏️ Setup Profile"))
async def setup_profile_menu(client, message):
    await message.reply("Profile Settings:", reply_markup=PROFILE_MENU)

@app.on_message(filters.private & filters.text("🖼 Set Photo"))
async def ask_photo(client, message):
    user_states[message.from_user.id] = "set_photo"
    await message.reply("Send me your Display Picture.")

@app.on_message(filters.private & filters.text("✏️ Set Username"))
async def ask_username(client, message):
    user_states[message.from_user.id] = "set_username"
    await message.reply("Send me the Username you want to display.")

@app.on_message(filters.private & filters.text("🎂 Set Age"))
async def ask_age(client, message):
    user_states[message.from_user.id] = "set_age"
    await message.reply("Send me your Age (Numbers only).")

@app.on_message(filters.private & filters.text("🎯 Set Hobby"))
async def ask_hobby(client, message):
    user_states[message.from_user.id] = "set_hobby"
    await message.reply("Send me your Hobby.")

@app.on_message(filters.private & filters.text("📝 Set Bio"))
async def ask_bio(client, message):
    user_states[message.from_user.id] = "set_bio"
    await message.reply("Send me a short Bio about yourself.")

@app.on_message(filters.private & filters.photo)
async def handle_photo(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if state == "set_photo":
        file_id = message.photo.file_id
        save_user_profile(user_id, photo_file_id=file_id)
        user_states[user_id] = None
        await message.reply("Profile Photo updated!")
    else:
        partner_id = get_partner(user_id)
        if partner_id:
            await client.send_photo(partner_id, message.photo.file_id)
        else:
            await message.reply("You are not in a chat. Use Setup Profile to set your DP.")

@app.on_message(filters.private & filters.text)
async def handle_text_inputs(client, message):
    user_id = message.from_user.id
    text = message.text
    state = user_states.get(user_id)

    if state == "set_username":
        save_user_profile(user_id, username=text)
        user_states[user_id] = None
        await message.reply(f"Username set to: {text}")
    elif state == "set_age":
        if text.isdigit():
            save_user_profile(user_id, age=int(text))
            user_states[user_id] = None
            await message.reply(f"Age set to: {text}")
        else:
            await message.reply("Age must be a number.")
    elif state == "set_hobby":
        save_user_profile(user_id, hobby=text)
        user_states[user_id] = None
        await message.reply(f"Hobby set to: {text}")
    elif state == "set_bio":
        save_user_profile(user_id, bio=text)
        user_states[user_id] = None
        await message.reply("Bio updated!")
    
    elif text == "👤 My Profile":
        data = get_user_profile(user_id)
        if not data:
            await message.reply("Profile not found. Please setup your profile.")
            return
        
        username, age, hobby, bio, photo_id = data
        caption = (
            f"**👤 User Profile**\n\n"
            f"**Name:** {username or 'Not Set'}\n"
            f"**Age:** {age or 'Not Set'}\n"
            f"**Hobby:** {hobby or 'Not Set'}\n"
            f"**Bio:** {bio or 'Not Set'}"
        )
        if photo_id:
            await client.send_photo(user_id, photo_id, caption=caption)
        else:
            await message.reply(caption)

    elif text == "🔍 Find Partner":
        if is_user_banned(user_id):
            await message.reply("You are banned from using this bot.")
            return

        partner = get_partner(user_id)
        if partner:
            await message.reply("You are already in a chat! Type /stop to end it.")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM queue WHERE user_id != ? LIMIT 1", (user_id,))
        waiting_user = cursor.fetchone()
        conn.close()

        if waiting_user:
            partner_id = waiting_user[0]
            remove_from_queue(partner_id)
            create_pair(user_id, partner_id)
            
            await message.reply("Partner found! Say Hi. (Send /stop to end chat)")
            await client.send_message(partner_id, "Partner found! Say Hi. (Send /stop to end chat)")
        else:
            add_to_queue(user_id)
            await message.reply("Searching for a partner... Please wait.")

    elif text == "🛑 Stop Chat" or text == "/stop":
        partner_id = delete_pair(user_id)
        if partner_id:
            await message.reply("Chat ended. You left the conversation.", reply_markup=MAIN_MENU)
            await client.send_message(partner_id, "Partner left the chat. Use /start to find new one.")
        else:
            remove_from_queue(user_id)
            await message.reply("You are not in a chat.", reply_markup=MAIN_MENU)
    
    elif get_partner(user_id) and not state:
        partner_id = get_partner(user_id)
        await client.send_message(partner_id, text)

# --- ADMIN PANEL LOGIC ---
@app.on_callback_query(filters.regex("admin_"))
async def admin_callback(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if user_id != ADMIN_ID:
        await callback_query.answer("You are not admin!", show_alert=True)
        return

    if data == "admin_stats":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pairs")
        active_chats = cursor.fetchone()[0]
        conn.close()
        
        await callback_query.message.edit_text(
            f"📊 **Bot Statistics**\n\nTotal Users: {total_users}\nActive Chats: {active_chats}",
            reply_markup=ADMIN_PANEL
        )
    
    elif data == "admin_broadcast":
        user_states[user_id] = "admin_broadcast"
        await callback_query.message.reply("Send me the message to broadcast to all users.")
    
    elif data == "admin_ban_prompt":
        user_states[user_id] = "admin_ban"
        await callback_query.message.reply("Send me the User ID to ban.")
    
    elif data == "admin_unban_prompt":
        user_states[user_id] = "admin_unban"
        await callback_query.message.reply("Send me the User ID to unban.")

@app.on_message(filters.private & filters.user(ADMIN_ID))
async def handle_admin_actions(client, message):
    admin_id = message.from_user.id
    state = user_states.get(admin_id)

    if state == "admin_broadcast":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        
        count = 0
        for (uid,) in users:
            try:
                await client.forward_messages(uid, admin_id, message.id)
                count += 1
                await asyncio.sleep(0.1)
            except Exception:
                continue
        
        user_states[admin_id] = None
        await message.reply(f"Broadcast complete! Sent to {count} users.")

    elif state == "admin_ban":
        if message.text.isdigit():
            target_id = int(message.text)
            save_user_profile(target_id, is_banned=1)
            await message.reply(f"User {target_id} has been banned.")
        else:
            await message.reply("Invalid ID.")
        user_states[admin_id] = None

    elif state == "admin_unban":
        if message.text.isdigit():
            target_id = int(message.text)
            save_user_profile(target_id, is_banned=0)
            await message.reply(f"User {target_id} has been unbanned.")
        else:
            await message.reply("Invalid ID.")
        user_states[admin_id] = None

print("Bot is running...")
app.run()
