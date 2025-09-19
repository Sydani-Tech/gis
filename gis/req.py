import frappe
from frappe import _
import requests
import json


from frappe.utils.password import set_encrypted_password

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource
)

from gis.access_to_records import (
  projects, forms, outreach_forms, grids, save_building, save_settlement, save_household, save_children, save_vaccination, save_vaccination_summary, create_error_log, projects_for_dashboard_viewers
)

from gis.grid import (grid_facilities, grid_buildings, 
grid_states, grid_lgas, grid_wards, grid_settlements, grid_households)

import frappe
from frappe.utils.password import set_encrypted_password

@frappe.whitelist(allow_guest=True)
def login(email, password):
    if is_valid_email(email):
        try:
            # Authenticate User
            login_manager = frappe.auth.LoginManager()
            login_manager.authenticate(user=email, pwd=password)
            login_manager.post_login()
        except frappe.exceptions.AuthenticationError:
            frappe.clear_messages()
            frappe.response["error"] = {"code": 401, "message": "Authentication Failed"}
            return
        
        user_doc = frappe.get_doc("User", email)

        # Check if API Key already exists
        if not user_doc.api_key:
            user_doc.api_key = frappe.generate_hash(length=18)
            user_doc.save(ignore_permissions=True)

        # Check if API Secret exists in Sec Keys
        fields = ['key']
        filters = {'usr': email}
        user_key = fetch_db_resource(doc='Sec Keys', fields=fields, filters=filters)

        if user_key:
            api_secret = user_key[0]['key']
        else:
            api_secret = frappe.generate_hash(length=18)

            # Store secret securely in User doctype (hashed)
            set_encrypted_password("User", email, api_secret, "api_secret")

            # Also store in 'Sec Keys' (if needed for other purposes)
            nk = frappe.get_doc({
                'doctype': 'Sec Keys',
                'usr': email,
                'key': api_secret
            })
            nk.insert(ignore_permissions=True)

        # Get user roles
        roles = frappe.permissions.get_roles(user=email)
        user_roles = [x for x in roles if x not in ["All", "Guest", "Desk Access"]]

        # Prepare API Response
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
    else:
        frappe.response["error"] = {"code": 401, "message": "Invalid Email"}


def generate_missing_api_secrets_for_users():
    target_roles = ["Enumerator", "Vaccinator", "Enumeration Validator", "Vaccination Validator", "Dashboard Viewer"]
    
    # Get all users with the required role profiles
    users = frappe.get_all(
        "User",
        filters={"role_profile_name": ["in", target_roles], "enabled": 1},
        fields=["name", "api_key", "api_secret"]
    )
    # Iterate through each user and generate api_secret if it doesn't exist
    for user in users:
        email = user.name

        # Check if the user already has an api_secret
        if user.api_secret:
            continue  # Skip if api_secret already exists

        # Generate the api_secret using the existing frappe method
        result = frappe.call("frappe.core.doctype.user.user.generate_keys", user=email)
        api_secret = result.get("api_secret")

        # Now update Sec Keys with the api_secret
        if frappe.db.exists("Sec Keys", {"usr": email}):
            frappe.db.set_value("Sec Keys", {"usr": email}, "key", api_secret)
        else:
            frappe.get_doc({
                "doctype": "Sec Keys",
                "usr": email,
                "key": api_secret
            }).insert(ignore_permissions=True)

        frappe.db.commit()  # Commit per user to avoid partial updates





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
    'ward': wardName,
    'status': 'Approved'
  }

  filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
  settlements = fetch_db_resource(
    doc='Settlement', fields=fields, filters=filters)

  set_res(settlements=settlements)  # Return all records if no filters are applied


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
        'state': state,
        'selected_facility': 1
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
    
    # Fetch facilities with filters if provided, else fetch all records
    facilities = fetch_db_resource(
        doc='Facility', 
        fields=fields, 
        filters=filters if filters else None
    )

     # Limit the result to 20 records
    # facilities = facilities[:20]
    
    # Return the fetched records
    set_res(facilities=facilities)

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
def facility_list(ward=None, lga=None, state=None):
    fields = [
    'name', 'facility_name'
  ]
    
    # Create filters only if arguments are provided
    filters = {
        'ward': ward,
        'local_government_area': lga,
        'state': state,
        'selected_facility': 1
    }
    filters = {k: v for k, v in filters.items() if v}  # Remove keys with None values
    
    # Fetch facilities with filters if provided, else fetch all records
    facilities = fetch_db_resource(
        doc='Facility', 
        fields=fields, 
        filters=filters if filters else None
    )

     # Limit the result to 20 records
    # facilities = facilities[:20]
    
    # Return the fetched records
    set_res(facilities=facilities)


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
        'state': state,
        'status': 'Approved'
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
        'state': state,
        'status': 'Approved'
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
def get_vaccines():
    vaccines = fetch_db_resource(
        doc='Vaccine', fields=["name"], filters=None, 
        
    )
    vaccines = sorted(vaccines, key=lambda x: x['name'])
    set_res(vaccines=vaccines)
    
