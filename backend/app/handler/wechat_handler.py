import asyncio
from fastapi import Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, Response
import time
import hashlib
import xml.etree.ElementTree as ET
import configparser
import os
from collections import defaultdict
from datetime import datetime

from ..logger.logger import userqa_logger, log_error, log_info
from ..pearl_agent import PearlAIAgent
from ..auth.wechat_token_manager import get_token_manager
from ..client.wechat_client import get_wechat_client
from .predefined_message_handler import get_predefined_handler

# Read wechat token from config.ini
config = configparser.ConfigParser()
config_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
if not config.read(config_path, encoding='utf-8'):
    raise RuntimeError(f'Config file not found: {config_path}')
if not config.has_section('wechat'):
    raise RuntimeError(f'[wechat] section not found in {config_path}')

WECHAT_TOKEN = config.get('wechat', 'token')

# Get daily conversation limit from config, default to 5
DAILY_CONVERSATION_LIMIT = config.getint('wechat', 'daily_limit', fallback=5)


# In-memory chat history, Redis/DB is recommended for production
chat_history_dict = {}
user_locks = defaultdict(asyncio.Lock)

# Daily conversation limit tracking with thread safety
# Format: {user_id: {"date": "2025-07-03", "count": 3}}
user_daily_count = {}
user_count_locks = defaultdict(asyncio.Lock)

