import logging
import asyncio
import secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import json
import os
import html

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = "8211174189:AAHPSlr9tjlxYARlaTkz78EqIOpZILi2cgc"
ADMIN_ID = 6068463116
BOT_USERNAME = "ReferEarnSynaxBot"  # अपना बॉट यूजरनेम डालें (बिना @ के)

# Channels to verify (format: @channel_username or channel ID)
CHANNELS = [
    "@synaxbotz",
    "@synaxbotz",
    "@synaxbotz"
]

# Files storage
FILES_DATA_FILE = "files_data.json"
LINKS_DATA_FILE = "links_data.json"

# Store for files and links
files_data = {}
links_data = {}

# Initialize data files
if os.path.exists(FILES_DATA_FILE):
    with open(FILES_DATA_FILE, 'r') as f:
        files_data = json.load(f)

if os.path.exists(LINKS_DATA_FILE):
    with open(LINKS_DATA_FILE, 'r') as f:
        links_data = json.load(f)

def generate_unique_id():
    """Generate unique ID for files."""
    return secrets.token_urlsafe(8)

def generate_link_id():
    """Generate unique link ID."""
    return secrets.token_urlsafe(6)

def save_files_data():
    """Save files data to file."""
    with open(FILES_DATA_FILE, 'w') as f:
        json.dump(files_data, f)

def save_links_data():
    """Save links data to file."""
    with open(LINKS_DATA_FILE, 'w') as f:
        json.dump(links_data, f)

