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
        

@frappe.whitelist()
def table_overview(
    project=None,
    grid=None,
    settlement=None,
    ward=None,
    lga=None,
    state=None,
    form=None,
    page: int = 1,
    page_size: int = 200,
    download_all=None,
):
    """
    Fetch data for the dashboard based on selected form: Settlement, Building, Household, Children, or Vaccination.
    New:
      - Pagination: page, page_size (allowed: 100, 200, 350, 500; default 100)
      - Returns total_count and total_pages
      - download_all: if truthy, returns xlsx_file_url for a workbook with multiple sheets
    """
    # --- Basic guards ---
    if not project:
        return {"message": "Please provide a project to return the data for the dashboard.", "status": 400}

    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}

    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {"message": "You do not have the required role to visualize the dashboard, please contact the project manager.", "status": 401}

    # --- Normalize & validate pagination ---
    allowed_sizes = {100, 200, 350, 500}
    try:
        page = int(page) if page else 1
    except Exception:
        page = 1
    if page < 1:
        page = 1

    try:
        page_size = int(page_size) if page_size else 100
    except Exception:
        page_size = 100
    if page_size not in allowed_sizes:
        page_size = 100

    # --- User permissions → default filters ---
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": user},
        fields=["allow", "for_value", "is_default"]
    )

    filters = {}
    for allow_value in ["State", "Local Government Area", "Ward", "Settlement"]:
        allowed_records = [perm for perm in user_permissions if perm["allow"] == allow_value]
        if allowed_records:
            default_record = next((perm for perm in allowed_records if perm["is_default"]), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record["for_value"]
            else:
                filters[allow_value.lower().replace(" ", "_")] = ("in", [perm["for_value"] for perm in allowed_records])

    # Explicit filters override
    if grid:
        filters["grid"] = grid
    if settlement:
        filters["settlement"] = settlement
    if ward:
        filters["ward"] = ward
    if lga:
        filters["local_government_area"] = lga
    if state:
        filters["state"] = state
    if project:
        filters["project"] = project

    # Build WHERE clause and values; we’ll always qualify with alias `t` to avoid ambiguity
    sql_conditions = ["t.status = 'Approved'"]
    sql_values = []
    for key, value in filters.items():
        col = f"t.`{key}`"
        if isinstance(value, tuple) and value[0] == "in":
            sql_conditions.append(f"{col} IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"{col} = %s")
            sql_values.append(value)
    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    # --- Form → table/fields mapping ---
    form_table_mapping = {
        "Settlement": "tabSettlement",
        "Building": "tabBuilding",
        "Household": "tabHousehold",
        "Children": "tabChildren",
        "Vaccination": "tabVaccination",
    }

    field_selection = {
        "Settlement": [
            "name_of_settlement", "type_of_settlement", "archetype_for_rural", "archetype_for_urban",
            "name_of_settlementcommunity_head", "name_of_disease_surveillance_community_informant",
            "names_of_other_influential_members_within_settlement", "is_there_a_vdc",
            "how_often_does_the_vdc_meet", "ward", "local_government_area", "state"
        ],
        "Building": [
            "building_address", "building_picture", "building_picture_2", "building_type",
            "establishment_type", "health_facility", "how_many_households_occupy_this_building",
            "settlement", "ward", "local_government_area", "state"
        ],
        "Children": [
            "full_name", "date_of_birth", "vaccination_status", "gender", "last_vaccination_date",
            "vaccines_taken", "settlement", "ward", "local_government_area", "state"
        ],
        "Vaccination": [
            "full_name", "vaccination_status", "date_of_birth", "vaccination_date", "vaccines_taken",
            "next_vaccination_date", "gender", "care_givers_name", "household", "children", "facility",
            "settlement", "ward", "local_government_area", "state"
        ],
        "Household": [
            "name_of_household_head", "gender_of_household_head", "date_of_birth_of_household_head",
            "educational_level_of_household_head", "is_the_household_head_employed", "industry_of_employment",
            "average_monthly_income", "is_the_household_residing_in_a_rented_apartment",
            "how_many_people_live_in_the_household", "what_is_the_nearest_facility",
            "exact_distance_in_km", "settlement", "ward", "local_government_area", "state"
        ],
    }

    if form not in form_table_mapping:
        return {"message": "Invalid form type provided.", "status": 400}

    # Resolve selected table & fields
    table_name = form_table_mapping[form]
    selected_fields = field_selection.get(form, [])

    # Labels per field
    field_labels = {}
    for field in selected_fields:
        label = frappe.db.get_value("DocField", {"parent": form, "fieldname": field}, "label")
        field_labels[field] = label if label else field

    # Build SELECT field list (qualify with `t.`); convert DOB to Age (months → years+months)
    select_parts = []
    for field in selected_fields:
        if "date_of_birth" in field:
            # Return Age (months) as Age, we’ll pretty print below
            select_parts.append(f"TIMESTAMPDIFF(MONTH, t.`{field}`, CURDATE()) AS `Age`")
            field_labels[field] = "Age"
        else:
            select_parts.append(f"t.`{field}`")
    field_names_str = ", ".join(select_parts) if select_parts else "t.name"

    # --- Paginated data query for the chosen form ---
    # Count
    count_sql = f"SELECT COUNT(*) AS cnt FROM `{table_name}` t WHERE {where_clause}"
    total_count = frappe.db.sql(count_sql, tuple(sql_values), as_dict=True)[0]["cnt"] if sql_values is not None else 0
    total_pages = (total_count + page_size - 1) // page_size if page_size else 1
    if total_pages == 0:
        total_pages = 1

    # Page slice
    offset = (page - 1) * page_size
    page_sql = f"""
        SELECT {field_names_str}
        FROM `{table_name}` t
        WHERE {where_clause}
        ORDER BY t.modified DESC
        LIMIT %s OFFSET %s
    """
    page_values = tuple(sql_values) + (page_size, offset)
    records = frappe.db.sql(page_sql, page_values, as_dict=True)

    # Post-process label→human readable names (kept as in your original)
    if records:
        for record in records:
            if "ward" in record and record["ward"]:
                record["ward"] = frappe.db.get_value("Ward", record["ward"], "ward")
            if "local_government_area" in record and record["local_government_area"]:
                record["local_government_area"] = frappe.db.get_value("Local Government Area", record["local_government_area"], "local_government_area")
            if "state" in record and record["state"]:
                record["state"] = frappe.db.get_value("State", record["state"], "state")
            if "household" in record and record["household"]:
                record["household"] = frappe.db.get_value("Household", record["household"], "name_of_household_head")
            if "children" in record and record["children"]:
                record["children"] = frappe.db.get_value("Children", record["children"], "full_name")
            if "facility" in record and record["facility"]:
                record["facility"] = frappe.db.get_value("Facility", record["facility"], "facility_name")
            if "what_is_the_nearest_facility" in record and record["what_is_the_nearest_facility"]:
                record["what_is_the_nearest_facility"] = frappe.db.get_value("Facility", record["what_is_the_nearest_facility"], "facility_name")
            if "health_facility" in record and record["health_facility"]:
                record["health_facility"] = frappe.db.get_value("Facility", record["health_facility"], "facility_name")
            if "Age" in record:
                months = record["Age"]
                if months is not None:
                    if months < 12:
                        record["Age"] = f"{months} months"
                    else:
                        years = months // 12
                        remaining_months = months % 12
                        record["Age"] = f"{years} years {remaining_months} months"

    # Build headers in the same order as selected_fields
    headers = [field_labels[field] for field in selected_fields]
    data = [list(r.values()) for r in records]

    # --- KPI counts (kept as in your original, but qualified) ---
    # Reuse where_clause/sql_values for each table, changing only the table name and alias.
    def _count_on(table):
        sql = f"SELECT COUNT(*) AS count FROM `{table}` t WHERE {where_clause}"
        return frappe.db.sql(sql, tuple(sql_values), as_dict=True)[0]["count"]

    settlement_count = _count_on("tabSettlement")
    building_count = _count_on("tabBuilding")
    residential_building_count = frappe.db.sql(
        f"SELECT COUNT(*) AS count FROM `tabBuilding` t WHERE t.building_type = 'Residential' AND {where_clause}",
        tuple(sql_values),
        as_dict=True
    )[0]["count"]
    total_buildings = building_count
    residential_percentage = round((residential_building_count / total_buildings) * 100, 2) if total_buildings > 0 else 0
    household_count = _count_on("tabHousehold")
    children_count = _count_on("tabChildren")
    male_children_count = frappe.db.sql(
        f"SELECT COUNT(*) AS count FROM `tabChildren` t WHERE t.gender = 'Male' AND {where_clause}",
        tuple(sql_values),
        as_dict=True
    )[0]["count"]
    female_children_count = frappe.db.sql(
        f"SELECT COUNT(*) AS count FROM `tabChildren` t WHERE t.gender = 'Female' AND {where_clause}",
        tuple(sql_values),
        as_dict=True
    )[0]["count"]
    vaccination_count = _count_on("tabVaccination")

    # --- Optional: export all forms to XLSX (multi-sheet) ---
    xlsx_file_url = None
    if str(download_all).strip().lower() in {"1", "true"}:
        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
            import io

            # Helper to fetch full (unpaginated) rows for a form
            def _fetch_all_for_form(form_key: str):
                tbl = form_table_mapping[form_key]
                fields = field_selection[form_key]
                parts = []
                labels = {}
                for f in fields:
                    if "date_of_birth" in f:
                        parts.append(f"TIMESTAMPDIFF(MONTH, t.`{f}`, CURDATE()) AS `Age`")
                        labels[f] = "Age"
                    else:
                        parts.append(f"t.`{f}`")
                        labels[f] = frappe.db.get_value("DocField", {"parent": form_key, "fieldname": f}, "label") or f
                select_str = ", ".join(parts) if parts else "t.name"
                sql = f"SELECT {select_str} FROM `{tbl}` t WHERE {where_clause} ORDER BY t.modified DESC"
                rows = frappe.db.sql(sql, tuple(sql_values), as_dict=True)
                # Humanize some fields like above (kept consistent)
                for rec in rows:
                    if "ward" in rec and rec["ward"]:
                        rec["ward"] = frappe.db.get_value("Ward", rec["ward"], "ward")
                    if "local_government_area" in rec and rec["local_government_area"]:
                        rec["local_government_area"] = frappe.db.get_value("Local Government Area", rec["local_government_area"], "local_government_area")
                    if "state" in rec and rec["state"]:
                        rec["state"] = frappe.db.get_value("State", rec["state"], "state")
                    if "household" in rec and rec["household"]:
                        rec["household"] = frappe.db.get_value("Household", rec["household"], "name_of_household_head")
                    if "children" in rec and rec["children"]:
                        rec["children"] = frappe.db.get_value("Children", rec["children"], "full_name")
                    if "facility" in rec and rec["facility"]:
                        rec["facility"] = frappe.db.get_value("Facility", rec["facility"], "facility_name")
                    if "what_is_the_nearest_facility" in rec and rec["what_is_the_nearest_facility"]:
                        rec["what_is_the_nearest_facility"] = frappe.db.get_value("Facility", rec["what_is_the_nearest_facility"], "facility_name")
                    if "health_facility" in rec and rec["health_facility"]:
                        rec["health_facility"] = frappe.db.get_value("Facility", rec["health_facility"], "facility_name")
                    if "Age" in rec:
                        months = rec["Age"]
                        if months is not None:
                            if months < 12:
                                rec["Age"] = f"{months} months"
                            else:
                                years = months // 12
                                rem = months % 12
                                rec["Age"] = f"{years} years {rem} months"
                # Headers in same order
                hdrs = [labels[f] for f in fields]
                rows_list = [list(r.values()) for r in rows]
                return hdrs, rows_list, fields

            # Build workbook
            wb = Workbook()
            # First sheet: requested form
            ws = wb.active
            ws.title = (form or "Data")[:31]
            # Use current page headers + rows
            for col_idx, header in enumerate(headers, start=1):
                ws.cell(row=1, column=col_idx, value=header)
            for r_idx, row in enumerate(data, start=2):
                for c_idx, value in enumerate(row, start=1):
                    ws.cell(row=r_idx, column=c_idx, value=value)
            for col_idx in range(1, max(1, len(headers)) + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 18

            # Additional sheets for the other forms
            other_forms = [k for k in form_table_mapping.keys() if k != form]
            for fkey in other_forms:
                hdrs, rows_list, _ = _fetch_all_for_form(fkey)
                ws2 = wb.create_sheet(title=fkey[:31])
                for c, h in enumerate(hdrs, start=1):
                    ws2.cell(row=1, column=c, value=h)
                for r_i, row in enumerate(rows_list, start=2):
                    for c_i, v in enumerate(row, start=1):
                        ws2.cell(row=r_i, column=c_i, value=v)
                for col_idx in range(1, max(1, len(hdrs)) + 1):
                    ws2.column_dimensions[get_column_letter(col_idx)].width = 18

            # Save to File doc
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)

            filename = f"table_overview_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": filename,
                "attached_to_doctype": None,
                "attached_to_name": None,
                "is_private": 0,  # public
                "content": buf.getvalue(),
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            })
            file_doc.insert(ignore_permissions=True)
            frappe.db.commit()

            site_url = frappe.utils.get_url()  # e.g., https://admin.coveragetrackr.com
            xlsx_file_url = site_url + file_doc.file_url

        except Exception as e:
            frappe.log_error(f"Failed to build/export XLSX: {e}", "table_overview XLSX")
            xlsx_file_url = None

    # --- Final payload ---
    if not records:
        return {
            "message": "No records found for the selected criteria.",
            "status": 404,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
            "xlsx_file_url": xlsx_file_url,
        }

    return {
        "headers": headers,
        "data": data,
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        "total_settlements": settlement_count,
        "total_buildings": building_count,
        "residential_building_count": residential_building_count,
        "residential_building_percentage": residential_percentage,
        "total_households": household_count,
        "total_children": children_count,
        "total_male_children": male_children_count,
        "total_female_children": female_children_count,
        "total_vaccinations": vaccination_count,
        "xlsx_file_url": xlsx_file_url,
        "status": 200,
        "response": "Success",
    }


