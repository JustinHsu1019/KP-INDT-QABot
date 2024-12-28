from tools.utils.ai.call_ai import call_aied
from tools.utils.weaviate_op import search_do

def respond_to_message(message):
    alpha = 0.5
    use_gpt = True

    response_li = search_do(message, alp=alpha)
    return call_aied(response_li, message, use_gpt)
