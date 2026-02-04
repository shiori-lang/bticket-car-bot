#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bticket Car Booking Bot
Telegram bot for managing car bookings with concierge approval
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import json
from datetime import datetime

# ログ設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===========================================
# 設定（ここを変更してください）
# ===========================================
BOT_TOKEN = "7721052537:AAHEt2HDVIiFc-tobeBlOArSNm_Bkdk7jVo"  
CONCIERGE_CHAT_ID = -4849725102 
GROUP_CHAT_ID = -1003416443982

# 車両リスト
VEHICLES = [
    {"name": "Toyota Grandia", "plate": "IAC 8300", "location": "Junket"},
    {"name": "Toyota Hiace E-lite", "plate": "NEB 9255", "location": "BGC"},
    {"name": "Utility Vehicle Van", "plate": "CBL9754", "location": "BGC"},
    {"name": "Van Toyota HIACE", "plate": "NAE3633", "location": "BGC"},
]

# ドライバーリスト
DRIVERS = {
    "BGC": [
        "Timothy John Corpuz",
        "Celso Castillo Jr.",
        "Jo-emil Punzalan",
        "Bonifacio Dizon",
        "Jeremiah Oliva",
        "Darwin Padilla",
    ],
    "Junket": [
        "Jom Gabion",
        "Dominador Toyco Jr",
        "Antonio Florencio",
        "Severino Salandanan Jr",
    ],
    "Bodyguard": ["Mark Anthony Ces"],
}

# 会話の状態
LANGUAGE, GUEST_NAME, DATE, TIME, PICKUP, ROUTE, NOTE = range(7)

# 予約データを一時保存
pending_bookings = {}

# 多言語メッセージ
MESSAGES = {
    "ja": {
        "welcome": "こんにちは、{}さん！\n\nBticket Car Booking Botへようこそ🚗\n\nコマンド:\n/book - 新しい予約を開始\n/cancel - 予約をキャンセル\n/help - ヘルプを表示",
        "help": "📖 使い方:\n\n1. /book で予約を開始\n2. 質問に答えて情報を入力\n3. コンサージュが承認\n4. グループチャットに確定通知が届きます\n\n予約を途中でやめたい場合は /cancel を送信してください。",
        "book_start": "🚗 車の予約を開始します。\n\nまず言語を選択してください:",
        "language_selected": "✅ {}を選択しました。\n\nゲスト名を入力してください:\n（自分の名前でも、送迎するゲストの名前でもOKです）\n\nキャンセルする場合は /cancel を送信してください。",
        "ask_date": "📅 日付を入力してください:\n（例: 2025-02-01 または 2/1）",
        "ask_time": "🕐 時間を入力してください:\n（例: 14:00 または 2:00 PM）",
        "ask_pickup": "📍 ピックアップ場所を入力してください:\n（例: BGC Office, NAIA Terminal 3）",
        "ask_route": "🗺️ ルート（目的地）を入力してください:\n（例: BGC → NAIA → BGC）",
        "ask_note": "📝 備考（NOTE）があれば入力してください。\nなければ「なし」または「-」と入力してください:",
        "request_received": "✅ 予約リクエストを受け付けました！\n\nコンサージュが確認中です...\n承認されたら通知が届きます。",
        "approved": "✅ 予約が承認されました！\n\n🚗 車両: {}\n👤 ドライバー: {}\n📅 日時: {} {}",
        "rejected": "❌ 予約が却下されました。\n\n別の日時で再度お試しいただくか、コンサージュに直接お問い合わせください。",
        "cancelled": "予約をキャンセルしました。\nまた予約したい場合は /book を送信してください。",
        "error_concierge": "⚠️ エラー: コンサージュチャットIDが設定されていません。\n管理者に連絡してください。",
        "error_send": "⚠️ コンサージュへの送信に失敗しました。管理者に連絡してください。",
        "japanese": "日本語",
        "english": "English",
    },
    "en": {
        "welcome": "Hello, {}!\n\nWelcome to Bticket Car Booking Bot🚗\n\nCommands:\n/book - Start a new booking\n/cancel - Cancel booking\n/help - Show help",
        "help": "📖 How to use:\n\n1. Start booking with /book\n2. Answer the questions\n3. Concierge will approve\n4. Confirmation will be sent to group chat\n\nTo cancel the booking, send /cancel",
        "book_start": "🚗 Starting car booking.\n\nFirst, please select your language:",
        "language_selected": "✅ {} selected.\n\nPlease enter guest name:\n(Your name or the guest's name you're arranging transport for)\n\nTo cancel, send /cancel",
        "ask_date": "📅 Please enter date:\n(Example: 2025-02-01 or 2/1)",
        "ask_time": "🕐 Please enter time:\n(Example: 14:00 or 2:00 PM)",
        "ask_pickup": "📍 Please enter pickup location:\n(Example: BGC Office, NAIA Terminal 3)",
        "ask_route": "🗺️ Please enter route (destination):\n(Example: BGC → NAIA → BGC)",
        "ask_note": "📝 Please enter any notes if needed.\nIf none, enter 'none' or '-':",
        "request_received": "✅ Booking request received!\n\nConcierge is reviewing...\nYou will be notified once approved.",
        "approved": "✅ Booking approved!\n\n🚗 Vehicle: {}\n👤 Driver: {}\n📅 Date/Time: {} {}",
        "rejected": "❌ Booking was rejected.\n\nPlease try again with a different date/time or contact concierge directly.",
        "cancelled": "Booking cancelled.\nTo book again, send /book",
        "error_concierge": "⚠️ Error: Concierge chat ID not configured.\nPlease contact administrator.",
        "error_send": "⚠️ Failed to send to concierge. Please contact administrator.",
        "japanese": "日本語",
        "english": "English",
    }
}


