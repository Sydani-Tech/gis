import frappe
from frappe import _
import requests
import json

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource
)

from gis.access_to_records import (
  projects, forms, outreach_forms, grids, save_building, save_settlement, save_household, save_children, save_vaccination, projects_for_dashboard_viewers
)

from gis.grid import (grid_facilities, grid_buildings, 
grid_states, grid_lgas, grid_wards, grid_settlements, grid_households)

# Auth
# @frappe.whitelist(allow_guest=True)
# def login(email, password):
#   if is_valid_email(email):
#     try:
#       login_manager = frappe.auth.LoginManager()
#       login_manager.authenticate(user=email, pwd=password)
#       login_manager.post_login()
#     except frappe.exceptions.AuthenticationError:
#       frappe.clear_messages()
#       set_error(code=401)
#       return

#     user = generate_keys(email)
#     roles = frappe.permissions.get_roles(user=email)
#     user_roles = [x for x in roles if x not in ['All', 'Guest']]
#     # user={
#     #   "message": "Authenticated",
#     #   "sid": frappe.session.sid,
#     #   "api_key": user.api_key,
#     #   "api_secret": user.api_secret,
#     #   "username": user.username,
#     #   "email": user.email,
#     #   'roles': user_roles
#     # }
#     set_res(user=user)
#   else:
#     return set_res(error=401)
#     # return {'status': 'Failed', 'message': 'Invalid Email'}

@frappe.whitelist(allow_guest=True)
def login(email, password):
    if is_valid_email(email):
        try:
            login_manager = frappe.auth.LoginManager()
            login_manager.authenticate(user=email, pwd=password)
            login_manager.post_login()
        except frappe.exceptions.AuthenticationError:
            frappe.clear_messages()
            frappe.response["error"] = {"code": 401, "message": "Authentication Failed"}
            return

        user_doc = frappe.get_doc("User", email)
        fields = ['key']
        filters = {'name': email}
        user_key = fetch_db_resource(doc='Sec Keys', fields=fields, filters=filters)

        # api_secret = frappe.cache().get_value(email)
        if user_key:
          api_secret = user_key[0]['key']
        else:          
          api_secret = frappe.generate_hash(length=15)
          nk = frappe.get_doc({'doctype': 'Sec Keys', 'usr': email, 'key': api_secret})
          nk.save(ignore_permissions=True)
          # frappe.cache().set_value(email, api_secret)
          user_doc.api_secret = nk.key
          user_doc.save(ignore_permissions=True)
       
        # user_data = frappe.db.get_value("User", email, ["username", "full_name", "phone","user_image"], as_dict=True)
        roles = frappe.permissions.get_roles(user=email)
        user_roles = [x for x in roles if x not in ["All", "Guest", "Desk Access"]]

        frappe.response["message"] = "Success"
        frappe.response["home_page"] = "/app"
        frappe.response["full_name"] = user_doc.full_name
        frappe.response["status"] = 200
        frappe.response["user"] = {
            "api_key": user_doc.api_key,
            "api_secret": api_secret,
            "username": user_doc.username,
            "email": email,
            "roles": user_roles,
            "phone": user_doc.phone,
            "user_image": user_doc.user_image
        }

        # Prepare response
        # frappe.response["message"] = "Success"
        # frappe.response["home_page"] = "/app"
        # frappe.response["full_name"] = user_data.get("full_name")
        # frappe.response["status"] = 200
        # frappe.response["user"] = {
        #     "api_key": user_doc.api_key,
        #     "api_secret": api_secret,
        #     "username": user_data.get("username"),
        #     "email": email,
        #     "roles": user_roles,
        #     "phone": user_data.get("phone"),
        #     "user_image": user_data.get("user_image")
        # }
    else:
        frappe.response["error"] = {"code": 401, "message": "Invalid Email"}


def users():
  
  pass
  # u = frappe.get_doc('Sec Keys', 'abc2@sydani.org')
  # print(u)
  # api = frappe.get_doc("API Key", {"user": 'abc2@sydani.org'})

  # api_secret = frappe.generate_hash(length=32)
  # frappe.cache().set_value(usr, api_secret)
  # k = frappe.cache.get_value(usr)
  # usr_data = {
  #   'api_key': user_doc.api_key,
  #   'api_secret': user_doc.api_secret,
  #   'username': user_doc.username,
  #   'email': user_doc.email
  # }

  # if frappe.cache().get_value(usr):
  #   print(k)

