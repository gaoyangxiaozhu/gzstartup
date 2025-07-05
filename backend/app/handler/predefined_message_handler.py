"""
Predefined message handler for WeChat bot.
Handles simple greetings, thanks, and other predefined responses.
"""
import asyncio
import configparser
import os
from typing import Optional, Tuple
from ..logger.logger import log_info

class PredefinedMessageHandler:
    """
    Handle predefined messages like greetings, thanks, etc.
    This keeps the main handler clean and makes it easy to add new predefined responses.
    """
    
    def __init__(self):
        # Load configuration
        config = configparser.ConfigParser()
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        if config.read(config_path, encoding='utf-8') and config.has_section('wechat'):
            self.daily_limit = config.getint('wechat', 'daily_limit', fallback=5)
        else:
            self.daily_limit = 5
            
        # Predefined responses
        self.greeting_response = "你好！我是悦华珍珠AI助手宝儿，可以回答你任何和珍珠相关的问题。关于珍珠的品种、鉴别、历史、佩戴、护理等，如果你有任何疑问，欢迎随时提问！"
        self.thanks_response = "不客气！很高兴能为您解答。如果您以后还有任何关于珍珠的问题，随时欢迎来咨询我。祝您生活愉快！"
        self.subscribe_response_template = "Hi，感谢订阅沛珠记，成为我们大家庭的一员。我是AI珍珠专家宝儿，你可以向我咨询任何珍珠相关问题，我会努力回答！\n\n💡 温馨提示：每天您有{daily_limit}次对话机会，今日剩余{remaining}次。"
        self.stats_response_template = "📊 今日对话统计：\n已使用：{used}次\n剩余：{remaining}次\n总计：{daily_limit}次/天"
    
    def is_simple_greeting(self, text: str) -> bool:
        """
        Check if the text is a simple greeting that doesn't need AI processing.
        Uses keyword matching with length limit to catch various greeting combinations.
        
        Args:
            text: User input text
            
        Returns:
            True if it's a simple greeting, False otherwise
        """
        if not text:
            return False
        
        # Clean and normalize the text
        cleaned_text = text.strip().lower()
        
        # If text is too long, it's probably not a simple greeting
        MAX_GREETING_LENGTH = 6
        if len(cleaned_text) > MAX_GREETING_LENGTH:
            return False
        
        # Define greeting keywords
        greeting_keywords = [
            "你好", "您好", "hello", "hi", "嗨", "哈喽", 
            "早上好", "下午好", "晚上好", "晚安",
            "在吗", "在不在", "在线吗",
            "hey", "嘿"
        ]
        
        # Check if any greeting keyword is contained in the text
        for keyword in greeting_keywords:
            if keyword in cleaned_text:
                return True
        
        return False
    
    def is_simple_thanks(self, text: str) -> bool:
        """
        Check if the text is a simple thanks expression that doesn't need AI processing.
        Uses keyword matching with length limit to catch various thank you combinations.
        
        Args:
            text: User input text
            
        Returns:
            True if it's a simple thanks expression, False otherwise
        """
        if not text:
            return False
        
        # Clean and normalize the text
        cleaned_text = text.strip().lower()
        
        # Check if text contains Chinese characters
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in cleaned_text)
        
        # Set different length limits for Chinese and English
        MAX_THANKS_LENGTH = 6 if has_chinese else 10
        if len(cleaned_text) > MAX_THANKS_LENGTH:
            return False
        
        # Define thanks keywords
        thanks_keywords = [
            "谢谢", "谢了", "感谢", "多谢", "谢谢你", "谢谢您",
            "感谢你", "感谢您", "非常感谢", "十分感谢",
            "thanks", "thank you", "thx", "ty", "thks",
            "谢", "谢啦", "辛苦了", "辛苦", "赞", "cool",
            "棒", "好的", "ok", "okay"
        ]
        
        # Check if any thanks keyword is contained in the text
        for keyword in thanks_keywords:
            if keyword in cleaned_text:
                return True
        
        return False
    
    def is_stats_query(self, text: str) -> bool:
        """
        Check if the text is a query for conversation statistics.
        
        Args:
            text: User input text
            
        Returns:
            True if it's a stats query, False otherwise
        """
        if not text:
            return False
        
        return text.strip().lower() in ["剩余次数", "查询次数", "还有几次", "次数"]
    
    def handle_predefined_message(self, text: str, user_id: str, remaining_conversations: int) -> Optional[Tuple[str, str]]:
        """
        Handle predefined messages and return appropriate response.
        
        Args:
            text: User input text
            user_id: User ID for logging
            remaining_conversations: Number of remaining conversations today
            
        Returns:
            Tuple of (response_text, message_type) if handled, None otherwise
        """
        if self.is_stats_query(text):
            used = self.daily_limit - remaining_conversations
            response = self.stats_response_template.format(
                used=used,
                remaining=remaining_conversations,
                daily_limit=self.daily_limit
            )
            return response, "stats"
        
        elif self.is_simple_greeting(text):
            # log_info(f"Responded to greeting from {user_id} with predefined message")
            return self.greeting_response, "greeting"
        
        elif self.is_simple_thanks(text):
            # log_info(f"Responded to thanks from {user_id} with predefined message")
            return self.thanks_response, "thanks"
        
        return None
    
    def get_subscribe_response(self, remaining_conversations: int) -> str:
        """
        Get the subscribe welcome message.
        
        Args:
            remaining_conversations: Number of remaining conversations today
            
        Returns:
            Subscribe welcome message
        """
        return self.subscribe_response_template.format(
            daily_limit=self.daily_limit,
            remaining=remaining_conversations
        )
    
    def add_greeting_keyword(self, keyword: str):
        """
        Add a new greeting keyword (for future extensibility).
        
        Args:
            keyword: New greeting keyword to add
        """
        # This could be implemented to dynamically add keywords
        # For now, just a placeholder for future enhancement
        pass
    
    def add_thanks_keyword(self, keyword: str):
        """
        Add a new thanks keyword (for future extensibility).
        
        Args:
            keyword: New thanks keyword to add
        """
        # This could be implemented to dynamically add keywords
        # For now, just a placeholder for future enhancement
        pass


# Global instance for easy access
_predefined_handler = None
_handler_lock = asyncio.Lock()

async def get_predefined_handler() -> PredefinedMessageHandler:
    """
    Get the singleton predefined message handler with thread/async safety.
    Uses double-checked locking pattern for optimal performance.
    
    Returns:
        PredefinedMessageHandler instance
    """
    global _predefined_handler
    
    # First check without lock for performance (most common case)
    if _predefined_handler is not None:
        return _predefined_handler
    
    # Double-checked locking to ensure thread safety
    async with _handler_lock:
        if _predefined_handler is None:
            _predefined_handler = PredefinedMessageHandler()
    
    return _predefined_handler
