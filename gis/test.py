import frappe
import random
from frappe import _
from frappe.utils.data import today
import requests
import json
from datetime import datetime
from datetime import date


from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource, save_image
)
def test_fields2():
  fields = frappe.db.sql(f""" 
    SELECT *
    FROM `tabDocField`
    WHERE parent = 'Building'
    """,
    as_dict=True)
  
  return fields 

def test_fields():
  fields = frappe.db.sql(f""" 
    SELECT DISTINCT parentfield 
        FROM `tabDoctype Table` 
        WHERE parent = 'STRICAN - Phase 2';

    """,
    as_dict=True)
  return fields 


@frappe.whitelist()
def geolocation():
    try:
        # Fetch the Building record with the specified name
        # building = frappe.get_doc("Grid", "vuha6hqe62")
        building = frappe.get_doc("Building", "11c - Nsikak Edet Crescent")
        # Update the geolocation field
        # print(building.response_geolocation)
        print(building.geolocation)
        # print(building.geolocation_kyow)
        
        # building.response_geolocation = None
        # building.geolocation = None
        
       
        # building.geolocation = building.response_geolocation 

        # Set the geolocation field in the required GeoJSON format
        # building.geolocation = json.dumps({
        # # building.response_geolocation = json.dumps({
        #     "type": "FeatureCollection",
        #     "features": [
        #         {
        #             "type": "Feature",
        #             "properties": {},
        #             "geometry": {
        #                 "type": "Point",
        #                 # "coordinates": [7.475866, 9.042452]  # Longitude first, then Latitude (Sydani)
        #                 # "coordinates": [7.4042, 9.1099]  # Longitude first, then Latitude (Gwarinpa)
        #                 # "coordinates": [7.476275, 8.97323]  # Longitude first, then Latitude (Sunsine Homes)
        #                 # "coordinates": [6.553486, 9.591894]  # Longitude first, then Latitude (Haske Hotel, Niger)
        #                 # "coordinates": [7.4951, 9.0579]  # Longitude first, then Latitude (Asokoro)
        #                 # "coordinates": [6.1532668192084, 8.99168425242635]  # Longitude first, then Latitude (Alukusu)
        #                 "coordinates": [7.14320, 8.93120]  # Longitude first, then Latitude (Grid 1, Gui)

        #             }
        #         }
        #     ]
        # })
        
        
        # Save the changes
        # building.save()
        
        # Commit the transaction to the database
        # frappe.db.commit()
        
        return {
            "status": 200,
            "message": "Geolocation updated successfully."
        }
    except frappe.DoesNotExistError:
        return {
            "status": 404,
            "message": "Building record not found."
        }
    except Exception as e:
        return {
            "status": 500,
            "message": f"An error occurred: {str(e)}"
        }
import frappe
import json

@frappe.whitelist()
def fix_building_coordinates():
    """
    Scans Building documents and converts coordinate strings to floats
    in the GeoJSON 'geolocation' field, without changing the structure.
    """
    updated = 0
    buildings = frappe.get_all("Building", filters={"project": "STRICAN - Phase 2"}, fields=["name", "geolocation"])

    for b in buildings:
        if not b.geolocation:
            continue

        try:
            geo = json.loads(b.geolocation)

            feature = geo.get("features", [])[0] if geo.get("features") else None
            coords = feature.get("geometry", {}).get("coordinates", []) if feature else []

            # Only process if both coordinates exist and are strings
            if (
                isinstance(coords, list) and
                len(coords) == 2 and
                isinstance(coords[0], str) and isinstance(coords[1], str)
            ):
                # Convert both to float
                lon = float(coords[0])
                lat = float(coords[1])
                geo["features"][0]["geometry"]["coordinates"] = [lon, lat]

                # Save updated GeoJSON back to the document
                frappe.db.set_value("Building", b.name, "geolocation", json.dumps(geo))
                print(f"Fixed geolocation in Building '{b.name}'")
                updated += 1

        except Exception as e:
            frappe.log_error(f"Error fixing geolocation in Building '{b.name}': {e}", "Geo Fix")

    print(f"✔ Updated {updated} Building records with float coordinates.")


import frappe

