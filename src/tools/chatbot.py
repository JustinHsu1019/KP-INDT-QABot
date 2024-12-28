from tools.utils.ai.call_ai import call_aied
# from tools.utils.weaviate_op import search_do
from tools.utils.retrieval_agent import search_do, format_content
from tools.utils.retrieval_agent import WeaviateSemanticSearch

weav_eng = WeaviateSemanticSearch('Kpitprod')

def respond_to_message(message):
    alpha = 0.8
    use_gpt = True

    r_uuid = search_do(message, alp=alpha)
    content_list = []
    for i in range(len(r_uuid)):
        content_info = weav_eng.get_data_by_uuid(r_uuid[i])
        content_list.append(format_content(content_info))
    return call_aied(content_list, message, use_gpt)
