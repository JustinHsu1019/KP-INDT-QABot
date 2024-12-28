import time
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import utils.config_log as config_log
import weaviate
from langchain_text_splitters import RecursiveCharacterTextSplitter


config, logger, CONFIG_PATH = config_log.setup_config_and_logging()
config.read(CONFIG_PATH)

wea_url = config.get('Weaviate', 'weaviate_url')
openai_api_key = config.get('OpenAI', 'api_key')


class WeaviateManager:
    def __init__(self, classnm):
        self.url = wea_url
        self.client = weaviate.Client(url=wea_url, additional_headers={'X-OpenAI-Api-Key': openai_api_key})
        self.classnm = classnm
        self.check_class_exist()

    def check_class_exist(self):
        if self.client.schema.exists(self.classnm):
            print(f'{self.classnm} is ready')
            return True
        schema = {
            'class': self.classnm,
            'properties': [
                {'name': 'uuid', 'dataType': ['text']},
                {
                    'name': 'title',
                    'dataType': ['text'],
                    'tokenization': 'gse',
                },
                {
                    'name': 'content',
                    'dataType': ['text'],
                    'tokenization': 'gse',
                },
            ],
            'vectorizer': 'text2vec-openai',
            'moduleConfig': {
                'text2vec-openai': {'model': 'text-embedding-3-large', 'dimensions': 3072, 'type': 'text'}
            },
        }
        print(f'creating {self.classnm}...')
        self.client.schema.create_class(schema)
        print(f'{self.classnm} is ready')
        return True

    def insert_data(self, title_text, content_text):
        data_object = {'uuid': str(uuid.uuid4()), 'title': title_text, 'content': content_text}
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.client.data_object.create(data_object, self.classnm)
                break
            except weaviate.exceptions.RequestError as e:
                if '429' in str(e):
                    print(f'Rate limit exceeded, retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})')
                    time.sleep(5)
                else:
                    raise


if __name__ == '__main__':
    """ insert data to weaviate (Template)"""
    manager = WeaviateManager("kpit")

    with open('data/柯姓被告等新聞資料.txt', encoding='utf-8') as file:
        content = file.read()

    # new_cp = content.split('femh')
    # 因為 merged_output.txt 沒有用 'femh' 預先分好
    # 所以需要用 langchain 的 textsplitter 來切分，設定 Tokens 2000, overlap=500
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
    new_cp = text_splitter.split_text(content)

    for lines in new_cp:
        manager.insert_data("", lines)