def find_facilities_without_buildings():
    facilities_without_buildings = []

    # Get all Facility records where selected_facility is 1
    facilities = frappe.get_all("Facility", filters={"selected_facility": 1}, fields=["name", "facility_name"])

    for facility in facilities:
        # Check if any Building is linked to this facility
        building_count = frappe.db.count("Building", filters={"health_facility": facility["name"]})

        if building_count == 0:
            facilities_without_buildings.append(facility)

    if facilities_without_buildings:
        print("\nFacilities with no linked Buildings:\n")
        for f in facilities_without_buildings:
            print(f"- {f['facility_name']} ({f['name']})")
    else:
        print("All selected facilities have at least one building linked.")

def submit_vaccination_summary():
    record = frappe.get_doc("Vaccination Validation Summary", "Vaccination Validation - 00117")
    record.submit()


import json
import frappe

# ============== Public API =================
@frappe.whitelist()
def update_all_centroids(store_geometry_only: int = 0, batch_size: int = 500):
    """
    Compute and store centroid for *all* records in these doctypes:
      - State
      - Local Government Area
      - Ward

    Writes to field 'centroid' as GeoJSON.
      - If store_geometry_only=1 → stores a Geometry (Point) object only
      - Else (default) → stores a Feature with Point geometry

    Returns a summary dict.
    """
    doctypes = ["State", "Local Government Area", "Ward"]
    geo_field = "geolocation"
    out = {}

    for dt in doctypes:
        res = _process_doctype(dt, geo_field, "centroid",
                               store_geometry_only=bool(int(store_geometry_only)),
                               batch_size=int(batch_size))
        out[dt] = res

    frappe.db.commit()
    return out


# ============== Internal Helpers =================
def _process_doctype(doctype, geom_field, centroid_field, store_geometry_only=False, batch_size=500):
    logger = frappe.logger("update_all_centroids")
    # sanity checks for fields
    if not frappe.db.has_column(doctype, geom_field):
        msg = f"{doctype}: missing field `{geom_field}`"
        logger.warning(msg)
        return {"updated": 0, "skipped": 0, "missing_geolocation_field": True}

    if not frappe.db.has_column(doctype, centroid_field):
        msg = f"{doctype}: missing field `{centroid_field}` (create it as JSON/Long Text)"
        logger.warning(msg)
        return {"updated": 0, "skipped": 0, "missing_centroid_field": True}

    updated = 0
    skipped = 0
    start = 0

    while True:
        rows = frappe.get_all(
            doctype,
            fields=["name", geom_field],
            limit_start=start,
            limit_page_length=batch_size,
        )
        if not rows:
            break

        for r in rows:
            name = r.get("name")
            raw_geo = r.get(geom_field)

            gj = _safe_parse_geojson(raw_geo)
            if not gj:
                skipped += 1
                continue

            geom = _extract_geometry(gj)
            poly_geom = _largest_polygon_geometry(geom)
            if not poly_geom:
                skipped += 1
                continue

            cx, cy = _centroid_for_polygon_geometry(poly_geom)

            if store_geometry_only:
                value = json.dumps({"type": "Point", "coordinates": [cx, cy]}, ensure_ascii=False)
            else:
                value = json.dumps({
                    "type": "Feature",
                    "properties": {
                        "source_doctype": doctype,
                        "source_name": name,
                        "derived": "centroid"
                    },
                    "geometry": {"type": "Point", "coordinates": [cx, cy]}
                }, ensure_ascii=False)

            # Write without touching modified timestamp if you prefer — change update_modified to True if needed
            frappe.db.set_value(doctype, name, centroid_field, value, update_modified=False)
            updated += 1

        start += batch_size
        frappe.db.commit()  # commit per batch to avoid long transactions

    return {"updated": updated, "skipped": skipped, "batch_size": batch_size}


# ---- GeoJSON utilities (pure Python) ----
def _safe_parse_geojson(val):
    if not val:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, (bytes, bytearray)):
        try:
            return json.loads(val.decode("utf-8", "ignore"))
        except Exception:
            return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            # tolerate NDJSON-ish blobs
            features = []
            for line in s.splitlines():
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "Feature":
                        features.append(obj)
                    elif obj.get("type") == "FeatureCollection":
                        features.extend(obj.get("features", []))
                except Exception:
                    pass
            if features:
                return {"type": "FeatureCollection", "features": features}
    return None