@frappe.whitelist()
def serious_aefi():
    serious_aefi = fetch_db_resource(
        doc='Serious AEFI', fields=["name"], filters=None, 
        
    )
    serious_aefi = sorted(serious_aefi, key=lambda x: x['name'])
    set_res(serious_aefi=serious_aefi)

@frappe.whitelist()
def non_serious_aefi():
    non_serious_aefi = fetch_db_resource(
        doc='Non Serious AEFI', fields=["name"], filters=None, 
        
    )
    non_serious_aefi = sorted(non_serious_aefi, key=lambda x: x['name'])
    set_res(non_serious_aefi=non_serious_aefi)

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


@frappe.whitelist()
def get_user_location(longitude, latitude):

    """
    Get the grid, Ward, LGA that contains the given longitude and latitude.
    """
    if not longitude or not latitude:
            return {"status": "error", "message": "Missing longitude or latitude."}

    try:

        # Construct GeoJSON Point
        point_geojson = json.dumps({
            "type": "Point",
            "coordinates": [float(longitude), float(latitude)]
        })

        # Query Grid that contains the point
        grid = frappe.db.sql("""
            SELECT name, title FROM `tabGrid`
            WHERE enabled = 1 AND ST_Intersects(
                ST_GeomFromGeoJSON(
                    CAST(
                        JSON_UNQUOTE(JSON_EXTRACT(geolocation_kyow, '$.features[0].geometry')) AS CHAR
                    )
                ),
                ST_GeomFromGeoJSON(%s)
            )
            LIMIT 1
        """, (point_geojson), as_dict=True)

    

       #Query Ward that contains the point
        ward = frappe.db.sql("""
        SELECT 
            name, 
            ward, 
            local_government_area, 
            state 
        FROM `tabWard`
        WHERE ST_Intersects(
            ST_GeomFromGeoJSON(
                JSON_UNQUOTE(
                    JSON_EXTRACT(geolocation, '$.geometry')
                )
            ),
            ST_GeomFromGeoJSON(%s)
        )
        LIMIT 1
        """, (point_geojson,), as_dict=True)

        lga = frappe.get_value(
            "Local Government Area", 
            ward[0]['local_government_area'] if ward else None, 
            ["name", "local_government_area", "state", "country"], 
            as_dict=True
        ) if ward else None

        return {
            "message": "Geo lookup successful",
            "status": 200,
            "grid": grid[0]['title'] if grid else None,
            "ward": ward[0]['ward'] if ward else None,
            "lga": lga['local_government_area'] if lga else None,
            "state": ward[0]['state'] if ward else None,
        }

    except Exception as e:
        return {"status": "error", "message": f"Geo lookup failed: {str(e)}"}





# def cr():
#   r = frappe.db.sql("select * from `tabFacility` where name = 'Anguwan Fatika Primary Health Center-Unguwar Fatika-Zaria-Kaduna'", as_dict=True)
#   print(r[0]['geolocation'])