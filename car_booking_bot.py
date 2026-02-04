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
BOT_TOKEN = "7721052537:AAHC0Khs1NudLzbOzKmsB1AI4NugnaeYQSw"
CONCIERGE_CHAT_ID = -4849725102
GROUP_CHAT_ID = -1003416443982

# 車両リスト
VEHICLES = [
    {"name": "Toyota Grandia", "plate": "IAC 8300", "location": "Junket"},
    {"name": "Toyota Hiace E-lite", "plate": "NEB 9255", "location": "BGC"},
    {"name": "Utility Vehicle Van", "plate": "CBL9754", "location": "BGC"},
    {"name": "Van Toyota HIACE", "plate": "NAE3633", "location": "BGC"},
]

# ドライバーリスト（名前とTelegramリンク）
DRIVERS = {
    "BGC": [
        {"name": "Timothy John Corpuz", "telegram": "https://t.me/TanJiroBetrnk"},
        {"name": "Celso Castillo Jr.", "telegram": "https://t.me/celsojrcastillo"},
        {"name": "Jo-emil Punzalan", "telegram": "https://t.me/Joemilp25"},
        {"name": "Bonifacio Dizon", "telegram": "https://t.me/Junior08011979"},
        {"name": "Jeremiah Oliva", "telegram": "https://t.me/Jayremaya"},
    ],
    "Junket": [
        {"name": "Jom Gabion", "telegram": "https://t.me/k08e24"},
        {"name": "Dominador Toyco Jr", "telegram": "https://t.me/Toyix81"},
        {"name": "Antonio Florencio", "telegram": "https://t.me/Poging0025"},
        {"name": "Severino Salandanan Jr", "telegram": "https://t.me/dobolsierra"},
    ],
    "Bodyguard": [
        {"name": "Mark Anthony Ces", "telegram": "https://t.me/kenvic21"},
        {"name": "Alvin Principe", "telegram": "https://t.me/Vhinox"},
        {"name": "Francisco Romero", "telegram": "https://t.me/Romerojr83"},
    ],
}

# 会話の状態
LANGUAGE, GUEST_NAME, DATE, TIME, PICKUP, ROUTE, NOTE, ALTERNATIVE_SUGGESTION = range(8)

# 予約データを一時保存
pending_bookings = {}