@frappe.whitelist(allow_guest=False)
def logout(email):
    # cookie_value = frappe.local.cookie_manager.get_cookie()
    # frappe.sessions.clear_sessions(user=email, keep_current=False)
    # frappe.clear_cache(user=email)
    # frappe.local.login_manager.logout()
    # frappe.cache().delete_value(email)
    # generate_keys(email)
    # frappe.response['message'] = {'success': 1, "message": 'Logged out'}

    api_secret = frappe.generate_hash(length=15)
    user_doc = frappe.get_doc("User", email)
    
    try:
      nk = frappe.get_doc('Sec Keys', email)
      nk.key = api_secret
      nk.save(ignore_permissions=True)
    except Exception as e:
      pass
    # frappe.cache().set_value(email, api_secret)
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)
    set_res(user={"message": 'Logged out'})


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
@frappe.whitelist()
def states(stateName=None):
  fields = ['name', 'state', 'country', 'geolocation']
  
  if stateName:
    filters = {'name': stateName}
    # filters = {'state': {'in': stateName}}
  else:
    filters = {}
  
  states = fetch_db_resource(doc='State', fields=fields, filters=filters)
  if states:
    set_res(states=states)

# get state lgas
@frappe.whitelist()
def lgas(stateName):
  fields = ['name', 'local_government_area', 'state', 'country', 'geolocation']
  filters = {'state': stateName}
  lgas = fetch_db_resource(
    doc='Local Government Area', fields=fields, filters=filters)

  if lgas:
    set_res(lgas=lgas)


# get single lga
@frappe.whitelist()
def lga(lgaName):
  fields = ['name', 'local_government_area', 'state', 'country', 'geolocation']
  filters = {'name': lgaName}
  lga = fetch_db_resource(
    doc='Local Government Area', fields=fields, filters=filters)

  if lga:
    set_res(lga=lga)