# @frappe.whitelist()
# def vaccination_overview(
#     project=None,
#     grid=None,
#     settlement=None,
#     ward=None,
#     lga=None,
#     state=None,
#     gender=None,                 # "Male" | "Female" (optional)
#     vaccination_status=None,     # exact string (optional)
#     start_age=None,              # in months (optional, int-like)
#     end_age=None,                # in months (optional, int-like)
#     under2_only=None,            # "1"/"true"/True => restrict DOB <= 24 months
#     trend_granularity="monthly"  # "daily" | "weekly" | "monthly" | "quarterly" | "yearly"
# ):
#     """
#     Aggregated vaccination stats (Approved only) + grouped multi-bar chart + trend analysis.
#     """

#     # --- Auth / role checks ---
#     user = frappe.session.user
#     if user == "Guest":
#         return {"message": "You must be logged in to access this data.", "status": 401}

#     user_roles = frappe.get_roles(user)
#     if "Dashboard Viewer" not in user_roles:
#         return {"message": "You do not have the required role to visualize the dashboard, please contact the project manager.", "status": 401}

#     # --- Permission-driven filters (same pattern as your endpoints) ---
#     user_permissions = frappe.get_all(
#         "User Permission",
#         filters={"user": user},
#         fields=["allow", "for_value", "is_default"]
#     )

