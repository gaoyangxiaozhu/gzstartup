import sys
import os
import pytest
from fastapi.testclient import TestClient

# Dynamically add backend to sys.path to ensure that the app package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app

client = TestClient(app)

def test_pearl_question():
    resp = client.post("/chat/qa", json={"question": "介绍下珍珠里面的小米珠？"})
    assert resp.status_code == 200
    data = resp.json()
    assert "珍珠" in data["answer"] or "小米珠" in data["answer"] or "AI服务暂时不可用" in data["answer"]

def test_non_pearl_question():
    resp = client.post("/chat/qa", json={"question": "你会下围棋吗？"})
    assert resp.status_code == 200
    data = resp.json()
    assert "只能解答珍珠相关的问题" in data["answer"] or "AI服务暂时不可用" in data["answer"]

def test_empty_question():
    resp = client.post("/chat/qa", json={"question": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "只能解答珍珠相关的问题" in data["answer"] or "AI服务暂时不可用" in data["answer"]
