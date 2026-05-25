import json
import os
from shapely.geometry import shape


def main():
    geojson_path = "src/state_filter/data/us_states.geojson"
    output_path = "src/state_filter/data/bounding_boxes.json"

    if not os.path.exists(geojson_path):
        print(f"Error: GeoJSON file not found at {geojson_path}")
        return

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    bboxes = {}
    for feature in data.get("features", []):
        state_name = feature["properties"]["name"]
        geom = shape(feature["geometry"])
        min_lon, min_lat, max_lon, max_lat = geom.bounds

        # Keep precision reasonable for coordinates (4 decimal places is plenty for bounding boxes)
        bboxes[state_name] = {
            "minLon": round(min_lon, 4),
            "maxLon": round(max_lon, 4),
            "maxLat": round(max_lat, 4),
            "minLat": round(min_lat, 4),
        }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(bboxes, f, indent=2, sort_keys=True)

    print(
        f"Successfully generated {output_path} with {len(bboxes)} state bounding boxes."
    )


if __name__ == "__main__":
    main()