#     filters = {}
#     for allow_value in ["State", "Local Government Area", "Ward", "Settlement"]:
#         allowed_records = [p for p in user_permissions if p["allow"] == allow_value]
#         if allowed_records:
#             default_record = next((p for p in allowed_records if p.get("is_default")), None)
#             if default_record:
#                 filters[allow_value.lower().replace(" ", "_")] = default_record["for_value"]
#             else:
#                 filters[allow_value.lower().replace(" ", "_")] = ("in", [p["for_value"] for p in allowed_records])

#     # Explicit API filters
#     if grid:
#         filters["grid"] = grid
#     if settlement:
#         filters["settlement"] = settlement
#     if ward:
#         filters["ward"] = ward
#     if lga:
#         filters["local_government_area"] = lga
#     if state:
#         filters["state"] = state
#     if project:
#         filters["project"] = project

#     # --- Vaccination WHERE clause (positional params for aggregations) ---
#     v_where = ["status = 'Approved'"]
#     v_vals = []

#     for key, value in filters.items():
#         if isinstance(value, tuple) and value[0] == "in":
#             v_where.append(f"`{key}` IN %s")
#             v_vals.append(tuple(value[1]))
#         else:
#             v_where.append(f"`{key}` = %s")
#             v_vals.append(value)

#     if gender:
#         v_where.append("gender = %s")
#         v_vals.append(gender)

#     if vaccination_status:
#         v_where.append("vaccination_status = %s")
#         v_vals.append(vaccination_status)

#     # Age filters via date_of_birth
#     if start_age is not None and end_age is not None:
#         v_where.append("date_of_birth IS NOT NULL")
#         v_where.append("TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) BETWEEN %s AND %s")
#         v_vals.extend([int(start_age), int(end_age)])
#     else:
#         if str(under2_only).strip().lower() in {"1", "true"}:
#             v_where.append("date_of_birth IS NOT NULL")
#             v_where.append("TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) <= 24")

#     v_where_clause = " AND ".join(v_where)

#     # --- Primary totals aggregation (Vaccination) ---
#     row = frappe.db.sql(
#         f"""
#         SELECT
#             COUNT(*)                                                        AS total_vaccinations,

#             SUM(CASE WHEN gender='Male'   THEN 1 ELSE 0 END)               AS total_male_vaccinations,
#             SUM(CASE WHEN gender='Female' THEN 1 ELSE 0 END)               AS total_female_vaccinations,

#             -- Fully Vaccinated (Measles 2)
#             SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' THEN 1 ELSE 0 END)                                   AS fully_vaccinated_total,
#             SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' AND gender='Male'   THEN 1 ELSE 0 END)               AS fully_vaccinated_male,
#             SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' AND gender='Female' THEN 1 ELSE 0 END)               AS fully_vaccinated_female,

#             -- Vaccinated to Age
#             SUM(CASE WHEN vaccination_status='Vaccinated to Age' THEN 1 ELSE 0 END)                                              AS vaccinated_to_age_total,
#             SUM(CASE WHEN vaccination_status='Vaccinated to Age' AND gender='Male'   THEN 1 ELSE 0 END)                          AS vaccinated_to_age_male,
#             SUM(CASE WHEN vaccination_status='Vaccinated to Age' AND gender='Female' THEN 1 ELSE 0 END)                          AS vaccinated_to_age_female,

