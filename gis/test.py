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

    # if settlement_archetype == "IDP Camp" and type_of_settlement == "Urban":
    #     archetype_for_urban = "IDP Camp"
    # elif settlement_archetype == "Urban Slum" and type_of_settlement == "Urban":
    #     archetype_for_urban = "Urban Slum"
    # elif settlement_archetype == "Security-Compromised" and type_of_settlement == "Urban":
    #     archetype_for_urban = "Security-Compromised"
    # elif settlement_archetype == "Riverine" and type_of_settlement == "Urban":
    #     archetype_for_urban = "Riverine"
    # elif settlement_archetype == "Security-Compromised" and type_of_settlement == "Rural":
    #     archetype_for_rural = "Security-Compromised"
    # elif settlement_archetype == "IDP Camp" and type_of_settlement == "Rural":
    #     archetype_for_rural = "IDP Camp"
    # elif settlement_archetype == "Hard to reach" and type_of_settlement == "Rural":
    #     archetype_for_rural = "Hard to reach"
    # elif settlement_archetype == "Riverine" and type_of_settlement == "Rural":
    #     archetype_for_rural = "Riverine"
    # elif settlement_archetype == "Nomadic" and type_of_settlement == "Rural":
    #     archetype_for_rural = "Nomadic"

    # elif type_of_settlement == "Urban" and not settlement_archetype:
    #     type_of_settlement = "Urban"
    # elif type_of_settlement == "Rural" and not settlement_archetype:
    #     type_of_settlement = "Rural"

    # -- Filters dict (used for SQL) --
    filters = {}
    if grid:        filters["grid"] = grid
    if settlement:  filters["name"] = settlement
    if ward:        filters["ward"] = ward
    if lga:         filters["local_government_area"] = lga   # building table field
    if state:       filters["state"] = state
    if status:      filters["status"] = status
    if type_of_settlement: filters["type_of_settlement"] = type_of_settlement

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

    # If grid or ward or settlement is provided → return the original rows + aggregates
    if grid or settlement or ward:
        settlement_query = f"""
            SELECT
                s.name,
                s.type_of_settlement,
                s.distance_from_settlement_to_facility,
                s.name_of_settlementcommunity_head,
                s.contact_of_settlementcommunity_head,
                s.name_of_disease_surveillance_community_informant,
                s.type_of_session,
                s.session_frequency,
                s.major_ethnic_group,
                s.archetype_for_rural,
                s.archetype_for_urban,
                s.response_geolocation,
                s.settlement,
                s.grid,

                -- Aggregates per settlement
                COALESCE(hh_agg.total_population, 0)     AS total_population,
                COALESCE(hh_agg.total_pregnant_women, 0) AS total_pregnant_women,
                COALESCE(ch_agg.total_children, 0)       AS total_children

            FROM `tabSettlement` s

            -- Sum population for all Approved households;
            -- Sum pregnant women only where the household flag is 'Yes'
            LEFT JOIN (
                SELECT
                    hh.settlement,
                    SUM(COALESCE(hh.how_many_people_live_in_the_household, 0)) AS total_population,
                    SUM(
                        CASE
                            WHEN hh.are_there_any_pregnant_women_in_the_household = 'Yes'
                            THEN COALESCE(hh.how_many_pregnant_women_are_there, 0)
                            ELSE 0
                        END
                    ) AS total_pregnant_women
                FROM `tabHousehold` hh
                WHERE hh.status = 'Approved'
                AND hh.settlement IS NOT NULL AND hh.settlement <> ''
                GROUP BY hh.settlement
            ) hh_agg
                ON hh_agg.settlement = s.name

            -- Count Approved children per settlement (via Household link)
            LEFT JOIN (
                SELECT
                    h.settlement,
                    COUNT(*) AS total_children
                FROM `tabChildren` c
                JOIN `tabHousehold` h
                ON h.name = c.household
                WHERE c.status = 'Approved'
                AND h.settlement IS NOT NULL AND h.settlement <> ''
                GROUP BY h.settlement
            ) ch_agg
                ON ch_agg.settlement = s.name

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
                "actual_name": frappe.db.get_value("State", label, "state"),
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
                "actual_name": frappe.db.get_value("Local Government Area", label, "local_government_area"),
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
                "actual_name": frappe.db.get_value("Ward", label, "ward"),
                "total_settlements": int(r["total_settlements"]),
                "urban_settlements": int(r["urban_settlements"]),
                "rural_settlements": int(r["rural_settlements"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # Fallback → original rows
    settlement_query = f"""
        SELECT name, distance_from_settlement_to_facility, type_of_settlement, archetype_for_rural, archetype_for_urban,
                response_geolocation, major_ethnic_group, settlement, grid
        FROM `tabSettlement`
        WHERE {full_where}
    """
    try:
        rows = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)
        return {"status": 200, "response": "Success", "data": rows}
    except Exception as e:
        return {"message": f"Error fetching data: {str(e)}", "status": "error"}
  


@frappe.whitelist()
def facility_map(grid=None, settlement=None, ward=None, lga=None, state=None, facility_type=None):
    # -- Auth & guards --
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}

    if "Dashboard Viewer" not in frappe.get_roles(user):
        return {"message": "You do not have the required role to view the map, please contact the project manager.", "status": 401}

    # -- Filters dict (used for SQL) --
    filters = {}
    if grid:        filters["grid"] = grid
    if settlement:  filters["settlement"] = settlement
    if ward:        filters["ward"] = ward
    if lga:         filters["local_government_area"] = lga   # building table field
    if state:       filters["state"] = state
    if facility_type:      filters["facility_type"] = facility_type

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
        - For Facility: fieldname='geolocation'
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
                COUNT(*) AS total_facilities,
                SUM(CASE WHEN facility_type = 'Private' THEN 1 ELSE 0 END) AS private_facilities,
                SUM(CASE WHEN facility_type = 'Public' THEN 1 ELSE 0 END) AS public_facilities
            FROM `tabFacility`
            WHERE {full_where}
              AND `{field_name}` IS NOT NULL
              AND TRIM(`{field_name}`) != ''
              AND selected_facility = 1
            GROUP BY `{field_name}`
            ORDER BY `{field_name}`
        """
        return frappe.db.sql(q, tuple(sql_values), as_dict=True)

    # If grid or ward or settlement is provided → return the original rows + aggregates
    if grid or settlement or ward:
        facility_query = f"""
      
        SELECT
            f.name,
            f.facility_type,
            f.facility_name,
            f.name_of_oic,
            f.contact_of_oic,
            COALESCE(COUNT(DISTINCT c.name), 0) AS catchment_settlement_count,
            COALESCE(
            GROUP_CONCAT(DISTINCT c.settlement ORDER BY c.settlement SEPARATOR ', '),
            ''
            ) AS catchment_settlements
        FROM (
            SELECT
                name, facility_type, facility_name, name_of_oic, contact_of_oic
            FROM `tabFacility`
            WHERE {full_where}
            AND selected_facility = 1
        ) f
        LEFT JOIN `tabFacility Catchment Area` c
            ON c.parent = f.name
            AND c.parenttype = 'Facility'
            AND c.parentfield = 'facility_catchment_area'
        GROUP BY
            f.name, f.facility_type, f.facility_name, f.name_of_oic, f.contact_of_oic
        ORDER BY f.name;
        """
        try:
            rows = frappe.db.sql(facility_query, tuple(sql_values), as_dict=True)
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
                "actual_name": frappe.db.get_value("State", label, "state"),
                "total_facilities": int(r["total_facilities"]),
                "private_facilities": int(r["private_facilities"]),
                "public_facilities": int(r["public_facilities"]),
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
                "actual_name": frappe.db.get_value("Local Government Area", label, "local_government_area"),
                "total_facilities": int(r["total_facilities"]),
                "private_facilities": int(r["private_facilities"]),
                "public_facilities": int(r["public_facilities"]),
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
                "actual_name": frappe.db.get_value("Ward", label, "ward"),
                "total_facilities": int(r["total_facilities"]),
                "private_facilities": int(r["private_facilities"]),
                "public_facilities": int(r["public_facilities"]),
                "centroid": centroid,
            })
        return {"status": 200, "response": "Success", "data": data}

    # Fallback → original rows
    settlement_query = f"""
        SELECT name, distance_from_settlement_to_facility, type_of_settlement, archetype_for_rural, archetype_for_urban,
                response_geolocation, major_ethnic_group, settlement, grid
        FROM `tabSettlement`
        WHERE {full_where}
    """
    try:
        rows = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)
        return {"status": 200, "response": "Success", "data": rows}
    except Exception as e:
        return {"message": f"Error fetching data: {str(e)}", "status": "error"}
  






