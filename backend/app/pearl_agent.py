import os
import configparser

from langchain.chat_models import init_chat_model
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
    "悦华珍珠是我们公司正在推的品牌标识，如果用户的问题设计到我们自己的珍珠相关内容比如悦华珍珠品牌相关的咨询，请使用tools进行回答，不允许编造。"
    "如果用户的问题与珍珠完全无关（如天气、体育、娱乐、编程等），请礼貌回复：很抱歉，我只能解答珍珠相关的问题。"
    "如果用户提到之前的对话内容，请结合chat_history进行判断和回答。"
)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("user", "{input}")
])

model = init_chat_model(
    "azure_openai:o4-mini",
    azure_deployment="o4-mini",
)

agent_node = create_react_agent(
    model=model,
    tools=tools
)

embeddings = AzureOpenAIEmbeddings(model="azure_openai:text-embedding-3-large")


class PearlAIAgent:
    def __init__(self):
        self.agent = agent_node
        # self.vectorstore = ... # 向量库已禁用

    def is_yuehua_question(self, question):
        return "悦华珍珠" in question

    def answer(self, question, user_id=None, chat_history=None):
        chat_history = chat_history or []
        prompt = prompt_template.invoke({"input": question, "chat_history": chat_history})
        result = self.agent.invoke(prompt)
        ai_reply = [m.content for m in result["messages"] if m.__class__.__name__ == "AIMessage"][-1]
        return ai_reply
