from langchain_core.tools import tool
import asyncio
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def _run_spark_geospatial_task(catalog_table: str, spatial_filter: str) -> str:
    """
    Synchronous function that initializes an ephemeral SparkSession,
    connects to HBase/GeoMesa, runs the calculation, and tears down.
    This runs in a separate thread.
    """
    from pyspark.sql import SparkSession
    from pyspark.conf import SparkConf
    import os
    
    logger.info(f"Initializing ephemeral Spark session for table: {catalog_table}")
    
    # Ensure HADOOP_CONF_DIR is set for HBase configs
    os.environ["HADOOP_CONF_DIR"] = settings.HADOOP_CONF_DIR
    
    conf = SparkConf()
    conf.setMaster(settings.SPARK_MASTER)
    conf.setAppName(f"GeospatialSubAgent-{catalog_table}")
    
    # Network config if running inside docker mapped network
    if settings.SPARK_DRIVER_HOST:
        conf.set("spark.driver.host", settings.SPARK_DRIVER_HOST)
    conf.set("spark.driver.port", str(settings.SPARK_DRIVER_PORT))
    
    # Note: In a true deployment, you would also specify spark.jars here 
    # to distribute the GeoMesa HBase runtime to executors.
    conf.set("spark.jars", f"{settings.GEOMESA_JARS_PATH}/geomesa-hbase-spark-runtime-hbase2_2.12-3.5.2.jar")
    
    spark = None
    try:
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        
        # --- GeoMesa Boilerplate ---
        df = spark.read.format("geomesa") \
            .option("geomesa.data.store", "hbase") \
            .option("hbase.catalog", catalog_table) \
            .load()
        df.createOrReplaceTempView("geo_data")
        
        logger.info(f"Running heavy Spark task on HBase catalog '{catalog_table}' with filter: {spatial_filter}")
        result = spark.sql(f"SELECT count(*) FROM geo_data WHERE st_intersects(geom, st_geomFromWKT('{spatial_filter}'))")
        count = result.collect()[0][0]
        
        return f"Successfully processed geospatial task. Found {count} features matching {spatial_filter} in {catalog_table}."
    
    except Exception as e:
        logger.error(f"Spark job failed: {str(e)}")
        return f"Error executing geospatial task: {str(e)}"
    
    finally:
        if spark:
            spark.stop()
            logger.info("Spark session cleanly terminated.")


@tool
async def geospatial_calculation_tool(catalog_table: str, spatial_filter: str) -> str:
    """
    Sub-agent tool for executing heavy Geospatial Big Data calculations on HBase via Apache Spark.
    Args:
        catalog_table: The HBase catalog table name containing the features.
        spatial_filter: A WKT (Well-Known Text) geometry string to filter by.
    """
    # Wrap the heavy JVM initialization and Spark networking in to_thread 
    # so we don't block the FastAPI async event loop.
    return await asyncio.to_thread(_run_spark_geospatial_task, catalog_table, spatial_filter)


@tool
def ingest_geospatial_data_tool(file_path: str, catalog_table: str, feature_name: str) -> str:
    """
    Sub-agent tool for ingesting geospatial data (like GeoJSON) into GeoMesa HBase.
    Args:
        file_path: The absolute path to the file inside the container (e.g. /datapc/tunisia.geojson).
        catalog_table: The target HBase catalog table name.
        feature_name: The feature type name to assign to the ingested data.
    """
    import subprocess
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


def _run_raster_ingest_task(file_path: str, catalog_table: str, layer_name: str) -> str:
    from pyspark.sql import SparkSession
    from pyspark.conf import SparkConf
    import os
    import geopyspark as gps
    
    logger.info(f"Initializing GeoPySpark session for raster ingest: {file_path}")
    
    os.environ["HADOOP_CONF_DIR"] = settings.HADOOP_CONF_DIR
    
    conf = SparkConf()
    conf.setMaster(settings.SPARK_MASTER)
    conf.setAppName(f"RasterIngestSubAgent-{layer_name}")
    
    if settings.SPARK_DRIVER_HOST:
        conf.set("spark.driver.host", settings.SPARK_DRIVER_HOST)
    conf.set("spark.driver.port", str(settings.SPARK_DRIVER_PORT))
    
    spark = None
    try:
        # GeoPySpark requires its own initialized SparkContext wrapper
        gps_conf = gps.geopyspark_conf(master=settings.SPARK_MASTER, appName=f"RasterIngest-{layer_name}")
        for k, v in conf.getAll():
            gps_conf.set(k, v)
        
        spark = SparkSession.builder.config(conf=gps_conf).getOrCreate()
        
        logger.info(f"Reading raster from {file_path}...")
        # Note: geopyspark needs file:// prefix for local files
        if not file_path.startswith("file://") and not file_path.startswith("hdfs://"):
            file_path = f"file://{file_path}"
            
        raster_layer = gps.geotiff.get(layer_type=gps.LayerType.SPATIAL, uri=file_path)
        
        logger.info("Tiling raster layer...")
        tiled_layer = raster_layer.tile_to_layout(layout=gps.GlobalLayout(), target_crs=3857)
        
        # Write to HBase catalog using URI format
        catalog_uri = f"hbase://zookeeper?table={catalog_table}"
        
        logger.info(f"Writing tiled raster to catalog: {catalog_uri} with layer name: {layer_name}")
        gps.write(uri=catalog_uri, layer_name=layer_name, tiled_raster_layer=tiled_layer)
        
        return f"Successfully ingested raster {file_path} into HBase catalog {catalog_table} under layer {layer_name}."
        
    except Exception as e:
        logger.error(f"Raster ingest failed: {str(e)}")
        return f"Error executing raster ingest: {str(e)}"
    finally:
        if spark:
            spark.stop()
            logger.info("Spark session cleanly terminated.")

@tool
async def ingest_raster_data_tool(file_path: str, catalog_table: str, layer_name: str) -> str:
    """
    Sub-agent tool for ingesting raster data (like GeoTIFFs) into a distributed GeoTrellis catalog in HBase.
    Args:
        file_path: The absolute path or URI to the raster file (e.g. /datapc/raster.tif).
        catalog_table: The target HBase catalog table name.
        layer_name: The layer name to assign to the ingested raster data.
    """
    return await asyncio.to_thread(_run_raster_ingest_task, file_path, catalog_table, layer_name)
