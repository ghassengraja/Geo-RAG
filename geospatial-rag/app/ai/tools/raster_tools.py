from langchain_core.tools import tool
import logging
import os
from app.livy_client import livy_client

logger = logging.getLogger(__name__)

def load_scala_template(template_name: str, **kwargs) -> str:
    template_path = os.path.join(os.path.dirname(__file__), "scala_templates", template_name)
    with open(template_path, "r") as f:
        template = f.read()
    for k, v in kwargs.items():
        template = template.replace(f"__{k}__", str(v))
    return template

@tool
async def ingest_raster_data_tool(file_path: str, catalog_table: str, layer_name: str) -> str:
    """
    Sub-agent tool for ingesting raster data (like GeoTIFFs) into a distributed GeoTrellis catalog in HBase.
    Args:
        file_path: The absolute path to the raster file inside the container (e.g. /datapc/R0040496_red.tif).
        catalog_table: The target HBase catalog table name.
        layer_name: The layer name to assign to the ingested raster data.
    """
    logger.info(f"Ingesting raster {file_path} into {catalog_table} as {layer_name} using spark-shell...")
    
    # Load and format the Scala script from template
    scala_script = load_scala_template(
        "ingest_raster.scala",
        file_path=file_path,
        catalog_table=catalog_table,
        layer_name=layer_name
    )
    
    try:
        output = await livy_client.execute_scala_code(scala_script)
        if "RASTER_INGESTION_SUCCESS" in output:
            return f"Successfully ingested raster {file_path} into HBase catalog {catalog_table} under layer {layer_name}."
        else:
            return f"Raster ingestion might have failed. Output:\n{output}"
    except Exception as e:
        logger.error(f"Unexpected error during raster ingest: {e}")
        return f"Unexpected error during raster ingest: {str(e)}"

@tool
async def retrieve_raster_tile_tool(catalog_table: str, layer_name: str, min_x: float, min_y: float, max_x: float, max_y: float, output_path: str) -> str:
    """
    Sub-agent tool to extract a specific bounded spatial area from a massive ingested GeoTrellis raster layer.
    Args:
        catalog_table: The target HBase catalog table name.
        layer_name: The layer name inside the catalog.
        min_x: Minimum X (Longitude) of the bounding box.
        min_y: Minimum Y (Latitude) of the bounding box.
        max_x: Maximum X (Longitude) of the bounding box.
        max_y: Maximum Y (Latitude) of the bounding box.
        output_path: Absolute path inside the spark container to save the extracted GeoTIFF (e.g. /datapc/cropped.tif).
    """
    logger.info(f"Retrieving cropped tile from {layer_name} in {catalog_table} to {output_path}...")
    
    scala_script = load_scala_template(
        "retrieve_raster_tile.scala",
        catalog_table=catalog_table,
        layer_name=layer_name,
        min_x=min_x,
        min_y=min_y,
        max_x=max_x,
        max_y=max_y,
        output_path=output_path
    )
    
    try:
        output = await livy_client.execute_scala_code(scala_script)
        if "RASTER_RETRIEVE_SUCCESS" in output:
            return f"Successfully retrieved cropped tile and saved to {output_path}."
        else:
            return f"Failed to retrieve tile. Output:\n{output}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@tool
async def get_raster_metadata_tool(catalog_table: str, layer_name: str) -> str:
    """
    Sub-agent tool to quickly retrieve the CRS, spatial extent, and cell resolution of an ingested GeoTrellis raster.
    Args:
        catalog_table: The target HBase catalog table name.
        layer_name: The layer name inside the catalog.
    """
    logger.info(f"Getting metadata for {layer_name} in {catalog_table}...")
    
    scala_script = load_scala_template(
        "get_raster_metadata.scala",
        catalog_table=catalog_table,
        layer_name=layer_name
    )
    
    try:
        output = await livy_client.execute_scala_code(scala_script)
        if "RASTER_METADATA_SUCCESS" in output:
            info = output.split("RASTER_METADATA_SUCCESS:\n")[-1].strip()
            return f"Raster Metadata:\n{info}"
        else:
            return f"Failed to retrieve metadata. Output:\n{output}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@tool
async def calculate_map_algebra_tool(catalog_table: str, layer_name: str, operation: str, value: float, output_layer_name: str) -> str:
    """
    Sub-agent tool to perform distributed pixel math (Local Map Algebra) across the cluster.
    Args:
        catalog_table: The target HBase catalog table name.
        layer_name: The layer name to process.
        operation: The math operation to perform ('threshold', 'multiply', 'add').
        value: The scalar value for the operation.
        output_layer_name: The new layer name to save the results under.
    """
    logger.info(f"Running {operation} with {value} on {layer_name}, saving to {output_layer_name}...")
    
    scala_script = load_scala_template(
        "calculate_map_algebra.scala",
        catalog_table=catalog_table,
        layer_name=layer_name,
        operation=operation,
        value=value,
        output_layer_name=output_layer_name
    )
    
    try:
        output = await livy_client.execute_scala_code(scala_script)
        if "RASTER_MATH_SUCCESS" in output:
            return f"Successfully processed Map Algebra ({operation} {value}) and saved to layer '{output_layer_name}'."
        else:
            return f"Failed to perform Map Algebra. Output:\n{output}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

raster_tools = [ingest_raster_data_tool, retrieve_raster_tile_tool, get_raster_metadata_tool, calculate_map_algebra_tool]
