# import frappe, json
# from datetime import datetime
# from werkzeug.wrappers import Response
# from frappe import get_site_config


# # Hard caps / defaults
# MAX_LIMIT = 15000
# DEFAULT_LIMIT = 15000

# # ---- Allowed doctypes & geometry field mapping ----
# ALLOWED = {
#     "Children": {
#         "geom_field": "geolocation",
#         "default_status": "Approved",
#         "exclude_fields": {
#             "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
#             "docstatus","idx"
#         },
#         "filter_map": {
#             "status": "status",
#             "settlement": "settlement",
#             "ward": "ward",
#             "local_government_area": "local_government_area",
#             "state": "state",
#             "household": "household",
#             "building": "building",
#         },
#     },
#     "Household": {
#         "geom_field": "geolocation",
#         "default_status": "Approved",
#         "exclude_fields": {
#             "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
#             "docstatus","idx"
#         },
#         "filter_map": {
#             "status": "status",
#             "settlement": "settlement",
#             "ward": "ward",
#             "local_government_area": "local_government_area",
#             "state": "state",
#             "building": "building",
#         },
#     },
#     "Building": {
#         "geom_field": "geolocation",
#         "default_status": "Approved",
#         "exclude_fields": {
#             "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
#             "docstatus","idx"
#         },
#         "filter_map": {
#             "status": "status",
#             "settlement": "settlement",
#             "ward": "ward",
#             "local_government_area": "local_government_area",
#             "state": "state",
#         },
#     },
#     "Facility": {
#         "geom_field": "geolocation",
#         "default_status": None,   # HF typically has no status
#         "exclude_fields": {
#             "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
#             "docstatus","idx"
#         },
#         "filter_map": {
#             "ward": "ward",
#             "local_government_area": "local_government_area",
#             "state": "state",
#         },
#     },
#     "Settlement": {
#         "geom_field": "geolocation",
#         "default_status": "Approved",
#         "exclude_fields": {
#             "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
#             "docstatus","idx"
#         },
#         "filter_map": {
#             "ward": "ward",
#             "local_government_area": "local_government_area",
#             "state": "state",
#         },
#     },
# }

# # ----------------- helpers -----------------
# def _safe_json(val):
#     """Parse JSON safely; returns dict or None."""
#     if not val:
#         return None
#     if isinstance(val, dict):
#         return val
#     if isinstance(val, (bytes, bytearray)):
#         try:
#             return json.loads(val.decode("utf-8", "ignore"))
#         except Exception:
#             return None
#     if isinstance(val, str):
#         s = val.strip()
#         if not s:
#             return None
#         try:
#             return json.loads(s)
#         except Exception:
#             return None
#     return None

# def _extract_geometry(gj):
#     """
#     Normalize stored GeoJSON into a Geometry object:
#     - If it's a FeatureCollection, take the first feature's geometry (if any).
#     - If it's a Feature, return its 'geometry'.
#     - If it's already a Geometry, return it.
#     - Else None.
#     """
#     if not isinstance(gj, dict):
#         return None
#     t = gj.get("type")
#     if t == "FeatureCollection":
#         feats = gj.get("features") or []
#         if feats and isinstance(feats[0], dict):
#             return feats[0].get("geometry")
#         return None
#     if t == "Feature":
#         return gj.get("geometry")
#     # assume it’s a Geometry
#     if "type" in gj and "coordinates" in gj:
#         return gj
#     # sometimes we store {"geometry": {...}}
#     if "geometry" in gj and isinstance(gj["geometry"], dict):
#         return gj["geometry"]
#     return None

# def _to_feature(row, geom_field, exclude_props, field_whitelist=None):
#     """Turn a row dict into a GeoJSON Feature with clean properties."""
#     geom_json = _safe_json(row.get(geom_field))
#     geometry = _extract_geometry(geom_json)
#     props = {k: v for k, v in row.items() if k not in (exclude_props | {geom_field})}
#     if field_whitelist:
#         props = {k: v for k, v in props.items() if k in field_whitelist or k == "name"}
#     return {"type": "Feature", "geometry": geometry, "properties": props}