import frappe

DRY_RUN_SQL = """
SELECT
  b.name AS building,
  b.building_type,
  COALESCE(b.how_many_households_occupy_this_building, 0) AS expected_households,
  COALESCE(h.actual_households, 0)                         AS actual_households,
  b.status                                                 AS current_status
FROM `tabBuilding` b
LEFT JOIN (
  SELECT building, COUNT(*) AS actual_households
  FROM `tabHousehold`
  WHERE building IS NOT NULL AND building <> ''
  {docstatus_clause}
  GROUP BY building
) h ON h.building = b.name
ORDER BY b.name
"""

CANDIDATES_SQL = """
SELECT
  b.name AS building
FROM `tabBuilding` b
LEFT JOIN (
  SELECT building, COUNT(*) AS actual_households
  FROM `tabHousehold`
  WHERE building IS NOT NULL AND building <> ''
  {docstatus_clause}
  GROUP BY building
) h ON h.building = b.name
WHERE COALESCE(b.how_many_households_occupy_this_building, 0) > COALESCE(h.actual_households, 0)
  AND b.status <> 'Returned'
ORDER BY b.name
"""

UPDATE_SQL = """
UPDATE `tabBuilding` b
LEFT JOIN (
  SELECT building, COUNT(*) AS actual_households
  FROM `tabHousehold`
  WHERE building IS NOT NULL AND building <> ''
  {docstatus_clause}
  GROUP BY building
) h ON h.building = b.name
SET b.status   = 'Returned',
    b.modified = NOW(),
    b.modified_by = 'Administrator'
WHERE COALESCE(b.how_many_households_occupy_this_building, 0) > COALESCE(h.actual_households, 0)
  AND b.status <> 'Returned'
"""

