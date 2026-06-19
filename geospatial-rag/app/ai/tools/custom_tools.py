from langchain_core.tools import tool
import logging
from app.livy_client import livy_client

logger = logging.getLogger(__name__)

@tool
async def execute_custom_scala_job_tool(scala_script: str) -> str:
    """
    Sub-agent tool to execute custom Scala/Spark code on the cluster via Livy.
    Use this tool ONLY when your standard templates do not cover the user's request.
    CRITICAL: You MUST use `search_documentation_tool` to lookup the correct GeoTrellis/GeoMesa syntax BEFORE writing custom code with this tool to avoid syntax and logic errors.
    
    Args:
        scala_script: The complete, raw Scala code to execute. It must be a valid script that can be run in the spark-shell.
    """
    logger.info("Executing custom Scala job...")
    try:
        output = await livy_client.execute_scala_code(scala_script)
        return f"Custom Scala Job Output:\n{output}"
    except Exception as e:
        logger.error(f"Custom Scala job failed: {e}")
        return f"Error executing custom Scala job: {str(e)}"