# def _build_filters(cfg, args):
#     """Map incoming query args into frappe.get_all filters."""
#     filt = {}
#     for api_key, col in cfg["filter_map"].items():
#         if col is None:
#             continue
#         val = args.get(api_key)
#         if val is None or val == "":
#             continue
#         if isinstance(val, str) and "," in val:
#             filt[col] = ["in", [x.strip() for x in val.split(",") if x.strip()]]
#         else:
#             filt[col] = val
#     if cfg.get("default_status") and "status" in cfg["filter_map"] and "status" not in filt:
#         filt[cfg["filter_map"]["status"]] = cfg["default_status"]
#     return filt

# def _get_fields_for_query(doctype, geom_field, field_whitelist):
#     base = ["name", geom_field]
#     if field_whitelist:
#         return list({*base, *field_whitelist})
#     return ["*"]  # fetch all, we’ll drop excluded at serialization

# # ----------------- endpoint -----------------
# @frappe.whitelist(allow_guest=True)  # keep allow_guest while testing
# def export_geojson_arcgis(
#     doctype: str,
#     limit: int = DEFAULT_LIMIT,
#     offset: int = 0,
#     fields: str | None = None,
#     updated_since: str | None = None,
#     # common filters:
#     state: str | None = None,
#     local_government_area: str | None = None,
#     ward: str | None = None,
#     settlement: str | None = None,
#     status: str | None = None,
# ):

        
#     """
#     Return **pure GeoJSON**:

#     {
#       "type": "FeatureCollection",
#       "name": "<Doctype>",
#       "features": [ { "type":"Feature", "properties": {...}, "geometry": {...} }, ... ]
#     }

#     - No child tables.
#     - Paging via limit/offset.
#     - Optional 'fields' (comma list) to whitelist properties.
#     - Optional 'updated_since' (ISO-8601) filters `modified` >= timestamp.
#     """
#     if doctype not in ALLOWED:
#         frappe.throw(f"Doctype not allowed: {doctype}")

#     cfg = ALLOWED[doctype]
#     geom_field = cfg["geom_field"]
#     exclude_props = set(cfg["exclude_fields"])

#     try:
#         limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
#         offset = max(0, int(offset or 0))
#     except Exception:
#         frappe.throw("Invalid limit/offset")

#     field_whitelist = None
#     if fields:
#         field_whitelist = set([f.strip() for f in fields.split(",") if f and f.strip()])

#     args = {
#         "state": state,
#         "local_government_area": local_government_area,
#         "ward": ward,
#         "settlement": settlement,
#         "status": status,
#     }
#     filters = _build_filters(cfg, args)

#     if updated_since:
#         try:
#             _ = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
#             filters["modified"] = [">=", updated_since]
#         except Exception:
#             frappe.throw("updated_since must be ISO-8601, e.g. 2024-10-10T12:00:00Z")

#     fields_for_query = _get_fields_for_query(doctype, geom_field, field_whitelist)

#     rows = frappe.get_all(
#         doctype,
#         filters=filters,
#         fields=fields_for_query,
#         limit_page_length=limit,
#         limit_start=offset,
#         order_by="modified desc, name asc",
#     )

#     # features = []
#     # for r in rows:
#     #     feat = _to_feature(r, geom_field, exclude_props, field_whitelist)
#     #     # Only include if geometry is present & valid
#     #     if feat.get("geometry"):
#     #         features.append(feat)

#     # Build base URL from site_config.site_name
#     site_conf = get_site_config()
#     site_name = site_conf.get("site_name")
#     base_url = f"https://{site_name}" if site_name else ""

#     features = []
#     for r in rows:
#         feat = _to_feature(r, geom_field, exclude_props, field_whitelist)

#         if not feat.get("geometry"):
#             continue

#         # If this is Building, prepend full URL to picture fields
#         if doctype == "Building" and base_url:
#             props = feat.get("properties", {}) or {}
#             for key in ("building_picture", "building_picture_2"):
#                 val = props.get(key)
#                 if isinstance(val, str) and val.startswith("/"):
#                     props[key] = base_url + val
#             feat["properties"] = props

#         features.append(feat)


#     fc = {
#         "type": "FeatureCollection",
#         "name": doctype,
#         "features": features,
#     }

