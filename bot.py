import os
import sys
import logging
import datetime
import calendar
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable with better error handling
def get_token():
    """Get bot token from environment variables with fallbacks."""
    token = os.environ.get('BOT_TOKEN')
    if not token:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ No BOT_TOKEN found in environment variables!")
        logger.error("Please add BOT_TOKEN to your Railway Variables.")
        logger.error("If you're testing locally, create a .env file.")
        sys.exit(1)
    return token

TOKEN = get_token()
logger.info("✅ Bot token loaded successfully!")

# Store user's selected date
user_selections = {}

# Calendar months in English
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def build_calendar(year: int, month: int, selected_day: int = None):
    """
    Build an inline keyboard for a specific month/year.
    Returns (keyboard, month_name)
    """
    # Get month info
    cal = calendar.monthcalendar(year, month)
    month_name = f"{MONTHS[month-1]} {year}"
    
    # Build keyboard
    keyboard = []
    
    # Header row with month/year and navigation
    nav_row = [
        InlineKeyboardButton("◀️", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(f"{month_name}", callback_data="cal_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"cal_next_{year}_{month}")
    ]
    keyboard.append(nav_row)
    
    # Day names row
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_row = [InlineKeyboardButton(day, callback_data="cal_ignore") for day in day_names]
    keyboard.append(day_row)
    
    # Calendar days
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                # Highlight selected day
                if selected_day == day:
                    week_row.append(InlineKeyboardButton(f"✅{day}", callback_data=f"cal_select_{year}_{month}_{day}"))
                else:
                    week_row.append(InlineKeyboardButton(str(day), callback_data=f"cal_select_{year}_{month}_{day}"))
        keyboard.append(week_row)
    
    # Today button
    today = datetime.date.today()
    keyboard.append([
        InlineKeyboardButton("📅 Today", callback_data=f"cal_today"),
        InlineKeyboardButton("❌ Close", callback_data="cal_close")
    ])
    
    return InlineKeyboardMarkup(keyboard), month_name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    user = update.effective_user
    welcome_text = f"""
📅 **Welcome to CalGeneratorBot, {user.first_name}!**

I can help you select dates easily.

**Commands:**
/calendar - Open interactive calendar
/help - Show this help message
/my_date - Show your last selected date

**Features:**
• Interactive month/year navigation
• Select any date
• Get date in multiple formats
• Shows weekday/weekend status

Just click /calendar to get started!
"""
    await update.message.reply_text(welcome_text)


async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the interactive calendar for the user."""
    user_id = update.effective_user.id
    
    # Default to current month/year
    today = datetime.date.today()
    year, month = today.year, today.month
    
    # Build calendar
    keyboard, month_name = build_calendar(year, month)
    
    await update.message.reply_text(
        f"📅 **Select a date:**\n\n{month_name}",
        reply_markup=keyboard
    )


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user's selections on the inline calendar."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Extract data
    parts = data.split('_')
    action = parts[0]
    
    if action == "cal_ignore":
        # Ignore clicks on non-interactive buttons
        return
    
    elif action == "cal_close":
        # Close the calendar
        await query.edit_message_text("❌ Calendar closed.")
        return
    
    elif action == "cal_today":
        # Select today's date
        today = datetime.date.today()
        user_selections[user_id] = today
        await query.edit_message_text(
            f"✅ **You selected: {today.strftime('%Y-%m-%d')}**\n\n"
            f"📅 Day: {today.strftime('%A')}\n"
            f"📆 Date: {today.strftime('%B %d, %Y')}"
        )
        return
    
    elif action == "cal_select":
        # User selected a specific day
        year = int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
        
        selected_date = datetime.date(year, month, day)
        user_selections[user_id] = selected_date
        
        # Format the response
        day_name = selected_date.strftime('%A')
        month_name = selected_date.strftime('%B')
        date_formatted = selected_date.strftime('%Y-%m-%d')
        
        # Check if it's a weekend
        is_weekend = selected_date.weekday() >= 5  # 5=Saturday, 6=Sunday
        
        response = f"""
✅ **You selected: {date_formatted}**

📅 Day: {day_name}
📆 Date: {month_name} {day}, {year}
{'🔴 Weekend' if is_weekend else '🟢 Weekday'}

**In other formats:**
• DD/MM/YYYY: {selected_date.strftime('%d/%m/%Y')}
• MM/DD/YYYY: {selected_date.strftime('%m/%d/%Y')}
• Full: {selected_date.strftime('%A, %B %d, %Y')}
"""
        await query.edit_message_text(response)
        return
    
    elif action == "cal_prev":
        # Navigate to previous month
        year = int(parts[1])
        month = int(parts[2])
        
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        
        # Rebuild calendar
        keyboard, month_name = build_calendar(year, month)
        await query.edit_message_text(
            f"📅 **Select a date:**\n\n{month_name}",
            reply_markup=keyboard
        )
        return
    
    elif action == "cal_next":
        # Navigate to next month
        year = int(parts[1])
        month = int(parts[2])
        
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        
        # Rebuild calendar
        keyboard, month_name = build_calendar(year, month)
        await query.edit_message_text(
            f"📅 **Select a date:**\n\n{month_name}",
            reply_markup=keyboard
        )
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    help_text = """
📖 **How to use CalGeneratorBot:**

1️⃣ Type /calendar to open the interactive calendar
2️⃣ Use ◀️ and ▶️ to navigate between months
3️⃣ Click on any day to select it
4️⃣ Get the date in multiple formats!

**Commands:**
/start - Welcome message
/calendar - Open the date picker
/my_date - Show your last selected date
/help - Show this help message

**Features:**
• Interactive month/year navigation
• Auto-highlights selected dates
• Shows day of week, weekend/weekday status
• Multiple date formats
• "Today" button for quick selection

💡 **Tip:** Your selected date is saved for future reference!
"""
    await update.message.reply_text(help_text)


async def my_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's last selected date."""
    user_id = update.effective_user.id
    
    if user_id in user_selections:
        selected_date = user_selections[user_id]
        await update.message.reply_text(
            f"📅 Your last selected date was: **{selected_date.strftime('%Y-%m-%d')}**\n"
            f"({selected_date.strftime('%A, %B %d, %Y')})"
        )
    else:
        await update.message.reply_text(
            "You haven't selected any date yet.\n"
            "Use /calendar to pick a date!"
        )


def main() -> None:
    """Start the bot."""
    try:
        # Create Application
        application = Application.builder().token(TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("calendar", calendar_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("my_date", my_date))
        
        # Add callback handler for calendar button presses
        application.add_handler(CallbackQueryHandler(calendar_callback))
        
        # Start the Bot
        logger.info("🚀 CalGeneratorBot started successfully!")
        logger.info("📅 Press Ctrl+C to stop.")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
