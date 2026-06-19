from langchain_core.tools import tool
import logging
from app.ai.llm import get_embedding_model
from langchain_chroma import Chroma
import os

logger = logging.getLogger(__name__)

# Initialize ChromaDB vector store
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "../../../data/chroma_db")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

try:
    vector_store = Chroma(
        collection_name="documentation",
        embedding_function=get_embedding_model(),
        persist_directory=CHROMA_PERSIST_DIR
    )
except Exception as e:
    logger.error(f"Failed to initialize Chroma vector store: {e}")
    vector_store = None


@tool
async def search_documentation_tool(query: str) -> str:
    """
    Sub-agent tool for retrieving GeoTrellis and GeoMesa library documentation.
    CRITICAL: Use this tool BEFORE writing any custom Scala code to ensure you use the correct classes, methods, and syntax.
    
    Args:
        query: A highly specific technical search query (e.g., "How to use ZCurveKeyIndexMethod", "Syntax for masking a TileLayerRDD").
    """
    logger.info(f"Searching PDF documentation for: {query}")
    
    if not vector_store:
        return "Error: Documentation vector store is not initialized. Ensure the indexer has been run."
        
    try:
        # Search the ChromaDB
        results = await vector_store.asimilarity_search(query, k=3)
        
        if not results:
            return "No relevant documentation found. Try rewording your query."
            
        formatted_docs = []
        for i, doc in enumerate(results):
            source = doc.metadata.get("source", "Unknown Source")
            page = doc.metadata.get("page", "Unknown Page")
            formatted_docs.append(f"--- Result {i+1} (Source: {source}, Page: {page}) ---\n{doc.page_content}\n")
            
        return "\n".join(formatted_docs)
        
    except Exception as e:
        logger.error(f"Documentation search failed: {e}")
        return f"Error searching documentation: {str(e)}"

rag_tools = [search_documentation_tool]
