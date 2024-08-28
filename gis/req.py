import frappe
from frappe import _
import requests
import json

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource
)


# Auth
@frappe.whitelist(allow_guest=True)
def login(email, password):
  if is_valid_email(email):
    try:
      login_manager = frappe.auth.LoginManager()
      login_manager.authenticate(user=email, pwd=password)
      login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
      frappe.clear_messages()
      set_error(code=401)
      return

    user = generate_keys(email)
    roles = frappe.permissions.get_roles(user=email)
    user_roles = [x for x in roles if x not in ['All', 'Guest']]

    set_res(user={
      "message": "Authenticated",
      "sid": frappe.session.sid,
      "api_key": user.api_key,
      "api_secret": user.api_secret,
      "username": user.username,
      "email": user.email,
      'roles': user_roles
    })
  else:
    return set_res(error=401)
    # return {'status': 'Failed', 'message': 'Invalid Email'}


@frappe.whitelist()
def logout(email):
    # cookie_value = frappe.local.cookie_manager.get_cookie()
    frappe.sessions.clear_sessions(user=email, keep_current=False, device=None, force=True)
    frappe.clear_cache(user=email)
    frappe.local.login_manager.logout()
    frappe.cache().delete_value(email)
    generate_keys(email)
    frappe.response['message'] = {'success': 1, "message": 'Logged out'}

@frappe.whitelist()
def change_password(email, old_password, new_password):
  if is_valid_email(email):
    try:
      login_manager = frappe.auth.LoginManager()
      login_manager.authenticate(user=email, pwd=old_password)
      login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
      frappe.clear_messages()
      set_error(code=401)
      return
  
    reset_user_password(email, new_password)
    return login(email, new_password)

@frappe.whitelist(allow_guest=True)
def grids():
  grids = fetch_db_resource(f"""
    SELECT * FROM `tabGrid` 
  """)
  set_res(data=grids)

# def building_fields():
#   file_dir = '/home/frappe/frappe-bench/apps/gis/gis/fixtures'
#   file_name = f'{file_dir}/doctype.json'
#   json_dict = read_json_as_dict(file_name)
#   filtered_doc = None

#   for doc in json_dict:
#     if doc["autoname"] == "format:{building_number} - {street_name}":
#       filtered_doc = doc

#   if filtered_doc:
#     for field in filtered_doc['fields']:
#       print(field)
#       print(" ")


# get all states
@frappe.whitelist(allow_guest=True)
def states():
  fields = ['name', 'state', 'country', 'geolocation']
  states = fetch_db_resource(doc='State', fields=fields)
  if states:
    set_res(states=states)

# get a single state
@frappe.whitelist(allow_guest=True)
def state(stateName):

  fields = ['name', 'state', 'country', 'geolocation']
  filters = {'name': stateName}
  state = fetch_db_resource(doc='State', fields=fields, filters=filters)

  if state:
    set_res(state=state)

# get state lgas
@frappe.whitelist(allow_guest=True)
def lgas(stateName):
  fields = ['name', 'local_government_area', 'state', 'country', 'geolocation']
  filters = {'state': stateName}
  lgas = fetch_db_resource(
    doc='Local Government Area', fields=fields, filters=filters)

  if lgas:
    set_res(lgas=lgas)


# get single lga
@frappe.whitelist(allow_guest=True)
def lga(lgaName):
  fields = ['name', 'local_government_area', 'state', 'country', 'geolocation']
  filters = {'name': lgaName}
  lga = fetch_db_resource(
    doc='Local Government Area', fields=fields, filters=filters)

  if lga:
    set_res(lga=lga)

# get all lga wards
@frappe.whitelist(allow_guest=True)
def wards(stateName, lgaName):
  fields = [
    'name', 'ward', 'local_government_area', 
    'state', 'country', 'geolocation'
  ]
  filters = {'state': stateName, 'local_government_area': lgaName}
  wards = fetch_db_resource(
    doc='Ward', fields=fields, filters=filters)

  if wards:
    set_res(wards=wards)

# get a single ward
@frappe.whitelist(allow_guest=True)
def ward(wardName):
  fields = [
    'name', 'ward', 'local_government_area', 
    'state', 'country', 'geolocation'
  ]
  filters = {'name': wardName}
  ward = fetch_db_resource(
    doc='Ward', fields=fields, filters=filters)

  if ward:
    set_res(ward=ward)

# get all wards facilities
@frappe.whitelist(allow_guest=True)
def facilities(stateName, lgaName, wardName):
  fields = [
    'name', 'facility_name', 'facility_address', 
    'ward', 'local_government_area', 
    'state', 'country', 'geolocation'
  ]
  filters = {'state': stateName, 'local_government_area': lgaName, 'ward': wardName}
  facilities = fetch_db_resource(
    doc='Facility', fields=fields, filters=filters)

  if facilities:
    set_res(facilities=facilities)


# get all wards facilities
@frappe.whitelist(allow_guest=True)
def facility(facilityName):
  fields = [
    'name', 'facility_name', 'facility_address', 
    'ward', 'local_government_area', 
    'state', 'country', 'geolocation'
  ]
  filters = {'name': facilityName}
  facility = fetch_db_resource(
    doc='Facility', fields=fields, filters=filters)

  if facility:
    set_res(facility=facility)


def get_doctype():
  # CHARACTER_MAXIMUM_LENGTH,
  # NUMERIC_PRECISION,
  stmt = f""" 
    SELECT
      TABLE_NAME,
      COLUMN_NAME,
      DATA_TYPE,
      NUMERIC_SCALE,
      COLUMN_TYPE,
      COLUMN_KEY,
      EXTRA
    FROM
      INFORMATION_SCHEMA.COLUMNS
    WHERE 
      TABLE_NAME = 'tabBuilding'
  """

  doc = frappe.db.sql(stmt, as_dict=True)
  for field in doc:
    print(field)
    print(" ")