object Script {
  def run(): Unit = {
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

val path: String = "__file_path__"
val geoTiff: SinglebandGeoTiff = GeoTiffReader.readSingleband(path)

val tile = geoTiff.tile match {
  case t: UByteGeoTiffTile => t.toArrayTile
  case other => other
}

val hbaseConfig = HBaseConfiguration.create()
hbaseConfig.set("hbase.zookeeper.quorum", "zookeeper")
hbaseConfig.set("hbase.zookeeper.property.clientPort", "2181")
val instance = HBaseInstance(hbaseConfig)

val attrTable = "__catalog_table___attr"
val layerTable = "__catalog_table___data"

val store = HBaseAttributeStore(instance, attrTable)
val writer = HBaseLayerWriter(store, layerTable)

val layerId = LayerId("__layer_name__", 0)

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
  }
}
// End of scala script
