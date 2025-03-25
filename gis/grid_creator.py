import frappe
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point, shape
from shapely.ops import voronoi_diagram
import json

def create_hexagon(center_x, center_y, hex_size):
    """
    Creates a perfect hexagonal polygon centered at (center_x, center_y).
    """
    angles = np.linspace(0, 2 * np.pi, 7)  # 6 sides + closing point
    points = [(center_x + hex_size * np.cos(angle), center_y + hex_size * np.sin(angle)) for angle in angles]
    return Polygon(points)

def create_hex_grid(ward_polygon, hex_size):
    """
    Generates a grid of hexagons within the given ward polygon, ensuring no overlaps.
    """
    minx, miny, maxx, maxy = ward_polygon.bounds
    hex_width = hex_size * 2
    hex_height = np.sqrt(3) * hex_size

    hexagons = []
    y = miny
    row = 0
    while y < maxy:
        x = minx if row % 2 == 0 else minx + hex_size
        while x < maxx:
            hexagon = create_hexagon(x, y, hex_size)
            if hexagon.intersects(ward_polygon):
                hexagons.append(hexagon)
            x += hex_width * 0.75  # Move by 75% of the width to form the staggered grid
        y += hex_height * 0.5  # Move up by half height
        row += 1
    
    return hexagons

def clip_hexagons_to_ward(hexagons, ward_polygon):
    """
    Clips hexagons to prevent overlaps and ensures they fit within the ward polygon.
    """
    # Generate Voronoi diagram for precise clipping
    merged_hexagons = MultiPolygon(hexagons)
    voronoi_regions = voronoi_diagram(merged_hexagons)
    clipped_hexagons = [region.intersection(ward_polygon) for region in voronoi_regions.geoms if region.is_valid]
    
    return clipped_hexagons

def generate_hexagonal_grid(ward_name, hex_size):
    """
    Generates a hexagonal grid within a ward's boundary, ensuring no overlaps.
    """
    ward_doc = frappe.get_doc("Ward", ward_name)
    ward_geojson = frappe.parse_json(ward_doc.geolocation)
    ward_polygon = Polygon(ward_geojson["geometry"]["coordinates"][0])

    # Generate hexagonal grids
    hexagons = create_hex_grid(ward_polygon, hex_size)
    clipped_hexagons = clip_hexagons_to_ward(hexagons, ward_polygon)
    
    # print(f"Generated {len(clipped_hexagons)} hexagons for ward '{ward_name}'.")

    settlements = get_approved_settlements(ward_name)
    
    # grid_preview_url = preview_grids_on_map(ward_polygon, clipped_hexagons, settlements)

    # print(f"✅ Grid preview available at: {grid_preview_url}")

    # return grid_preview_url

    # Save grids to Frappe
    # save_grids_to_frappe(clipped_hexagons, ward_name)

    # return clipped_hexagons
    return clipped_hexagons, ward_polygon, settlements


def get_approved_settlements(ward_name):
    """
    Fetches all approved settlements within the given ward and returns them as Shapely Point geometries.
    """
    settlements = frappe.get_all("Settlement",
        filters={"ward": ward_name, "status": "Approved"},
        fields=["name", "response_geolocation"]
    )

    settlement_points = []
    for settlement in settlements:
        geojson = frappe.parse_json(settlement.response_geolocation)
        features = geojson.get("features", [])

        for feature in features:
            if feature["geometry"]["type"] == "Point":
                coords = feature["geometry"]["coordinates"]
                point = Point(coords)
                settlement_points.append({"name": settlement["name"], "geometry": point})

    return settlement_points


import os
import json
import folium
from shapely.geometry import Polygon, MultiPolygon

