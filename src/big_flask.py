from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    RichMenu, RichMenuArea, RichMenuBounds, RichMenuSize,
    URIAction, MessageAction, MessageEvent, TextMessage, TextSendMessage
)
import datetime
import tools.utils.config_log as config_log
import tools.chatbot as chatbot

# Load Config
config, logger, CONFIG_PATH = config_log.setup_config_and_logging()
config.read(CONFIG_PATH)
LINE_CHANNEL_ACCESS_TOKEN = config.get('Line', 'channel_access_token')
LINE_CHANNEL_SECRET = config.get('Line', 'secret')

# Initialize Flask and Line Bot API
app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Session memory
user_sessions = {}
user_ding = {}
user_ai_usage = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Check your channel access token/channel secret.")
        return 'Invalid signature', 400

    return 'OK', 200


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # 確保初始化 user_ai_usage 與 user_sessions
    if user_id not in user_ai_usage:
        user_ai_usage[user_id] = {"count": 0, "last_reset": datetime.now()}

    # 檢查是否需要重置每日次數限制
    now = datetime.now()
    last_reset = user_ai_usage[user_id]["last_reset"]
    if (now - last_reset).days >= 1:
        user_ai_usage[user_id] = {"count": 0, "last_reset": now}

    # 檢查每日次數是否超過限制
    if user_ai_usage[user_id]["count"] >= 50:
        reply = "您已經超過每日 50 則問答的限制，請明天再來！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # AI 聊天功能
    bot_reply = chatbot.respond_to_message(text)

    # 計數器加 1
    user_ai_usage[user_id]["count"] += 1

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=bot_reply))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
