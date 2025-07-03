from app.logger.logger import log_error, log_info

try:
    """
    Let's disable the Notion vector store sync for now.
    """
    # log_info("[Startup] 开始同步Notion知识库到本地向量存储...")
    from app.notion.data_syncer import NotionDBDataSyncer
    # NotionDBDataSyncer.persist_vector_store()
except Exception as e:
    log_error(f"[Startup] Notion知识库同步失败: {str(e)}", e)