def preview_grids_on_map(ward_polygon, clipped_hexagons, settlements):
    """
    Generates an interactive map to preview the grids that will be saved, ensuring consistency.
    Saves it in the public files directory of Frappe.
    """

    # Create a base map centered around the ward
    minx, miny, maxx, maxy = ward_polygon.bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # Add the ward boundary
    folium.GeoJson(ward_polygon, name="Ward Boundary", style_function=lambda x: {
        "color": "black", "weight": 2, "fillOpacity": 0.1
    }).add_to(m)

    saved_count = 0  # Keep track of actual grids

    # Add the clipped hexagons (only those that will be saved)
    for idx, hexagon in enumerate(clipped_hexagons):
        if isinstance(hexagon, (Polygon, MultiPolygon)) and not hexagon.is_empty:
            polygons = hexagon.geoms if isinstance(hexagon, MultiPolygon) else [hexagon]

            for poly in polygons:
                coords = [(y, x) for x, y in poly.exterior.coords]  # Swap lat/lon
                
                # Assign title based on actual saving order
                grid_title = f"Grid {saved_count + 1}"

                # Draw grid polygon
                folium.Polygon(
                    locations=coords, 
                    color="blue", 
                    weight=1, 
                    fill=True, 
                    fill_opacity=0.3,
                    tooltip=grid_title
                ).add_to(m)

                # Place grid title at the centroid
                centroid = poly.centroid
                folium.Marker(
                    location=[centroid.y, centroid.x], 
                    icon=folium.DivIcon(html=f'<div style="font-size: 12px; color: blue; font-weight: bold;">{grid_title}</div>')
                ).add_to(m)

                saved_count += 1  # Increment counter after valid save


    # Add settlements as markers
    for settlement in settlements:
        point = settlement["geometry"]
        folium.Marker(
            location=[point.y, point.x],  # Latitude, Longitude
            popup=settlement["name"],
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    # Save the map in the public files directory
    file_path = frappe.utils.get_site_path("public", "files", "grid_preview.html")
    m.save(file_path)

    # Correct the file URL for access
    base_url = frappe.utils.get_url()  # Dynamically get site URL
    file_url = f"{base_url}/files/grid_preview.html"

    

    return {
        "file_url":file_url,
        "number_of_grids": saved_count
    }






import json
import frappe
from shapely.geometry import Polygon, MultiPolygon

def save_grids_to_frappe(clipped_hexagons, ward_name):
    """
    Saves the clipped hexagonal grids to the Frappe 'Grid' Doctype.
    """
    saved_count = 0  # Track successfully saved grids
    saved_titles = []

    for hexagon in clipped_hexagons:
        if isinstance(hexagon, (Polygon, MultiPolygon)) and not hexagon.is_empty:
            polygons = hexagon.geoms if isinstance(hexagon, MultiPolygon) else [hexagon]

            for poly in polygons:
                grid_title = f"Grid {saved_count + 1}"

                grid_doc = frappe.get_doc({
                    "doctype": "Grid",
                    "ward": ward_name,
                    "geolocation_kyow": json.dumps({
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [list(poly.exterior.coords)]
                                    }
                                }
                            ]
                        }),
                    "project": "STRICAN - Phase 2",
                    "title": grid_title,
                    "local_government_area": frappe.get_value("Ward", ward_name, "local_government_area"),
                    "state": frappe.get_value("Ward", ward_name, "state"),
                })
                grid_doc.insert(ignore_permissions=True)
                saved_titles.append(grid_title)
                saved_count += 1

    frappe.db.commit()
    # print(f"✅ Successfully saved {saved_count} grids: {saved_titles}")
    return (f"✅ Successfully saved {saved_count} grids")



import frappe
import json
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union

