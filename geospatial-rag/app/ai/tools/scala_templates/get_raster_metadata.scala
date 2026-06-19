object Script {
  def run(): Unit = {
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
val attributeStore = HBaseAttributeStore(instance, "__catalog_table___attr")
val layerId = LayerId("__layer_name__", 0)

try {
  val metadata = attributeStore.readMetadata[TileLayerMetadata[SpatialKey]](layerId)
  println("RASTER_METADATA_SUCCESS:")
  println(s"CRS: ${metadata.crs}")
  println(s"Extent: ${metadata.extent}")
  println(s"CellType: ${metadata.cellType}")
  println(s"Bounds: ${metadata.bounds}")
} catch {
  case e: Exception => println(s"RASTER_METADATA_ERROR: ${e.getMessage}")
}
  }
}
// End of scala script