#             -- Under Immunized
#             SUM(CASE WHEN vaccination_status='Under Immunized' THEN 1 ELSE 0 END)                                                AS under_immunized_total,
#             SUM(CASE WHEN vaccination_status='Under Immunized' AND gender='Male'   THEN 1 ELSE 0 END)                             AS under_immunized_male,
#             SUM(CASE WHEN vaccination_status='Under Immunized' AND gender='Female' THEN 1 ELSE 0 END)                             AS under_immunized_female,

#             -- Zero Dose
#             SUM(CASE WHEN vaccination_status='Zero Dose' THEN 1 ELSE 0 END)                                                       AS zero_dose_total,
#             SUM(CASE WHEN vaccination_status='Zero Dose' AND gender='Male'   THEN 1 ELSE 0 END)                                   AS zero_dose_male,
#             SUM(CASE WHEN vaccination_status='Zero Dose' AND gender='Female' THEN 1 ELSE 0 END)                                   AS zero_dose_female,

#             -- Never Vaccinated
#             SUM(CASE WHEN vaccination_status='Never Vaccinated' THEN 1 ELSE 0 END)                                                AS never_vaccinated_total,
#             SUM(CASE WHEN vaccination_status='Never Vaccinated' AND gender='Male'   THEN 1 ELSE 0 END)                            AS never_vaccinated_male,
#             SUM(CASE WHEN vaccination_status='Never Vaccinated' AND gender='Female' THEN 1 ELSE 0 END)                            AS never_vaccinated_female,

#             -- From Enumeration (children is not null)
#             SUM(CASE WHEN children IS NOT NULL AND children <> '' THEN 1 ELSE 0 END)                                              AS from_enumeration_count

#         FROM `tabVaccination`
#         WHERE {v_where_clause}
#         """,
#         tuple(v_vals),
#         as_dict=True,
#     )

#     if not row:
#         return {"message": "No records found for the selected criteria.", "status": 404}

#     r = row[0]
#     total = r.get("total_vaccinations", 0) or 0
#     from_enum = r.get("from_enumeration_count", 0) or 0
#     not_from_enum = max(total - from_enum, 0)

#     pct_from_enum = round((from_enum / total) * 100.0, 2) if total else 0.0
#     pct_not_from_enum = round((not_from_enum / total) * 100.0, 2) if total else 0.0

#     # Pie chart
#     # piechart = {
#     #     "labels": ["From Enumeration", "From Other Outreaches"],
#     #     "counts": [from_enum, not_from_enum],
#     #     "percentages": [pct_from_enum, pct_not_from_enum],
#     #     "total": total
#     # }

#     data = [
#         {"type": "From Enumeration", "percentage": pct_from_enum, "count": from_enum},
#         {"type": "From Other Outreaches", "percentage": pct_not_from_enum, "count": not_from_enum}
#     ]


#     # ----------------------------
#     # Multi-bar grouped chart
#     # ----------------------------
#     # Decide grouping level
#     if not state:
#         group_by = "state"
#         group_label_sql = "state"
#     elif state and not lga:
#         group_by = "local_government_area"
#         group_label_sql = "local_government_area"
#     elif state and lga and not ward:
#         group_by = "ward"
#         group_label_sql = "ward"
#     else:
#         group_by = "settlement"
#         group_label_sql = "settlement"

#     # Vaccination grouped
#     v_groups = frappe.db.sql(
#         f"""
#         SELECT
#             {group_label_sql} AS label,
#             COUNT(*) AS total_vaccination,
#             SUM(CASE WHEN children IS NOT NULL AND children <> '' THEN 1 ELSE 0 END) AS vaccinated_from_enumeration
#         FROM `tabVaccination`
#         WHERE {v_where_clause}
#         GROUP BY {group_label_sql}
#         """,
#         tuple(v_vals),
#         as_dict=True,
#     )

#     # Children under-2 grouped (Approved, <24 months) mirroring filters
#     c_where = ["status = 'Approved'", "TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) < 24"]
#     c_vals = []
#     for key, value in filters.items():
#         if isinstance(value, tuple) and value[0] == "in":
#             c_where.append(f"`{key}` IN %s")
#             c_vals.append(tuple(value[1]))
#         else:
#             c_where.append(f"`{key}` = %s")
#             c_vals.append(value)
#     if gender:
#         c_where.append("gender = %s")
#         c_vals.append(gender)
#     c_where_clause = " AND ".join(c_where)

#     c_groups = frappe.db.sql(
#         f"""
#         SELECT
#             {group_label_sql} AS label,
#             COUNT(*) AS under2_children_enumerated
#         FROM `tabChildren`
#         WHERE {c_where_clause}
#         GROUP BY {group_label_sql}
#         """,
#         tuple(c_vals),
#         as_dict=True,
#     )

#     c_map = {row["label"]: row["under2_children_enumerated"] for row in c_groups}
#     groups_out = []
#     for vg in v_groups:
#         label = vg["label"]
#         total_vaccination = vg["total_vaccination"] or 0
#         vaccinated_from_enumeration = vg["vaccinated_from_enumeration"] or 0
#         under2 = c_map.get(label, 0)
#         pct = round((vaccinated_from_enumeration / under2) * 100.0, 2) if under2 != 0 else 0.0

#         groups_out.append({
#             "label": label,
#             "total_vaccination": total_vaccination,
#             "enumerated_children": under2,
#             "vaccinated_from_enumeration": vaccinated_from_enumeration,
#             "percentage_vaccinated_from_enumeration": pct,
#             "target": "15%",
            
#         })

#     # ----------------------------
#     # Trend analysis (period-first & antigen-first)
#     # ----------------------------
#     antigens = ["Measles 2", "OPV 0", "BCG", "HEP B0", "PENTA 1", "PENTA 3"]

#     # Map granularity to MySQL DATE_FORMAT / expressions
#     if trend_granularity == "daily":
#         period_sql = "DATE_FORMAT(v.creation, '%%d-%%m-%%y')"
#     elif trend_granularity == "weekly":
#         # Get the Monday date of the ISO week
#         # period_sql = "STR_TO_DATE(CONCAT(YEARWEEK(v.creation, 3), ' Monday'), '%X%V %W')"
#         period_sql = "STR_TO_DATE(CONCAT(YEARWEEK(v.creation, 3), ' Monday'), '%%X%%V %%W')"