def _docstatus_clause(only_submitted_households: bool) -> str:
    return "AND docstatus = 1" if only_submitted_households else ""

def dry_run_buildings(expected_vs_actual=True, only_submitted_households=False, limit=None):
    """
    Dry-run viewer.
    - expected_vs_actual=True: show full preview (expected vs actual, per building).
    - only_submitted_households=True: count only submitted households.
    - limit: optional int to limit output rows in the console.
    """
    clause = _docstatus_clause(only_submitted_households)
    sql = DRY_RUN_SQL.format(docstatus_clause=clause)
    rows = frappe.db.sql(sql, as_dict=True)
    if expected_vs_actual:
        print(f"[Dry-Run] Buildings preview (rows={len(rows)})")
        if limit:
            rows = rows[:int(limit)]
        for r in rows:
            status_if_applied = "Returned" if (r["expected_households"] > r["actual_households"]) else r["current_status"]
            will_change = int(status_if_applied == "Returned" and r["current_status"] != "Returned")
            print(
                f"- {r['building']} | type={r['building_type']} | "
                f"expected={r['expected_households']} | actual={r['actual_households']} | "
                f"current={r['current_status']} | would_be={status_if_applied} | will_change={will_change}"
            )
    else:
        # show only candidates
        sql = CANDIDATES_SQL.format(docstatus_clause=clause)
        rows = frappe.db.sql(sql, as_dict=True)
        print(f"[Dry-Run] Buildings that would change to 'Returned' (rows={len(rows)}):")
        if limit:
            rows = rows[:int(limit)]
        for r in rows:
            print(f"- {r['building']}")
    return rows

