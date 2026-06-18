from langchain_core.tools import tool
import subprocess
import logging

logger = logging.getLogger(__name__)

@tool
def geospatial_calculation_tool(catalog_table: str, spatial_filter: str) -> str:
    """
    Sub-agent tool for executing Geospatial calculations on HBase via GeoMesa CLI.
    Args:
        catalog_table: The HBase catalog table name containing the features.
        spatial_filter: A WKT (Well-Known Text) geometry string to filter by.
    """
    logger.info(f"Running calculation on {catalog_table} with filter {spatial_filter}")
    try:
        # First, get the feature type name from the catalog
        cmd_get_feature = ["docker", "exec", "hbase-master", "geomesa-hbase", "get-type-names", "-c", catalog_table]
        res_feat = subprocess.run(cmd_get_feature, capture_output=True, text=True, check=True)
        
        # Output usually contains the feature names, one per line. Let's take the first valid line.
        lines = [line.strip() for line in res_feat.stdout.split("\n") if line.strip() and not "INFO" in line and not "WARN" in line]
        if not lines:
            return f"Error: Could not find any feature types in catalog {catalog_table}."
        feature_name = lines[0]
        
        # Now run the export with the spatial filter
        cmd_export = [
            "docker", "exec", "hbase-master", "geomesa-hbase", "export",
            "-c", catalog_table,
            "-f", feature_name,
            "-q", f"INTERSECTS(geom, {spatial_filter})",
            "--no-header"
        ]
        res_export = subprocess.run(cmd_export, capture_output=True, text=True, check=True)
        
        # Count the number of features returned
        features = [line for line in res_export.stdout.split("\n") if line.strip()]
        count = len(features)
        
        return f"Successfully processed geospatial task. Found {count} features matching {spatial_filter} in {catalog_table}."
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Calculation failed: {e.stderr}")
        return f"Error executing geospatial task: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {str(e)}"


@tool
def ingest_geospatial_data_tool(file_path: str, catalog_table: str, feature_name: str) -> str:
    """
    Sub-agent tool for ingesting geospatial data (like GeoJSON) into GeoMesa HBase.
    Args:
        file_path: The absolute path to the file inside the container (e.g. /datapc/tunisia.geojson).
        catalog_table: The target HBase catalog table name.
        feature_name: The feature type name to assign to the ingested data.
    """
    logger.info(f"Ingesting {file_path} into {catalog_table} as {feature_name} using GeoMesa CLI...")
    try:
        cmd = [
            "docker", "exec", "hbase-master",
            "geomesa-hbase", "ingest",
            "--force",
            "-c", catalog_table,
            "-f", feature_name,
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Successfully ingested {file_path} into {catalog_table}. Output: {result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Ingest failed: {e.stderr}")
        return f"Failed to ingest data. Error: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error during ingest: {e}")
        return f"Unexpected error during ingest: {str(e)}"

@tool
def list_spatial_files_tool() -> str:
    """
    Sub-agent tool for listing all available spatial data catalogs and tables stored in HBase.
    """
    logger.info("Listing HBase tables to find spatial catalogs...")
    try:
        cmd = [
            "docker", "exec", "hbase-master",
            "sh", "-c", "echo 'list' | hbase shell -n"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Available HBase tables (catalogs):\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to list tables: {e.stderr}")
        return f"Failed to list tables. Error: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {str(e)}"

@tool
def describe_schema_tool(catalog_table: str, feature_name: str) -> str:
    """
    Sub-agent tool to retrieve the schema, Coordinate Reference System (CRS), and attributes of a GeoMesa feature type.
    Args:
        catalog_table: The HBase catalog table name.
        feature_name: The feature type name to inspect.
    """
    logger.info(f"Describing schema for {feature_name} in {catalog_table}...")
    try:
        cmd = ["docker", "exec", "hbase-master", "geomesa-hbase", "describe-schema", "-c", catalog_table, "-f", feature_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Schema for {feature_name}:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Describe schema failed: {e.stderr}")
        return f"Failed to describe schema. Error: {e.stderr}"

@tool
def get_feature_names_tool(catalog_table: str) -> str:
    """
    Sub-agent tool to list all the feature types (layers) stored inside a specific GeoMesa catalog table.
    Args:
        catalog_table: The HBase catalog table name.
    """
    logger.info(f"Getting feature names for catalog {catalog_table}...")
    try:
        cmd = ["docker", "exec", "hbase-master", "geomesa-hbase", "get-type-names", "-c", catalog_table]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Feature types in {catalog_table}:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Get feature names failed: {e.stderr}")
        return f"Failed to get feature names. Error: {e.stderr}"

@tool
def export_spatial_data_tool(catalog_table: str, feature_name: str, max_features: int = 5, cql_filter: str = "") -> str:
    """
    Sub-agent tool to extract a subset of data (or the whole dataset) into GeoJSON format.
    Args:
        catalog_table: The HBase catalog table name.
        feature_name: The feature type name to export.
        max_features: The maximum number of records to export (default 5). Keep it small for inspection.
        cql_filter: (Optional) A CQL filter to subset the data (e.g. 'BBOX(geom, -74, 40, -73, 41)').
    """
    logger.info(f"Exporting up to {max_features} features from {feature_name} in {catalog_table}...")
    try:
        cmd = [
            "docker", "exec", "hbase-master", 
            "geomesa-hbase", "export", 
            "-c", catalog_table, 
            "-f", feature_name, 
            "-F", "json", 
            "-m", str(max_features)
        ]
        if cql_filter:
            cmd.extend(["-q", cql_filter])
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Exported GeoJSON Data:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Export failed: {e.stderr}")
        return f"Failed to export data. Error: {e.stderr}"

@tool
def analyze_stats_tool(catalog_table: str, feature_name: str, stat_type: str = "bounds") -> str:
    """
    Sub-agent tool to get statistics (like bounding box or feature count) of a GeoMesa dataset.
    Args:
        catalog_table: The HBase catalog table name.
        feature_name: The feature type name to analyze.
        stat_type: The type of statistic to calculate. Options are 'bounds' (for spatial extent) or 'count' (for total features).
    """
    logger.info(f"Calculating {stat_type} for {feature_name} in {catalog_table}...")
    try:
        if stat_type.lower() == "bounds":
            cmd = ["docker", "exec", "hbase-master", "geomesa-hbase", "stats-bounds", "-c", catalog_table, "-f", feature_name]
        elif stat_type.lower() == "count":
            cmd = ["docker", "exec", "hbase-master", "geomesa-hbase", "stats-count", "-c", catalog_table, "-f", feature_name]
        else:
            return "Invalid stat_type. Must be 'bounds' or 'count'."
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return f"Statistics ({stat_type}) for {feature_name}:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        logger.error(f"Stats analysis failed: {e.stderr}")
        return f"Failed to analyze stats. Error: {e.stderr}"


vector_tools = [geospatial_calculation_tool, ingest_geospatial_data_tool, list_spatial_files_tool, describe_schema_tool, get_feature_names_tool, export_spatial_data_tool, analyze_stats_tool]