#     elif trend_granularity == "quarterly":
#         period_sql = "CONCAT(YEAR(v.creation), '-Q', QUARTER(v.creation))"
#     elif trend_granularity == "yearly":
#         period_sql = "YEAR(v.creation)"
#     else:  # monthly default
#         period_sql = "DATE_FORMAT(v.creation, '%%b %%y')"


#     # Build named WHERE for trend to allow %(antigens)s
#     v2_where = ["v.status = 'Approved'"]
#     v2_params = {}

#     def _add_param(name, val):
#         # Helper to avoid collisions; names are unique here
#         v2_params[name] = val
#         return f"%({name})s"

#     # Same filter logic, but with table alias v. and named params
#     for key, value in filters.items():
#         if isinstance(value, tuple) and value[0] == "in":
#             placeholder = _add_param(f"in_{key}", tuple(value[1]))
#             v2_where.append(f"v.`{key}` IN {placeholder}")
#         else:
#             placeholder = _add_param(key, value)
#             v2_where.append(f"v.`{key}` = {placeholder}")

#     if gender:
#         v2_where.append(f"v.gender = {_add_param('gender', gender)}")

#     if vaccination_status:
#         v2_where.append(f"v.vaccination_status = {_add_param('vaccination_status', vaccination_status)}")

#     if start_age is not None and end_age is not None:
#         v2_where.append("v.date_of_birth IS NOT NULL")
#         v2_where.append(f"TIMESTAMPDIFF(MONTH, v.date_of_birth, CURDATE()) BETWEEN {_add_param('age_start', int(start_age))} AND {_add_param('age_end', int(end_age))}")
#     else:
#         if str(under2_only).strip().lower() in {"1", "true"}:
#             v2_where.append("v.date_of_birth IS NOT NULL")
#             v2_where.append("TIMESTAMPDIFF(MONTH, v.date_of_birth, CURDATE()) <= 24")

#     named_where_clause = " AND ".join(v2_where)
#     v2_params["antigens"] = tuple(antigens)

#     trend_sql = f"""
#         SELECT
#             {period_sql} AS period,
#             vm.vaccine AS antigen,
#             COUNT(*) AS count,
#             MIN(v.creation) AS period_sort
#         FROM `tabVaccination` v
#         INNER JOIN `tabVaccine Multiselect` vm
#             ON vm.parent = v.name
#         WHERE {named_where_clause}
#           AND vm.vaccine IN %(antigens)s
#         GROUP BY period, vm.vaccine
#         ORDER BY period_sort ASC, vm.vaccine ASC
#     """
#     trend_rows = frappe.db.sql(trend_sql, v2_params, as_dict=True)

#     # Build both antigen-first and period-first structures
#     antigen_map = {a: {} for a in antigens}
#     period_label_order = []
#     seen_periods = set()
#     weekly_mode = (trend_granularity == "weekly")

#     def _format_yearweek_label(yw):
#         try:
#             s = str(yw)
#             if len(s) < 6:
#                 return s
#             year, week = s[:4], s[4:]
#             return f"{year}-W{int(week):02d}"
#         except Exception:
#             return str(yw)

#     for ri in trend_rows:
#         per_raw = ri["period"]
#         label = _format_yearweek_label(per_raw) if weekly_mode else str(per_raw)
#         if label not in seen_periods:
#             seen_periods.add(label)
#             period_label_order.append(label)

#         ag = ri["antigen"]
#         cnt = ri["count"] or 0
#         if ag in antigen_map:
#             antigen_map[ag][label] = cnt

#     # Antigen-first
#     lines = []
#     for ag in antigens:
#         line_points = [{"period": p, "count": antigen_map[ag].get(p, 0)} for p in period_label_order]
#         lines.append({"antigen": ag, "data": line_points})

#     # Period-first (chronological, each period holds a dict of antigen counts)
#     trend_by_period = []
#     for p in period_label_order:
#         counts = {ag: antigen_map[ag].get(p, 0) for ag in antigens}
#         trend_by_period.append({"period": p, "counts": counts})

#     # --- Final payload ---
#     payload = {
#         "total_vaccinations": total,
#         "total_male_vaccinations": r.get("total_male_vaccinations", 0) or 0,
#         "total_female_vaccinations": r.get("total_female_vaccinations", 0) or 0,

#         "fully_vaccinated_children": {
#             "total":  r.get("fully_vaccinated_total", 0) or 0,
#             "male":   r.get("fully_vaccinated_male", 0) or 0,
#             "female": r.get("fully_vaccinated_female", 0) or 0,
#             "percentage": round((r.get("fully_vaccinated_total", 0) or 0) / total * 100.0, 0) if total else 0.0
#         },
#         "vaccinated_to_age": {
#             "total":  r.get("vaccinated_to_age_total", 0) or 0,
#             "male":   r.get("vaccinated_to_age_male", 0) or 0,
#             "female": r.get("vaccinated_to_age_female", 0) or 0,
#             "percentage": round((r.get("vaccinated_to_age_total", 0) or 0) / total * 100.0, 0) if total else 0.0
#         },
#         "under_immunized": {
#             "total":  r.get("under_immunized_total", 0) or 0,
#             "male":   r.get("under_immunized_male", 0) or 0,
#             "female": r.get("under_immunized_female", 0) or 0,
#             "percentage": round((r.get("under_immunized_total", 0) or 0) / total * 100.0, 0) if total else 0.0
#         },
#         "zero_dose": {
#             "total":  r.get("zero_dose_total", 0) or 0,
#             "male":   r.get("zero_dose_male", 0) or 0,
#             "female": r.get("zero_dose_female", 0) or 0,
#             "percentage": round((r.get("zero_dose_total", 0) or 0) / total * 100.0, 0) if total else 0.0
#         },
#         "never_vaccinated": {
#             "total":  r.get("never_vaccinated_total", 0) or 0,
#             "male":   r.get("never_vaccinated_male", 0) or 0,
#             "female": r.get("never_vaccinated_female", 0) or 0,
#             "percentage": round((r.get("never_vaccinated_total", 0) or 0) / total * 100.0, 0) if total else 0.0
#         },

#         "percentage_vaccination_from_enumeration": {
#             "count": from_enum,
#             "percentage": pct_from_enum,
#             "piechart": data
#         },

