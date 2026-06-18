import os
import requests
import time

JARS = {
    "geotrellis-vector_2.12-3.5.1.jar": "https://repo1.maven.org/maven2/org/locationtech/geotrellis/geotrellis-vector_2.12/3.5.1/geotrellis-vector_2.12-3.5.1.jar",
    "jts-core-1.16.1.jar": "https://repo1.maven.org/maven2/org/locationtech/jts/jts-core/1.16.1/jts-core-1.16.1.jar",
    "circe-core_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/io/circe/circe-core_2.12/0.13.0/circe-core_2.12-0.13.0.jar",
    "circe-generic_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/io/circe/circe-generic_2.12/0.13.0/circe-generic_2.12-0.13.0.jar",
    "circe-parser_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/io/circe/circe-parser_2.12/0.13.0/circe-parser_2.12-0.13.0.jar",
    "circe-numbers_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/io/circe/circe-numbers_2.12/0.13.0/circe-numbers_2.12-0.13.0.jar",
    "circe-jawn_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/io/circe/circe-jawn_2.12/0.13.0/circe-jawn_2.12-0.13.0.jar",
    "jawn-parser_2.12-1.0.0.jar": "https://repo1.maven.org/maven2/org/typelevel/jawn-parser_2.12/1.0.0/jawn-parser_2.12-1.0.0.jar",
    "cats-core_2.12-2.1.1.jar": "https://repo1.maven.org/maven2/org/typelevel/cats-core_2.12/2.1.1/cats-core_2.12-2.1.1.jar",
    "geotrellis-layer_2.12-3.5.1.jar": "https://repo1.maven.org/maven2/org/locationtech/geotrellis/geotrellis-layer_2.12/3.5.1/geotrellis-layer_2.12-3.5.1.jar",
    "geotrellis-store_2.12-3.5.1.jar": "https://repo1.maven.org/maven2/org/locationtech/geotrellis/geotrellis-store_2.12/3.5.1/geotrellis-store_2.12-3.5.1.jar",
    "geotrellis-macros_2.12-3.5.1.jar": "https://repo1.maven.org/maven2/org/locationtech/geotrellis/geotrellis-macros_2.12/3.5.1/geotrellis-macros_2.12-3.5.1.jar",
    "geotrellis-util_2.12-3.5.1.jar": "https://repo1.maven.org/maven2/org/locationtech/geotrellis/geotrellis-util_2.12/3.5.1/geotrellis-util_2.12-3.5.1.jar",
    "pureconfig-core_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/com/github/pureconfig/pureconfig-core_2.12/0.13.0/pureconfig-core_2.12-0.13.0.jar",
    "pureconfig-generic_2.12-0.13.0.jar": "https://repo1.maven.org/maven2/com/github/pureconfig/pureconfig-generic_2.12/0.13.0/pureconfig-generic_2.12-0.13.0.jar",
    "monocle-core_2.12-1.5.1.jar": "https://repo1.maven.org/maven2/com/github/julien-truffaut/monocle-core_2.12/1.5.1/monocle-core_2.12-1.5.1.jar",
    "monocle-macro_2.12-1.5.1.jar": "https://repo1.maven.org/maven2/com/github/julien-truffaut/monocle-macro_2.12/1.5.1/monocle-macro_2.12-1.5.1.jar"
}

out_dir = "/home/ghassen/Bureau/geospatial-rag-app/geotrellis_jars"
os.makedirs(out_dir, exist_ok=True)

for name, url in JARS.items():
    path = os.path.join(out_dir, name)
    if os.path.exists(path):
        print(f"Already have {name}")
        continue
    
    print(f"Downloading {name}...")
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Success: {name}")
            break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
