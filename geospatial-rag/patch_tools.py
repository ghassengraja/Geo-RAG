import os

path = "/home/ghassen/Bureau/geospatial-rag-app/geospatial-rag/app/ai/tools/raster_tools.py"
with open(path, "r") as f:
    content = f.read()

# Remove --packages from the spark-shell command
content = content.replace(
    ", '--packages', 'org.locationtech.geotrellis:geotrellis-spark_2.12:3.5.1,org.locationtech.geotrellis:geotrellis-spark-store-hbase_2.12:3.5.1'",
    ""
)

with open(path, "w") as f:
    f.write(content)
print("Removed --packages")