#     # body = json.dumps(fc, ensure_ascii=False)
#     body = frappe.as_json(fc)
#     # Replace the escaped Naira sign with the literal symbol
#     body = body.replace("\\u20a6", "₦")
#     resp = Response(body, mimetype="application/json; charset=utf-8")
#     # Optional CORS for ArcGIS/clients
#     resp.headers["Access-Control-Allow-Origin"] = "*"
#     return resp


import frappe, json
from datetime import datetime
from werkzeug.wrappers import Response
from frappe import get_site_config


# Hard caps / defaults
MAX_LIMIT = 15000
DEFAULT_LIMIT = 15000

# ---- Allowed doctypes & geometry field mapping ----
ALLOWED = {
    "Children": {
        "geom_field": "geolocation",
        "default_status": "Approved",
        "exclude_fields": {
            "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
            "docstatus","idx"
        },
        "filter_map": {
            "status": "status",
            "settlement": "settlement",
            "ward": "ward",
            "local_government_area": "local_government_area",
            "state": "state",
            "household": "household",
            "building": "building",
        },
    },
    "Household": {
        "geom_field": "geolocation",
        "default_status": "Approved",
        "exclude_fields": {
            "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
            "docstatus","idx"
        },
        "filter_map": {
            "status": "status",
            "settlement": "settlement",
            "ward": "ward",
            "local_government_area": "local_government_area",
            "state": "state",
            "building": "building",
        },
    },
    "Building": {
        "geom_field": "geolocation",
        "default_status": "Approved",
        "exclude_fields": {
            "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
            "docstatus","idx"
        },
        "filter_map": {
            "status": "status",
            "settlement": "settlement",
            "ward": "ward",
            "local_government_area": "local_government_area",
            "state": "state",
        },
    },
    "Facility": {
        "geom_field": "geolocation",
        "default_status": None,   # HF typically has no status
        "exclude_fields": {
            "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
            "docstatus","idx"
        },
        "filter_map": {
            "ward": "ward",
            "local_government_area": "local_government_area",
            "state": "state",
        },
    },
    "Settlement": {
        "geom_field": "geolocation",
        "default_status": "Approved",
        "exclude_fields": {
            "owner","modified_by","creation","modified","_user_tags","_comments","_assign",
            "docstatus","idx"
        },
        "filter_map": {
            "ward": "ward",
            "local_government_area": "local_government_area",
            "state": "state",
        },
    },
}

# ----------------- helpers -----------------
def _safe_json(val):
    """Parse JSON safely; returns dict or None."""
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
            return None
    return None

def _extract_geometry(gj):
    """
    Normalize stored GeoJSON into a Geometry object:
    - If it's a FeatureCollection, take the first feature's geometry (if any).
    - If it's a Feature, return its 'geometry'.
    - If it's already a Geometry, return it.
    - Else None.
    """
    if not isinstance(gj, dict):
        return None
    t = gj.get("type")
    if t == "FeatureCollection":
        feats = gj.get("features") or []
        if feats and isinstance(feats[0], dict):
            return feats[0].get("geometry")
        return None
    if t == "Feature":
        return gj.get("geometry")
    # assume it’s a Geometry
    if "type" in gj and "coordinates" in gj:
        return gj
    # sometimes we store {"geometry": {...}}
    if "geometry" in gj and isinstance(gj["geometry"], dict):
        return gj["geometry"]
    return None

def _to_feature(row, geom_field, exclude_props, field_whitelist=None):
    """Turn a row dict into a GeoJSON Feature with clean properties."""
    geom_json = _safe_json(row.get(geom_field))
    geometry = _extract_geometry(geom_json)
    props = {k: v for k, v in row.items() if k not in (exclude_props | {geom_field})}
    if field_whitelist:
        props = {k: v for k, v in props.items() if k in field_whitelist or k == "name"}
    return {"type": "Feature", "geometry": geometry, "properties": props}

def _build_filters(cfg, args):
    """Map incoming query args into frappe.get_all filters."""
    filt = {}
    for api_key, col in cfg["filter_map"].items():
        if col is None:
            continue
        val = args.get(api_key)
        if val is None or val == "":
            continue
        if isinstance(val, str) and "," in val:
            filt[col] = ["in", [x.strip() for x in val.split(",") if x.strip()]]
        else:
            filt[col] = val
    if cfg.get("default_status") and "status" in cfg["filter_map"] and "status" not in filt:
        filt[cfg["filter_map"]["status"]] = cfg["default_status"]
    return filt

