import frappe
from frappe import _
from frappe.utils.password import update_password
from datetime import datetime, timedelta
import requests
import random
import time
import re
import json
import os


session = requests.Session()

def sanitize_input(input_str):
  return re.sub(r'\W', '', input_str)

def auth_perm(doctype, ptype, docid):
  if 'StripeAdmin' in frappe.get_roles():
    return True

def is_valid_date_format(input_str):
  # Define the regular expression pattern for 'YYYY-MM-DD' format
  date_pattern = r'^\d{4}-\d{2}-\d{2}$'
  # Check if the input string matches the pattern
  return re.match(date_pattern, input_str) is not None

# convert date to dhis period and period to date

def is_valid_email(email):
  email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  return re.match(email_pattern, email) is not None

def convert_date(date_str, to='date'):
  if to == 'date':
    date_obj = datetime.strptime(date_str, "%Y-%m")
    # Add the day component to the date
    date_with_day = date_obj.replace(day=1)
    # Convert the date back to string format
    return date_with_day.strftime("%Y-%m-%d")
  elif to == 'period':
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_with_day = date_obj.replace(day=1)
    return date_with_day.strftime("%Y-%m")

def auto_dates():
  dateTo = datetime.now().replace(day=1).strftime('%Y-%m-%d')
  dateFrom = datetime.now().replace(day=1) - timedelta(days=124)
  dateFrom = dateFrom.replace(day=1).strftime('%Y-%m-%d')
  dateFrom = '2023-01-01'
  dateTo = '2023-04-01'
  return {'from': dateFrom, 'to': dateTo}

def generate_keys(user):
  user_doc = frappe.get_doc("User", user)
  sid = frappe.session.user
 
  if frappe.cache().get_value(user):
    user_doc.api_secret = frappe.cache.get_value(user)
    user_doc.sid = frappe.cache.get_value(f'{user}_sid')
  else:
    api_secret = frappe.generate_hash(length=15)
    frappe.cache().set_value(user, api_secret)
    frappe.cache().set_value(f'{user}_sid', sid)
    user_doc.api_secret = frappe.cache.get_value(user)

    # api_key = frappe.generate_hash(length=32)
    # api_secret = frappe.generate_hash(length=32)

  if not user_doc.api_key:
    user_doc.api_key = frappe.generate_hash(length=15)
  
  usr_data = {
    'api_key': user_doc.api_key,
    'api_secret': user_doc.api_secret,
    'username': user_doc.username,
    'email': user_doc.email
  }

  user_doc.save(ignore_permissions=True)
  
  # u.api_secret = frappe.cache.get_value(user)
  # return u.api_secret
  # return frappe.cache.get_value(user);
  return usr_data

def get_date_range(start_date_str, end_date_str):
  if is_valid_date_format(start_date_str) == False:
      return []
  if is_valid_date_format(end_date_str) == False:
      return []
  # Convert the date strings to datetime objects and set the day component to 1
  start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(day=1)
  end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(day=1)

  # Initialize an empty list to store the dates
  date_range = []

  # Loop through the months and add the first day of each month to the list
  current_date = start_date

  while current_date <= end_date:
      date_range.append(current_date.strftime('%Y-%m-%d'))
      current_date = current_date + timedelta(days=31)
      current_date = current_date.replace(day=1)
  return date_range


def set_error(code):
    message = ''

    if code == 401:
        message = 'Authentication Error'
    elif code == 403:
        message = "You dont have permission to access the requested resource"
    elif code == 404:
        message = 'No record found'
    elif code == 505:
        message = 'Internal Server Error'

    frappe.response.message = message
    frappe.response.code = code


def set_res(**kwargs):
  if 'error' in kwargs:
    return set_error(kwargs['error'])
  
  frappe.response.message = 'Success'
  frappe.response.status = 200
  for key, val in kwargs.items():
    frappe.response[key] = val

def fetch_db_resource(stmt=None, var=None, doc=None, fields=None, filters=None):
  try:
    data = None

    if stmt and var:
      data = frappe.db.sql(stmt, var, as_dict=True)
    elif stmt:
       data = frappe.db.sql(stmt, as_dict=True)
    elif doc:
      data = frappe.db.get_all(doc, fields=fields, filters=filters)
    
    if len(data) > 0:
      return data
    else:
      set_error(code=404)
  except:
    set_error(code=505)
  return

def save_image(request, field_name, img_name):
    uploaded_file = request.files[field_name]

    if uploaded_file:
        # Fetch site_name from site_config.json
        site_name = frappe.get_site_config().get("site_name", "admin.coveragetrackr.com")  # Default fallback

        # Construct save path dynamically
        save_path = os.path.join(os.path.expanduser('~'),
                                 f'frappe-bench/sites/{site_name}/public/files',
                                 img_name)

        with open(save_path, 'wb') as new_file:
            new_file.write(uploaded_file.read())

        return f"/files/{img_name}"
    
    return "";


def reset_user_password(user_email, new_password):
    print(new_password)
    user = frappe.get_doc("User", user_email)
    if user:
        update_password(user.name, new_password)
        return f"Password reset for user: {user_email}"
    else:
        return f"User not found: {user_email}"

def add_role_permissions(role):
    doc_permitted = [
        'Grid Creator',
        'State',
        'Local Government Area',
        'Ward',
        'Facility',
        'Grid Doctypes',
        'Grid',
        'Assignees'
    ]

    for doc in doc_permitted:
        if not frappe.db.get_value('Custom DocPerm', dict(parent=doc, role=role,
		permlevel=0, if_owner=0)):

            custom_docperm = frappe.get_doc({
                "doctype":"Custom DocPerm",
                "__islocal": 1,
                "parent": doc,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": 0,
                'read': 1,
            })
            custom_docperm.save()
            frappe.db.commit()


def create_user(names):
  for name in names:
    firstname = name['Name'].split(' ')[0].title()
    lastname = name['Name'].split(' ')[1].title()
    username = name['Email']
    password = f'{firstname.lower()}@8867'

    if not 'role' in name:
      role = 'GISAdmin'
    else:
      role = name['role']

    role_name = frappe.get_value('Role', {'role_name': role}, 'name')
    if not role_name:
        
      new_role = frappe.get_doc({
        'doctype': 'Role',
        'role_name': role,
        'desk_access': 0  # Set to 1 if you want Desk access for this role
      })

      new_role.insert()
      frappe.db.commit()

      role_name = new_role.name
      add_role_permissions(role_name)

    new_user = frappe.get_doc({
      "doctype": "User",
      "email": username,
      "first_name": firstname,
      "last_name": lastname,
      "password": password,
      "roles": [{'role': role_name}]
    })

    new_user.insert()
    frappe.db.commit()

    print({'email': username, 'password': password})
    reset_user_password(username, password)

def read_json_as_dict(file_path):
    with open(file_path, 'r') as file:
      data = json.load(file)
    return data

def create_admin():
  create_user([{"Name": "Gis Admin", "Email": "gis.admin@sydani.org"}])

def sanitize_name(name):
    # Strip spaces
    name = name.strip()
    # Remove unwanted characters (anything not a letter, number, or space)
    name = re.sub(r"[^A-Za-z0-9\s]", "", name)
    # Collapse multiple spaces into one
    name = re.sub(r"\s+", " ", name)
    return name

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