def _extract_geometry(obj):
    if not isinstance(obj, dict):
        return None
    t = obj.get("type")
    if t in ("Polygon", "MultiPolygon", "Point", "LineString", "MultiLineString", "MultiPoint"):
        return obj
    if t == "Feature":
        return obj.get("geometry")
    if t == "FeatureCollection":
        feats = obj.get("features") or []
        if feats:
            return feats[0].get("geometry")
    return None


def _largest_polygon_geometry(geom):
    gtype = (geom or {}).get("type")
    coords = (geom or {}).get("coordinates")

    if gtype == "Polygon":
        return {"type": "Polygon", "coordinates": coords}

    if gtype == "MultiPolygon":
        if not coords:
            return None
        best = None
        best_area = 0.0
        for poly in coords:
            if not poly or not poly[0]:
                continue
            area = abs(_ring_area(poly[0]))
            if area > best_area:
                best_area = area
                best = poly
        return {"type": "Polygon", "coordinates": best} if best else None

    return None  # ignore non-polygonal geometries


def _centroid_for_polygon_geometry(polygon_geom):
    rings = polygon_geom.get("coordinates") or []
    total_area = 0.0
    cx_sum = 0.0
    cy_sum = 0.0

    for ring in rings:
        if not ring or len(ring) < 3:
            continue
        if ring[0] != ring[-1]:
            ring = ring + [ring[0]]
        A = _ring_area(ring)   # signed
        Cx, Cy = _ring_centroid(ring, A)
        total_area += A
        cx_sum += Cx
        cy_sum += Cy

    if abs(total_area) < 1e-12:
        # degenerate fallback
        pts = [pt for ring in rings for pt in ring]
        if not pts:
            return (0.0, 0.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (sum(xs)/len(xs), sum(ys)/len(ys))

    return (cx_sum / total_area, cy_sum / total_area)


def _ring_area(ring):
    A = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        A += (x1 * y2 - x2 * y1)
    return 0.5 * A


def _ring_centroid(ring, signed_area=None):
    if signed_area is None:
        signed_area = _ring_area(ring)
    if abs(signed_area) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return (sum(xs)/len(xs), sum(ys)/len(ys))

    Cx = 0.0
    Cy = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        cross = (x1 * y2 - x2 * y1)
        Cx += (x1 + x2) * cross
        Cy += (y1 + y2) * cross

    # A-weighted partial sums (divide by 6 here, divide by total area later)
    return ((1.0/6.0) * Cx, (1.0/6.0) * Cy)



import json
import frappe

@frappe.whitelist()
def map_overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None,
                 building_type=None, establishment_type=None, health_facility=None, status=None):
    # -- Auth & guards --
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}

    if not project:
        return {"message": "Please provide a project to return the data for the map.", "status": 400}

    if "Dashboard Viewer" not in frappe.get_roles(user):
        return {"message": "You do not have the required role to view the map, please contact the project manager.", "status": 401}

    # -- Normalize building_type shortcuts --
    if building_type == "Residential Only":
        building_type = "Residential"
    elif building_type == "Non Residential Only":
        building_type = "Non-residential"
    elif building_type == "Health Facilities Only":
        building_type = "Non-residential"; establishment_type = "Health Facility"
    elif building_type == "Schools Only":
        building_type = "Non-residential"; establishment_type = "School"
    elif building_type == "Churches Only":
        building_type = "Non-residential"; establishment_type = "Church"
    elif building_type == "Mosques Only":
        building_type = "Non-residential"; establishment_type = "Mosque"

    # -- Filters dict (used for SQL) --
    filters = {"project": project}
    if grid:        filters["grid"] = grid
    if settlement:  filters["settlement"] = settlement
    if ward:        filters["ward"] = ward
    if lga:         filters["local_government_area"] = lga   # building table field
    if state:       filters["state"] = state
    if status:      filters["status"] = status

    if health_facility:
        building_type = "Non-residential"
        establishment_type = "Health Facility"
        filters["health_facility"] = health_facility

    if building_type:
        filters["building_type"] = building_type
    if establishment_type:
        filters["establishment_type"] = establishment_type

    # Build WHERE clause & values
    sql_conditions, sql_values = [], []
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, tuple) and value[0] == "in":
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)
    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"
    full_where = f"{where_clause}"

    # ---- helpers ----
    def _to_geojson(val):
        """Return a GeoJSON object (dict) or None."""
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        if isinstance(val, (bytes, bytearray)):
            try:
                return json.loads(val.decode("utf-8", "ignore"))
            except Exception:
                return None
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            try:
                return json.loads(s)
            except Exception:
                return None
        return None

    def _wrap_as_fc(geom_or_feat):
        """Wrap a Geometry/Feature into a FeatureCollection with a single Feature for consistent output."""
        if geom_or_feat is None:
            return None
        if isinstance(geom_or_feat, dict):
            t = geom_or_feat.get("type")
            if t == "FeatureCollection":
                return geom_or_feat
            if t == "Feature":
                return {"type": "FeatureCollection", "features": [geom_or_feat]}
            # assume Geometry
            return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geom_or_feat}]}
        return None

    def _fetch_geo(doctype, key, fieldname, fallback_fields=None, wrap_fc=True):
        """
        Fetch a GeoJSON from a doctype (by name or label field), returning dict (optionally wrapped as FC).
        - For State/LGA/Ward: fieldname='centroid'
        - For Settlement: fieldname='response_geolocation'
        """
        if not key:
            return None
        val = frappe.db.get_value(doctype, key, fieldname)
        if not val and fallback_fields:
            for fld in fallback_fields:
                try:
                    docname = frappe.db.get_value(doctype, {fld: key}, "name")
                    if docname:
                        val = frappe.db.get_value(doctype, docname, fieldname)
                        if val:
                            break
                except Exception:
                    pass
        gj = _to_geojson(val)
        return _wrap_as_fc(gj) if wrap_fc else gj

    def _group_aggregates(field_name):
        """
        Single, efficient aggregation query per level.
        Returns rows with label and all requested aggregates.
        """
        allowed = {"state", "local_government_area", "ward", "settlement"}
        if field_name not in allowed:
            frappe.throw(f"Invalid group-by field: {field_name}")

        q = f"""
            SELECT
                `{field_name}` AS label,
                COUNT(*) AS total_buildings,
                SUM(CASE WHEN building_type = 'Residential' THEN 1 ELSE 0 END) AS residential_buildings,
                SUM(CASE WHEN building_type = 'Non-residential' THEN 1 ELSE 0 END) AS non_residential_buildings,
                SUM(CASE WHEN building_type = 'Non-residential' AND establishment_type = 'Health Facility' THEN 1 ELSE 0 END) AS health_facilities,
                SUM(CASE WHEN building_type = 'Non-residential' AND establishment_type = 'School' THEN 1 ELSE 0 END) AS schools,
                SUM(CASE WHEN building_type = 'Non-residential' AND establishment_type = 'Mosque' THEN 1 ELSE 0 END) AS mosques,
                SUM(CASE WHEN building_type = 'Non-residential' AND establishment_type = 'Church' THEN 1 ELSE 0 END) AS churches,
                SUM(CASE WHEN building_type = 'Non-residential' AND establishment_type = 'Commercial' THEN 1 ELSE 0 END) AS commercial_buildings
            FROM `tabBuilding`
            WHERE {full_where}
              AND `{field_name}` IS NOT NULL
              AND TRIM(`{field_name}`) != ''
            GROUP BY `{field_name}`
            ORDER BY `{field_name}`
        """
        return frappe.db.sql(q, tuple(sql_values), as_dict=True)

    # ---- routing ----
    # If grid or settlement is provided → return the original rows
    if grid or settlement:
        building_query = f"""
            SELECT name, percentage_of_vaccinated_children, building_vaccination_status,
                   geolocation, building_type, establishment_type, health_facility, settlement, grid
            FROM `tabBuilding`
            WHERE {full_where}
        """
        try:
            rows = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)
            return {"status": 200, "response": "Success", "data": rows}
        except Exception as e:
            return {"message": f"Error fetching data: {str(e)}", "status": "error"}

    # No state/lga/ward/settlement → counts per State + centroid (State.doctype)
    if not state and not lga and not ward and not settlement:
        try:
            rows = _group_aggregates("state")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="State",
                key=label,
                fieldname="centroid",
                fallback_fields=["state", "name"],  # your label field on State
                wrap_fc=True
            )
            data.append({
                "state": label,
                "total_buildings": int(r["total_buildings"]),
                "residential_buildings": int(r["residential_buildings"]),
                "non_residential_buildings": int(r["non_residential_buildings"]),
                "health_facilities": int(r["health_facilities"]),
                "schools": int(r["schools"]),
                "mosques": int(r["mosques"]),
                "churches": int(r["churches"]),
                "commercial_buildings": int(r["commercial_buildings"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # State provided → counts per LGA + centroid (LGA.doctype)
    if state and not lga and not ward and not settlement:
        try:
            rows = _group_aggregates("local_government_area")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="Local Government Area",
                key=label,
                fieldname="centroid",
                fallback_fields=["local_government_Area", "name"],  # your label field on LGA
                wrap_fc=True
            )
            data.append({
                "lga": label,
                "total_buildings": int(r["total_buildings"]),
                "residential_buildings": int(r["residential_buildings"]),
                "non_residential_buildings": int(r["non_residential_buildings"]),
                "health_facilities": int(r["health_facilities"]),
                "schools": int(r["schools"]),
                "mosques": int(r["mosques"]),
                "churches": int(r["churches"]),
                "commercial_buildings": int(r["commercial_buildings"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # LGA provided → counts per Ward + centroid (Ward.doctype)
    if lga and not ward and not settlement:
        try:
            rows = _group_aggregates("ward")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="Ward",
                key=label,
                fieldname="centroid",
                fallback_fields=["ward", "name"],  # your label field on Ward
                wrap_fc=True
            )
            data.append({
                "ward": label,
                "total_buildings": int(r["total_buildings"]),
                "residential_buildings": int(r["residential_buildings"]),
                "non_residential_buildings": int(r["non_residential_buildings"]),
                "health_facilities": int(r["health_facilities"]),
                "schools": int(r["schools"]),
                "mosques": int(r["mosques"]),
                "churches": int(r["churches"]),
                "commercial_buildings": int(r["commercial_buildings"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # Ward provided (no settlement) → counts per Settlement + response_geolocation (Point) from Settlement.doctype
    if ward and not settlement:
        try:
            rows = _group_aggregates("settlement")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            point_fc = _fetch_geo(
                doctype="Settlement",
                key=label,
                fieldname="response_geolocation",
                fallback_fields=["settlement", "name"],  # your label field on Settlement
                wrap_fc=True
            )
            data.append({
                "settlement": label,
                "total_buildings": int(r["total_buildings"]),
                "residential_buildings": int(r["residential_buildings"]),
                "non_residential_buildings": int(r["non_residential_buildings"]),
                "health_facilities": int(r["health_facilities"]),
                "schools": int(r["schools"]),
                "mosques": int(r["mosques"]),
                "churches": int(r["churches"]),
                "commercial_buildings": int(r["commercial_buildings"]),
                "geolocation": point_fc,  # original point
            })
        return {"status": 200, "response": "Success", "data": data}

    # Fallback → original rows
    building_query = f"""
        SELECT name, percentage_of_vaccinated_children, building_vaccination_status,
               geolocation, building_type, establishment_type, health_facility, settlement, grid
        FROM `tabBuilding`
        WHERE {full_where}
    """
    try:
        rows = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)
        return {"status": 200, "response": "Success", "data": rows}
    except Exception as e:
        return {"message": f"Error fetching data: {str(e)}", "status": "error"}



@frappe.whitelist()
def settlement_map(grid=None, settlement=None, ward=None, lga=None, state=None, status=None,
                 type_of_settlement=None, settlement_archetype=None):
    # -- Auth & guards --
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}

    if "Dashboard Viewer" not in frappe.get_roles(user):
        return {"message": "You do not have the required role to view the map, please contact the project manager.", "status": 401}

    # -- Normalize settlement_type shortcuts --

    if settlement_archetype == "IDP Camp" and type_of_settlement == "Urban":
        archetype_for_urban = "IDP Camp"
    elif settlement_archetype == "Urban Slum" and type_of_settlement == "Urban":
        archetype_for_urban = "Urban Slum"
    elif settlement_archetype == "Security-Compromised" and type_of_settlement == "Urban":
        archetype_for_urban = "Security-Compromised"
    elif settlement_archetype == "Riverine" and type_of_settlement == "Urban":
        archetype_for_urban = "Riverine"
    elif settlement_archetype == "Security-Compromised" and type_of_settlement == "Rural":
        archetype_for_rural = "Security-Compromised"
    elif settlement_archetype == "IDP Camp" and type_of_settlement == "Rural":
        archetype_for_rural = "IDP Camp"
    elif settlement_archetype == "Hard to reach" and type_of_settlement == "Rural":
        archetype_for_rural = "Hard to reach"
    elif settlement_archetype == "Riverine" and type_of_settlement == "Rural":
        archetype_for_rural = "Riverine"
    elif settlement_archetype == "Nomadic" and type_of_settlement == "Rural":
        archetype_for_rural = "Nomadic"

    elif type_of_settlement == "Urban" and not settlement_archetype:
        type_of_settlement = "Urban"
    elif type_of_settlement == "Rural" and not settlement_archetype:
        type_of_settlement = "Rural"

    # -- Filters dict (used for SQL) --
    filters = {}
    if grid:        filters["grid"] = grid
    if settlement:  filters["settlement"] = settlement
    if ward:        filters["ward"] = ward
    if lga:         filters["local_government_area"] = lga   # building table field
    if state:       filters["state"] = state
    if status:      filters["status"] = status

    # Build WHERE clause & values
    sql_conditions, sql_values = [], []
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, tuple) and value[0] == "in":
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)
    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"
    full_where = f"{where_clause}"

    # ---- helpers ----
    def _to_geojson(val):
        """Return a GeoJSON object (dict) or None."""
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        if isinstance(val, (bytes, bytearray)):
            try:
                return json.loads(val.decode("utf-8", "ignore"))
            except Exception:
                return None
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            try:
                return json.loads(s)
            except Exception:
                return None
        return None

    def _wrap_as_fc(geom_or_feat):
        """Wrap a Geometry/Feature into a FeatureCollection with a single Feature for consistent output."""
        if geom_or_feat is None:
            return None
        if isinstance(geom_or_feat, dict):
            t = geom_or_feat.get("type")
            if t == "FeatureCollection":
                return geom_or_feat
            if t == "Feature":
                return {"type": "FeatureCollection", "features": [geom_or_feat]}
            # assume Geometry
            return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geom_or_feat}]}
        return None

    def _fetch_geo(doctype, key, fieldname, fallback_fields=None, wrap_fc=True):
        """
        Fetch a GeoJSON from a doctype (by name or label field), returning dict (optionally wrapped as FC).
        - For State/LGA/Ward: fieldname='centroid'
        - For Settlement: fieldname='response_geolocation'
        """
        if not key:
            return None
        val = frappe.db.get_value(doctype, key, fieldname)
        if not val and fallback_fields:
            for fld in fallback_fields:
                try:
                    docname = frappe.db.get_value(doctype, {fld: key}, "name")
                    if docname:
                        val = frappe.db.get_value(doctype, docname, fieldname)
                        if val:
                            break
                except Exception:
                    pass
        gj = _to_geojson(val)
        return _wrap_as_fc(gj) if wrap_fc else gj

    def _group_aggregates(field_name):
        """
        Single, efficient aggregation query per level.
        Returns rows with label and all requested aggregates.
        """
        allowed = {"state", "local_government_area", "ward", "settlement"}
        if field_name not in allowed:
            frappe.throw(f"Invalid group-by field: {field_name}")

        q = f"""
            SELECT
                `{field_name}` AS label,
                COUNT(*) AS total_settlements,
                SUM(CASE WHEN type_of_settlement = 'Urban' THEN 1 ELSE 0 END) AS urban_settlements,
                SUM(CASE WHEN type_of_settlement = 'Rural' THEN 1 ELSE 0 END) AS rural_settlements
            FROM `tabSettlement`
            WHERE {full_where}
              AND `{field_name}` IS NOT NULL
              AND TRIM(`{field_name}`) != ''
            GROUP BY `{field_name}`
            ORDER BY `{field_name}`
        """
        return frappe.db.sql(q, tuple(sql_values), as_dict=True)

    # ---- routing ----
    # If grid or ward or settlement is provided → return the original rows
    if grid or settlement or ward:
        settlement_query = f"""
            SELECT name, type_of_settlement, archetype_for_rural, archetype_for_urban,
                   response_geolocation, settlement, grid
            FROM `tabSettlement`
            WHERE {full_where}
        """
        try:
            rows = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)
            return {"status": 200, "response": "Success", "data": rows}
        except Exception as e:
            return {"message": f"Error fetching data: {str(e)}", "status": "error"}

    # No state/lga/ward/settlement → counts per State + centroid (State.doctype)
    if not state and not lga and not ward and not settlement:
        try:
            rows = _group_aggregates("state")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="State",
                key=label,
                fieldname="centroid",
                fallback_fields=["state", "name"],  # your label field on State
                wrap_fc=True
            )
            data.append({
                "state": label,
                "total_settlements": int(r["total_settlements"]),
                "urban_settlements": int(r["urban_settlements"]),
                "rural_settlements": int(r["rural_settlements"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # State provided → counts per LGA + centroid (LGA.doctype)
    if state and not lga and not ward and not settlement:
        try:
            rows = _group_aggregates("local_government_area")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="Local Government Area",
                key=label,
                fieldname="centroid",
                fallback_fields=["local_government_Area", "name"],  # your label field on LGA
                wrap_fc=True
            )
            data.append({
                "lga": label,
                "total_settlements": int(r["total_settlements"]),
                "urban_settlements": int(r["urban_settlements"]),
                "rural_settlements": int(r["rural_settlements"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # LGA provided → counts per Ward + centroid (Ward.doctype)
    if lga and not ward and not settlement:
        try:
            rows = _group_aggregates("ward")
        except Exception as e:
            return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

        data = []
        for r in rows:
            label = r["label"]
            centroid = _fetch_geo(
                doctype="Ward",
                key=label,
                fieldname="centroid",
                fallback_fields=["ward", "name"],  # your label field on Ward
                wrap_fc=True
            )
            data.append({
                "ward": label,
                "total_settlements": int(r["total_settlements"]),
                "urban_settlements": int(r["urban_settlements"]),
                "rural_settlements": int(r["rural_settlements"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # Ward provided (no settlement) → counts per Settlement + response_geolocation (Point) from Settlement.doctype
    # if ward and not settlement:
    #     try:
    #         rows = _group_aggregates("settlement")
    #     except Exception as e:
    #         return {"message": f"Error fetching grouped data: {str(e)}", "status": "error"}

    #     data = []
    #     for r in rows:
    #         label = r["label"]
    #         point_fc = _fetch_geo(
    #             doctype="Settlement",
    #             key=label,
    #             fieldname="response_geolocation",
    #             fallback_fields=["settlement", "name"],  # your label field on Settlement
    #             wrap_fc=True
    #         )
    #         data.append({
    #             "settlement": label,
    #             "total_settlements": int(r["total_settlements"]),
    #             "urban_settlements": int(r["urban_settlements"]),
    #             "rural_settlements": int(r["rural_settlements"]),
    #             "centroid": centroid,
    #         })
    #     return {"status": 200, "response": "Success", "data": data}

    # Fallback → original rows
    settlement_query = f"""
        SELECT name, type_of_settlement, archetype_for_rural, archetype_for_urban,
                response_geolocation,  settlement, grid
        FROM `tabSettlement`
        WHERE {full_where}
    """
    try:
        rows = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)
        return {"status": 200, "response": "Success", "data": rows}
    except Exception as e:
        return {"message": f"Error fetching data: {str(e)}", "status": "error"}