def _get_fields_for_query(doctype, geom_field, field_whitelist):
    base = ["name", geom_field]
    if field_whitelist:
        return list({*base, *field_whitelist})
    return ["*"]  # fetch all, we’ll drop excluded at serialization

@frappe.whitelist(allow_guest=True)  # keep allow_guest while testing
def export_geojson_arcgis(
    doctype: str,
    limit: int = DEFAULT_LIMIT,      # page size
    page: int = 1,                   # 1-based page number
    fields: str | None = None,
    updated_since: str | None = None,
    # common filters:
    state: str | None = None,
    local_government_area: str | None = None,
    ward: str | None = None,
    settlement: str | None = None,
    status: str | None = None,
):
    """
    Return **GeoJSON FeatureCollection** with simple page-based pagination.

    Query params:
      - doctype: one of the ALLOWED doctypes
      - limit:   page size (max 10,000)
      - page:    1-based page number
      - fields:  comma list to whitelist properties
      - updated_since: ISO-8601 datetime → filters `modified >=` this value

    Response:
    {
      "type": "FeatureCollection",
      "name": "<Doctype>",
      "features": [...],
      "properties": {
        "page": <int>,
        "page_size": <int>,
        "total_features": <int>,
        "total_pages": <int>
      }
    }
    """
    if doctype not in ALLOWED:
        frappe.throw(f"Doctype not allowed: {doctype}")

    cfg = ALLOWED[doctype]
    geom_field = cfg["geom_field"]
    exclude_props = set(cfg["exclude_fields"])

    # ---- paging params ----
    try:
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        page = max(1, int(page or 1))
    except Exception:
        frappe.throw("Invalid limit/page")

    offset = (page - 1) * limit

    # ---- field whitelist ----
    field_whitelist = None
    if fields:
        field_whitelist = set(
            f.strip() for f in fields.split(",") if f and f.strip()
        )

    # ---- build filters ----
    args = {
        "state": state,
        "local_government_area": local_government_area,
        "ward": ward,
        "settlement": settlement,
        "status": status,
    }
    filters = _build_filters(cfg, args)

    if updated_since:
        try:
            _ = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            filters["modified"] = [">=", updated_since]
        except Exception:
            frappe.throw("updated_since must be ISO-8601, e.g. 2024-10-10T12:00:00Z")

    fields_for_query = _get_fields_for_query(doctype, geom_field, field_whitelist)

    # ---- total count for pagination ----
    total_features = frappe.db.count(doctype, filters=filters)
    # avoid division by zero
    total_pages = (total_features + limit - 1) // limit if total_features else 0

    # clamp page if user requested beyond last page
    if total_pages and page > total_pages:
        page = total_pages
        offset = (page - 1) * limit

    # ---- fetch current page ----
    rows = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields_for_query,
        limit_page_length=limit,
        limit_start=offset,
        # changed: order by *creation* instead of modified
        order_by="creation desc, name asc",
    )

    # ---- build features ----
    site_conf = get_site_config()
    site_name = site_conf.get("site_name")
    base_url = f"https://{site_name}" if site_name else ""

    features = []
    for r in rows:
        feat = _to_feature(r, geom_field, exclude_props, field_whitelist)

        if not feat.get("geometry"):
            continue

        # If this is Building, prepend full URL to picture fields
        if doctype == "Building" and base_url:
            props = feat.get("properties", {}) or {}
            for key in ("building_picture", "building_picture_2"):
                val = props.get(key)
                if isinstance(val, str) and val.startswith("/"):
                    props[key] = base_url + val
            feat["properties"] = props

        features.append(feat)

    fc = {
        "type": "FeatureCollection",
        "name": doctype,
        "features": features,
        "properties": {  # valid extra member on FeatureCollection
            "page": page,
            "page_size": limit,
            "total_features": total_features,
            "total_pages": total_pages,
        },
    }

    body = frappe.as_json(fc)
    body = body.replace("\\u20a6", "₦")  # unescape Naira sign

    resp = Response(body, mimetype="application/json; charset=utf-8")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp



import frappe, json
from datetime import datetime
from werkzeug.wrappers import Response
from frappe import get_site_config