class WeChatHandler:
    agent = PearlAIAgent()

    @classmethod
    async def check_daily_limit(cls, user_id):
        """Check if user has exceeded daily conversation limit (thread-safe)"""
        async with user_count_locks[user_id]:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if user_id not in user_daily_count:
                user_daily_count[user_id] = {"date": today, "count": 0}
                return True
            
            user_data = user_daily_count[user_id]
            
            # Reset count if it's a new day
            if user_data["date"] != today:
                user_daily_count[user_id] = {"date": today, "count": 0}
                return True
            
            # Check if user has exceeded limit
            return user_data["count"] < DAILY_CONVERSATION_LIMIT
    
    @classmethod
    async def increment_daily_count(cls, user_id):
        """Increment user's daily conversation count (thread-safe)"""
        async with user_count_locks[user_id]:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if user_id not in user_daily_count:
                user_daily_count[user_id] = {"date": today, "count": 1}
            else:
                user_data = user_daily_count[user_id]
                if user_data["date"] == today:
                    user_daily_count[user_id]["count"] += 1
                else:
                    user_daily_count[user_id] = {"date": today, "count": 1}
    
    @classmethod
    async def check_and_increment_daily_count(cls, user_id):
        """Check limit and increment count atomically (thread-safe)"""
        async with user_count_locks[user_id]:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Initialize if not exists
            if user_id not in user_daily_count:
                user_daily_count[user_id] = {"date": today, "count": 0}
            
            user_data = user_daily_count[user_id]
            
            # Reset count if it's a new day
            if user_data["date"] != today:
                user_daily_count[user_id] = {"date": today, "count": 0}
                user_data = user_daily_count[user_id]
            
            # Check if user has exceeded limit
            if user_data["count"] >= DAILY_CONVERSATION_LIMIT:
                return False, user_data["count"]
            
            # Increment count
            user_daily_count[user_id]["count"] += 1
            return True, user_daily_count[user_id]["count"]
    
    @classmethod
    async def get_remaining_conversations(cls, user_id):
        """Get remaining conversations for today (thread-safe)"""
        async with user_count_locks[user_id]:
            today = datetime.now().strftime("%Y-%m-%d")
            
            if user_id not in user_daily_count or user_daily_count[user_id]["date"] != today:
                return DAILY_CONVERSATION_LIMIT
            
            used = user_daily_count[user_id]["count"]
            return max(0, DAILY_CONVERSATION_LIMIT - used)

    @staticmethod
    def build_wechat_text_reply(to_user, from_user, content):
        """构建微信文本回复XML"""
        now = int(time.time())
        return f"""<xml>
  <ToUserName><![CDATA[{to_user}]]></ToUserName>
  <FromUserName><![CDATA[{from_user}]]></FromUserName>
  <CreateTime>{now}</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[{content}]]></Content>
</xml>"""

    @staticmethod
    def parse_wechat_message(xml_data):
        """parse WeChat XML message into a dictionary"""
        try:
            if isinstance(xml_data, bytes):
                xml_data = xml_data.decode('utf-8')
            xml = ET.fromstring(xml_data)
            return {
                "MsgType": xml.findtext("MsgType"),
                "FromUserName": xml.findtext("FromUserName"), 
                "ToUserName": xml.findtext("ToUserName"),
                "Content": xml.findtext("Content"),
                "Event": xml.findtext("Event"),
                "CreateTime": xml.findtext("CreateTime")
            }
        except Exception as e:
            log_error(f"Failed to parse WeChat message: {e}")
            return None

    @staticmethod
    async def get_access_token():
        """Get WeChat API access token using the centralized token manager"""
        token_manager = await get_token_manager()
        return await token_manager.get_access_token()


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
    async def _safe_agent_answer(cls, question, user_id, chat_history):
        try:
            # run the agent.answer method in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls.agent.answer, question, chat_history)
        except Exception as e:
            import traceback
            msg = str(e)
            if hasattr(e, 'status_code') and e.status_code == 400:
                if hasattr(e, 'body') and 'ResponsibleAIPolicyViolation' in str(e.body):
                    return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
                elif 'ResponsibleAIPolicyViolation' in msg:
                    return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
                else:
                    log_error(f"OpenAI API error: {msg}\n{traceback.format_exc()}")
                    return "抱歉，我出了点问题，目前无法处理您的请求，请稍后再试吧。"
            elif 'ResponsibleAIPolicyViolation' in msg:
                return "抱歉，我是一名AI珍珠专家，我不能做回答珍珠相关问题的其他操作"
            else:
                log_error(f"OpenAI API error: {msg}\n{traceback.format_exc()}")
                return "抱歉，出了点问题，目前无法处理您的请求，请稍后再试吧。"

    @classmethod
    async def wechat_qa(cls, request: Request, background_tasks: BackgroundTasks = None):
        """async wechat message handler with background processing"""
        body = await request.body()
        msg = cls.parse_wechat_message(body)
        
        if not msg:
            return PlainTextResponse("Invalid message format", status_code=400)
        
        msg_type = msg["MsgType"]
        from_user = msg["FromUserName"]
        to_user = msg["ToUserName"]
        reply = "暂不支持此类型消息。"

        if msg_type == "event":
            event = msg["Event"]
            if event == "subscribe":
                remaining = await cls.get_remaining_conversations(from_user)
                predefined_handler = await get_predefined_handler()
                reply = predefined_handler.get_subscribe_response(remaining)
                # clear chat history for new subscribers
                chat_history_dict[from_user] = []
                
        elif msg_type == "text":
            content = msg["Content"]
            log_info(f"Received question from {from_user}: {content}", gz_log=userqa_logger)
            
            # Try to handle with predefined message handler first
            predefined_handler = await get_predefined_handler()
            remaining = await cls.get_remaining_conversations(from_user)
            predefined_response = predefined_handler.handle_predefined_message(content, from_user, remaining)
            
            if predefined_response:
                reply, message_type = predefined_response
                log_info(f"Handled {message_type} message for {from_user}")
            # Check daily conversation limit and increment atomically
            elif not await cls.check_daily_limit(from_user):
                remaining = await cls.get_remaining_conversations(from_user)
                reply = "不好意思哈，由于计算资源有限，你每天只有五次对话的机会，请明天再来聊呗"
                log_info(f"User {from_user} exceeded daily limit ({DAILY_CONVERSATION_LIMIT} conversations)")
            else:
                # Use atomic check and increment
                can_proceed, used_count = await cls.check_and_increment_daily_count(from_user)
                if not can_proceed:
                    reply = "不好意思哈，由于计算资源有限，你每天只有五次对话的机会，请明天再来聊呗"
                    log_info(f"User {from_user} exceeded daily limit ({DAILY_CONVERSATION_LIMIT} conversations)")
                else:
                    remaining = DAILY_CONVERSATION_LIMIT - used_count
                    log_info(f"User {from_user} conversation count incremented to {used_count}. Remaining today: {remaining}")
                    
                    # if has BackgroundTasks support, use async processing
                    if background_tasks:
                        background_tasks.add_task(cls.process_and_reply, from_user, content)
                        reply = "⌛ 让我思考下哈，请稍等片刻..."
                    else:
                        st_time = time.time()
                        chat_history = chat_history_dict.get(from_user, [])
                        reply = await cls._safe_agent_answer(content, from_user, chat_history)
                        log_info(f"Answer for {from_user} costs {time.time() - st_time:.2f}s")
                        chat_history.append({"role": "user", "content": content})
                        chat_history.append({"role": "assistant", "content": reply})
                        chat_history_dict[from_user] = chat_history[-20:]

        reply_xml = cls.build_wechat_text_reply(from_user, to_user, reply)
        return Response(content=reply_xml, media_type="application/xml")

    @classmethod
    async def wechat_callback(cls, request: Request, background_tasks: BackgroundTasks):
        """process WeChat callback asynchronously"""
        return await cls.wechat_qa(request, background_tasks)

    # keep the legacy synchronous handler for compatibility
    @classmethod
    async def wechat_qa_legacy(cls, request: Request):
        """legacy synchronous handler for WeChat messages (deprecated, kept for compatibility)"""
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
                remaining = await cls.get_remaining_conversations(from_user)
                predefined_handler = await get_predefined_handler()
                reply = predefined_handler.get_subscribe_response(remaining)
                chat_history = []
        elif msg_type == "text":
            question = xml.findtext("Content")
            log_info(f"Received question from {from_user}: {question}", gz_log=userqa_logger)
            # Try to handle with predefined message handler first
            predefined_handler = await get_predefined_handler()
            remaining = await cls.get_remaining_conversations(from_user)
            predefined_response = predefined_handler.handle_predefined_message(question, from_user, remaining)
            
            if predefined_response:
                reply, message_type = predefined_response
                # log_info(f"Handled {message_type} message for {from_user}")
            # Check daily conversation limit
            elif not await cls.check_daily_limit(from_user):
                reply = "不好意思，由于计算资源有限，你每天只有五次对话的计划哈，请明天再来聊呗"
                log_info(f"User {from_user} exceeded daily limit ({DAILY_CONVERSATION_LIMIT} conversations)")
            else:
                # Use atomic check and increment
                can_proceed, used_count = await cls.check_and_increment_daily_count(from_user)
                if not can_proceed:
                    reply = "不好意思哈，由于计算资源有限，你每天只有五次对话的机会，请明天再来聊呗"
                    log_info(f"User {from_user} exceeded daily limit ({DAILY_CONVERSATION_LIMIT} conversations)")
                else:
                    remaining = DAILY_CONVERSATION_LIMIT - used_count
                    log_info(f"User {from_user} conversation count incremented to {used_count}. Remaining today: {remaining}")
                    
                    # Use user lock to protect chat history operations (fix race condition)
                    async with user_locks[from_user]:
                        st_time = time.time()
                        reply = await cls._safe_agent_answer(question, from_user, chat_history)
                        log_info(f"Answer for {from_user} costs {time.time() - st_time:.2f}s")
                        chat_history.append({"role": "user", "content": question})
                        chat_history.append({"role": "assistant", "content": reply})
                        chat_history = chat_history[-20:]

        chat_history_dict[key] = chat_history
        resp_xml = f"""<xml>\n    <ToUserName><![CDATA[{from_user}]]></ToUserName>\n    <FromUserName><![CDATA[{to_user}]]></FromUserName>\n    <CreateTime>{int(time.time())}</CreateTime>\n    <MsgType><![CDATA[text]]></MsgType>\n    <Content><![CDATA[{reply}]]></Content>\n    </xml>"""
        return PlainTextResponse(resp_xml, media_type='application/xml')

    @classmethod
    async def send_customer_service_message(cls, openid, content):
        """Send a customer service message via WeChat API using the client"""
        wechat_client = await get_wechat_client()
        success = await wechat_client.send_text_message(openid, content)
        
        if success:
            log_info(f"Successfully sent customer service message to {openid}")
        else:
            log_error(f"Failed to send customer service message to {openid}")
        
        return success

    @classmethod
    async def process_and_reply(cls, user_id, content):
        """Process user questions and reply"""
        try:
            log_info(f"Starting background processing for user {user_id}")
            lock = user_locks[user_id]
            async with lock:
                chat_history = chat_history_dict.get(user_id, [])
            
                st_time = time.time()
                reply = await cls._safe_agent_answer(content, user_id, chat_history)
                processing_time = time.time() - st_time
                
                log_info(f"AI processing completed for {user_id} in {processing_time:.2f}s")
                
                chat_history.append({"role": "user", "content": content})
                chat_history.append({"role": "assistant", "content": reply})
                chat_history_dict[user_id] = chat_history[-20:]

                success = await cls.send_customer_service_message(user_id, reply)
                if success:
                    log_info(f"Successfully sent reply to {user_id}")
                else:
                    log_error(f"Failed to send reply to {user_id}")
                
        except Exception as e:
            log_error(f"Error in background processing for {user_id}: {e}")
            error_msg = "抱歉哈，处理您的问题时出现了错误，请稍后重试。"
            await cls.send_customer_service_message(user_id, error_msg)
