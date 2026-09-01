import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# البيانات الخاصة بك المدمجة تلقائياً
# ---------------------------------------------------------
BOT_TOKEN = "8814604397:AAFB0Pj4cUkUt3MugpVRUwkm6h5uU5W9M24"
API_KEY = "5096024d4d9345aeac50f27dff5cdf6d"
CHANNEL_ID = "@YourChannelUsername"  # ضع معرف قناتك هنا (مثال: @my_channel)

WAITING_AMOUNT, WAITING_ODDS = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# دالة سحب بيانات المباريات من الـ API
def fetch_today_matches():
    url = "https://v3.football.api-sports.io/fixtures"
    params = {'date': '2026-09-01'}  # يجلب مباريات اليوم
    headers = {'x-apisports-key': API_KEY}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if not data.get("response"):
            return "❌ لا توجد مباريات مسجلة حالياً أو انتهت طلبات الـ API اليومية."

        matches_text = "⚽ **أبرز مباريات اليوم والإحصائيات:**\n\n"
        for item in data['response'][:3]: # جلب أول 3 مباريات
            home_team = item['teams']['home']['name']
            away_team = item['teams']['away']['name']
            league = item['league']['name']
            status = item['fixture']['status']['long']
            
            matches_text += f"🏆 **{league}**\n"
            matches_text += f"⚔️ {home_team} × {away_team}\n"
            matches_text += f"📌 **الحالة:** {status}\n"
            matches_text += "───────────────\n"
            
        return matches_text
    except Exception as e:
        return f"❌ خطأ أثناء جلب البيانات: {str(e)}"

# القائمة الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📊 جلب مباريات اليوم (API)", callback_data="api_today_stats"),
            InlineKeyboardButton("💰 حاسبة الرهان والأرباح", callback_data="calc_bet"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = "👋 **أهلاً بك في بوت التحليل الرياضي وحسابات الرهان!**"
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "api_today_stats":
        await query.edit_message_text("🔄 جاري الاتصال بالـ API وجلب الإحصائيات...")
        api_data_text = fetch_today_matches()
        
        keyboard = [
            [InlineKeyboardButton("📢 نشر الإحصائيات في القناة", callback_data="post_channel")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.edit_message_text(api_data_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "post_channel":
        try:
            msg_to_send = query.message.text
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📢 **تحديث جديد:**\n\n{msg_to_send}", parse_mode="Markdown")
            await query.answer("✅ تم النشر بنجاح في القناة!", show_alert=True)
        except Exception:
            await query.answer("❌ تعذر النشر! تأكد من إضافة البوت أدمن في القناة وكتابة معرف القناة صح في الكود.", show_alert=True)

    elif query.data == "main_menu":
        await start(update, context)

# حاسبة الرهان
async def start_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 **حاسبة الرهان:**\n\nأدخل **المبلغ** الذي تريد الرهان به (مثال: `20`):", parse_mode="Markdown")
    return WAITING_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if not user_input.replace('.', '', 1).isdigit():
        await update.message.reply_text("❌ أدخل رقماً صحيحاً للمبلغ:")
        return WAITING_AMOUNT

    context.user_data['amount'] = float(user_input)
    await update.message.reply_text("ممتاز! الآن أدخل قيمة الـ **Odds** من منصة 1xBet (مثال: `1.80`):")
    return WAITING_ODDS

async def get_odds_and_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        odds = float(user_input)
    except ValueError:
        await update.message.reply_text("❌ أدخل رقماً صحيحاً للـ Odds:")
        return WAITING_ODDS

    amount = context.user_data['amount']
    total_return = amount * odds
    net_profit = total_return - amount

    result_text = (
        "📊 **نتيجة الحسابات:**\n"
        "───────────────\n"
        f"💵 **المبلغ المدخل:** ${amount:.2f}\n"
        f"📈 **الـ Odds:** {odds}\n"
        "───────────────\n"
        f"🏆 **العائد الإجمالي (المسترجع):** ${total_return:.2f}\n"
        f"💰 **الربح الصافي:** ${net_profit:.2f}\n"
    )

    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
    await update.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    calc_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_calc, pattern="^calc_bet$")],
        states={
            WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            WAITING_ODDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_odds_and_calculate)],
        },
        fallbacks=[CommandHandler("cancel", cancel_calc)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(calc_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