# Admin keyboard
def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("📝 Host Text"), KeyboardButton("📁 Host File")],
        [KeyboardButton("🔗 Generate Link"), KeyboardButton("📊 Files List")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("📋 Content Manager")],
        [KeyboardButton("📈 Stats"), KeyboardButton("❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# User keyboard
def get_user_keyboard():
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("📁 My Files"), KeyboardButton("❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    args = context.args
    
    # Check if coming from a file link
    if args and len(args) > 0:
        link_id = args[0]
        await handle_file_link(update, context, link_id)
        return
    
    # Set appropriate keyboard based on user
    if user_id == ADMIN_ID:
        reply_markup = get_admin_keyboard()
    else:
        reply_markup = get_user_keyboard()
    
    # Check if user is subscribed to all channels
    is_subscribed = await check_subscription(user_id, context)
    
    welcome_text = f"👋 Welcome {update.effective_user.first_name}!\n\n"
    
    if is_subscribed:
        welcome_text += "✅ You have access to all channels.\n"
        welcome_text += "Use the menu below to access files."
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
    else:
        welcome_text += "📋 Please join all channels to access files."
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
        await ask_for_subscription(update, context)

async def handle_file_link(update: Update, context: ContextTypes.DEFAULT_TYPE, link_id: str):
    """Handle file link access."""
    user_id = update.effective_user.id
    
    if link_id not in links_data:
        await update.message.reply_text(
            "❌ Invalid or expired link!",
            reply_markup=get_user_keyboard()
        )
        return
    
    file_id = links_data[link_id]["file_id"]
    
    if file_id not in files_data:
        await update.message.reply_text(
            "❌ File not found!",
            reply_markup=get_user_keyboard()
        )
        return
    
    # Check if user is subscribed to all channels
    is_subscribed = await check_subscription(user_id, context)
    
    if is_subscribed:
        # User is subscribed, send the file
        await send_file_to_user(update, file_id)
        
        # Track download
        files_data[file_id]["downloads"] = files_data[file_id].get("downloads", 0) + 1
        save_files_data()
        
        # Add to user's accessed files
        user_files = files_data[file_id].get("accessed_by", {})
        if str(user_id) not in user_files:
            user_files[str(user_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            files_data[file_id]["accessed_by"] = user_files
            save_files_data()
    else:
        # Ask user to subscribe first
        await update.message.reply_text(
            f"📋 <b>File Access Required!</b>\n\n"
            f"📁 File: {files_data[file_id].get('name', 'Unnamed')}\n\n"
            f"You need to join all channels first to access this file.",
            parse_mode=ParseMode.HTML
        )
        await ask_for_subscription_with_file(update, context, link_id)

async def ask_for_subscription_with_file(update: Update, context: ContextTypes.DEFAULT_TYPE, link_id: str):
    """Ask user to subscribe with file context."""
    keyboard = []
    
    # Add channel links
    for i, channel in enumerate(CHANNELS, 1):
        channel_username = channel.replace('@', '')
        keyboard.append([InlineKeyboardButton(
            f"📢 Channel {i} - {channel_username}",
            url=f"https://t.me/{channel_username}"
        )])
    
    # Add verify button with file context
    keyboard.append([InlineKeyboardButton("✅ Verify & Get File", callback_data=f"verify_file_{link_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 <b>Please join all channels to access the file:</b>\n\n"
        "1️⃣ First join all channels\n"
        "2️⃣ Then click Verify & Get File\n"
        "3️⃣ Get your file instantly\n\n"
        "⚠️ <b>Note:</b> You must join ALL channels to get access.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def ask_for_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to subscribe to channels."""
    keyboard = []
    
    # Add channel links
    for i, channel in enumerate(CHANNELS, 1):
        channel_username = channel.replace('@', '')
        keyboard.append([InlineKeyboardButton(
            f"📢 Channel {i} - {channel_username}",
            url=f"https://t.me/{channel_username}"
        )])
    
    # Add verify button
    keyboard.append([InlineKeyboardButton("✅ Verify Subscription", callback_data="verify_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 <b>Please join all channels to access files:</b>\n\n"
        "1️⃣ First join all channels\n"
        "2️⃣ Then click Verify Subscription\n"
        "3️⃣ Access all files\n\n"
        "⚠️ <b>Note:</b> You must join ALL channels to get access.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is subscribed to all channels."""
    try:
        for channel in CHANNELS:
            chat_member = await context.bot.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )
            # Check if user is member, administrator, creator, or left/kicked
            if chat_member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verify subscription button."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    if callback_data == "verify_subscription":
        is_subscribed = await check_subscription(user_id, context)
        
        if is_subscribed:
            await query.edit_message_text(
                "✅ <b>Subscription Verified!</b>\n\n"
                "Now you can access all files.\n"
                "Use /start to continue.",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                "❌ <b>You haven't joined all channels!</b>\n\n"
                "Please join ALL channels first and try again.",
                parse_mode=ParseMode.HTML
            )
            await ask_for_subscription_callback(query, context)
    
    elif callback_data.startswith("verify_file_"):
        link_id = callback_data.replace("verify_file_", "")
        
        if link_id not in links_data:
            await query.edit_message_text(
                "❌ Invalid or expired link!",
                parse_mode=ParseMode.HTML
            )
            return
        
        is_subscribed = await check_subscription(user_id, context)
        
        if is_subscribed:
            file_id = links_data[link_id]["file_id"]
            
            if file_id not in files_data:
                await query.edit_message_text(
                    "❌ File not found!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            await query.edit_message_text(
                "✅ <b>Access Granted!</b>\n\n"
                "Sending your file...",
                parse_mode=ParseMode.HTML
            )
            
            # Send the file
            await send_file_to_user_callback(query, file_id)
            
            # Track download
            files_data[file_id]["downloads"] = files_data[file_id].get("downloads", 0) + 1
            save_files_data()
            
            # Add to user's accessed files
            user_files = files_data[file_id].get("accessed_by", {})
            if str(user_id) not in user_files:
                user_files[str(user_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                files_data[file_id]["accessed_by"] = user_files
                save_files_data()
        else:
            await query.edit_message_text(
                "❌ <b>You haven't joined all channels!</b>\n\n"
                "Please join ALL channels first to get the file.",
                parse_mode=ParseMode.HTML
            )

async def ask_for_subscription_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Ask for subscription via callback."""
    keyboard = []
    
    for i, channel in enumerate(CHANNELS, 1):
        channel_username = channel.replace('@', '')
        keyboard.append([InlineKeyboardButton(
            f"📢 Channel {i} - {channel_username}",
            url=f"https://t.me/{channel_username}"
        )])
    
    keyboard.append([InlineKeyboardButton("✅ Verify Subscription", callback_data="verify_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "📋 <b>Please join all channels to access files:</b>\n\n"
        "1️⃣ First join all channels\n"
        "2️⃣ Then click Verify Subscription\n"
        "3️⃣ Access all files\n\n"
        "⚠️ <b>Note:</b> You must join ALL channels to get access.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def send_file_to_user(update: Update, file_id: str):
    """Send file to user."""
    file_data = files_data[file_id]
    
    try:
        caption_text = file_data.get("caption", "")
        safe_caption = html.escape(caption_text) if caption_text else ""
        caption = f"📁 <b>{file_data.get('name', 'File')}</b>\n\n{safe_caption}"
        
        if file_data["file_type"] == "photo":
            await update.message.reply_photo(
                photo=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "video":
            await update.message.reply_video(
                video=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "document":
            await update.message.reply_document(
                document=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "text":
            await update.message.reply_text(
                f"📝 <b>{file_data.get('name', 'Text')}</b>\n\n{safe_caption}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text(
            "❌ Error sending file. Please try again later."
        )

async def send_file_to_user_callback(query, file_id: str):
    """Send file to user via callback."""
    file_data = files_data[file_id]
    
    try:
        caption_text = file_data.get("caption", "")
        safe_caption = html.escape(caption_text) if caption_text else ""
        caption = f"📁 <b>{file_data.get('name', 'File')}</b>\n\n{safe_caption}"
        
        if file_data["file_type"] == "photo":
            await query.message.reply_photo(
                photo=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "video":
            await query.message.reply_video(
                video=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "document":
            await query.message.reply_document(
                document=file_data["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        elif file_data["file_type"] == "text":
            await query.message.reply_text(
                f"📝 <b>{file_data.get('name', 'Text')}</b>\n\n{safe_caption}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await query.message.reply_text(
            "❌ Error sending file. Please try again later."
        )

# Admin commands
async def admin_host_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to host text."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    await update.message.reply_text(
        "📝 Please send the text you want to host:\n"
        "Format: Text message (first line will be used as filename)",
        reply_markup=get_admin_keyboard()
    )
    context.user_data['awaiting_text'] = True

async def admin_host_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to host file."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    await update.message.reply_text(
        "📁 Please send a file with caption:\n"
        "Format: /host [filename] [caption]\n\n"
        "Supported files: Document, Photo, Video\n\n"
        "Example: /host MyFile.pdf This is my file",
        reply_markup=get_admin_keyboard()
    )

async def admin_generate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate link for a file."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not files_data:
        await update.message.reply_text(
            "📭 No files available to generate links.\n"
            "First host some files.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    # Create keyboard with file list
    keyboard = []
    files_list = list(files_data.items())[:10]  # Show first 10 files
    
    for file_id, file_data in files_list:
        file_name = file_data.get('name', f"File_{file_id[:6]}")
        keyboard.append([InlineKeyboardButton(
            f"📁 {file_name[:20]}",
            callback_data=f"genlink_{file_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("📋 All Files", callback_data="show_all_files")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔗 <b>Select a file to generate link:</b>\n\n"
        "Click on a file to generate its sharing link.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def admin_files_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of hosted files."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not files_data:
        await update.message.reply_text(
            "📭 No files hosted yet.",
            reply_markup=get_admin_keyboard()
        )
        return
    
    files_list_text = "📁 <b>Hosted Files:</b>\n\n"
    
    for i, (file_id, file_data) in enumerate(files_data.items(), 1):
        file_name = file_data.get('name', f"File_{i}")
        file_type = file_data.get('file_type', 'Unknown')
        date = file_data.get('date', 'Unknown')
        downloads = file_data.get('downloads', 0)
        
        files_list_text += f"{i}. <b>{file_name}</b>\n"
        files_list_text += f"   Type: {file_type} | 📥 {downloads} downloads\n"
        files_list_text += f"   Date: {date}\n\n"
    
    # Add generate link button
    keyboard = [[InlineKeyboardButton("🔗 Generate Link", callback_data="generate_link_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        files_list_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin stats."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    total_files = len(files_data)
    total_links = len(links_data)
    total_downloads = sum(file_data.get('downloads', 0) for file_data in files_data.values())
    
    stats_text = (
        f"📈 <b>Bot Statistics</b>\n\n"
        f"📊 <b>Total Files:</b> {total_files}\n"
        f"🔗 <b>Total Links:</b> {total_links}\n"
        f"📥 <b>Total Downloads:</b> {total_downloads}\n"
        f"📢 <b>Channels:</b> {len(CHANNELS)}\n\n"
        f"<b>Channel List:</b>\n"
    )
    
    for i, channel in enumerate(CHANNELS, 1):
        stats_text += f"{i}. {channel}\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard()
    )

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    await update.message.reply_text(
        "📢 Broadcast feature will be implemented soon!\n"
        "Currently under development.",
        reply_markup=get_admin_keyboard()
    )

async def admin_content_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage hosted content."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if files_data:
        keyboard = []
        
        # Add buttons for file management
        keyboard.append([InlineKeyboardButton("🗑️ Delete All Files", callback_data="delete_all_files")])
        keyboard.append([InlineKeyboardButton("🗑️ Delete All Links", callback_data="delete_all_links")])
        keyboard.append([InlineKeyboardButton("📋 View Files", callback_data="view_files_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📋 <b>Content Manager</b>\n\n"
            f"Total Files: {len(files_data)}\n"
            f"Total Links: {len(links_data)}\n\n"
            "Select an option:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📭 No content to manage.\n"
            "Host some files first.",
            reply_markup=get_admin_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Admin keyboard button handlers
    if user_id == ADMIN_ID:
        if message_text == "📝 Host Text":
            await admin_host_text(update, context)
        elif message_text == "📁 Host File":
            await admin_host_file(update, context)
        elif message_text == "🔗 Generate Link":
            await admin_generate_link(update, context)
        elif message_text == "📊 Files List":
            await admin_files_list(update, context)
        elif message_text == "📈 Stats":
            await admin_stats(update, context)
        elif message_text == "📢 Broadcast":
            await admin_broadcast(update, context)
        elif message_text == "📋 Content Manager":
            await admin_content_manager(update, context)
        elif message_text == "❓ Help":
            await help_command(update, context)
        elif context.user_data.get('awaiting_text'):
            # Handle text input for hosting
            text = message_text
            lines = text.split('\n')
            file_name = lines[0][:50] if lines[0].strip() else "Text_File"
            caption = text
            
            file_id = generate_unique_id()
            files_data[file_id] = {
                "name": file_name,
                "caption": caption,
                "file_type": "text",
                "file_id": None,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "downloads": 0,
                "accessed_by": {}
            }
            
            save_files_data()
            context.user_data['awaiting_text'] = False
            
            # Generate link automatically
            link_id = generate_link_id()
            links_data[link_id] = {
                "file_id": file_id,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "clicks": 0
            }
            save_links_data()
            
            link_url = f"https://t.me/{BOT_USERNAME}?start={link_id}"
            
            await update.message.reply_text(
                f"✅ Text hosted successfully!\n\n"
                f"📝 Name: {file_name}\n"
                f"🔗 Download Link: {link_url}\n\n"
                f"Share this link with users. They need to join channels to access.",
                reply_markup=get_admin_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "Please use the menu buttons or commands.",
                reply_markup=get_admin_keyboard()
            )
    else:
        # Regular users
        if message_text == "📁 My Files":
            await user_my_files(update, context)
        elif message_text == "❓ Help":
            await help_command(update, context)
        else:
            await update.message.reply_text(
                "Use /start to begin or ❓ Help for assistance.",
                reply_markup=get_user_keyboard()
            )

async def user_my_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's accessed files."""
    user_id = update.effective_user.id
    
    user_files = []
    for file_id, file_data in files_data.items():
        accessed_by = file_data.get("accessed_by", {})
        if str(user_id) in accessed_by:
            user_files.append((file_id, file_data))
    
    if user_files:
        files_text = "📁 <b>Your Accessed Files:</b>\n\n"
        
        for i, (file_id, file_data) in enumerate(user_files, 1):
            file_name = file_data.get('name', f"File_{i}")
            access_date = file_data.get('accessed_by', {}).get(str(user_id), "Unknown")
            
            files_text += f"{i}. <b>{file_name}</b>\n"
            files_text += f"   Accessed: {access_date}\n\n"
        
        await update.message.reply_text(
            files_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_user_keyboard()
        )
    else:
        await update.message.reply_text(
            "📭 You haven't accessed any files yet.\n"
            "Use /start and join channels to access files.",
            reply_markup=get_user_keyboard()
        )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file from admin for hosting."""
    if update.effective_user.id != ADMIN_ID:
        return
    
    message = update.message
    
    if message.caption and message.caption.startswith('/host'):
        # Parse caption: /host filename caption text
        parts = message.caption.split(' ', 2)
        
        if len(parts) < 2:
            await message.reply_text(
                "❌ Format: /host [filename] [caption]\n"
                "Example: /host MyFile.pdf This is my file",
                reply_markup=get_admin_keyboard()
            )
            return
        
        file_name = parts[1] if len(parts) > 1 else "Unnamed_File"
        caption = parts[2] if len(parts) > 2 else ""
        
        file_id = None
        file_type = None
        
        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "photo"
        elif message.video:
            file_id = message.video.file_id
            file_type = "video"
        elif message.document:
            file_id = message.document.file_id
            file_type = "document"
        else:
            await message.reply_text("❌ Unsupported file type!", reply_markup=get_admin_keyboard())
            return
        
        # Generate unique file ID
        unique_id = generate_unique_id()
        files_data[unique_id] = {
            "name": file_name,
            "caption": caption,
            "file_type": file_type,
            "file_id": file_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "downloads": 0,
            "accessed_by": {}
        }
        
        save_files_data()
        
        # Generate link automatically
        link_id = generate_link_id()
        links_data[link_id] = {
            "file_id": unique_id,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "clicks": 0
        }
        save_links_data()
        
        link_url = f"https://t.me/{BOT_USERNAME}?start={link_id}"
        
        await message.reply_text(
            f"✅ File hosted successfully!\n\n"
            f"📁 Name: {file_name}\n"
            f"📄 Type: {file_type}\n"
            f"🔗 Download Link: {link_url}\n\n"
            f"Share this link with users. They need to join channels to access.",
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.HTML
        )
    elif update.effective_user.id == ADMIN_ID:
        # Admin sent file without /host command
        await message.reply_text(
            "⚠️ To host this file, add caption: /host [filename] [caption]\n"
            "Example: /host MyFile.pdf This is my file",
            reply_markup=get_admin_keyboard()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    if callback_data.startswith("genlink_"):
        # Generate link for specific file
        file_id = callback_data.replace("genlink_", "")
        
        if file_id not in files_data:
            await query.edit_message_text("❌ File not found!")
            return
        
        # Generate link
        link_id = generate_link_id()
        links_data[link_id] = {
            "file_id": file_id,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "clicks": 0
        }
        save_links_data()
        
        file_data = files_data[file_id]
        link_url = f"https://t.me/{BOT_USERNAME}?start={link_id}"
        
        await query.edit_message_text(
            f"✅ Link generated successfully!\n\n"
            f"📁 File: {file_data.get('name', 'Unnamed')}\n"
            f"🔗 Download Link: {link_url}\n\n"
            f"Share this link with users.",
            parse_mode=ParseMode.HTML
        )
    
    elif callback_data == "generate_link_menu":
        await admin_generate_link_callback(query, context)
    
    elif callback_data == "view_files_list":
        await admin_files_list_callback(query, context)
    
    elif callback_data == "delete_all_files":
        if user_id == ADMIN_ID:
            files_data.clear()
            save_files_data()
            await query.edit_message_text("✅ All files deleted successfully!")
    
    elif callback_data == "delete_all_links":
        if user_id == ADMIN_ID:
            links_data.clear()
            save_links_data()
            await query.edit_message_text("✅ All links deleted successfully!")
    
    elif callback_data == "show_all_files":
        await show_all_files_callback(query, context)

async def admin_generate_link_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Generate link menu via callback."""
    if not files_data:
        await query.edit_message_text("📭 No files available!")
        return
    
    keyboard = []
    files_list = list(files_data.items())
    
    for file_id, file_data in files_list:
        file_name = file_data.get('name', f"File_{file_id[:6]}")
        keyboard.append([InlineKeyboardButton(
            f"📁 {file_name[:20]}",
            callback_data=f"genlink_{file_id}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 <b>Select a file to generate link:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def admin_files_list_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Show files list via callback."""
    if not files_data:
        await query.edit_message_text("📭 No files hosted yet!")
        return
    
    files_list_text = "📁 <b>Hosted Files:</b>\n\n"
    
    for i, (file_id, file_data) in enumerate(files_data.items(), 1):
        file_name = file_data.get('name', f"File_{i}")
        file_type = file_data.get('file_type', 'Unknown')
        downloads = file_data.get('downloads', 0)
        
        files_list_text += f"{i}. <b>{file_name}</b>\n"
        files_list_text += f"   Type: {file_type} | 📥 {downloads} downloads\n\n"
    
    await query.edit_message_text(
        files_list_text,
        parse_mode=ParseMode.HTML
    )

async def show_all_files_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Show all files for link generation."""
    if not files_data:
        await query.edit_message_text("📭 No files available!")
        return
    
    keyboard = []
    all_files = list(files_data.items())
    
    # Split into chunks of 5 for pagination
    chunk_size = 5
    chunks = [all_files[i:i + chunk_size] for i in range(0, len(all_files), chunk_size)]
    
    for chunk in chunks[0]:  # Show first chunk
        for file_id, file_data in chunk:
            file_name = file_data.get('name', f"File_{file_id[:6]}")
            keyboard.append([InlineKeyboardButton(
                f"📁 {file_name[:20]}",
                callback_data=f"genlink_{file_id}"
            )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 <b>Select a file to generate link:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        help_text = (
            "🤖 <b>Admin Help Menu</b>\n\n"
            "<b>Menu Buttons:</b>\n"
            "📝 Host Text - Host text messages\n"
            "📁 Host File - Host files with captions\n"
            "🔗 Generate Link - Create shareable links\n"
            "📊 Files List - View all hosted files\n"
            "📈 Stats - View bot statistics\n"
            "📋 Content Manager - Manage content\n"
            "📢 Broadcast - Broadcast messages\n\n"
            "<b>File Hosting:</b>\n"
            "Send file with caption: /host [filename] [caption]\n\n"
            "<b>Link System:</b>\n"
            "1. Host a file/text\n"
            "2. Generate link\n"
            "3. Share link with users\n"
            "4. Users join channels and get file"
        )
        reply_markup = get_admin_keyboard()
    else:
        help_text = (
            "🤖 <b>User Help</b>\n\n"
            "<b>How to get files:</b>\n"
            "1. Get a file link from admin\n"
            "2. Click the link to open bot\n"
            "3. Join all required channels\n"
            "4. Verify subscription\n"
            "5. Get your file instantly\n\n"
            "<b>Commands:</b>\n"
            "/start - Start bot\n"
            "📁 My Files - View your accessed files\n\n"
            "<b>Channels to join:</b>\n"
        )
        
        for i, channel in enumerate(CHANNELS, 1):
            help_text += f"{i}. {channel}\n"
        
        reply_markup = get_user_keyboard()
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("host_text", admin_host_text))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(verify_callback, pattern="^(verify_subscription|verify_file_)"))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add message handler for files
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.ALL, 
        handle_file
    ))
    
    # Start the Bot
    print("🤖 Bot is starting...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📢 Channels: {CHANNELS}")
    print("✅ Bot is running. Press Ctrl+C to stop.")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
