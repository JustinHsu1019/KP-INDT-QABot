# from datetime import datetime

from tools.utils.ai.gemini_tem import gemini_template
from tools.utils.ai.gpt_tem import gpt_template


def call_aied(wait, quest, use_gpt: bool):
    prompt = f"""You are a helpful and informative bot that answers questions using text from the reference passage included below. \
Be sure to respond in a complete sentence, being comprehensive, including all relevant background information. \
However, you are talking to a non-technical audience, so be sure to break down complicated concepts and \
strike a friendly and conversational tone. \
If the passage is irrelevant to the answer, you may ignore it.
請用繁體中文回答

使用者問題：'{quest}'

PASSAGE:
'{wait[0]}

{wait[1]}

{wait[2]}

{wait[3]}

{wait[4]}'

ANSWER:
"""
    try:
        if use_gpt:
            res = gpt_template(prompt)
        else:
            res = gemini_template(prompt)
    except Exception:
        res = '太多使用者請求了！請等待幾秒後再重新詢問'

    return res