def apply_building_status_returned(only_submitted_households=False, batch_size=500, use_orm=True):
    """
    Apply the rule:
      If how_many_households_occupy_this_building > actual linked households,
      set Building.status = 'Returned'.

    Params:
      - only_submitted_households: count only submitted households (docstatus=1)
      - batch_size: commit every N updates (ORM mode)
      - use_orm: True = use Frappe ORM (triggers doc events/validations),
                 False = run the SQL once (fast; bypasses events)
    """
    clause = _docstatus_clause(only_submitted_households)

    if use_orm:
        # Get candidate building names via SQL, then update via Doc API.
        candidates = frappe.db.sql(CANDIDATES_SQL.format(docstatus_clause=clause), as_dict=True)
        total = len(candidates)
        print(f"[Apply-ORM] Candidates to set 'Returned': {total}")

        updated = 0
        for i, row in enumerate(candidates, start=1):
            name = row["building"]
            try:
                doc = frappe.get_doc("Building", name)
                # Double-check condition (defensive) — optional:
                # You can skip if doc.status already 'Returned'
                if doc.get("status") != "Returned":
                    doc.status = "Returned"
                    doc.save(ignore_permissions=True)  # triggers validations & on_update
                    updated += 1
            except Exception as e:
                frappe.log_error(f"Failed to set Returned for Building {name}: {e}")

            if i % batch_size == 0:
                frappe.db.commit()
                print(f"  committed {i}/{total} processed...")

        frappe.db.commit()
        print(f"[Apply-ORM] Updated: {updated} / {total}")
        return {"updated": updated, "total_candidates": total}

    else:
        # Direct SQL path (fast). We still run it via frappe.db.sql (Python wraps it),
        # but this bypasses Doc events/validations.
        frappe.db.sql("SET SESSION SQL_SAFE_UPDATES = 0")
        frappe.db.sql(UPDATE_SQL.format(docstatus_clause=clause))
        # Fetch number of affected rows
        affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
        frappe.db.sql("SET SESSION SQL_SAFE_UPDATES = 1")
        frappe.db.commit()
        print(f"[Apply-SQL] Rows updated: {affected}")
        return {"updated": affected}

# bench --site admin.coveragetrackr.com execute gis.test.dry_run_buildings --kwargs '{"expected_vs_actual": 1, "only_submitted_households": 0, "limit": 50}'
# bench --site admin.coveragetrackr.com execute gis.test.apply_building_status_returned --kwargs '{"only_submitted_households": 0, "use_orm": 0}'




import frappe

# ---------- SQL templates ----------
DRY_RUN_SQL_HH = """
SELECT
  hh.name AS household,
  COALESCE(hh.how_many_household_members_are_below_5, 0) AS expected_under5,
  COALESCE(c.actual_children, 0) AS actual_children,
  hh.status AS current_status
FROM `tabHousehold` hh
LEFT JOIN (
  SELECT household, COUNT(*) AS actual_children
  FROM `tabChildren`
  WHERE household IS NOT NULL AND household <> ''
  {child_docstatus_clause}
  {child_age_clause}
  GROUP BY household
) c ON c.household = hh.name
ORDER BY hh.name
"""

CANDIDATES_SQL_HH = """
SELECT hh.name AS household
FROM `tabHousehold` hh
LEFT JOIN (
  SELECT household, COUNT(*) AS actual_children
  FROM `tabChildren`
  WHERE household IS NOT NULL AND household <> ''
  {child_docstatus_clause}
  {child_age_clause}
  GROUP BY household
) c ON c.household = hh.name
WHERE COALESCE(hh.how_many_household_members_are_below_5, 0) > COALESCE(c.actual_children, 0)
  AND hh.status <> 'Returned'
ORDER BY hh.name
"""

UPDATE_SQL_HH = """
UPDATE `tabHousehold` hh
LEFT JOIN (
  SELECT household, COUNT(*) AS actual_children
  FROM `tabChildren`
  WHERE household IS NOT NULL AND household <> ''
  {child_docstatus_clause}
  {child_age_clause}
  GROUP BY household
) c ON c.household = hh.name
SET hh.status   = 'Returned',
    hh.modified = NOW(),
    hh.modified_by = 'Administrator'
WHERE COALESCE(hh.how_many_household_members_are_below_5, 0) > COALESCE(c.actual_children, 0)
  AND hh.status <> 'Returned'
"""

def _child_docstatus_clause(only_submitted_children: bool) -> str:
    return "AND docstatus = 1" if only_submitted_children else ""

def _child_age_clause(use_age_filter: bool, dob_field: str = None, age_field: str = None) -> str:
    """
    Optional: restrict count to under-5s.
    - If your Children doctype has an integer 'age_years' column, pass age_field='age_years'.
    - If it has a DOB column, pass dob_field='dob' (or whatever it's called).
    If neither provided or use_age_filter=False, returns empty string.
    """
    if not use_age_filter:
        return ""
    if age_field:
        return f"AND {age_field} < 5"
    if dob_field:
        return f"AND TIMESTAMPDIFF(YEAR, {dob_field}, CURDATE()) < 5"
    return ""  # no filter if not specified

