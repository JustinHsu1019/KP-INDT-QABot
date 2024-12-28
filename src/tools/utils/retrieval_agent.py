import os
import sys

import voyageai
import weaviate
from langchain.embeddings import OpenAIEmbeddings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import utils.config_log as config_log

config, logger, CONFIG_PATH = config_log.setup_config_and_logging()
config.read(CONFIG_PATH)

voyage_api_key = config.get('VoyageAI', 'api_key')
wea_url = config.get('Weaviate', 'weaviate_url')
PROPERTIES = ['uuid', 'title', 'content']

os.environ['OPENAI_API_KEY'] = config.get('OpenAI', 'api_key')


def rerank_with_voyage(query, documents, api_key):
    vo = voyageai.Client(api_key=api_key)
    # 提取所有 `content` 用於 rerank
    content_list = [doc['content'] for doc in documents]
    reranking = vo.rerank(query, content_list, model='rerank-2', top_k=5)

    # 取得重排序後的 indices 並映射回原始的 documents
    sorted_indices = [result.index for result in reranking.results]
    top_documents = [documents[i] for i in sorted_indices]

    return top_documents


class WeaviateSemanticSearch:
    def __init__(self, classnm):
        self.url = wea_url
        self.embeddings = OpenAIEmbeddings(chunk_size=1, model='text-embedding-3-large')
        self.client = weaviate.Client(url=wea_url)
        self.classnm = classnm

    def aggregate_count(self):
        return self.client.query.aggregate(self.classnm).with_meta_count().do()

    def get_data_by_uuid(self, uuid):
        result = self.client.query.get(class_name=self.classnm, properties=PROPERTIES).with_where({
            "path": ["uuid"],
            "operator": "Equal",
            "valueText": uuid
        }).do()
        return result

    def get_all_data(self, limit=100):
        if self.client.schema.exists(self.classnm):
            result = self.client.query.get(class_name=self.classnm, properties=PROPERTIES).with_limit(limit).do()
            return result
        else:
            raise Exception(f'Class {self.classnm} does not exist.')

    def delete_class(self):
        self.client.schema.delete_class(self.classnm)

    def hybrid_search(self, query, num, alpha):
        query_vector = self.embeddings.embed_query(query)
        vector_str = ','.join(map(str, query_vector))
        gql_query = f"""
        {{
            Get {{
                {self.classnm}(hybrid: {{query: "{query}", vector: [{vector_str}], alpha: {alpha} }}, limit: {num}) {{
                    uuid
                    content
                    _additional {{
                        distance
                        score
                    }}
                }}
            }}
        }}
        """
        search_results = self.client.query.raw(gql_query)

        if 'errors' in search_results:
            raise Exception(search_results['errors'][0]['message'])

        results = search_results['data']['Get'][self.classnm]
        return results


def search_do(input_, alp):
    searcher = WeaviateSemanticSearch("Kpitprod")
    results = searcher.hybrid_search(input_, 100, alpha=alp) # 留給 Reranker 多少筆來排序，可以做一下壓力測試得知，越多越好

    documents = [{'content': result['content'], 'uuid': result['uuid']} for result in results]

    # 使用 rerank 並保留 uuid
    reranked_documents = rerank_with_voyage(input_, documents, voyage_api_key)

    result_uuid = [doc['uuid'] for doc in reranked_documents]

    return result_uuid


def format_content(data):
    try:
        record = data['data']['Get']['Kpitprod'][0]
        content = record.get('content', '')
        return content
    except Exception as e:
        return ""
