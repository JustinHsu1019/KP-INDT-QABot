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

@app.route("/create_rich_menu", methods=['POST'])
def create_rich_menu():
    """
    Creates a rich menu and links it to the LINE account. 
    Accepts size parameters via request.
    """
    # Default size values
    width = 2500
    height = 1620

    # Define RichMenuSize dynamically
    size = RichMenuSize(width=width, height=height)

    # Define actions
    actions = [
        # Top row
        URIAction(label="失智症病情追蹤", uri="https://liff.line.me/2006697633-bzKdLp4L"),
        MessageAction(label="AI 聊天機器人", text="AI 聊天"),
        MessageAction(label="照護壓力檢測", text="壓力檢測"),
        # Bottom row
        MessageAction(label="失智症知識大補帖", text="訂閱知識"),
        MessageAction(label="失智風險檢測", text="風險檢測"),
        URIAction(label="加入社群", uri="https://line.me/ti/g2/coKOzXMoNv0Ze7IHNmNRtpkdlRQzDUdSOkhmGg?utm_source=invitation&utm_medium=link_copy&utm_campaign=default")
    ]

    # Divide actions into rows (3 per row)
    areas = []
    for i, action in enumerate(actions):
        bounds = RichMenuBounds(
            x=(i % 3) * (width // 3),
            y=(height // 2 if i >= 3 else 0),
            width=width // 3,
            height=height // 2
        )
        areas.append(RichMenuArea(bounds=bounds, action=action))

    rich_menu = RichMenu(
        size=size,
        selected=False,
        name="Main Menu",
        chat_bar_text="選單",
        areas=areas
    )
    try:
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        logger.info(f"Rich menu created with ID: {rich_menu_id}")
    except Exception as e:
        logger.error(f"Failed to create rich menu: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500

    # Upload image for the rich menu
    try:
        with open("src/rich_menu.png", "rb") as img:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", img)
        logger.info("Rich menu image uploaded successfully.")
    except Exception as e:
        logger.error(f"Failed to upload rich menu image: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500

    # Link rich menu to all users
    try:
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info("Rich menu set as default successfully.")
    except Exception as e:
        logger.error(f"Failed to set default rich menu: {e}")
        return jsonify({"status": "failed", "error": str(e)}), 500

    return jsonify({"status": "success", "rich_menu_id": rich_menu_id}), 200

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
