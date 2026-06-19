object Script {
  def run(): Unit = {
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

val attrTable = "__catalog_table___attr"
val layerTable = "__catalog_table___data"
val attributeStore = HBaseAttributeStore(instance, attrTable)
val reader = HBaseLayerReader(attributeStore)
val writer = HBaseLayerWriter(attributeStore, layerTable)

val layerId = LayerId("__layer_name__", 0)
val rdd = reader.read[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](layerId)

val processedRdd = rdd.withContext { rdd =>
  rdd.mapValues { tile =>
    tile.map { p =>
      if ("__operation__" == "threshold") {
        if (p > __value__) 1 else 0
      } else if ("__operation__" == "multiply") {
        (p * __value__).toInt
      } else if ("__operation__" == "add") {
        (p + __value__).toInt
      } else {
        p
      }
    }
  }
}

val outLayerId = LayerId("__output_layer_name__", 0)
writer.write[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](outLayerId, processedRdd, ZCurveKeyIndexMethod)
println("RASTER_MATH_SUCCESS")
  }
}
// End of scala script
