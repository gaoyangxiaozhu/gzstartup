import os
import sys
import pytest

# Dynamically add backend to sys.path to ensure that the app package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.notion.data_syncer import NotionDBDataLoader

def test_notion_data_loader_load(monkeypatch):
    """Test loading data from Notion (mocked)."""
    # Mock NotionDBLoader.load to return fake docs
    class FakeDoc:
        def __init__(self, page_content):
            self.page_content = page_content
            self.metadata = {}
    monkeypatch.setattr(
        "langchain_community.document_loaders.NotionDBLoader.load",
        lambda self: [FakeDoc("悦华珍珠品牌定位：高端珍珠首饰。"), FakeDoc("悦华珍珠购买方式：悦华微信小商城。")] 
    )
    docs = NotionDBDataLoader.load_data()
    assert len(docs) == 2
    assert any("悦华珍珠品牌定位" in doc.page_content for doc in docs)


def test_notion_data_loader_vectorstore(monkeypatch, tmp_path):
    """Test building and saving vector store (mocked)."""
    # Mock load_data to return fake docs
    class FakeDoc:
        def __init__(self, page_content):
            self.page_content = page_content
            self.metadata = {}
    monkeypatch.setattr(
        NotionDBDataLoader, "load_data",
        classmethod(lambda cls: [FakeDoc("悦华珍珠品牌定位：高端珍珠首饰。"), FakeDoc("悦华珍珠购买方式：悦华微信小商城。")] )
    )
    # Mock OpenAIEmbeddings to avoid real API call
    import backend.app.notion.data_syncer
    monkeypatch.setattr(app.notion.data_syncer, "OpenAIEmbeddings", lambda *a, **kw: None)
    # Mock FAISS.from_documents to return a dummy object
    class DummyVS:
        def save_local(self, path):
            with open(os.path.join(path, "dummy"), "w") as f:
                f.write("ok")
    monkeypatch.setattr("langchain.vectorstores.FAISS.from_documents", lambda docs, emb: DummyVS())
    NotionDBDataLoader.local_vector_store_path = str(tmp_path)
    NotionDBDataLoader.persist_vector_store()
    assert os.path.exists(os.path.join(tmp_path, "dummy"))
