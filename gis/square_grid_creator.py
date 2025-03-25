import os
import json
import folium
import frappe
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union


# import numpy as np
# from shapely.geometry import Polygon, MultiPolygon
# import frappe

# def create_square(center_x, center_y, step):
#     """Creates a square polygon centered at (center_x, center_y) with side length step."""
#     half_step = step / 2
#     return Polygon([
#         (center_x - half_step, center_y - half_step),
#         (center_x + half_step, center_y - half_step),
#         (center_x + half_step, center_y + half_step),
#         (center_x - half_step, center_y + half_step),
#         (center_x - half_step, center_y - half_step)
#     ])

# def extend_grids_to_cover_gaps(grids, ward_polygon):
#     """Extends the nearest grids to cover gaps while keeping everything within the ward boundary."""
#     all_grid_area = MultiPolygon(grids)
#     missing_area = ward_polygon.difference(all_grid_area)

#     if missing_area.is_empty:
#         return grids  # No gaps to fill

#     if isinstance(missing_area, Polygon):
#         missing_polygons = [missing_area]
#     elif isinstance(missing_area, MultiPolygon):
#         missing_polygons = list(missing_area.geoms)
#     else:
#         return grids  # No valid gaps detected

#     for missing in missing_polygons:
#         nearest_grid = min(grids, key=lambda g: g.distance(missing))
#         extended_grid = nearest_grid.union(missing).intersection(ward_polygon)

#         if isinstance(extended_grid, Polygon):
#             grids.append(extended_grid)
#         elif isinstance(extended_grid, MultiPolygon):
#             grids.extend(list(extended_grid.geoms))

#     return grids

# def create_square_grid(ward_polygon, square_size):
#     """
#     Generates a trimmed and extended grid of squares within the given ward polygon.
#     """
#     minx, miny, maxx, maxy = ward_polygon.bounds
#     squares = []
#     step = np.sqrt(square_size)  # Convert square km to approximate degrees

#     x = minx
#     while x <= maxx:
#         y = miny
#         while y <= maxy:
#             square = create_square(x + step / 2, y + step / 2, step)  # Centered grid
#             if square.intersects(ward_polygon):
#                 clipped_square = square.intersection(ward_polygon)  # Trim excess parts
                
#                 if isinstance(clipped_square, Polygon):
#                     if clipped_square.area > (0.25 * square.area):  # Keep valid grids
#                         squares.append(clipped_square)
#                 elif isinstance(clipped_square, MultiPolygon):  # Handle multiple polygons
#                     squares.extend([poly for poly in clipped_square.geoms if poly.area > (0.25 * square.area)])
#             y += step
#         x += step
    
#     return extend_grids_to_cover_gaps(squares, ward_polygon)

# def generate_square_grid(ward_name, square_size):
#     """
#     Generates a square grid within a ward's boundary.
#     """
#     ward_doc = frappe.get_doc("Ward", ward_name)
#     ward_geojson = frappe.parse_json(ward_doc.geolocation)
#     ward_polygon = Polygon(ward_geojson["geometry"]["coordinates"][0])
    
#     clipped_squares = create_square_grid(ward_polygon, square_size)
#     settlements = get_approved_settlements(ward_name)
    
#     return clipped_squares, ward_polygon, settlements





import numpy as np
from shapely.geometry import Polygon, MultiPolygon
import frappe

def create_square(center_x, center_y, step):
    """Creates a square polygon centered at (center_x, center_y) with side length step."""
    half_step = step / 2
    return Polygon([
        (center_x - half_step, center_y - half_step),
        (center_x + half_step, center_y - half_step),
        (center_x + half_step, center_y + half_step),
        (center_x - half_step, center_y + half_step),
        (center_x - half_step, center_y - half_step)
    ])

# def extend_grids_to_cover_gaps(grids, ward_polygon):
#     """Extends the nearest grids to cover gaps while keeping everything within the ward boundary."""
#     all_grid_area = MultiPolygon(grids)
#     missing_area = ward_polygon.difference(all_grid_area)