@frappe.whitelist()
def wards(lga=None, state=None):
    fields = [
        'name', 'ward', 'local_government_area', 
        'state', 'country', 'geolocation'
    ]
    
    # Create filters only if arguments are provided
    filters = {
        'local_government_area': lga,
        'state': state
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
    
    # Fetch wards with filters if provided, else fetch all records
    wards = fetch_db_resource(
        doc='Ward', 
        fields=fields, 
        filters=filters
    )

    # Limit the result to 20 records
    wards = wards[:20]
    
    # Return the fetched records
    set_res(wards=wards)

# get a single ward
@frappe.whitelist()
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

# get all wards settlements
@frappe.whitelist()
def settlements(stateName=None, lgaName=None, wardName=None):
  fields = [
    'name', 'ward', 'local_government_area', 
    'state', 'country', 'name_of_settlementcommunity_head', 'contact_of_settlementcommunity_head','type_of_settlement','facility_geolocation'
  ]

  filters = {
    'state': stateName,
    'local_government_area': lgaName,
    'ward': wardName
  }

  filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
  settlements = fetch_db_resource(
    doc='Settlement', fields=fields, filters=filters)

  set_res(settlements=settlements)  # Return all records if no filters are applied

# get all wards facilities
# @frappe.whitelist(allow_guest=True)
# def facilities(stateName= None, lgaName=None, wardName=None):
#   fields = [
#     'name', 'facility_name', 'facility_address', 
#     'ward', 'local_government_area', 
#     'state', 'country', 'geolocation'
#   ]
#   filters = {'state': stateName, 'local_government_area': lgaName, 'ward': wardName}
#   facilities = fetch_db_resource(
#     doc='Facility', fields=fields, filters=filters)

#   if facilities:
#     set_res(facilities=facilities)


@frappe.whitelist()
def facilities(ward=None, lga=None, state=None):
    fields = [
    'name', 'facility_name', 'facility_address', 
    'ward', 'local_government_area', 
    'state', 'country', 'geolocation'
  ]
    
    # Create filters only if arguments are provided
    filters = {
        'ward': ward,
        'local_government_area': lga,
        'state': state
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
    
    # Fetch facilities with filters if provided, else fetch all records
    facilities = fetch_db_resource(
        doc='Facility', 
        fields=fields, 
        filters=filters if filters else None
    )

     # Limit the result to 20 records
    facilities = facilities[:20]
    
    # Return the fetched records
    set_res(facilities=facilities)


# @frappe.whitelist(allow_guest=True)
# def facilities(stateName, lgaName, wardName):
#   fields = [
#     'name', 'facility_name', 'facility_address', 
#     'ward', 'local_government_area', 
#     'state', 'country', 'geolocation'
#   ]
#   filters = {'state': stateName, 'local_government_area': lgaName, 'ward': wardName}
#   facilities = fetch_db_resource(
#     doc='Facility', fields=fields, filters=filters)

#   if facilities:
#     set_res(facilities=facilities)



# get all wards facilities
@frappe.whitelist()
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

@frappe.whitelist()
def get_building(settlement=None, ward=None, lga=None, state=None):
    fields = [
        'name', 'building_number', 'building_address', 'settlement', 
        'ward', 'local_government_area', 'state', 
        'country', 'geolocation', 'building_type'
    ]
    
    # Create filters only if arguments are provided
    filters = {
        'ward': ward,
        'settlement': settlement,
        'local_government_area': lga,
        'state': state
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values

    # Prepare SQL query
    conditions = ["building_type = 'Residential'"]
    sql_values = []

    # Add filters to conditions
    for key, value in filters.items():
        conditions.append(f"{key} = %s")
        sql_values.append(value)
    
    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT {', '.join(fields)}
        FROM `tabBuilding`
        WHERE {where_clause}
    """
    
    # Execute the query
    buildings = frappe.db.sql(query, sql_values, as_dict=True)
    
    # Return the fetched records
    return {"buildings": buildings}



@frappe.whitelist()
def get_household(building=None, settlement=None, ward=None, lga=None, state=None):
    fields = [
        'name', 'name_of_household_head', 'building', 'settlement', 'phone_number',
        'ward', 'local_government_area', 'state', 'geolocation'
    ]
    
    # Create filters only if arguments are provided
    filters = {
        'building': building,
        'settlement': settlement,
        'ward': ward,
        'local_government_area': lga,
        'state': state
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
    
    # Fetch buildings with filters if provided, else fetch all records
    households = fetch_db_resource(
        doc='Household', 
        fields=fields, 
        filters=filters if filters else None
    )
    
    # Return the fetched records
    set_res(households=households)
    

@frappe.whitelist()
def get_user_records(project, form=None, status=None):
    
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    if not project:
        set_res(message="Project is a required filter.")
        return

    # Fetch user roles
    user_roles = frappe.permissions.get_roles(user)

    # Determine which table to fetch fields from based on user roles
    table_doctype = ""
    if "Enumerator" in user_roles:
        table_doctype = "Doctype Table"
    elif "Outreach Worker" in user_roles:
        table_doctype = "Outreach Doctype Table"

    if not table_doctype:
        set_res(message="User does not have permission to fetch records.")
        return

    # Fetch table definitions for the specified project
    table_definitions = frappe.get_all(
        table_doctype,
        fields=["document_type"],
        filters={"parent": project}
    )

    # Dynamically build tables and fields to fetch
    tables_to_fetch = {}
    filters = {"owner": user, "project": project}

    if status:
        filters["status"] = status

    for table in table_definitions:
        doc_type = table.get("document_type")
        if doc_type:
            tables_to_fetch[doc_type] = fetch_db_resource(
                doc=doc_type, fields=["*"], filters=filters
            )

    # If a specific form is provided, fetch only that form's records
    if form:
        tables_to_fetch = {form: tables_to_fetch.get(form)}

    # Return all records matching filters
    records = {k: v for k, v in tables_to_fetch.items() if v}

    if records:
        set_res(**records)
    else:
        set_res(message="No records found")

# def get_doctype():
#   # CHARACTER_MAXIMUM_LENGTH,
#   # NUMERIC_PRECISION,
#   stmt = f""" 
#     SELECT
#       TABLE_NAME,
#       COLUMN_NAME,
#       DATA_TYPE,
#       NUMERIC_SCALE,
#       COLUMN_TYPE,
#       COLUMN_KEY,
#       EXTRA
#     FROM
#       INFORMATION_SCHEMA.COLUMNS
#     WHERE 
#       TABLE_NAME = 'tabBuilding'
#   """

#   doc = frappe.db.sql(stmt, as_dict=True)
#   for field in doc:
#     print(field)
#     print(" ")

def cr():
  r = frappe.db.sql("select * from `tabFacility` where name = 'Anguwan Fatika Primary Health Center-Unguwar Fatika-Zaria-Kaduna'", as_dict=True)
  print(r[0]['geolocation'])