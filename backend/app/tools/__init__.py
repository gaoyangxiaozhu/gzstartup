"""
Yuehua Pearl Agent related tool functions
Merge multiple original tools into a parameterized unified tool to support different types of queries
Use the data access layer to read content from markdown files
"""

import asyncio
from langchain_core.tools import tool
from ..logger.logger import log_error, log_warn, log_info
from ..data import get_yuehua_content

@tool
def get_yuehua_pearl_info(query_type: str = "general") -> str:
    """
    获取悦华珍珠相关信息的统一工具。
    
    Args:
        query_type: 查询类型，可以是：
            - "brand": 品牌定位、产品系列、供应商等
            - "price": 价格信息、折扣等
            - "style": 款式信息、珍珠类型、定制服务等  
            - "purchase": 购买方式、商城、小程序、实体店等
            - "other": 其他信息（团队、品牌故事、工艺、活动等）
            - "general": 通用信息（会返回所有相关信息）
    
    Returns:
        str: 对应的悦华珍珠信息
    """
    try:
        log_info(f"Getting yuehua pearl info for query_type: {query_type}")
        
        valid_types = ["brand", "price", "style", "purchase", "other", "general"]
        if query_type not in valid_types:
            log_warn(f"Unknown query_type: {query_type}, falling back to 'other'")
            # For invalid query types, other type content is returned by default to avoid displaying 
            # technical error messages to users
            query_type = "other"
        
        content_type = query_type
        if query_type == "price":
            content_type = "pricing"
        elif query_type == "style":
            content_type = "styles"
        elif query_type == "general":
            try:
                brand_content = asyncio.run(get_yuehua_content("brand"))
                style_content = asyncio.run(get_yuehua_content("styles"))
                price_content = asyncio.run(get_yuehua_content("pricing"))
                purchase_content = asyncio.run(get_yuehua_content("purchase"))
                
                return f"""关于悦华珍珠的详细信息：

【品牌介绍】
{brand_content}

【产品款式】
{style_content}

【价格信息】
{price_content}

【购买方式】
{purchase_content}

如有其他问题，请加沛姐微信咨询。"""
            except Exception as e:
                log_error(f"Error getting general info: {str(e)}")
                return "抱歉，获取综合信息时出现错误，请稍后重试。"
        
        # Using the Data Access Layer to Get Content
        content = asyncio.run(get_yuehua_content(content_type))
        
        if content is None:
            log_error(f"Failed to load content for query_type: {query_type}")
            return "抱歉，出了点问题哈，暂时无法获取悦华珍珠相关信息，请稍后重试或加沛姐微信咨询。"
        
        return content
            
    except Exception as e:
        log_error(f"Error in get_yuehua_pearl_info: {str(e)}")
        return "抱歉，出了点问题哈，暂时无法获取悦华珍珠相关信息，请稍后重试或加沛姐微信咨询。"

tools = [
    get_yuehua_pearl_info
]