#     if missing_area.is_empty:
#         return grids  # No gaps to fill

#     if isinstance(missing_area, Polygon):
#         missing_polygons = [missing_area]
#     elif isinstance(missing_area, MultiPolygon):
#         missing_polygons = list(missing_area.geoms)
#     else:
#         return grids  # No valid gaps detected

#     updated_grids = grids[:]
#     for missing in missing_polygons:
#         nearest_grid = min(grids, key=lambda g: g.distance(missing))
#         extended_grid = nearest_grid.union(missing).intersection(ward_polygon)
        
#         # Replace the old grid with the extended one
#         updated_grids.remove(nearest_grid)
        
#         if isinstance(extended_grid, Polygon):
#             updated_grids.append(extended_grid)
#         elif isinstance(extended_grid, MultiPolygon):
#             updated_grids.extend(list(extended_grid.geoms))

#     return updated_grids


def extend_grids_to_cover_gaps(grids, ward_polygon):
    """Extends the nearest grids to cover gaps while keeping everything within the ward boundary."""
    all_grid_area = MultiPolygon(grids)
    missing_area = ward_polygon.difference(all_grid_area)

    if missing_area.is_empty:
        return grids  # No gaps to fill

    if isinstance(missing_area, Polygon):
        missing_polygons = [missing_area]
    elif isinstance(missing_area, MultiPolygon):
        missing_polygons = list(missing_area.geoms)
    else:
        return grids  # No valid gaps detected

    updated_grids = grids[:]
    for missing in missing_polygons:
        nearest_grid = min(grids, key=lambda g: g.distance(missing))
        
        if nearest_grid in updated_grids:  # Ensure the grid exists before attempting removal
            updated_grids.remove(nearest_grid)
        
        extended_grid = nearest_grid.union(missing).intersection(ward_polygon)

        if isinstance(extended_grid, Polygon):
            updated_grids.append(extended_grid)
        elif isinstance(extended_grid, MultiPolygon):
            updated_grids.extend(list(extended_grid.geoms))

    return updated_grids








def create_square_grid(ward_polygon, square_size):
    """
    Generates a trimmed and extended grid of squares within the given ward polygon.
    """
    minx, miny, maxx, maxy = ward_polygon.bounds
    squares = []
    step = np.sqrt(square_size)  # Convert square km to approximate degrees

    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            square = create_square(x + step / 2, y + step / 2, step)  # Centered grid
            if square.intersects(ward_polygon):
                clipped_square = square.intersection(ward_polygon)  # Trim excess parts
                
                if isinstance(clipped_square, Polygon):
                    if clipped_square.area > (0.25 * square.area):  # Keep valid grids
                        squares.append(clipped_square)
                elif isinstance(clipped_square, MultiPolygon):  # Handle multiple polygons
                    squares.extend([poly for poly in clipped_square.geoms if poly.area > (0.25 * square.area)])
            y += step
        x += step
    
    return extend_grids_to_cover_gaps(squares, ward_polygon)

def generate_square_grid(ward_name, square_size):
    """
    Generates a square grid within a ward's boundary.
    """
    ward_doc = frappe.get_doc("Ward", ward_name)
    ward_geojson = frappe.parse_json(ward_doc.geolocation)
    ward_polygon = Polygon(ward_geojson["geometry"]["coordinates"][0])
    
    clipped_squares = create_square_grid(ward_polygon, square_size)
    settlements = get_approved_settlements(ward_name)
    
    return clipped_squares, ward_polygon, settlements


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





