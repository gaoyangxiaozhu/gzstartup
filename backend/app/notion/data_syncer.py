import os 

from langchain_community.document_loaders import NotionDBLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings

import configparser

from app.logger.logger import log_info

config = configparser.ConfigParser()

config_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
if not config.read(config_path, encoding='utf-8'):
    raise RuntimeError(f'Config file not found: {config_path}')
if not config.has_section('notion'):
    raise RuntimeError(f'[notion] section not found in {config_path}')

notion_token = config.get('notion', 'integration_token')
database_id = config.get('notion', 'database_id')
local_vector_store_path = config.get('notion',
    'local_vector_store_path', fallback='/data/notion_vectorstore')

if not config.has_section('azure_openai'):
    raise RuntimeError(f'[azure_openai] section not found in {config_path}')
os.environ["AZURE_OPENAI_API_KEY"] = config.get('azure_openai', 'api_key')
os.environ["AZURE_OPENAI_ENDPOINT"] = config.get('azure_openai', 'endpoint')
os.environ["OPENAI_API_VERSION"] = config.get('azure_openai', 'api_version')


embeddings = AzureOpenAIEmbeddings(
    model="azure_openai:text-embedding-3-large",
    chunk_size=1000)

class NotionDBDataSyncer:
    """Class to load data from Notion database and build a vector store."""
    local_vector_store_path = local_vector_store_path

    @classmethod
    def load_data(cls):
        loader = NotionDBLoader(integration_token=notion_token, database_id=database_id)
        return loader.load()  # Returns List[Document] with title, content, etc.
    
    @classmethod
    def build_vector_store(cls):
        """Build a vector store from Notion data."""
        docs = cls.load_data()
        log_info(f"Loaded {len(docs)} documents from Notion database successfully.")
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs_split = splitter.split_documents(docs)
        vectorstore = FAISS.from_documents(docs_split, embedding=embeddings)
        log_info(f"Built vector store with {len(docs_split)} chunks done.")
        return vectorstore

    @classmethod
    def persist_vector_store(cls):
        """Persist the vector store to a local path."""
        vectorstore = cls.build_vector_store()
        vectorstore.save_local(cls.local_vector_store_path)
        log_info(f"Vector store saved to {cls.local_vector_store_path}")