def get_message(lang: str, key: str, *args) -> str:
    """言語に応じたメッセージを取得"""
    msg = MESSAGES.get(lang, MESSAGES["en"]).get(key, "")
    if args:
        return msg.format(*args)
    return msg


# ===========================================
# コマンドハンドラー
# ===========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """startコマンドの処理"""
    user = update.effective_user
    # デフォルト言語は英語
    lang = context.user_data.get('language', 'en')
    
    await update.message.reply_text(
        get_message(lang, 'welcome', user.first_name)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """helpコマンドの処理"""
    lang = context.user_data.get('language', 'en')
    await update.message.reply_text(get_message(lang, 'help'))


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """現在のチャットIDを取得（設定用）"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title if chat_type != 'private' else 'Private Chat'
    
    await update.message.reply_text(
        f"📋 チャット情報:\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Type: {chat_type}\n"
        f"Title: {chat_title}\n\n"
        f"このIDをコードに設定してください。",
        parse_mode='Markdown'
    )


# ===========================================
# 予約フロー
# ===========================================

async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """予約開始 - 言語選択"""
    user = update.effective_user
    
    # 言語選択ボタン
    keyboard = [
        [
            InlineKeyboardButton("🇯🇵 日本語", callback_data="lang_ja"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🚗 Starting car booking.\n車の予約を開始します。\n\nPlease select your language:\n言語を選択してください:",
        reply_markup=reply_markup
    )
    
    # ユーザー情報を保存
    context.user_data['requested_by'] = user.first_name
    context.user_data['user_id'] = user.id
    
    return LANGUAGE


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """言語選択のコールバック"""
    query = update.callback_query
    await query.answer()
    
    # 言語を取得
    lang = query.data.split('_')[1]  # lang_ja -> ja
    context.user_data['language'] = lang
    
    lang_name = get_message(lang, 'japanese' if lang == 'ja' else 'english')
    
    await query.edit_message_text(
        get_message(lang, 'language_selected', lang_name)
    )
    
    return GUEST_NAME


async def guest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ゲスト名を受け取る"""
    lang = context.user_data.get('language', 'en')
    context.user_data['guest_name'] = update.message.text
    
    await update.message.reply_text(get_message(lang, 'ask_date'))
    
    return DATE


async def date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """日付を受け取る"""
    lang = context.user_data.get('language', 'en')
    context.user_data['date'] = update.message.text
    
    await update.message.reply_text(get_message(lang, 'ask_time'))
    
    return TIME


async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """時間を受け取る"""
    lang = context.user_data.get('language', 'en')
    context.user_data['time'] = update.message.text
    
    await update.message.reply_text(get_message(lang, 'ask_pickup'))
    
    return PICKUP


async def pickup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ピックアップ場所を受け取る"""
    lang = context.user_data.get('language', 'en')
    context.user_data['pickup'] = update.message.text
    
    await update.message.reply_text(get_message(lang, 'ask_route'))
    
    return ROUTE


async def route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ルートを受け取る"""
    lang = context.user_data.get('language', 'en')
    context.user_data['route'] = update.message.text
    
    await update.message.reply_text(get_message(lang, 'ask_note'))
    
    return NOTE


async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """備考を受け取り、コンサージュに送信"""
    lang = context.user_data.get('language', 'en')
    context.user_data['note'] = update.message.text
    
    # 確認メッセージを社員に送信
    await update.message.reply_text(get_message(lang, 'request_received'))
    
    # コンサージュチャットに送信
    await send_to_concierge(update, context)
    
    return ConversationHandler.END


async def send_to_concierge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """コンサージュチャットに承認リクエストを送信"""
    lang = context.user_data.get('language', 'en')
    
    if CONCIERGE_CHAT_ID is None:
        await update.message.reply_text(get_message(lang, 'error_concierge'))
        return
    
    data = context.user_data
    booking_id = f"{data['user_id']}-{int(datetime.now().timestamp())}"
    
    # 予約データを保存
    pending_bookings[booking_id] = data.copy()
    
    # メッセージ作成 (英語のみ)
    message = (
        "🔔 NEW BOOKING REQUEST\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 GUEST NAME: {data['guest_name']}\n"
        f"📅 DATE: {data['date']}\n"
        f"🕐 TIME: {data['time']}\n"
        f"📍 PICK UP: {data['pickup']}\n"
        f"🗺️ ROUTE: {data['route']}\n"
        f"📝 NOTE: {data['note']}\n"
        f"✍️ REQUESTED BY: {data['requested_by']}\n"
        f"🌐 LANGUAGE: {data['language'].upper()}\n"
        "━━━━━━━━━━━━━━━\n"
        "Select vehicle and driver:"
    )
    
    # 車両選択ボタン
    keyboard = []
    for i, vehicle in enumerate(VEHICLES):
        keyboard.append([
            InlineKeyboardButton(
                f"🚗 {vehicle['plate']} ({vehicle['name']})",
                callback_data=f"vehicle_{booking_id}_{i}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=CONCIERGE_CHAT_ID,
            text=message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send to concierge: {e}")
        await update.message.reply_text(get_message(lang, 'error_send'))


async def vehicle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """車両選択のコールバック"""
    query = update.callback_query
    await query.answer()
    
    # データ解析: callback_data format is "vehicle_USERID-TIMESTAMP_VEHICLEINDEX"
    parts = query.data.split('_')
    # parts[0] = 'vehicle', parts[1] = 'USERID-TIMESTAMP', parts[2] = index
    booking_id = parts[1]
    vehicle_index = int(parts[2])
    vehicle = VEHICLES[vehicle_index]
    
    # 予約データに車両情報を追加
    if booking_id in pending_bookings:
        pending_bookings[booking_id]['vehicle'] = vehicle
        pending_bookings[booking_id]['vehicle_index'] = vehicle_index
    
    # ドライバー選択ボタンを表示
    location = vehicle['location']
    keyboard = []
    
    # 該当ロケーションのドライバー
    if location in DRIVERS:
        for driver in DRIVERS[location]:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {driver}",
                    callback_data=f"driver_{booking_id}_{driver}"
                )
            ])
    
    # ボディガードも追加
    for driver in DRIVERS["Bodyguard"]:
        keyboard.append([
            InlineKeyboardButton(
                f"🛡️ {driver} (Bodyguard)",
                callback_data=f"driver_{booking_id}_{driver}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"✅ Vehicle Selected: {vehicle['plate']} ({vehicle['name']})\n\n"
             f"Now select a driver:",
        reply_markup=reply_markup
    )


async def driver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ドライバー選択のコールバック"""
    query = update.callback_query
    await query.answer()
    
    # データ解析: callback_data format is "driver_USERID-TIMESTAMP_DRIVERNAME"
    parts = query.data.split('_', 2)
    # parts[0] = 'driver', parts[1] = 'USERID-TIMESTAMP', parts[2] = driver name
    booking_id = parts[1]
    driver_name = parts[2]
    
    # 予約データにドライバー情報を追加
    if booking_id in pending_bookings:
        pending_bookings[booking_id]['driver'] = driver_name
        pending_bookings[booking_id]['approved_by'] = query.from_user.first_name
    
    # 承認・却下ボタン
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{booking_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{booking_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"✅ Vehicle: {pending_bookings[booking_id]['vehicle']['plate']}\n"
             f"✅ Driver: {driver_name}\n\n"
             f"Approve this booking?",
        reply_markup=reply_markup
    )


async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """承認のコールバック"""
    query = update.callback_query
    await query.answer("Booking approved!")
    
    # データ解析
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    data = pending_bookings[booking_id]
    lang = data.get('language', 'en')
    
    # グループチャットに確定通知を送信
    await send_confirmation_to_group(context, data)
    
    # リクエストした社員に通知
    try:
        await context.bot.send_message(
            chat_id=data['user_id'],
            text=get_message(lang, 'approved', 
                           data['vehicle']['plate'],
                           data['driver'],
                           data['date'],
                           data['time'])
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")
    
    # コンサージュチャットのメッセージを更新
    await query.edit_message_text(
        f"✅ Approved\n\n"
        f"Booking ID: {booking_id}\n"
        f"Approved by: {query.from_user.first_name}"
    )
    
    # 予約データを削除
    del pending_bookings[booking_id]


async def reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """却下のコールバック"""
    query = update.callback_query
    await query.answer("Booking rejected.")
    
    # データ解析
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    data = pending_bookings[booking_id]
    lang = data.get('language', 'en')
    
    # リクエストした社員に通知
    try:
        await context.bot.send_message(
            chat_id=data['user_id'],
            text=get_message(lang, 'rejected')
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")
    
    # コンサージュチャットのメッセージを更新
    await query.edit_message_text(
        f"❌ Rejected\n\n"
        f"Booking ID: {booking_id}\n"
        f"Rejected by: {query.from_user.first_name}"
    )
    
    # 予約データを削除
    del pending_bookings[booking_id]


async def send_confirmation_to_group(context: ContextTypes.DEFAULT_TYPE, data: dict):
    """グループチャットに確定通知を送信"""
    
    if GROUP_CHAT_ID is None:
        logger.error("Group chat ID is not set")
        return
    
    vehicle = data['vehicle']
    
    message = (
        "🚗 CAR BOOKING CONFIRMED\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 CAR NUMBER: {vehicle['plate']}\n"
        f"👤 ASSIGNED DRIVER: {data['driver']}\n"
        f"👥 GUEST NAME: {data['guest_name']}\n"
        f"📅 DATE: {data['date']}\n"
        f"🕐 TIME: {data['time']}\n"
        f"📍 PICK UP: {data['pickup']}\n"
        f"🗺️ ROUTE: {data['route']}\n"
        f"✍️ REQUESTED BY: {data['requested_by']}\n"
        f"✅ APPROVED BY: {data['approved_by']}\n"
        f"🤖 BOOKED BY: Bticket Car Booking Bot\n"
        f"📝 NOTE: {data['note']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=message
        )
    except Exception as e:
        logger.error(f"Failed to send confirmation to group: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """予約をキャンセル"""
    lang = context.user_data.get('language', 'en')
    await update.message.reply_text(get_message(lang, 'cancelled'))
    
    context.user_data.clear()
    return ConversationHandler.END


# ===========================================
# メイン関数
# ===========================================

def main():
    """Botを起動"""
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ エラー: BOT_TOKENを設定してください！")
        return
    
    # Applicationを作成
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 会話ハンドラー
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('book', book_start)],
        states={
            LANGUAGE: [CallbackQueryHandler(language_callback, pattern='^lang_')],
            GUEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, guest_name)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time)],
            PICKUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, pickup)],
            ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, route)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # ハンドラーを登録
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("getchatid", get_chat_id))
    application.add_handler(conv_handler)
    
    # コールバックハンドラー
    application.add_handler(CallbackQueryHandler(vehicle_callback, pattern='^vehicle_'))
    application.add_handler(CallbackQueryHandler(driver_callback, pattern='^driver_'))
    application.add_handler(CallbackQueryHandler(approve_callback, pattern='^approve_'))
    application.add_handler(CallbackQueryHandler(reject_callback, pattern='^reject_'))
    
    # Botを起動
    print("🚗 Bticket Car Booking Bot を起動しています...")
    print("停止するには Ctrl+C を押してください")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
