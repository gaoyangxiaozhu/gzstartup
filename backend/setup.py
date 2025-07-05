from setuptools import setup, find_packages

setup(
    name="gzpearlagent-backend",
    version="0.1.0",
    description="GZPearlAgent FastAPI backend",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        'fastapi==0.115.4',
        'uvicorn==0.30.1',
        'tornado>=6.1',
        'toml>=0.10.2',
        'pydantic>=2.10.5',
        'langchain>=0.3.26',
        'langgraph>=0.5.0',
        'langchain-openai>=0.3.27',
        'langchain-core>=0.3.26',
        'langchain-community>=0.3.26',
        'notion-client>=2.4.0',
        'faiss-cpu>=1.7.4',
        'httpx>=0.27.0',
        'python-dotenv>=1.0.0',
        'openai>=1.0.0',
        'starlette>=0.38.0',
        'pytest>=7.0.0',
        'aiofiles>=23.0.0'
    ],
    package_data={
        'app': ['config.ini', 'data/markdown/*.md'],
    },
    include_package_data=True,
)
