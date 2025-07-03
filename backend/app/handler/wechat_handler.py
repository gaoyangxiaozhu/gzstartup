from fastapi import Query, Request
from fastapi.responses import PlainTextResponse
import time
import hashlib
import xml.etree.ElementTree as ET

from ..exception.gzpearl_agent_exception import OpenAIBadRequestException
from ..pearl_agent import PearlAIAgent

WECHAT_TOKEN = "your_token_here"


# In-memory chat history, Redis/DB is recommended for production
chat_history_dict = {}

class WeChatHandler:
    agent = PearlAIAgent()
    
    @classmethod
    async def wechat_check(cls, signature: str, timestamp: str, nonce: str, echostr: str):
        check_list = [WECHAT_TOKEN, timestamp, nonce]
        check_list.sort()
        check_str = ''.join(check_list)
        hashcode = hashlib.sha1(check_str.encode('utf-8')).hexdigest()
        if hashcode == signature:
            return PlainTextResponse(echostr)
        return PlainTextResponse("signature error", status_code=403)

    @classmethod
    def _safe_agent_answer(cls, question, user_id, chat_history):
        try:
            return cls.agent.answer(question, user_id=user_id, chat_history=chat_history)
        except Exception as e:
            import traceback
            msg = str(e)
            if hasattr(e, 'status_code') and e.status_code == 400:
                if hasattr(e, 'body') and 'ResponsibleAIPolicyViolation' in str(e.body):
                    return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
                elif 'ResponsibleAIPolicyViolation' in msg:
                    return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
                else:
                    raise OpenAIBadRequestException(f"OpenAI API error: {msg}\n{traceback.format_exc()}")
            elif 'ResponsibleAIPolicyViolation' in msg:
                return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
            else:
                raise OpenAIBadRequestException(f"OpenAI API error: {msg}\n{traceback.format_exc()}")

    @classmethod
    async def wechat_qa(cls, request: Request):
        body = await request.body()
        xml = ET.fromstring(body)
        msg_type = xml.findtext("MsgType")
        from_user = xml.findtext("FromUserName")
        to_user = xml.findtext("ToUserName")
        key = from_user
        chat_history = chat_history_dict.get(key, [])
        reply = "暂不支持此类型消息。"

        if msg_type == "event":
            event = xml.findtext("Event")
            if event == "subscribe":
                reply = "Hi，感谢订阅沛珠记，成为我们大家庭的一员。我是AI珍珠专家宝儿，你可以向我咨询任何珍珠相关问题，我会努力回答！"
                chat_history = []
        elif msg_type == "text":
            question = xml.findtext("Content")
            reply = WeChatHandler._safe_agent_answer(question, from_user, chat_history)
            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": reply})
            chat_history = chat_history[-20:]

        chat_history_dict[key] = chat_history
        resp_xml = f"""<xml>\n    <ToUserName><![CDATA[{from_user}]]></ToUserName>\n    <FromUserName><![CDATA[{to_user}]]></FromUserName>\n    <CreateTime>{int(time.time())}</CreateTime>\n    <MsgType><![CDATA[text]]></MsgType>\n    <Content><![CDATA[{reply}]]></Content>\n    </xml>"""
        return PlainTextResponse(resp_xml, media_type='application/xml')

    @classmethod
    def chat_qa(cls, data, chat_history_dict, agent):
        user_id = data.user_id or "anonymous"
        session_id = data.session_id or "default"
        key = (user_id, session_id)
        chat_history = chat_history_dict.get(key, [])
        answer = WeChatHandler._safe_agent_answer(data.question, user_id, chat_history)
        chat_history.append({"role": "user", "content": data.question})
        chat_history.append({"role": "assistant", "content": answer})
        chat_history_dict[key] = chat_history[-20:]
        return answer