def preview_grids_on_map(ward_polygon, clipped_grids, settlements):
    """
    Generates an interactive map to preview the grids that will be saved, ensuring consistency.
    Saves it in the public files directory of Frappe.
    """
    minx, miny, maxx, maxy = ward_polygon.bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    folium.GeoJson(ward_polygon, name="Ward Boundary", style_function=lambda x: {
        "color": "black", "weight": 2, "fillOpacity": 0.1
    }).add_to(m)

    saved_count = 0
    for idx, grid in enumerate(clipped_grids):
        if isinstance(grid, (Polygon, MultiPolygon)) and not grid.is_empty:
            polygons = grid.geoms if isinstance(grid, MultiPolygon) else [grid]
            for poly in polygons:
                coords = [(y, x) for x, y in poly.exterior.coords]
                grid_title = f"Grid {saved_count + 1}"
                folium.Polygon(
                    locations=coords, 
                    color="blue", 
                    weight=1, 
                    fill=True, 
                    fill_opacity=0.3,
                    tooltip=grid_title
                ).add_to(m)
                centroid = poly.centroid
                folium.Marker(
                    location=[centroid.y, centroid.x], 
                    icon=folium.DivIcon(html=f'<div style="font-size: 12px; color: blue; font-weight: bold;">{grid_title}</div>')
                ).add_to(m)
                saved_count += 1

    for settlement in settlements:
        point = settlement["geometry"]
        folium.Marker(
            location=[point.y, point.x],  
            popup=settlement["name"],
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    file_path = frappe.utils.get_site_path("public", "files", "grid_preview.html")
    m.save(file_path)

    base_url = frappe.utils.get_url()
    file_url = f"{base_url}/files/grid_preview.html"

    return {"file_url": file_url, "number_of_grids": saved_count}

def save_grids_to_frappe(clipped_grids, ward_name):
    """
    Saves the clipped square grids to the Frappe 'Grid' Doctype.
    """
    saved_count = 0
    for grids in clipped_grids:
        if isinstance(grids, (Polygon, MultiPolygon)) and not grids.is_empty:
            polygons = grids.geoms if isinstance(grids, MultiPolygon) else [grids]
            for poly in polygons:
                grid_title = f"Grid {saved_count + 1}"
                grid_area_km2 = calculate_area_in_km2(poly)

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
                    "grid_area": grid_area_km2,
                    "local_government_area": frappe.get_value("Ward", ward_name, "local_government_area"),
                    "state": frappe.get_value("Ward", ward_name, "state"),
                })
                grid_doc.insert(ignore_permissions=True)
                saved_count += 1
    frappe.db.commit()
    return f"✅ Successfully saved {saved_count} grids"


import pyproj


def calculate_area_in_km2(poly):
    """Calculates the geodetic area of a polygon in square kilometers."""
    if not isinstance(poly, Polygon):  # Ensure poly is a Polygon
        return 0

    geodetic = pyproj.CRS("EPSG:4326")  # WGS 84 (lat/lon)
    projected = pyproj.CRS("EPSG:3857")  # Web Mercator (meters)

    transformer = pyproj.Transformer.from_crs(geodetic, projected, always_xy=True)
    
    projected_coords = [transformer.transform(x, y) for x, y in poly.exterior.coords]
    projected_polygon = Polygon(projected_coords)
    
    return projected_polygon.area / 1e6  # Convert m² to km²


from shapely.geometry import shape

@frappe.whitelist()
def calculate_grid_area_on_save(doc, method):
    """Calculate grid area before saving the Grid document."""
    if not doc.geolocation_kyow:
        return
    
    geojson_data = json.loads(doc.geolocation_kyow)
    if not geojson_data.get("features"):
        return
    
    feature = geojson_data["features"][0]  # Extract the first feature
    geometry = feature.get("geometry", {})

    if geometry.get("type") != "Polygon":
        return  # Only process Polygon type

    polygon = shape(geometry)  # Convert GeoJSON to Shapely Polygon
    doc.grid_area = calculate_area_in_km2(polygon)  # Store computed area











@frappe.whitelist()
def preview_grids(ward_name, square_size):
    square_size = float(square_size)
    clipped_squares, ward_polygon, settlements = generate_square_grid(ward_name, square_size)
    return preview_grids_on_map(ward_polygon, clipped_squares, settlements)

@frappe.whitelist()
def create_grids(ward_name, square_size):
    square_size = float(square_size)
    clipped_squares, ward_polygon, settlements = generate_square_grid(ward_name, square_size)
    return save_grids_to_frappe(clipped_squares, ward_name)