@frappe.whitelist()
def merge_grids(grid_names):
    """
    Merge multiple neighboring grids into one if they share an edge.
    
    Args:
        grid_names (list): List of grid names to be merged.
    
    Returns:
        dict: Success message with the new merged grid details.
    """
    if not isinstance(grid_names, list) or len(grid_names) < 2:
        frappe.throw("At least two grids are required for merging.")

    grids = frappe.get_all("Grid", filters={"name": ["in", grid_names]}, fields=["name", "geolocation_kyow", "enabled", "ward", "project", "local_government_area", "state", "title"])
    
    if not grids or len(grids) < 2:
        frappe.throw("Invalid grid names or insufficient grids to merge.")

    polygons = {}
    merged_titles = []
    
    for grid in grids:
        geojson = json.loads(grid["geolocation_kyow"])
        merged_titles.append(grid["title"])
        
        # Ensure it's a FeatureCollection and extract the first feature
        if geojson.get("type") == "FeatureCollection":
            if not geojson.get("features"):
                frappe.throw(f"Grid {grid['name']} has an empty FeatureCollection.")
            geojson = geojson["features"][0]["geometry"]  # Extract the first feature's geometry

        geom = shape(geojson)

        if not isinstance(geom, Polygon):
            frappe.throw(f"Grid {grid['name']} is not a valid Polygon.")
        
        polygons[grid["name"]] = geom

    # Check if all polygons are neighbors (share an edge)
    merged_polygon = None
    for name, poly in polygons.items():
        if merged_polygon is None:
            merged_polygon = poly
        else:
            if not merged_polygon.touches(poly) and not merged_polygon.intersects(poly):
                frappe.throw(f"Grid {name} is not a direct neighbor of the others.")
            merged_polygon = unary_union([merged_polygon, poly])  # Merge polygons

    # Ensure the merged result is a valid polygon
    if not isinstance(merged_polygon, Polygon):
        frappe.throw("The merged result is not a valid polygon.")

    # Convert the merged polygon into a FeatureCollection
    merged_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": merged_polygon.__geo_interface__  # Convert back to GeoJSON
            }
        ]
    }

    # Save the new merged grid
    merged_grid = frappe.get_doc({
        "doctype": "Grid",
        "title": " + ".join(merged_titles),  # Use merged titles instead of names
        "enabled": 1,  # The new grid is enabled
        "ward": grids[0]["ward"],
        "project": grids[0]["project"],
        "local_government_area": grids[0]["local_government_area"],
        "state": grids[0]["state"],
        "geolocation_kyow": json.dumps(merged_geojson)  # Store as FeatureCollection
    })
    merged_grid.insert(ignore_permissions=True)

    # Disable the source grids
    for grid in grid_names:
        frappe.db.set_value("Grid", grid, "enabled", 0)

    return {
        "message": "Grids merged successfully.",
        "new_grid_name": merged_grid.name,
        "geolocation": merged_grid.geolocation_kyow
    }



import frappe

@frappe.whitelist()
def test_merge_grids():
    """
    Manually supplies specific grids to test the merge function.
    
    Returns:
        dict: Response from the merge function.
    """
    # Define specific grids to merge (replace with actual grid names)
    selected_grids = ["9spi00rmgn", "1ol9oe3ing"]  # Replace with actual names

    if len(selected_grids) < 2:
        frappe.throw("At least two grids must be provided.")

    # Call the merge function
    response = frappe.call("gis.grid_creator.merge_grids", grid_names=selected_grids)


    return response




@frappe.whitelist()
def preview_grids(ward_name, hex_size):
    # ward_name = "City Center 1-Municipal Area Council-Fct"
    # hex_size = 0.085
    hex_size = float(hex_size)
    clipped_hexagons, ward_polygon, settlements = generate_hexagonal_grid(ward_name, hex_size)
    # preview_grids_on_map(ward_polygon, clipped_hexagons, settlements)
    # save_grids_to_frappe(clipped_hexagons, ward_name)

    return preview_grids_on_map(ward_polygon, clipped_hexagons, settlements)


import numpy as np
import frappe
@frappe.whitelist()
def create_grids(ward_name, hex_size):
    # ward_name = "City Center 1-Municipal Area Council-Fct"
    # hex_size = 0.085
    hex_size = float(hex_size)
    clipped_hexagons, ward_polygon, settlements = generate_hexagonal_grid(ward_name, hex_size)
    # save_grids_to_frappe(clipped_hexagons, ward_name)

    return save_grids_to_frappe(clipped_hexagons, ward_name)

