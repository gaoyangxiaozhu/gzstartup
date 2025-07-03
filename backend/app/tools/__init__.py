import configparser
import os
import re

from langchain_core.tools import tool

config = configparser.ConfigParser()

config_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')

if not config.read(config_path, encoding='utf-8'):
    raise RuntimeError(f'Config file not found: {config_path}')

# Read notion configuration
notion_token = config.get('notion', 'integration_token')
database_id = config.get('notion', 'database_id')

@tool
def get_yuehua_brand_info() -> str:
    """获取悦华珍珠品牌定位"""
    return """我们是一群喜欢珍珠的90后，希望用珍珠结交每一位爱美的你，悦华珍珠专注于高品质珍珠的设计与销售，致力于将传统珍珠文化与现代时尚完美结合。我们的供应商都来自于诸暨的优质供应商。

我们产品系列包括项链、手链、耳环、戒指等多种饰品形态。从经典单颗珍珠到创意多珠组合，满足不同场合需求。我们也有专业珠宝设计师，可以针对你的需求进行定制化。我们也注重品质把控。严格把控打磨与镶嵌工序，保留珍珠天然光泽。我们的作品均可提供品质检测证书。同时也提供售后保养与专业清洗服务，让你的珍珠常保光彩。"""

@tool
def get_yuehua_price_info() -> str:
    """获取悦华珍珠价格信息"""
    return """悦华珍珠的价格因款式、材质、工艺等因素而异。我们提供从几百元到上万元不等的多种选择，满足不同预算需求。具体价格请加沛姐微信咨询。"""


@tool
def get_yuehua_kind_info() -> str:
    """获取悦华珍珠款式信息"""
    return """悦华珍珠的款式多样，包括经典单颗珍珠项链、手链、耳环，以及创意多珠组合的现代设计。我们也提供定制服务，可以根据你的需求设计独一无二的珍珠饰品。具体款式请加沛姐微信咨询。"""

@tool
def get_yuehua_purchase_info() -> str:
    """获取悦华珍珠购买方式"""
    return """目前我们只支持通过微信团购群购买，暂不支持线上商城。请加沛姐微信获取最新团购信息和购买方式。"""

@tool
def get_yuehua_other_info() -> str:
    """获取悦华珍珠其他信息"""
    return """抱歉这个问题我不太了解，任何关于悦华珍珠的其他问题，欢迎加沛姐微信咨询。"""

tools = [
    get_yuehua_brand_info, 
    get_yuehua_kind_info,
    get_yuehua_price_info, 
    get_yuehua_purchase_info, 
    get_yuehua_other_info
]