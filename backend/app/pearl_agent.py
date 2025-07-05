import os
import configparser

from langchain.chat_models import init_chat_model
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureOpenAIEmbeddings
from langgraph.prebuilt import create_react_agent

from .tools import tools

config = configparser.ConfigParser()

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
if not config.read(config_path, encoding='utf-8'):
    raise RuntimeError(f'Config file not found: {config_path}')
if not config.has_section('azure_openai'):
    raise RuntimeError(f'[azure_openai] section not found in {config_path}')
os.environ["AZURE_OPENAI_API_KEY"] = config.get('azure_openai', 'api_key')
os.environ["AZURE_OPENAI_ENDPOINT"] = config.get('azure_openai', 'endpoint')
os.environ["OPENAI_API_VERSION"] = config.get('azure_openai', 'api_version')

local_vector_store_path = config.get('notion',
    'local_vector_store_path', fallback='/data/notion_vectorstore')

SYSTEM_PROMPT = (
    "你是一位优雅、专业的珍珠科普客服，只回答珍珠相关的科普问题。"
    "如果用户问你是谁、你的身份、你的名字等，请自我介绍为：我是悦华珍珠AI助手宝儿，可以回答你任何和珍珠相关的问题。"
    "如果用户的问题涉及珍珠相关内容（包括珍珠品种、历史、鉴别、养殖、购买、佩戴、护理、文化等），请尽量详细、专业地解答。"
    "**如果用户的问题涉及悦华珍珠或我们家的珍珠（包括悦华珍珠的品牌、款式、价格、购买方式等），必须调用 get_yuehua_pearl_info 工具获取信息。**"
    "调用工具时请根据用户问题选择合适的 query_type 参数："
    "- 询问品牌信息，品牌定位、产品系列、供应商时使用 'brand'"
    "- 询问价格、折扣时使用 'price'"
    "- 询问款式、珍珠类型、定制服务时使用 'style'"
    "- 询问购买方式、商城、实体店时使用 'purchase'"
    "- 询问团队、品牌故事、工艺、活动等其他信息时使用 'other'"
    "- 询问悦华珍珠综合信息或不确定具体类型时使用 'general'"
    "**不允许自行编写悦华珍珠相关内容，必须通过工具获取。**"
    "如果用户的问题与珍珠完全无关（如天气、体育、娱乐、编程等），请礼貌回复：很抱歉，我只能解答珍珠相关的问题。"
    "如果用户提到之前的对话内容，请结合chat_history进行判断和回答。"
)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("user", "{input}")
])

model = init_chat_model(
    "azure_openai:gpt-4.1", # o4-mini
    azure_deployment="gpt-4.1",
)

rac_agent = create_react_agent(
    model=model,
    tools=tools
)

prompt_template_function_agent_specific = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

function_agent = create_openai_functions_agent(model, tools, prompt_template_function_agent_specific)
agent_executor = AgentExecutor(agent=function_agent, tools=tools)

# embeddings = AzureOpenAIEmbeddings(model="azure_openai:text-embedding-3-large")

class PearlAIAgent:
    def __init__(self):
        # Let's use function agent by default
        self.agent = rac_agent
        self.agent_executor = agent_executor
        # self.vectorstore = ... # 向量库已禁用

    def is_yuehua_question(self, question):
        return "悦华珍珠" in question

    def answer(self, question, chat_history=None):
        chat_history = chat_history or []
        
        # React agent
        prompt = prompt_template.invoke({"input": question, "chat_history": chat_history})
        result = rac_agent.invoke(prompt)
        ai_reply = [m.content for m in result["messages"] if m.__class__.__name__ == "AIMessage"][-1]
        
        # Function agent
        # result = self.agent_executor.invoke({"input": question, "chat_history": chat_history})
        # ai_reply = result["output"]
        return ai_reply
