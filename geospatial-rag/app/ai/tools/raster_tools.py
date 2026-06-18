from langchain_core.tools import tool
import logging
from app.livy_client import livy_client

logger = logging.getLogger(__name__)

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
    
    # Generate the Scala script based on the user's hbase-geotrellis ingest code
    scala_script = f"""
object Script {{
  def run(): Unit = {{
import geotrellis.raster._
import geotrellis.spark._
import geotrellis.store.hbase._
import geotrellis.spark.store.hbase._
import geotrellis.layer._
import geotrellis.raster.io.geotiff._
import geotrellis.spark.tiling._
import geotrellis.store.avro.AvroRecordCodec
import geotrellis.store.index.ZCurveKeyIndexMethod
import geotrellis.store.LayerId
import org.apache.hadoop.hbase.HBaseConfiguration

val path: String = "{file_path}"
val geoTiff: SinglebandGeoTiff = GeoTiffReader.readSingleband(path)

val tile = geoTiff.tile match {{
  case t: UByteGeoTiffTile => t.toArrayTile
  case other => other
}}

val hbaseConfig = HBaseConfiguration.create()
hbaseConfig.set("hbase.zookeeper.quorum", "zookeeper")
hbaseConfig.set("hbase.zookeeper.property.clientPort", "2181")
val instance = HBaseInstance(hbaseConfig)

val attrTable = "{catalog_table}_attr"
val layerTable = "{catalog_table}_data"

val store = HBaseAttributeStore(instance, attrTable)
val writer = HBaseLayerWriter(store, layerTable)

val layerId = LayerId("{layer_name}", 0)

val layout = LayoutDefinition(geoTiff.extent, TileLayout(1, 1, geoTiff.tile.cols, geoTiff.tile.rows))
val tileLayerMetadata = TileLayerMetadata(
  cellType = geoTiff.tile.cellType,
  layout = layout,
  extent = geoTiff.extent,
  crs = geoTiff.crs,
  bounds = KeyBounds(SpatialKey(0, 0), SpatialKey(0, 0))
)

val rdd: TileLayerRDD[SpatialKey] = ContextRDD(sc.parallelize(Seq((SpatialKey(0, 0), tile))), tileLayerMetadata)

writer.write[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](layerId, rdd, ZCurveKeyIndexMethod)

println("RASTER_INGESTION_SUCCESS")
  }}
}}
// End of scala script
"""
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
    scala_script = f"""
object Script {{
  def run(): Unit = {{
import geotrellis.raster._
import geotrellis.spark._
import geotrellis.store.hbase._
import geotrellis.spark.store.hbase._
import geotrellis.layer._
import geotrellis.raster.io.geotiff._
import geotrellis.vector.Extent
import geotrellis.store.Intersects
import geotrellis.store.LayerId
import org.apache.hadoop.hbase.HBaseConfiguration

val hbaseConfig = HBaseConfiguration.create()
hbaseConfig.set("hbase.zookeeper.quorum", "zookeeper")
hbaseConfig.set("hbase.zookeeper.property.clientPort", "2181")
val instance = HBaseInstance(hbaseConfig)

val attrTable = "{catalog_table}_attr"
val attributeStore = HBaseAttributeStore(instance, attrTable)
val reader = HBaseLayerReader(attributeStore)

val layerId = LayerId("{layer_name}", 0)
val queryExtent = Extent({min_x}, {min_y}, {max_x}, {max_y})

try {{
  val layer = reader.query[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](layerId).where(Intersects(queryExtent)).result
  val stitched = layer.stitch()
  val cropped = stitched.crop(queryExtent)
  GeoTiff(cropped, layer.metadata.crs).write("{output_path}")
  println("RASTER_RETRIEVE_SUCCESS: Saved to {output_path}")
}} catch {{
  case e: Exception => println(s"RASTER_RETRIEVE_ERROR: ${{e.getMessage}}")
}}
  }}
}}
// End of scala script
"""
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
    scala_script = f"""
object Script {{
  def run(): Unit = {{
import geotrellis.spark.store.hbase._
import geotrellis.store.hbase._
import geotrellis.store.LayerId
import geotrellis.spark._
import geotrellis.layer._
import org.apache.hadoop.hbase.HBaseConfiguration

val hbaseConfig = HBaseConfiguration.create()
hbaseConfig.set("hbase.zookeeper.quorum", "zookeeper")
hbaseConfig.set("hbase.zookeeper.property.clientPort", "2181")
val instance = HBaseInstance(hbaseConfig)
val attributeStore = HBaseAttributeStore(instance, "{catalog_table}_attr")
val layerId = LayerId("{layer_name}", 0)

try {{
  val metadata = attributeStore.readMetadata[TileLayerMetadata[SpatialKey]](layerId)
  println("RASTER_METADATA_SUCCESS:")
  println(s"CRS: ${{metadata.crs}}")
  println(s"Extent: ${{metadata.extent}}")
  println(s"CellType: ${{metadata.cellType}}")
  println(s"Bounds: ${{metadata.bounds}}")
}} catch {{
  case e: Exception => println(s"RASTER_METADATA_ERROR: ${{e.getMessage}}")
}}
  }}
}}
// End of scala script
"""
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
    scala_script = f"""
object Script {{
  def run(): Unit = {{
import geotrellis.raster._
import geotrellis.spark._
import geotrellis.store.hbase._
import geotrellis.spark.store.hbase._
import geotrellis.layer._
import geotrellis.store.LayerId
import geotrellis.store.index.ZCurveKeyIndexMethod
import org.apache.hadoop.hbase.HBaseConfiguration

val hbaseConfig = HBaseConfiguration.create()
hbaseConfig.set("hbase.zookeeper.quorum", "zookeeper")
hbaseConfig.set("hbase.zookeeper.property.clientPort", "2181")
val instance = HBaseInstance(hbaseConfig)

val attrTable = "{catalog_table}_attr"
val layerTable = "{catalog_table}_data"
val attributeStore = HBaseAttributeStore(instance, attrTable)
val reader = HBaseLayerReader(attributeStore)
val writer = HBaseLayerWriter(attributeStore, layerTable)

val layerId = LayerId("{layer_name}", 0)
val rdd = reader.read[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](layerId)

val processedRdd = rdd.withContext {{ rdd =>
  rdd.mapValues {{ tile =>
    tile.map {{ p =>
      if ("{operation}" == "threshold") {{
        if (p > {value}) 1 else 0
      }} else if ("{operation}" == "multiply") {{
        (p * {value}).toInt
      }} else if ("{operation}" == "add") {{
        (p + {value}).toInt
      }} else {{
        p
      }}
    }}
  }}
}}

val outLayerId = LayerId("{output_layer_name}", 0)
writer.write[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](outLayerId, processedRdd, ZCurveKeyIndexMethod)
println("RASTER_MATH_SUCCESS")
  }}
}}
// End of scala script
"""
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
