object Script {
  def run(): Unit = {
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

val attrTable = "__catalog_table___attr"
val attributeStore = HBaseAttributeStore(instance, attrTable)
val reader = HBaseLayerReader(attributeStore)

val layerId = LayerId("__layer_name__", 0)
val queryExtent = Extent(__min_x__, __min_y__, __max_x__, __max_y__)

try {
  val layer = reader.query[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](layerId).where(Intersects(queryExtent)).result
  val stitched = layer.stitch()
  val cropped = stitched.crop(queryExtent)
  GeoTiff(cropped, layer.metadata.crs).write("__output_path__")
  println("RASTER_RETRIEVE_SUCCESS: Saved to __output_path__")
} catch {
  case e: Exception => println(s"RASTER_RETRIEVE_ERROR: ${e.getMessage}")
}
  }
}
// End of scala script