# We reuse the same MAX_LIMIT / DEFAULT_LIMIT constants:
# MAX_LIMIT = 10000
# DEFAULT_LIMIT = 10000

@frappe.whitelist()  # NOTE: no allow_guest=True → auth required
def export_excel_table(
    doctype: str,
    limit: int = DEFAULT_LIMIT,      # page size
    page: int = 1,                   # 1-based page number
    fields: str | None = None,
    updated_since: str | None = None,
    # common filters:
    state: str | None = None,
    local_government_area: str | None = None,
    ward: str | None = None,
    settlement: str | None = None,
    status: str | None = None,
):
    """
    Return a JSON *table* suitable for Excel / Power Query:

    {
      "doctype": "Building",
      "page": 1,
      "page_size": 10000,
      "total_rows": 12345,
      "total_pages": 2,
      "rows": [
        { "name": "...", "field1": "...", ... },
        ...
      ]
    }

    Notes:
    - Auth required (session cookie or API key/secret).
    - Page-based pagination: ?limit=10000&page=1
    - Optional 'fields' = comma-separated list to whitelist columns.
    - Optional 'updated_since' (ISO-8601) filters `modified >=`.
    """

    # --- 1. Validate doctype ---
    if doctype not in ALLOWED:
        frappe.throw(f"Doctype not allowed: {doctype}")

    cfg = ALLOWED[doctype]
    geom_field = cfg["geom_field"]
    exclude_props = set(cfg["exclude_fields"])

    # --- 2. Paging parameters ---
    try:
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        page = max(1, int(page or 1))
    except Exception:
        frappe.throw("Invalid limit/page")

    offset = (page - 1) * limit

    # --- 3. Field whitelist (optional) ---
    field_whitelist = None
    if fields:
        field_whitelist = set(
            f.strip() for f in fields.split(",") if f and f.strip()
        )

    # --- 4. Filters (state, LGA, ward, etc.) ---
    args = {
        "state": state,
        "local_government_area": local_government_area,
        "ward": ward,
        "settlement": settlement,
        "status": status,
    }
    filters = _build_filters(cfg, args)

    if updated_since:
        try:
            _ = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            filters["modified"] = [">=", updated_since]
        except Exception:
            frappe.throw("updated_since must be ISO-8601, e.g. 2024-10-10T12:00:00Z")

    fields_for_query = _get_fields_for_query(doctype, geom_field, field_whitelist)

    # --- 5. Total count for pagination ---
    total_rows = frappe.db.count(doctype, filters=filters)
    total_pages = (total_rows + limit - 1) // limit if total_rows else 0

    # Clamp page if too high
    if total_pages and page > total_pages:
        page = total_pages
        offset = (page - 1) * limit

    # --- 6. Fetch current page (ordered by creation) ---
    rows_raw = frappe.get_all(
        doctype,
        filters=filters,
        fields=fields_for_query,
        limit_page_length=limit,
        limit_start=offset,
        order_by="creation desc, name asc",  # or "creation asc" if you prefer oldest-first
    )

    # --- 7. Clean / normalize rows for Excel ---
    site_conf = get_site_config()
    site_name = site_conf.get("site_name")
    base_url = f"https://{site_name}" if site_name else ""

    rows_clean = []
    for r in rows_raw:
        row = {}

        # We keep name by default
        row["name"] = r.get("name")

        for k, v in r.items():
            if k == "name":
                continue

            # Drop internal / excluded fields
            if k in exclude_props:
                continue

            # If a whitelist is provided, only keep those + geom_field
            if field_whitelist and (k not in field_whitelist) and (k != geom_field):
                continue

            row[k] = v

        # For Buildings, expand picture URLs
        if doctype == "Building" and base_url:
            for key in ("building_picture", "building_picture_2"):
                val = row.get(key)
                if isinstance(val, str) and val.startswith("/"):
                    row[key] = base_url + val

        rows_clean.append(row)

    payload = {
        "doctype": doctype,
        "page": page,
        "page_size": limit,
        "total_rows": total_rows,
        "total_pages": total_pages,
        "rows": rows_clean,
    }

    body = frappe.as_json(payload)
    body = body.replace("\\u20a6", "₦")  # unescape Naira sign if present

    resp = Response(body, mimetype="application/json; charset=utf-8")
    # CORS is usually not needed for Excel Power Query, but safe:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