# 代替案待ちのコンサージュ
awaiting_alternative = {}

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
        "approved": "✅ 予約が承認されました！\n\n🚗 車両: {}\n👤 ドライバー: {}\n📱 ドライバーTelegram: {}\n📅 日時: {} {}",
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
        "approved": "✅ Booking approved!\n\n🚗 Vehicle: {}\n👤 Driver: {}\n📱 Driver Telegram: {}\n📅 Date/Time: {} {}",
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
    
    # ロケーション選択ボタンを表示
    keyboard = [
        [InlineKeyboardButton("🏢 BGC Drivers", callback_data=f"location_{booking_id}_BGC")],
        [InlineKeyboardButton("🎰 Junket Drivers", callback_data=f"location_{booking_id}_Junket")],
        [InlineKeyboardButton("🛡️ Bodyguard", callback_data=f"location_{booking_id}_Bodyguard")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"✅ Vehicle Selected: {vehicle['plate']} ({vehicle['name']})\n\n"
             f"Select driver location:",
        reply_markup=reply_markup
    )




async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ロケーション選択のコールバック"""
    query = update.callback_query
    await query.answer()
    
    # データ解析: callback_data format is "location_USERID-TIMESTAMP_LOCATION"
    parts = query.data.split('_', 2)
    booking_id = parts[1]
    location = parts[2]
    
    # 選択したロケーションのドライバーボタンを表示
    keyboard = []
    
    if location in DRIVERS:
        for driver in DRIVERS[location]:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {driver['name']}",
                    callback_data=f"driver_{booking_id}_{driver['name']}"
                )
            ])
    
    # 戻るボタンを追加
    keyboard.append([
        InlineKeyboardButton("⬅️ Back to Locations", callback_data=f"backvehicle_{booking_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    location_label = {
        "BGC": "🏢 BGC",
        "Junket": "🎰 Junket",
        "Bodyguard": "🛡️ Bodyguard"
    }.get(location, location)
    
    await query.edit_message_text(
        text=f"✅ Location: {location_label}\n\n"
             f"Select a driver:",
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
    
    # ドライバーのTelegramリンクを取得
    driver_telegram = "N/A"
    for location_drivers in DRIVERS.values():
        for driver in location_drivers:
            if driver['name'] == driver_name:
                driver_telegram = driver['telegram']
                break
    
    # 予約データにドライバー情報を追加
    if booking_id in pending_bookings:
        pending_bookings[booking_id]['driver'] = driver_name
        pending_bookings[booking_id]['driver_telegram'] = driver_telegram
        pending_bookings[booking_id]['approved_by'] = query.from_user.first_name
    
    # 承認・却下・代替案提案ボタン
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{booking_id}")],
        [InlineKeyboardButton("💡 Suggest Alternative", callback_data=f"suggest_{booking_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{booking_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"✅ Vehicle: {pending_bookings[booking_id]['vehicle']['plate']}\n"
             f"✅ Driver: {driver_name}\n"
             f"📱 Driver Telegram: {driver_telegram}\n\n"
             f"Approve this booking?",
        reply_markup=reply_markup
    )



async def back_to_vehicle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ロケーション選択に戻るコールバック"""
    query = update.callback_query
    await query.answer()
    
    # データ解析
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    vehicle = pending_bookings[booking_id]['vehicle']
    
    # ロケーション選択ボタンを再表示
    keyboard = [
        [InlineKeyboardButton("🏢 BGC Drivers", callback_data=f"location_{booking_id}_BGC")],
        [InlineKeyboardButton("🎰 Junket Drivers", callback_data=f"location_{booking_id}_Junket")],
        [InlineKeyboardButton("🛡️ Bodyguard", callback_data=f"location_{booking_id}_Bodyguard")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"✅ Vehicle Selected: {vehicle['plate']} ({vehicle['name']})\n\n"
             f"Select driver location:",
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
        driver_telegram = data.get('driver_telegram', 'N/A')
        await context.bot.send_message(
            chat_id=data['user_id'],
            text=get_message(lang, 'approved', 
                           data['vehicle']['plate'],
                           data['driver'],
                           driver_telegram,
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


async def suggest_alternative_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """代替案提案のコールバック"""
    query = update.callback_query
    await query.answer()
    
    # データ解析
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    # コンサージュIDを保存（後で代替案を受け取るため）
    awaiting_alternative[query.from_user.id] = {
        'booking_id': booking_id,
        'concierge_message_id': query.message.message_id,
        'concierge_chat_id': query.message.chat_id
    }
    
    # コンサージュに代替案入力を促す
    await query.edit_message_text(
        f"💡 Suggesting Alternative Time\n\n"
        f"Original Request:\n"
        f"📅 Date: {pending_bookings[booking_id]['date']}\n"
        f"🕐 Time: {pending_bookings[booking_id]['time']}\n\n"
        f"Please reply to this message with the alternative date and time.\n"
        f"Format: YYYY-MM-DD HH:MM\n"
        f"Example: 2026-02-05 14:00"
    )


async def handle_alternative_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """コンサージュからの代替案入力を処理"""
    user_id = update.effective_user.id
    
    if user_id not in awaiting_alternative:
        return
    
    alternative_info = awaiting_alternative[user_id]
    booking_id = alternative_info['booking_id']
    
    if booking_id not in pending_bookings:
        await update.message.reply_text("⚠️ Error: Booking not found.")
        del awaiting_alternative[user_id]
        return
    
    # 代替案のテキストを取得
    alternative_datetime = update.message.text.strip()
    
    # 代替案を保存
    pending_bookings[booking_id]['alternative_datetime'] = alternative_datetime
    pending_bookings[booking_id]['alternative_proposed_by'] = update.effective_user.first_name
    
    data = pending_bookings[booking_id]
    lang = data.get('language', 'en')
    
    # リクエスターに代替案を送信
    keyboard = [
        [InlineKeyboardButton("✅ Accept Alternative", callback_data=f"acceptalt_{booking_id}")],
        [InlineKeyboardButton("❌ Decline Alternative", callback_data=f"declinealt_{booking_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if lang == 'ja':
        alt_message = (
            f"💡 代替案の提案\n\n"
            f"申し訳ございません。ご希望の日時では予約が難しい状況です。\n\n"
            f"📅 元のリクエスト: {data['date']} {data['time']}\n"
            f"💡 代替案: {alternative_datetime}\n\n"
            f"この代替案でよろしいでしょうか？"
        )
    else:
        alt_message = (
            f"💡 Alternative Time Suggested\n\n"
            f"Sorry, the requested time is not available.\n\n"
            f"📅 Original Request: {data['date']} {data['time']}\n"
            f"💡 Suggested Alternative: {alternative_datetime}\n\n"
            f"Would you like to accept this alternative?"
        )
    
    try:
        await context.bot.send_message(
            chat_id=data['user_id'],
            text=alt_message,
            reply_markup=reply_markup
        )
        
        # コンサージュに確認
        await update.message.reply_text(
            f"✅ Alternative sent to requester!\n\n"
            f"💡 Suggested: {alternative_datetime}\n"
            f"Waiting for requester's response..."
        )
        
    except Exception as e:
        logger.error(f"Failed to send alternative to user: {e}")
        await update.message.reply_text("⚠️ Failed to send alternative to requester.")
    
    # 代替案待ちステータスを削除
    del awaiting_alternative[user_id]


async def accept_alternative_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """リクエスターが代替案を承認"""
    query = update.callback_query
    await query.answer()
    
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    data = pending_bookings[booking_id]
    lang = data.get('language', 'en')
    
    # 元の日時を代替案に更新
    data['original_date'] = data['date']
    data['original_time'] = data['time']
    data['date'], data['time'] = data['alternative_datetime'].split(' ', 1)
    
    # リクエスターに確認
    if lang == 'ja':
        await query.edit_message_text(
            f"✅ 代替案を承認しました\n\n"
            f"💡 新しい日時: {data['date']} {data['time']}\n\n"
            f"コンサージュが最終承認を行います..."
        )
    else:
        await query.edit_message_text(
            f"✅ Alternative Accepted\n\n"
            f"💡 New Date/Time: {data['date']} {data['time']}\n\n"
            f"Waiting for concierge final approval..."
        )
    
    # コンサージュに最終承認ボタンを送信
    keyboard = [
        [InlineKeyboardButton("✅ Final Approve", callback_data=f"finalapprove_{booking_id}")],
        [InlineKeyboardButton("❌ Cancel Booking", callback_data=f"reject_{booking_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=CONCIERGE_CHAT_ID,
            text=f"✅ Requester Accepted Alternative!\n\n"
                 f"👤 Guest: {data['guest_name']}\n"
                 f"📅 Original: {data['original_date']} {data['original_time']}\n"
                 f"💡 New Time: {data['date']} {data['time']}\n"
                 f"🚗 Vehicle: {data['vehicle']['plate']}\n"
                 f"👤 Driver: {data['driver']}\n\n"
                 f"Please confirm final approval:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to notify concierge: {e}")


async def decline_alternative_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """リクエスターが代替案を却下"""
    query = update.callback_query
    await query.answer()
    
    booking_id = query.data.split('_')[1]
    
    if booking_id not in pending_bookings:
        await query.edit_message_text("⚠️ Error: Booking not found.")
        return
    
    data = pending_bookings[booking_id]
    lang = data.get('language', 'en')
    
    # リクエスターに確認
    if lang == 'ja':
        await query.edit_message_text(
            f"❌ 代替案を却下しました\n\n"
            f"予約がキャンセルされました。\n"
            f"別の日時で再度予約をお願いします。"
        )
    else:
        await query.edit_message_text(
            f"❌ Alternative Declined\n\n"
            f"Booking has been cancelled.\n"
            f"Please submit a new request with a different time."
        )
    
    # コンサージュに通知
    try:
        await context.bot.send_message(
            chat_id=CONCIERGE_CHAT_ID,
            text=f"❌ Requester Declined Alternative\n\n"
                 f"Booking ID: {booking_id}\n"
                 f"Guest: {data['guest_name']}\n"
                 f"Booking cancelled."
        )
    except Exception as e:
        logger.error(f"Failed to notify concierge: {e}")
    
    # 予約データを削除
    del pending_bookings[booking_id]


async def final_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """代替案の最終承認"""
    query = update.callback_query
    await query.answer("Final approval confirmed!")
    
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
        driver_telegram = data.get('driver_telegram', 'N/A')
        await context.bot.send_message(
            chat_id=data['user_id'],
            text=get_message(lang, 'approved', 
                           data['vehicle']['plate'],
                           data['driver'],
                           driver_telegram,
                           data['date'],
                           data['time'])
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")
    
    # コンサージュチャットのメッセージを更新
    await query.edit_message_text(
        f"✅ Final Approval Complete\n\n"
        f"Booking ID: {booking_id}\n"
        f"New Time: {data['date']} {data['time']}\n"
        f"Approved by: {query.from_user.first_name}"
    )
    
    # 予約データを削除
    del pending_bookings[booking_id]


async def send_confirmation_to_group(context: ContextTypes.DEFAULT_TYPE, data: dict):
    """グループチャットに確定通知を送信"""
    
    if GROUP_CHAT_ID is None:
        logger.error("Group chat ID is not set")
        return
    
    vehicle = data['vehicle']
    driver_telegram = data.get('driver_telegram', 'N/A')
    
    message = (
        "🚗 CAR BOOKING CONFIRMED\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚗 CAR NUMBER: {vehicle['plate']}\n"
        f"👤 ASSIGNED DRIVER: {data['driver']}\n"
        f"📱 DRIVER TELEGRAM: {driver_telegram}\n"
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
    application.add_handler(CallbackQueryHandler(location_callback, pattern='^location_'))
    application.add_handler(CallbackQueryHandler(driver_callback, pattern='^driver_'))
    application.add_handler(CallbackQueryHandler(back_to_vehicle_callback, pattern='^backvehicle_'))
    application.add_handler(CallbackQueryHandler(approve_callback, pattern='^approve_'))
    application.add_handler(CallbackQueryHandler(suggest_alternative_callback, pattern='^suggest_'))
    application.add_handler(CallbackQueryHandler(accept_alternative_callback, pattern='^acceptalt_'))
    application.add_handler(CallbackQueryHandler(decline_alternative_callback, pattern='^declinealt_'))
    application.add_handler(CallbackQueryHandler(final_approve_callback, pattern='^finalapprove_'))
    application.add_handler(CallbackQueryHandler(reject_callback, pattern='^reject_'))
    
    # メッセージハンドラー（代替案入力用）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alternative_input))
    
    # Botを起動
    print("🚗 Bticket Car Booking Bot を起動しています...")
    print("停止するには Ctrl+C を押してください")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

