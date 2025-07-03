import os
import sys
import time
import hashlib
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Dynamically add backend to sys.path to ensure that the app package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.wx import router, WECHAT_TOKEN

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def make_signature(token, timestamp, nonce):
    check_list = [token, timestamp, nonce]
    check_list.sort()
    check_str = ''.join(check_list)
    return hashlib.sha1(check_str.encode('utf-8')).hexdigest()

def test_wechat_check():
    timestamp = str(int(time.time()))
    nonce = "123456"
    echostr = "hello_wechat"
    signature = make_signature(WECHAT_TOKEN, timestamp, nonce)
    resp = client.get("/wechat", params={
        "signature": signature,
        "timestamp": timestamp,
        "nonce": nonce,
        "echostr": echostr
    })
    assert resp.status_code == 200
    assert resp.text == echostr

def test_wechat_check_invalid_signature():
    timestamp = str(int(time.time()))
    nonce = "123456"
    echostr = "hello_wechat"
    signature = "invalid_signature"
    resp = client.get("/wechat", params={
        "signature": signature,
        "timestamp": timestamp,
        "nonce": nonce,
        "echostr": echostr
    })
    assert resp.status_code == 403
    assert resp.text == "signature error"

def test_wechat_text_message(monkeypatch):
    from_user = "user123"
    to_user = "gh_abcdefg"
    content = "珍珠是什么？"
    xml = f"""<xml>
    <ToUserName><![CDATA[{to_user}]]></ToUserName>
    <FromUserName><![CDATA[{from_user}]]></FromUserName>
    <CreateTime>{int(time.time())}</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{content}]]></Content>
    <MsgId>1234567890</MsgId>
    </xml>"""
    resp = client.post("/wechat", data=xml.encode("utf-8"), headers={"Content-Type": "application/xml"})
    assert resp.status_code == 200
    assert "珍珠" in resp.text

def test_wechat_event_subscribe():
    from_user = "user123"
    to_user = "gh_abcdefg"
    xml = f"""<xml>
    <ToUserName><![CDATA[{to_user}]]></ToUserName>
    <FromUserName><![CDATA[{from_user}]]></FromUserName>
    <CreateTime>{int(time.time())}</CreateTime>
    <MsgType><![CDATA[event]]></MsgType>
    <Event><![CDATA[subscribe]]></Event>
    </xml>"""
    resp = client.post("/wechat", data=xml.encode("utf-8"), headers={"Content-Type": "application/xml"})
    assert resp.status_code == 200
    assert "感谢订阅" in resp.text