# ---------- DRY RUN ----------
def dry_run_households_under5(expected_vs_actual=True,
                              only_submitted_children=False,
                              limit=None,
                              use_age_filter=False,
                              dob_field=None,
                              age_field=None):
    """
    Dry-run for Household vs Children (under-5 expected vs actual).
    - expected_vs_actual=True: show preview with expected/actual per Household.
    - only_submitted_children=True: count only children with docstatus=1.
    - use_age_filter=True: count only under-5s (set either age_field or dob_field).
    - limit: limit printed rows in console (for bench execute).
    """
    child_docstatus = _child_docstatus_clause(only_submitted_children)
    child_age = _child_age_clause(use_age_filter, dob_field=dob_field, age_field=age_field)

    if expected_vs_actual:
        sql = DRY_RUN_SQL_HH.format(child_docstatus_clause=child_docstatus, child_age_clause=child_age)
        rows = frappe.db.sql(sql, as_dict=True)
        print(f"[Dry-Run HH] Preview rows: {len(rows)}")
        if limit:
            rows = rows[:int(limit)]
        for r in rows:
            status_if = "Returned" if (r["expected_under5"] > r["actual_children"]) else r["current_status"]
            will_change = int(status_if == "Returned" and r["current_status"] != "Returned")
            print(
                f"- {r['household']} | expected_under5={r['expected_under5']} | "
                f"actual_children={r['actual_children']} | current={r['current_status']} "
                f"| would_be={status_if} | will_change={will_change}"
            )
        return rows
    else:
        sql = CANDIDATES_SQL_HH.format(child_docstatus_clause=child_docstatus, child_age_clause=child_age)
        rows = frappe.db.sql(sql, as_dict=True)
        print(f"[Dry-Run HH] Candidates to change: {len(rows)}")
        if limit:
            rows = rows[:int(limit)]
        for r in rows:
            print(f"- {r['household']}")
        return rows

# ---------- APPLY ----------
def apply_household_status_returned_under5(only_submitted_children=False,
                                           use_age_filter=False,
                                           dob_field=None,
                                           age_field=None,
                                           batch_size=500,
                                           use_orm=True):
    """
    Apply rule to Households:
      If how_many_household_members_are_below_5 > (count of linked Children),
      set Household.status = 'Returned'.

    Params:
      - only_submitted_children: count only children with docstatus=1
      - use_age_filter: count only under-5s (set dob_field or age_field)
      - dob_field / age_field: column names in tabChildren to compute '< 5'
      - batch_size: ORM commit interval
      - use_orm: True = use Doc API (triggers events), False = run direct SQL
    """
    child_docstatus = _child_docstatus_clause(only_submitted_children)
    child_age = _child_age_clause(use_age_filter, dob_field=dob_field, age_field=age_field)

    if use_orm:
        # Get candidate households via SQL, then update via the Doc API
        candidates = frappe.db.sql(
            CANDIDATES_SQL_HH.format(child_docstatus_clause=child_docstatus, child_age_clause=child_age),
            as_dict=True
        )
        total = len(candidates)
        print(f"[Apply-ORM HH] Candidates: {total}")

        updated = 0
        for i, row in enumerate(candidates, start=1):
            name = row["household"]
            try:
                doc = frappe.get_doc("Household", name)
                if doc.get("status") != "Returned":
                    doc.status = "Returned"
                    doc.save(ignore_permissions=True)
                    updated += 1
            except Exception as e:
                frappe.log_error(f"Failed to set Returned for Household {name}: {e}")

            if i % batch_size == 0:
                frappe.db.commit()
                print(f"  committed {i}/{total} processed...")

        frappe.db.commit()
        print(f"[Apply-ORM HH] Updated: {updated} / {total}")
        return {"updated": updated, "total_candidates": total}

    else:
        # Direct SQL inside Python (fast; bypasses Doc events)
        frappe.db.sql("SET SESSION SQL_SAFE_UPDATES = 0")
        frappe.db.sql(UPDATE_SQL_HH.format(child_docstatus_clause=child_docstatus, child_age_clause=child_age))
        affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
        frappe.db.sql("SET SESSION SQL_SAFE_UPDATES = 1")
        frappe.db.commit()
        print(f"[Apply-SQL HH] Rows updated: {affected}")
        return {"updated": affected}

# bench --site admin.coveragetrackr.com execute gis.test.dry_run_households_under5 --kwargs '{"expected_vs_actual": 1, "only_submitted_children": 0, "limit": 50}'
# bench --site admin.coveragetrackr.com execute gis.test.apply_household_status_returned_under5 --kwargs '{"only_submitted_children": 0, "use_orm": 0, "batch_size": 5}'