#         "multi_bar": {
#             "group_by": group_by,   # "state" | "local_government_area" | "ward" | "settlement"
#             "groups": groups_out
#         },

#         "trend_analysis": {
#             "granularity": trend_granularity,
#             "periods": period_label_order,
#             "lines": lines
#         },
#         "trend_by_period": {
#             "granularity": trend_granularity,
#             "data": trend_by_period
#         },

#         "status": 200,
#         "response": "Success"
#     }

#     return payload


@frappe.whitelist()
def vaccination_overview(
    project=None,
    grid=None,
    settlement=None,
    ward=None,
    lga=None,
    state=None,
    gender=None,                 # "Male" | "Female" (optional)
    vaccination_status=None,     # exact string (optional)
    start_age=None,              # in months (optional, int-like)
    end_age=None,                # in months (optional, int-like)
    under2_only=None,            # "1"/"true"/True => restrict DOB <= 24 months
    trend_granularity="monthly"  # "daily" | "weekly" | "monthly" | "quarterly" | "yearly"
):
    """
    Aggregated vaccination stats (Approved only) + grouped multi-bar chart + trend analysis.
    """

    # --- Auth / role checks ---
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}

    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {"message": "You do not have the required role to visualize the dashboard, please contact the project manager.", "status": 401}

    # --- Permission-driven filters (same pattern as your endpoints) ---
    user_permissions = frappe.get_all(
        "User Permission",
        filters={"user": user},
        fields=["allow", "for_value", "is_default"]
    )

    filters = {}
    for allow_value in ["State", "Local Government Area", "Ward", "Settlement"]:
        allowed_records = [p for p in user_permissions if p["allow"] == allow_value]
        if allowed_records:
            default_record = next((p for p in allowed_records if p.get("is_default")), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record["for_value"]
            else:
                filters[allow_value.lower().replace(" ", "_")] = ("in", [p["for_value"] for p in allowed_records])

    # Explicit API filters
    if grid:
        filters["grid"] = grid
    if settlement:
        filters["settlement"] = settlement
    if ward:
        filters["ward"] = ward
    if lga:
        filters["local_government_area"] = lga
    if state:
        filters["state"] = state
    if project:
        filters["project"] = project

    # --- Vaccination WHERE clause (positional params for aggregations) ---
    v_where = ["status = 'Approved'"]
    v_vals = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == "in":
            v_where.append(f"`{key}` IN %s")
            v_vals.append(tuple(value[1]))
        else:
            v_where.append(f"`{key}` = %s")
            v_vals.append(value)

    if gender:
        v_where.append("gender = %s")
        v_vals.append(gender)

    if vaccination_status:
        v_where.append("vaccination_status = %s")
        v_vals.append(vaccination_status)

    # Age filters via date_of_birth
    if start_age is not None and end_age is not None:
        v_where.append("date_of_birth IS NOT NULL")
        v_where.append("TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) BETWEEN %s AND %s")
        v_vals.extend([int(start_age), int(end_age)])
    else:
        if str(under2_only).strip().lower() in {"1", "true"}:
            v_where.append("date_of_birth IS NOT NULL")
            v_where.append("TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) <= 24")

    v_where_clause = " AND ".join(v_where)

    # --- Primary totals aggregation (Vaccination) ---
    row = frappe.db.sql(
        f"""
        SELECT
            COUNT(*)                                                        AS total_vaccinations,

            SUM(CASE WHEN gender='Male'   THEN 1 ELSE 0 END)               AS total_male_vaccinations,
            SUM(CASE WHEN gender='Female' THEN 1 ELSE 0 END)               AS total_female_vaccinations,

            -- Fully Vaccinated (Measles 2)
            SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' THEN 1 ELSE 0 END)                                   AS fully_vaccinated_total,
            SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' AND gender='Male'   THEN 1 ELSE 0 END)               AS fully_vaccinated_male,
            SUM(CASE WHEN vaccination_status='Fully Vaccinated (Measles 2)' AND gender='Female' THEN 1 ELSE 0 END)               AS fully_vaccinated_female,

            -- Vaccinated to Age
            SUM(CASE WHEN vaccination_status='Vaccinated to Age' THEN 1 ELSE 0 END)                                              AS vaccinated_to_age_total,
            SUM(CASE WHEN vaccination_status='Vaccinated to Age' AND gender='Male'   THEN 1 ELSE 0 END)                          AS vaccinated_to_age_male,
            SUM(CASE WHEN vaccination_status='Vaccinated to Age' AND gender='Female' THEN 1 ELSE 0 END)                          AS vaccinated_to_age_female,

            -- Under Immunized
            SUM(CASE WHEN vaccination_status='Under Immunized' THEN 1 ELSE 0 END)                                                AS under_immunized_total,
            SUM(CASE WHEN vaccination_status='Under Immunized' AND gender='Male'   THEN 1 ELSE 0 END)                             AS under_immunized_male,
            SUM(CASE WHEN vaccination_status='Under Immunized' AND gender='Female' THEN 1 ELSE 0 END)                             AS under_immunized_female,

            -- Zero Dose
            SUM(CASE WHEN vaccination_status='Zero Dose' THEN 1 ELSE 0 END)                                                       AS zero_dose_total,
            SUM(CASE WHEN vaccination_status='Zero Dose' AND gender='Male'   THEN 1 ELSE 0 END)                                   AS zero_dose_male,
            SUM(CASE WHEN vaccination_status='Zero Dose' AND gender='Female' THEN 1 ELSE 0 END)                                   AS zero_dose_female,

            -- Never Vaccinated
            SUM(CASE WHEN vaccination_status='Never Vaccinated' THEN 1 ELSE 0 END)                                                AS never_vaccinated_total,
            SUM(CASE WHEN vaccination_status='Never Vaccinated' AND gender='Male'   THEN 1 ELSE 0 END)                            AS never_vaccinated_male,
            SUM(CASE WHEN vaccination_status='Never Vaccinated' AND gender='Female' THEN 1 ELSE 0 END)                            AS never_vaccinated_female,

            -- From Enumeration (children is not null)
            SUM(CASE WHEN children IS NOT NULL AND children <> '' THEN 1 ELSE 0 END)                                              AS from_enumeration_count

        FROM `tabVaccination`
        WHERE {v_where_clause}
        """,
        tuple(v_vals),
        as_dict=True,
    )

    if not row:
        return {"message": "No records found for the selected criteria.", "status": 404}

    r = row[0]
    total = r.get("total_vaccinations", 0) or 0
    from_enum = r.get("from_enumeration_count", 0) or 0
    not_from_enum = max(total - from_enum, 0)

    pct_from_enum = round((from_enum / total) * 100.0, 2) if total else 0.0
    pct_not_from_enum = round((not_from_enum / total) * 100.0, 2) if total else 0.0

    # Pie chart
    data = [
        {"type": "From Enumeration", "percentage": pct_from_enum, "count": from_enum},
        {"type": "From Other Outreaches", "percentage": pct_not_from_enum, "count": not_from_enum}
    ]


    # ----------------------------
    # Multi-bar grouped chart
    # ----------------------------
    # Decide grouping level
    if not state:
        group_by = "state"
        group_label_sql = "state"
    elif state and not lga:
        group_by = "local_government_area"
        group_label_sql = "local_government_area"
    elif state and lga and not ward:
        group_by = "ward"
        group_label_sql = "ward"
    else:
        group_by = "settlement"
        group_label_sql = "settlement"

    # Vaccination grouped
    v_groups = frappe.db.sql(
        f"""
        SELECT
            {group_label_sql} AS label,
            COUNT(*) AS total_vaccination,
            SUM(CASE WHEN children IS NOT NULL AND children <> '' THEN 1 ELSE 0 END) AS vaccinated_from_enumeration
        FROM `tabVaccination`
        WHERE {v_where_clause}
        GROUP BY {group_label_sql}
        """,
        tuple(v_vals),
        as_dict=True,
    )

    # Children under-2 grouped (Approved, <24 months) mirroring filters
    c_where = ["status = 'Approved'", "TIMESTAMPDIFF(MONTH, date_of_birth, CURDATE()) < 24"]
    c_vals = []
    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == "in":
            c_where.append(f"`{key}` IN %s")
            c_vals.append(tuple(value[1]))
        else:
            c_where.append(f"`{key}` = %s")
            c_vals.append(value)
    if gender:
        c_where.append("gender = %s")
        c_vals.append(gender)
    c_where_clause = " AND ".join(c_where)

    c_groups = frappe.db.sql(
        f"""
        SELECT
            {group_label_sql} AS label,
            COUNT(*) AS under2_children_enumerated
        FROM `tabChildren`
        WHERE {c_where_clause}
        GROUP BY {group_label_sql}
        """,
        tuple(c_vals),
        as_dict=True,
    )

    c_map = {row["label"]: row["under2_children_enumerated"] for row in c_groups}
    groups_out = []
    for vg in v_groups:
        label = vg["label"]
        total_vaccination = vg["total_vaccination"] or 0
        vaccinated_from_enumeration = vg["vaccinated_from_enumeration"] or 0
        under2 = c_map.get(label, 0)
        pct = round((vaccinated_from_enumeration / under2) * 100.0, 2) if under2 != 0 else 0.0

        groups_out.append({
            "label": label,
            "total_vaccination": total_vaccination,
            "enumerated_children": under2,
            "vaccinated_from_enumeration": vaccinated_from_enumeration,
            "percentage_vaccinated_from_enumeration": pct,
            "target": "15%",
            
        })

    # ----------------------------
    # Trend analysis (period-first & antigen-first)
    # ----------------------------
    antigens = ["Measles 2", "OPV 0", "BCG", "HEP B0", "PENTA 1", "PENTA 3"]

    # Map granularity to MySQL DATE_FORMAT / expressions
    if trend_granularity == "daily":
        period_sql = "DATE_FORMAT(v.creation, '%%d-%%m-%%y')"
    elif trend_granularity == "weekly":
        # Get the Monday date of the ISO week
        period_sql = "STR_TO_DATE(CONCAT(YEARWEEK(v.creation, 3), ' Monday'), '%%X%%V %%W')"
    elif trend_granularity == "quarterly":
        period_sql = "CONCAT(YEAR(v.creation), '-Q', QUARTER(v.creation))"
    elif trend_granularity == "yearly":
        period_sql = "YEAR(v.creation)"
    else:  # monthly default
        period_sql = "DATE_FORMAT(v.creation, '%%b %%y')"

    # Build named WHERE for trend to allow %(antigens)s
    v2_where = ["v.status = 'Approved'"]
    v2_params = {}

    def _add_param(name, val):
        # Helper to avoid collisions; names are unique here
        v2_params[name] = val
        return f"%({name})s"

    # Same filter logic, but with table alias v. and named params
    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == "in":
            placeholder = _add_param(f"in_{key}", tuple(value[1]))
            v2_where.append(f"v.`{key}` IN {placeholder}")
        else:
            placeholder = _add_param(key, value)
            v2_where.append(f"v.`{key}` = {placeholder}")

    if gender:
        v2_where.append(f"v.gender = {_add_param('gender', gender)}")

    if vaccination_status:
        v2_where.append(f"v.vaccination_status = {_add_param('vaccination_status', vaccination_status)}")

    if start_age is not None and end_age is not None:
        v2_where.append("v.date_of_birth IS NOT NULL")
        v2_where.append(f"TIMESTAMPDIFF(MONTH, v.date_of_birth, CURDATE()) BETWEEN {_add_param('age_start', int(start_age))} AND {_add_param('age_end', int(end_age))}")
    else:
        if str(under2_only).strip().lower() in {"1", "true"}:
            v2_where.append("v.date_of_birth IS NOT NULL")
            v2_where.append("TIMESTAMPDIFF(MONTH, v.date_of_birth, CURDATE()) <= 24")

    named_where_clause = " AND ".join(v2_where)
    v2_params["antigens"] = tuple(antigens)

    trend_sql = f"""
        SELECT
            {period_sql} AS period,
            vm.vaccine AS antigen,
            COUNT(*) AS count,
            MIN(v.creation) AS period_sort
        FROM `tabVaccination` v
        INNER JOIN `tabVaccine Multiselect` vm
            ON vm.parent = v.name
        WHERE {named_where_clause}
          AND vm.vaccine IN %(antigens)s
        GROUP BY period, vm.vaccine
        ORDER BY period_sort ASC, vm.vaccine ASC
    """
    trend_rows = frappe.db.sql(trend_sql, v2_params, as_dict=True)

    # ----------------------------
    # FILL MISSING PERIODS WITH ZEROS (no other changes)
    # ----------------------------
    from datetime import date, timedelta

    def _period_series_labels(granularity: str, start_dt: date, end_dt: date) -> list[str]:
        labels = []
        if not start_dt or not end_dt or start_dt > end_dt:
            return labels

        if granularity == "daily":
            cur = start_dt
            while cur <= end_dt:
                labels.append(cur.strftime("%d-%m-%y"))
                cur += timedelta(days=1)

        elif granularity == "weekly":
            # Normalize to Monday
            cur = start_dt - timedelta(days=start_dt.weekday())
            end_last_monday = end_dt - timedelta(days=end_dt.weekday())
            while cur <= end_last_monday:
                labels.append(cur.strftime("%Y-%m-%d"))  # Monday date label
                cur += timedelta(days=7)

        elif granularity == "monthly":
            y, m = start_dt.year, start_dt.month
            end_y, end_m = end_dt.year, end_dt.month
            while (y < end_y) or (y == end_y and m <= end_m):
                d = date(y, m, 1)
                labels.append(d.strftime("%b %y"))
                m += 1
                if m == 13:
                    m, y = 1, y + 1

        elif granularity == "quarterly":
            def _q(d: date) -> int: return ((d.month - 1) // 3) + 1
            y, q = start_dt.year, _q(start_dt)
            end_y, end_q = end_dt.year, _q(end_dt)
            while (y < end_y) or (y == end_y and q <= end_q):
                labels.append(f"{y}-Q{q}")
                q += 1
                if q == 5:
                    q, y = 1, y + 1

        else:  # yearly
            y = start_dt.year
            while y <= end_dt.year:
                labels.append(str(y))
                y += 1

        return labels

    # Min/max creation under same filters (no antigen restriction)
    minmax_sql = f"""
        SELECT MIN(v.creation) AS min_c, MAX(v.creation) AS max_c
        FROM `tabVaccination` v
        WHERE {named_where_clause}
    """
    _mm_params = dict(v2_params)
    _mm_params.pop("antigens", None)
    mm = frappe.db.sql(minmax_sql, _mm_params, as_dict=True)

    if mm and mm[0]["min_c"] and mm[0]["max_c"]:
        start_dt = mm[0]["min_c"].date()
        end_dt   = mm[0]["max_c"].date()
    else:
        start_dt = date.today()
        end_dt   = date.today()

    series_labels = _period_series_labels(trend_granularity, start_dt, end_dt)

    antigen_map = {a: {} for a in antigens}

    for ri in trend_rows:
        per_raw = ri["period"]
        if trend_granularity == "daily":
            label = str(per_raw)          # 'dd-mm-yy'
        elif trend_granularity == "weekly":
            label = str(per_raw)          # 'YYYY-MM-DD' (Monday)
        else:
            label = str(per_raw)          # monthly '%b %y', quarterly 'YYYY-Q#', yearly 'YYYY'
        antigen = ri["antigen"]
        cnt = int(ri["count"] or 0)
        if antigen in antigen_map:
            antigen_map[antigen][label] = cnt

    # Antigen-first (lines)
    lines = []
    for ag in antigens:
        line_points = [{"period": p, "count": antigen_map[ag].get(p, 0)} for p in series_labels]
        lines.append({"antigen": ag, "data": line_points})

    # Period-first (each period holds all antigen counts)
    trend_by_period = []
    for p in series_labels:
        counts = {ag: antigen_map[ag].get(p, 0) for ag in antigens}
        trend_by_period.append({"period": p, "counts": counts})

    period_label_order = series_labels
    # ----------------------------

    # --- Final payload ---
    payload = {
        "total_vaccinations": total,
        "total_male_vaccinations": r.get("total_male_vaccinations", 0) or 0,
        "total_female_vaccinations": r.get("total_female_vaccinations", 0) or 0,

        "fully_vaccinated_children": {
            "total":  r.get("fully_vaccinated_total", 0) or 0,
            "male":   r.get("fully_vaccinated_male", 0) or 0,
            "female": r.get("fully_vaccinated_female", 0) or 0,
            "percentage": round((r.get("fully_vaccinated_total", 0) or 0) / total * 100.0, 0) if total else 0.0
        },
        "vaccinated_to_age": {
            "total":  r.get("vaccinated_to_age_total", 0) or 0,
            "male":   r.get("vaccinated_to_age_male", 0) or 0,
            "female": r.get("vaccinated_to_age_female", 0) or 0,
            "percentage": round((r.get("vaccinated_to_age_total", 0) or 0) / total * 100.0, 0) if total else 0.0
        },
        "under_immunized": {
            "total":  r.get("under_immunized_total", 0) or 0,
            "male":   r.get("under_immunized_male", 0) or 0,
            "female": r.get("under_immunized_female", 0) or 0,
            "percentage": round((r.get("under_immunized_total", 0) or 0) / total * 100.0, 0) if total else 0.0
        },
        "zero_dose": {
            "total":  r.get("zero_dose_total", 0) or 0,
            "male":   r.get("zero_dose_male", 0) or 0,
            "female": r.get("zero_dose_female", 0) or 0,
            "percentage": round((r.get("zero_dose_total", 0) or 0) / total * 100.0, 0) if total else 0.0
        },
        "never_vaccinated": {
            "total":  r.get("never_vaccinated_total", 0) or 0,
            "male":   r.get("never_vaccinated_male", 0) or 0,
            "female": r.get("never_vaccinated_female", 0) or 0,
            "percentage": round((r.get("never_vaccinated_total", 0) or 0) / total * 100.0, 0) if total else 0.0
        },

        "percentage_vaccination_from_enumeration": {
            "count": from_enum,
            "percentage": pct_from_enum,
            "piechart": data
        },

        "multi_bar": {
            "group_by": group_by,   # "state" | "local_government_area" | "ward" | "settlement"
            "groups": groups_out
        },

        "trend_analysis": {
            "granularity": trend_granularity,
            "periods": period_label_order,
            "lines": lines
        },
        "trend_by_period": {
            "granularity": trend_granularity,
            "data": trend_by_period
        },

        "status": 200,
        "response": "Success"
    }

    return payload
