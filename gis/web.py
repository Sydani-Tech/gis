import frappe
from frappe import _
import requests
import json
from datetime import datetime
from datetime import date

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource
)

# @frappe.whitelist()
# def states(stateName=None):
# # Get the logged-in user
#     user = frappe.session.user
#     if user == "Guest":
#         return {"message": "You must be logged in to access this data.", "status": "error"}

#     fields = ['name', 'state', 'country', 'geolocation']
#     filters = {}

#     if stateName:
#         filters['name'] = stateName

#     # Check User Permissions for the provided user
#     user_permissions = frappe.get_all(
#         'User Permission',
#         filters={'user': user, 'allow': 'State'},
#         fields=['for_value']
#     )

#     if user_permissions:
#         # Extract the list of allowed states from user permissions
#         allowed_states = [permission['for_value'] for permission in user_permissions]
#         filters['name'] = ['in', allowed_states]

#     # Fetch the states based on the filters
#     states = fetch_db_resource(doc='State', fields=fields, filters=filters)

#     # Sort the fetched states alphabetically by name
#     if states:
#         states = sorted(states, key=lambda x: x['name'])
#         set_res(states=states)
#     else:
#         set_res(message="No states found.")


CACHE_KEY = "cached_all_states"

@frappe.whitelist()
def states(stateName=None):
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    cache = frappe.cache()
    cached_data = cache.get_value(CACHE_KEY)
    print(f"Cached data for {CACHE_KEY}: {cached_data}")

    if cached_data:
        all_states = json.loads(cached_data)
    else:
        # Load ALL States with polygons into cache (expensive only once)
        fields = ['name', 'state', 'country', 'geolocation']
        all_states = fetch_db_resource(doc='State', fields=fields, filters={})

        # Cache the full dataset for 24 hours
        cache.set_value(CACHE_KEY, json.dumps(all_states), expires_in_sec=864000)

    # Now filter the cached states in memory (per user)
    states = all_states

    if stateName:
        states = [s for s in states if s['name'] == stateName]

    # Apply User Permission filter (after cache)
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'State'},
        fields=['for_value']
    )
    if user_permissions:
        allowed_states = {p['for_value'] for p in user_permissions}
        states = [s for s in states if s['name'] in allowed_states]

    # Sort alphabetically by name
    if states:
        states = sorted(states, key=lambda x: x['name'])
        set_res(states=states)
    else:
        set_res(message="No states found.")

@frappe.whitelist()
def lgas(stateName=None):

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    if not stateName:
        set_res(message="State name is required.")
        return

    # Define the fields to fetch
    fields = ['name', 'state', 'local_government_area', 'geolocation']

    # Fetch user permissions where allow = 'Local Government Area'
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Local Government Area'},
        fields=['for_value']
    )

    # If there are user permissions, filter by those values
    if user_permissions:
        permitted_lgas = [perm['for_value'] for perm in user_permissions]
        filters = {'state': stateName, 'name': ('in', permitted_lgas)}
    else:
        # If no user permissions, fetch all LGAs for the given state
        filters = {'state': stateName}

    # Fetch LGAs based on the filters
    lgas = fetch_db_resource(
        doc='Local Government Area', fields=fields, filters=filters
    )

    # Sort the LGAs alphabetically by name
    if lgas:
        lgas = sorted(lgas, key=lambda x: x['name'])
        set_res(lgas=lgas)
    else:
        set_res(message="No LGAs found.")

@frappe.whitelist()
def wards(lga, state=None):
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    # Define fields to fetch
    fields = ['name', 'ward', 'local_government_area', 'state', 'geolocation']

    # Fetch user permissions where allow = 'Ward'
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Ward'},
        fields=['for_value']
    )

    # Build the filters
    filters = {}
    if user_permissions:
        permitted_wards = [perm['for_value'] for perm in user_permissions]
        filters['name'] = ('in', permitted_wards)

    # Add additional filters if provided
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state

    # Fetch wards based on the filters
    wards = fetch_db_resource(
        doc='Ward',
        fields=fields,
        filters=filters
    )

    # Sort wards alphabetically by name
    if wards:
        wards = sorted(wards, key=lambda x: x['name'])
        # Limit to the first 20 results
        set_res(wards=wards)
    else:
        set_res(message="No wards found.")

@frappe.whitelist()
def settlements(ward, lga, state):
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    # Define fields to fetch
    fields = ['name', 'name_of_settlement', 'ward', 'local_government_area', 'state']

    # Fetch user permissions where allow = 'Settlement'
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Settlement'},
        fields=['for_value']
    )

    # Build the filters
    filters = {}
    if user_permissions:
        permitted_settlements = [perm['for_value'] for perm in user_permissions]
        filters['name'] = ('in', permitted_settlements)

    # Add additional filters if provided
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state

    # Fetch settlements based on the filters
    settlements = fetch_db_resource(
        doc='Settlement',
        fields=fields,
        filters=filters
    )

    # Sort settlements alphabetically by name
    if settlements:
        settlements = sorted(settlements, key=lambda x: x['name'])
        # Limit to the first 20 results
        # settlements = settlements[:20]
        set_res(settlements=settlements)
    else:
        set_res(message="No settlements found.")



@frappe.whitelist()
def grids(ward, lga, state):

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    # Define fields to fetch
    fields = ['name', 'title', 'geolocation_kyow']

    # Fetch user permissions where allow = 'Settlement'
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Settlement'},
        fields=['for_value']
    )

    # Build the filters
    filters = {}
    if user_permissions:
        permitted_settlements = [perm['for_value'] for perm in user_permissions]
        filters['name'] = ('in', permitted_settlements)

    # Add additional filters if provided
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    filters['enabled'] = 1

    # Fetch settlements based on the filters
    grids = fetch_db_resource(
        doc='Grid',
        fields=fields,
        filters=filters
    )

    # Sort settlements alphabetically by name
    # if grids:
    #     grids = sorted(grids, key=lambda x: x['title'])

    if grids:
    # Sort by the numeric part of the grid title
        import re
        grids = sorted(grids, key=lambda x: int(re.search(r'\d+', x['title']).group()) if re.search(r'\d+', x['title']) else float('inf'))

        set_res(grids=grids)
    else:
        set_res(message="No Grids found.")



@frappe.whitelist()
def overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
    """
    Fetch data for the dashboard: total children, fully vaccinated children, and vaccination percentage.
    Filters applied: user permissions, settlement, ward, lga, state.
    """

    if not project:
        return {
            "message": "Please provide a project to return the data for the dashboard.",
            "status": 400
        }

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to visualize the dashboard, please contact the project manager.",
            "status": 401
        }

    # Fetch User Permissions for different `allow` values
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )

    # Initialize filters
    filters = {}

    # Process user permissions based on `allow` values
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [
            perm for perm in user_permissions if perm['allow'] == allow_value
        ]
        if allowed_records:
            # Prefer the record where `is_default` is 1, else use all records
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    # Override with directly provided filters, if any
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"


    # Query Children Table for Total Children
    children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND {where_clause}
    """
    children_count = frappe.db.sql(children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Vaccination Table for Records with children IS NULL
    vaccination_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND {where_clause}
    """
    vaccination_count = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)[0]['count']

    total_children = children_count + vaccination_count

    # Fully Vaccinated (Measles 2) Count from Children Table
    fully_vaccinated_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND status = 'Approved' AND {where_clause}
    """
    fully_vaccinated_count = frappe.db.sql(fully_vaccinated_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Fully Vaccinated (Measles 2) Count from Vaccination Table
    vaccination_fully_vaccinated_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND children IS NULL AND status = 'Approved' AND {where_clause}
    """
    vaccination_fully_vaccinated_count = frappe.db.sql(vaccination_fully_vaccinated_query, tuple(sql_values), as_dict=True)[0]['count']

    total_fully_vaccinated = fully_vaccinated_count + vaccination_fully_vaccinated_count

    # Calculate Percentage
    percentage_fully_vaccinated = (total_fully_vaccinated / total_children) * 100 if total_children > 0 else 0

    # Query Children Table for Zero Dose Children
    zero_dose_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND {where_clause}
    """
    zero_dose_children_count = frappe.db.sql(zero_dose_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Children Table for Zero Dose Male Children
    zero_dose_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND gender = 'Male' AND {where_clause}
    """
    zero_dose_male_children_count = frappe.db.sql(zero_dose_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    
    # Query Children Table for Zero Dose Female Children
    zero_dose_female_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND gender = 'Female' AND {where_clause}
    """
    zero_dose_female_children_count = frappe.db.sql(zero_dose_female_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of households
    household_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    household_count = frappe.db.sql(household_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of male household heads
    male_household_head_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND gender_of_household_head = 'Male' AND {where_clause}
    """
    male_household_head_count = frappe.db.sql(male_household_head_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of female household heads
    female_household_head_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND gender_of_household_head = 'Female' AND {where_clause}
    """
    female_household_head_count = frappe.db.sql(female_household_head_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Building Table for number of buildings
    building_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND {where_clause}
    """
    building_count = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Building Table for number of residential buildings
    residential_building_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND building_type = 'Residential' AND {where_clause}
    """
    residential_building_count = frappe.db.sql(residential_building_query, tuple(sql_values), as_dict=True)[0]['count']
    residential_building_percentage = round((residential_building_count / building_count) * 100, 2) if building_count > 0 else 0




    # Query Household Table for distribution of households by gender
    household_gender_query = f"""
      SELECT gender_of_household_head, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY gender_of_household_head
    """
    household_gender_distribution = frappe.db.sql(household_gender_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_households = sum(item['count'] for item in household_gender_distribution)
    for item in household_gender_distribution:
      item['percentage'] = round((item['count'] / total_households) * 100, 2) if total_households > 0 else 0


    # Query Building Table for distribution of establishments by type
    establishment_type_query = f"""
      SELECT establishment_type, COUNT(*) AS count
      FROM `tabBuilding`
      WHERE status = 'Approved' AND establishment_type IS NOT NULL AND building_type = 'Non-Residential' AND {where_clause}
      GROUP BY establishment_type
    """
    non_residential_building_distribution = frappe.db.sql(establishment_type_query, tuple(sql_values), as_dict=True)
    # Calculate percentages
    non_residential_buildings = sum(item['count'] for item in non_residential_building_distribution)
    for item in non_residential_building_distribution:
      item['percentage'] = round((item['count'] / non_residential_buildings) * 100, 0) if non_residential_buildings > 0 else 0

    # Query to fetch population distribution
    house_query = f"""
        SELECT 
            how_many_household_members_are_above_18,
            how_many_household_members_are_between_15_and_18_years,
            how_many_household_members_are_between_9_and_14_years,
            how_many_household_members_are_between_5_and_8_years,
            how_many_household_members_are_below_5,
            creation
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    house_records = frappe.db.sql(house_query, tuple(sql_values), as_dict=True)

    # Current year
    current_year = datetime.now().year

    # Initialize totals for each category
    population_distribution = {
        "above_18": 0,
        "between_15_and_18": 0,
        "between_9_and_14": 0,
        "between_5_and_8": 0,
        "below_5": 0,
    }

    # Process each record
    for record in house_records:
        # Sum up the population for this record
        above_18 = record.get("how_many_household_members_are_above_18", 0)
        between_15_and_18 = record.get("how_many_household_members_are_between_15_and_18_years", 0)
        between_9_and_14 = record.get("how_many_household_members_are_between_9_and_14_years", 0)
        between_5_and_8 = record.get("how_many_household_members_are_between_5_and_8_years", 0)
        below_5 = record.get("how_many_household_members_are_below_5", 0)

        # Add to totals
        population_distribution["above_18"] += above_18
        population_distribution["between_15_and_18"] += between_15_and_18
        population_distribution["between_9_and_14"] += between_9_and_14
        population_distribution["between_5_and_8"] += between_5_and_8
        population_distribution["below_5"] += below_5

    # Calculate total population
    total_population = sum(population_distribution.values())

    # Calculate percentages for distribution
    for key in population_distribution:
        population_distribution[key] = {
            "count": population_distribution[key],
            "percentage": round((population_distribution[key] / total_population) * 100, 2) if total_population > 0 else 0
        }
    
    # Convert the population_distribution dictionary into the desired format
    formatted_population_distribution = [
        {
            "population_type": "Above 18",
            "count": population_distribution["above_18"]["count"],
            "percentage": population_distribution["above_18"]["percentage"]
        },
        {
            "population_type": "Between 15 and 18",
            "count": population_distribution["between_15_and_18"]["count"],
            "percentage": population_distribution["between_15_and_18"]["percentage"]
        },
        {
            "population_type": "Between 9 and 14",
            "count": population_distribution["between_9_and_14"]["count"],
            "percentage": population_distribution["between_9_and_14"]["percentage"]
        },
        {
            "population_type": "Between 5 and 8",
            "count": population_distribution["between_5_and_8"]["count"],
            "percentage": population_distribution["between_5_and_8"]["percentage"]
        },
        {
            "population_type": "Below 5",
            "count": population_distribution["below_5"]["count"],
            "percentage": population_distribution["below_5"]["percentage"]
        }
    ]

    # Step 1: Fetch vaccination status from Children table
    children_vaccination_query = f"""
        SELECT vaccination_status, COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status IS NOT NULL AND {where_clause}
        GROUP BY vaccination_status
    """
    children_vaccination_data = frappe.db.sql(children_vaccination_query, tuple(sql_values), as_dict=True)

    # Step 2: Fetch vaccination status from Vaccination table where children is Null
    vaccination_query = f"""
        SELECT vaccination_status, COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND vaccination_status IS NOT NULL AND {where_clause}
        GROUP BY vaccination_status
    """
    vaccination_data = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)

    # Step 3: Combine the data and group by vaccination_status
    vaccination_status_distribution = {}

    # Add data from Children table
    for record in children_vaccination_data:
        vaccination_status = record["vaccination_status"]
        count = record["count"]
        vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

    # Add data from Vaccination table
    for record in vaccination_data:
        vaccination_status = record["vaccination_status"]
        count = record["count"]
        vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

    # Step 4: Format the data for output
    total_records = sum(vaccination_status_distribution.values())
    formatted_vaccination_status_distribution = [
        {
            "vaccination_status": status,
            "count": count,
            "percentage": round((count / total_records) * 100, 2) if total_records > 0 else 0
        }
        for status, count in vaccination_status_distribution.items()
    ]

    
    # Query Settlement Table for number of settlements
    if 'settlement' not in filters:
        settlement_query = f"""
            SELECT COUNT(*) AS count
            FROM `tabSettlement`
            WHERE status = 'Approved' AND {where_clause}
        """
        settlement_count = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)[0]['count']

    
    if 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:
        settlement_query = """
            SELECT 
                COUNT(*) AS count
            FROM `tabSettlement`
            WHERE `status` = 'Approved' 
                AND `project` = %s
                AND `name` = %s
                AND `ward` = %s 
                AND `local_government_area` = %s 
                AND `state` = %s
        """

        # Add grid filter if provided
        if 'grid' in filters:
            settlement_query += " AND `grid` = %s"

        # Prepare the SQL values dynamically
        sql_values = [filters['project'], filters['settlement'], filters['ward'], filters['local_government_area'], filters['state']]
        if 'grid' in filters:
            sql_values.append(filters['grid'])

        settlement_count = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)[0]['count']

    return {
        "status": 200,
        "response": "Success",
        "data": {
        "total_children": total_children,
        "fully_vaccinated_children": total_fully_vaccinated,
        "percentage_fully_vaccinated": round(percentage_fully_vaccinated, 2),
        "zero_dose_children": zero_dose_children_count,
        "zero_dose_male_children": zero_dose_male_children_count, 
        "zero_dose_female_children": zero_dose_female_children_count,
        "household_count": household_count,
        "male_household_head_count": male_household_head_count,
        "female_household_head_count": female_household_head_count,
        "building_count": building_count,
        "residential_building_percentage": residential_building_percentage,
        "settlement_count": settlement_count,
        "household_gender_distribution": household_gender_distribution,
        "non_residential_building_distribution": non_residential_building_distribution,
        "non_residential_buildings": non_residential_buildings,
        "formatted_population_distribution": formatted_population_distribution,
        "total_population": total_population,
        "formatted_vaccination_status_distribution": formatted_vaccination_status_distribution
      }
    }


@frappe.whitelist()
def map_overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None, building_type=None, establishment_type=None, health_facility=None):
    """
    Fetch data for the map overview: Residential buildings and their geolocation.
    Filters applied: state, lga, ward, settlement, grid (all optional).
    """
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": 401
        }
    
    # Check if project has been passed
    if not project:
        return {
            "message": "Please provide a project to return the data for the map.",
            "status": 400
        }

    # Check if the user has the "Map Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to view the map, please contact the project manager.",
            "status": 401
        }

    # Initialize filters
    filters = {}

    # Handle special filter values
    if building_type == "Residential Only":
        building_type = "Residential"

    elif building_type == "Non Residential Only":
        building_type = "Non-residential"

    elif building_type == "Health Facilities Only":
        building_type = "Non-residential"
        establishment_type = "Health Facility"

    elif building_type == "Schools Only":
        building_type = "Non-residential"
        establishment_type = "School"

    elif building_type == "Churches Only":
        building_type = "Non-residential"
        establishment_type = "Church"

    elif building_type == "Mosques Only":
        building_type = "Non-residential"
        establishment_type = "Mosque"

    # If a specific health facility is selected
    if health_facility:
        building_type = "Non-residential"
        establishment_type = "Health Facility"
        filters['health_facility'] = health_facility


    # Add optional filters
    if project:
        filters['project'] = project
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if building_type:
        filters['building_type'] = building_type
    if establishment_type:
        filters['establishment_type'] = establishment_type

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    # # Query the Building table for residential buildings
    # building_query = f"""
    #     SELECT name, percentage_of_vaccinated_children, building_vaccination_status, geolocation, building_type, establishment_type, health_facility
    #     FROM `tabBuilding`
    #     WHERE status = 'Approved' AND {where_clause}
    # """
    # try:
    #     building_data = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)

    # Query the Building table for residential buildings, excluding health facilities with gray vaccination status
    building_query = f"""
        SELECT 
            name, 
            percentage_of_vaccinated_children, 
            building_vaccination_status, 
            geolocation, 
            building_type, 
            establishment_type, 
            health_facility
        FROM `tabBuilding`
        WHERE status = 'Approved'
        AND NOT (health_facility IS NOT NULL AND building_vaccination_status = 'gray')
        AND {where_clause}
    """
    try:
        building_data = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)

    except Exception as e:
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error"
        }

    return {
        "status": 200,
        "response": "Success",
        "data": building_data
    }

@frappe.whitelist()
def get_building_data(building):
    """
    Fetch data for a given building, including pictures, approved households, and approved children in those households.
    If the building is not residential, fetch vaccination records instead.

    Args:
        building (str): The name of the building.

    Returns:
        dict: Building data with associated households and children or vaccination records.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": "error"
        }

    # Check if the user has the "Dashboard Viewer" role
    if "Dashboard Viewer" not in frappe.get_roles(user):
        return {
            "message": "You do not have the required role to view the map, please contact the project manager.",
            "status": "error"
        }

    if not building:
        return {
            "message": "Building name is required.",
            "status": 400
        }
    
    # Fetch building details including type and pictures
    building_data = frappe.db.get_value(
        "Building",
        building,
        ["building_picture", "building_picture_2", "building_type", "establishment_type", "health_facility", "settlement", "ward", "local_government_area", "state"],
        as_dict=True
    )

    # Fetch the values of the fields ward, local government area, and state
    if building_data:
        building_data["health_facility"] = frappe.db.get_value("Facility", building_data["health_facility"], "facility_name")
        building_data["ward"] = frappe.db.get_value("Ward", building_data["ward"], "ward")
        building_data["local_government_area"] = frappe.db.get_value("Local Government Area", building_data["local_government_area"], "local_government_area")
        building_data["state"] = frappe.db.get_value("State", building_data["state"], "state")

    if not building_data:
        return {
            "message": f"No building found with name: {building}",
            "status": 404
        }

    # Determine building_vaccination_status  
    # Fetch Children vaccination statuses
    children_statuses = frappe.db.sql(
        """
        SELECT vaccination_status
        FROM `tabChildren`
        WHERE building = %s AND status = 'Approved'
        """,
        (building,),
        as_dict=True
    )

    # Fetch Vaccination records linked to this building
    vaccination_statuses = frappe.db.sql(
        """
        SELECT vaccination_status
        FROM `tabVaccination`
        WHERE building = %s AND status = 'Approved'
        """,
        (building,),
        as_dict=True
    )

    # Combine all statuses
    all_statuses = [c["vaccination_status"] for c in children_statuses] + \
                [v["vaccination_status"] for v in vaccination_statuses]


    # Default if no records exist
    building_vaccination_status = "gray"

    if all_statuses:
        # If any status is NOT Fully Vaccinated or Vaccinated to Age -> Red
        if any(s not in ("Fully Vaccinated (Measles 2)", "Vaccinated to Age") for s in all_statuses):
            building_vaccination_status = "red"
        # If all are Fully Vaccinated or Vaccinated to Age, and at least one is Vaccinated to Age -> Yellow
        elif all(s in ("Fully Vaccinated (Measles 2)", "Vaccinated to Age") for s in all_statuses) and any(s == "Vaccinated to Age" for s in all_statuses):
            building_vaccination_status = "yellow"
        # If all are Fully Vaccinated -> Green
        elif all(s == "Fully Vaccinated (Measles 2)" for s in all_statuses):
            building_vaccination_status = "green"
        else:
            building_vaccination_status = "gray"  # default if no statuses (shouldn't trigger here)



    # Attach to building data
    building_data["building_vaccination_status"] = building_vaccination_status
        
    
    # Fetch both children and vaccination records in a single query
    combined_records = frappe.db.sql(
        """
        SELECT 
            full_name, 
            date_of_birth, 
            gender, 
            enumerated_vaccination_status,
            vaccination_status, 
            vaccination_date,
            vaccines_administered,
            next_vaccination_date,
            household
        FROM (
            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                vaccines_taken AS vaccines_administered,
                vaccination_date, 
                next_vaccination_date,
                NULL AS enumerated_vaccination_status,
                household
            FROM `tabVaccination`
            WHERE building = %(building)s AND status = 'Approved' AND children IS NULL AND building IS NOT NULL
            
            UNION ALL

            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                vaccines_taken AS vaccines_administered,
                last_vaccination_date AS vaccination_date,
                next_vaccination_date,
                enumerated_vaccination_status,
                household
            FROM `tabChildren`
            WHERE building = %(building)s AND status = 'Approved'
        ) AS combined_data
        """,
        {"building": building},
        as_dict=True
    )

    # Calculate age and structure data
    today = date.today()
    formatted_data = [
        {
            "full_name": record["full_name"],
            "gender": record["gender"],
            "vaccination_status": record["vaccination_status"],
            "age": (
                f"{(today.year - record['date_of_birth'].year) - (1 if today.month < record['date_of_birth'].month or (today.month == record['date_of_birth'].month and today.day < record['date_of_birth'].day) else 0)} years, "
                f"{((today.month - record['date_of_birth'].month) % 12 if today.day >= record['date_of_birth'].day else (today.month - record['date_of_birth'].month - 1) % 12)} months"
                if record["date_of_birth"] else "Unknown"
            ),
            "date_of_birth": record["date_of_birth"],
            "household_head": frappe.db.get_value("Household", record["household"], "name_of_household_head"),
            "enumerated_vaccination_status": record["enumerated_vaccination_status"],
            "vaccination_date": record["vaccination_date"],
            "vaccines_administered": record["vaccines_administered"],
            "next_vaccination_date": record["next_vaccination_date"],
        }
        for record in combined_records
    ]

    household_data = frappe.db.sql(
        """
        SELECT 
            name_of_household_head, 
            gender_of_household_head, 
            date_of_birth_of_household_head, 
            phone_number,
            educational_level_of_household_head,
            how_many_people_live_in_the_household,
            average_monthly_income
        FROM `tabHousehold`
        WHERE status = 'Approved' AND building = %(building)s
        """,
        {"building": building},
        as_dict=True
    )

    formatted_household_data = [
        {
            "name_of_household_head": record["name_of_household_head"],
            "gender_of_household_head": record["gender_of_household_head"],
            "date_of_birth_of_household_head": record["date_of_birth_of_household_head"],
            "age_of_household_head": (
                f"{(today.year - record['date_of_birth_of_household_head'].year) - (1 if today.month < record['date_of_birth_of_household_head'].month or (today.month == record['date_of_birth_of_household_head'].month and today.day < record['date_of_birth_of_household_head'].day) else 0)} years, "
                f"{((today.month - record['date_of_birth_of_household_head'].month) % 12 if today.day >= record['date_of_birth_of_household_head'].day else (today.month - record['date_of_birth_of_household_head'].month - 1) % 12)} months"
                if record["date_of_birth_of_household_head"] else "Unknown"
            ),
            "phone_number": record["phone_number"],
            "educational_level_of_household_head": record["educational_level_of_household_head"],
            "how_many_people_live_in_the_household": record["how_many_people_live_in_the_household"],
            "average_monthly_income": record["average_monthly_income"],
        }
        for record in household_data
    ]

    return {
        "status": 200,
        "data": {
            "building": {
                "name": building,
                "building_picture": building_data.get("building_picture"),
                "building_picture_2": building_data.get("building_picture_2"),
                "building_type": building_data.get("building_type"),
                "building_vaccination_status": building_data.get("building_vaccination_status"),
                "establishment_type": building_data.get("establishment_type"),
                "health_facility": building_data["health_facility"],
                "settlement": building_data["settlement"],
                "ward": building_data["ward"],
                "local_government_area": building_data["local_government_area"],
                "state": building_data["state"],
                "children_and_vaccination_data": formatted_data,
                "household_data": formatted_household_data
            }
        }
    }

@frappe.whitelist()
def table_overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None, form=None):
    """
    Fetch data for the dashboard based on selected form: Settlement, Building, Household, Children, or Vaccination.
    """
    if not project:
        return {"message": "Please provide a project to return the data for the dashboard.", "status": 400}

    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {"message": "You do not have the required role to visualize the dashboard, please contact the project manager.", "status": 401}

    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )
    
    filters = {}
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [perm for perm in user_permissions if perm['allow'] == allow_value]
        if allowed_records:
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project

    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    form_table_mapping = {
        "Settlement": "tabSettlement",
        "Building": "tabBuilding",
        "Household": "tabHousehold",
        "Children": "tabChildren",
        "Vaccination": "tabVaccination"
    }
    
    field_selection = {
        "Settlement": ["name_of_settlement", "type_of_settlement", "archetype_for_rural", "archetype_for_urban", "name_of_settlementcommunity_head", "name_of_disease_surveillance_community_informant", "names_of_other_influential_members_within_settlement", "is_there_a_vdc", "how_often_does_the_vdc_meet", "ward", "local_government_area", "state"],
        "Building": ["building_address", "building_picture", "building_picture_2", "building_type", "establishment_type", "health_facility", "how_many_households_occupy_this_building", "settlement", "ward", "local_government_area", "state"],
        "Children": ["full_name", "date_of_birth", "vaccination_status", "gender", "last_vaccination_date", "vaccines_taken", "settlement", "ward", "local_government_area", "state"],
        "Vaccination": ["full_name", "vaccination_status", "date_of_birth", "vaccination_date", "vaccines_taken", "next_vaccination_date", "gender", "care_givers_name", "household", "children", "facility", "settlement", "ward", "local_government_area", "state"],
        "Household": ["name_of_household_head", "gender_of_household_head", "date_of_birth_of_household_head", "educational_level_of_household_head", "is_the_household_head_employed", "industry_of_employment", "average_monthly_income", "is_the_household_residing_in_a_rented_apartment", "how_many_people_live_in_the_household", "what_is_the_nearest_facility", "exact_distance_in_km", "settlement", "ward", "local_government_area", "state"]
    }
    
    if form not in form_table_mapping:
        return {"message": "Invalid form type provided.", "status": 400}
    
    table_name = form_table_mapping[form]
    selected_fields = field_selection.get(form, [])
    
    field_labels = {}
    for field in selected_fields:
        label = frappe.db.get_value("DocField", {"parent": form, "fieldname": field}, "label")
        field_labels[field] = label if label else field
    
    field_names = []
    for field in selected_fields:
        if "date_of_birth" in field:
            field_names.append(f"TIMESTAMPDIFF(MONTH, `{field}`, CURDATE()) AS Age")
            field_labels[field] = "Age"
        else:
            field_names.append(f"`{field}`")
    
    field_names_str = ", ".join(field_names)
    
    query = f"""
        SELECT {field_names_str} FROM `{table_name}`
        WHERE status = 'Approved' AND {where_clause}
    """
    records = frappe.db.sql(query, tuple(sql_values), as_dict=True)
    
    if not records:
        return {"message": "No records found for the selected criteria.", "status": 404}
    
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
            if months < 12:
                record["Age"] = f"{months} months"
            else:
                years = months // 12
                remaining_months = months % 12
                record["Age"] = f"{years} years {remaining_months} months"
    
    headers = [field_labels[field] for field in selected_fields]
    data = [list(record.values()) for record in records]

    # Count the total number of settlements
    settlement_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
    """
    settlement_count = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)[0]['count']

    # Count the total number of buildings
    building_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND {where_clause}
    """
    building_count = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)[0]['count']


    # Count the total number residential of buildings
    residential_building_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND building_type = 'Residential' AND {where_clause}
    """
    residential_building_count = frappe.db.sql(residential_building_query, tuple(sql_values), as_dict=True)[0]['count']

    #Calculate the percentage of residential buildings
    total_buildings = building_count
    if total_buildings > 0:
        residential_percentage = round((residential_building_count / total_buildings) * 100, 2)
    else:
        residential_percentage = 0

    # Count the total number of households
    household_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    household_count = frappe.db.sql(household_query, tuple(sql_values), as_dict=True)[0]['count']

    # Count the total number of children
    children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND {where_clause}
    """
    children_count = frappe.db.sql(children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Count the total number of male children
    male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    male_children_count = frappe.db.sql(male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Count the total number of male children
    female_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND gender = 'Female' AND {where_clause}
    """
    female_children_count = frappe.db.sql(female_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Count the total number of vaccinations
    vaccination_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND {where_clause}
    """
    vaccination_count = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)[0]['count']

    
    return {
        "headers": headers,
        "data": data,
        "total_settlements": settlement_count,
        "total_buildings": building_count,
        "residential_building_count": residential_building_count,
        "residential_building_percentage": residential_percentage,
        "total_households": household_count,
        "total_children": children_count,
        "total_male_children": male_children_count,
        "total_female_children": female_children_count,
        "total_vaccinations": vaccination_count,
        "status": 200,
        "response": "Success"
    }



@frappe.whitelist()
def settlement_dashboard(project=None, grid=None, name_of_settlement=None, ward=None, lga=None, state=None):
    """
    Fetch data for the settlement dashboard.
    Filters applied: user permissions, settlement, ward, lga, state.
    """
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )

    filters = {}
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [perm for perm in user_permissions if perm['allow'] == allow_value]
        if allowed_records:
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    if project:
        filters['project'] = project
    if grid:
        filters['grid'] = grid
    if name_of_settlement:
        filters['name_of_settlement'] = name_of_settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state

    sql_conditions = []
    sql_values = []
    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    settlement_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
    """
    settlement_count = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)[0]['count']

    if settlement_count == 0:
        # Return early with default values
        return {
            "status": 200,
            "response": "No data found",
            "data": {
                "settlement_count": 0,
                "avg_distance_from_facility": 0,
                "settlement_type_distribution": [],
                "settlement_archetype": {},
                "distance_groups": {
                    "less_than_2km": 0,
                    "between_2km_and_5km": 0,
                    "farther_than_5km": 0,
                },
                "vdc_distribution": [],
                "vdc_periodic_meeting": [],
                "vdc_periodic_meeting_count": 0
            }
        }

    avg_distance_query = f"""
        SELECT AVG(distance_from_settlement_to_facility) AS average_distance
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
    """
    avg_distance_result = frappe.db.sql(avg_distance_query, tuple(sql_values), as_dict=True)
    avg_distance_from_facility = round(avg_distance_result[0]["average_distance"] or 0, 1)

    distance_group_query = f"""
        SELECT 
            SUM(CASE WHEN distance_from_settlement_to_facility < 2 THEN 1 ELSE 0 END) AS less_than_2km,
            SUM(CASE WHEN distance_from_settlement_to_facility BETWEEN 2 AND 5 THEN 1 ELSE 0 END) AS between_2km_and_5km,
            SUM(CASE WHEN distance_from_settlement_to_facility > 5 THEN 1 ELSE 0 END) AS farther_than_5km
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
    """
    distance_group_result = frappe.db.sql(distance_group_query, tuple(sql_values), as_dict=True)[0]

    # Calculate total count
    total_count = (
        distance_group_result["less_than_2km"] +
        distance_group_result["between_2km_and_5km"] +
        distance_group_result["farther_than_5km"]
    )

    # Avoid division by zero
    if total_count > 0:
        less_than_2km_percentage = round((distance_group_result["less_than_2km"] / total_count) * 100, 2)
        between_2km_and_5km_percentage = round((distance_group_result["between_2km_and_5km"] / total_count) * 100, 2)
        farther_than_5km_percentage = round((distance_group_result["farther_than_5km"] / total_count) * 100, 2)
    else:
        less_than_2km_percentage = 0
        between_2km_and_5km_percentage = 0
        farther_than_5km_percentage = 0

    settlement_type_query = f"""
        SELECT type_of_settlement, COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
        GROUP BY type_of_settlement
    """
    settlement_type_distribution = frappe.db.sql(settlement_type_query, tuple(sql_values), as_dict=True)
    for item in settlement_type_distribution:
        item['percentage'] = round((item['count'] / settlement_count) * 100, 1)

    vdc_distribution_query = f"""
        SELECT is_there_a_vdc, COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
        GROUP BY is_there_a_vdc
    """
    vdc_distribution = frappe.db.sql(vdc_distribution_query, tuple(sql_values), as_dict=True)
    for item in vdc_distribution:
        item['percentage'] = round((item['count'] / settlement_count) * 100, 1)

    vdc_periodic_meeting_query = f"""
        SELECT how_often_does_the_vdc_meet, COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND is_there_a_vdc = 'Yes' AND {where_clause}
        GROUP BY how_often_does_the_vdc_meet
    """
    vdc_periodic_meeting = frappe.db.sql(vdc_periodic_meeting_query, tuple(sql_values), as_dict=True)

    # Calculate total count
    total_vdc_meetings = sum(item["count"] for item in vdc_periodic_meeting)

    # Calculate percentages and update each item in the result
    for item in vdc_periodic_meeting:
        if total_vdc_meetings > 0:
            item["percentage"] = round((item["count"] / total_vdc_meetings) * 100, 2)
        else:
            item["percentage"] = 0


    vdc_periodic_meeting_count_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND is_there_a_vdc = 'Yes' AND {where_clause}
    """
    vdc_periodic_meeting_count = frappe.db.sql(vdc_periodic_meeting_count_query, tuple(sql_values), as_dict=True)[0]['count']
    
    archetype_group_query = f"""
    SELECT archetype_for_rural, archetype_for_urban, COUNT(*) AS count
    FROM `tabSettlement`
    WHERE status = 'Approved' AND {where_clause}
    GROUP BY archetype_for_rural, archetype_for_urban
    """
    archetype_group_result = frappe.db.sql(archetype_group_query, tuple(sql_values), as_dict=True)

    archetype_groups = {}
    for record in archetype_group_result:
        archetype = record["archetype_for_rural"] or record["archetype_for_urban"]
        if archetype not in archetype_groups:
            archetype_groups[archetype] = 0
        archetype_groups[archetype] += record["count"]

    # Calculate both count and percentage for each archetype
    settlement_archetype = {
        k: {
            "count": v,
            "percentage": round((v / settlement_count) * 100, 2) if settlement_count > 0 else 0
        }
        for k, v in archetype_groups.items()
    }


    return {
        "status": 200,
        "response": "Success",
        "data": {
            "settlement_count": settlement_count,
            "avg_distance_from_facility": avg_distance_from_facility,
            "settlement_type_distribution": settlement_type_distribution,
            "settlement_archetype": settlement_archetype,
            "distance_groups": {
                "Less than 2KM": {
                    "count": distance_group_result["less_than_2km"],
                    "percentage": less_than_2km_percentage,
                    "label": "Less than 2KM"
                },
                "Between 2KM and 5KM": {
                    "count": distance_group_result["between_2km_and_5km"],
                    "percentage": between_2km_and_5km_percentage,
                    "label": "Between 2KM and 5KM"
                },
                "Farther than 5KM": {
                    "count": distance_group_result["farther_than_5km"],
                    "percentage": farther_than_5km_percentage,
                    "label": "Farther than 5KM"
                },
            },

            "vdc_distribution": vdc_distribution,
            "vdc_periodic_meeting": vdc_periodic_meeting,
            "vdc_periodic_meeting_count": vdc_periodic_meeting_count,
        }
    }

@frappe.whitelist()
def distribution_of_settlements(project=None, grid=None, settlement=None, ward=None, local_government_area=None, state=None):
    """
    Fetch hierarchical settlement data and counts based on filters.
    Includes user permission checks for State, Local Government Area, Ward, and Settlement.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    # Initialize filters based on user permissions
    filters = {}
    # filters = {"project": project}

    # Override filters with directly provided values
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if local_government_area:
        filters['local_government_area'] = local_government_area
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    if 'state' not in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching states and settlement counts
        state_query = """
            SELECT 
                st.name, st.state,
                COUNT(se.name) AS settlement_count 
            FROM `tabState` st
            LEFT JOIN `tabSettlement` se 
                ON se.state = st.name 
                AND se.status = 'Approved' 
                AND se.project = %s
        """
        
        # Initialize query parameters
        query_params = [filters['project']]
        
        # Add grid filter dynamically if provided
        if 'grid' in filters:
            state_query += " AND se.grid = %s"
            query_params.append(filters['grid'])

        # Finalize the query with GROUP BY clause
        state_query += " GROUP BY st.name"

        try:
            # Execute the query with the dynamically built parameters
            states = frappe.db.sql(state_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"states": states}, "message": "States and settlement counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching LGAs and settlement counts
        lga_query = """
            SELECT 
                lga.name AS lga_name, 
                lga.local_government_area, 
                lga.state,
                COUNT(se.name) AS settlement_count 
            FROM `tabLocal Government Area` lga
            LEFT JOIN `tabSettlement` se 
                ON se.local_government_area = lga.name 
                AND se.status = 'Approved' 
                AND se.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            lga_query += " AND se.grid = %s"

        # Add the WHERE clause for state
        lga_query += """
            WHERE lga.state = %s
            GROUP BY lga.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['state'])

            # Execute the query with parameters
            lgas = frappe.db.sql(lga_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and settlement counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' in filters and 'ward' not in filters:
        # Fetch wards and their settlement counts
        ward_query = """
            SELECT 
                ward.name AS ward_name, 
                ward.ward,
                ward.local_government_area, 
                ward.state,
                COUNT(se.name) AS settlement_count 
            FROM `tabWard` ward
            LEFT JOIN `tabSettlement` se 
                ON se.ward = ward.name 
                AND se.status = 'Approved' 
                AND se.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            ward_query += " AND se.grid = %s"

        # Add the WHERE clause for lga
        ward_query += """
            WHERE ward.local_government_area = %s
            GROUP BY ward.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['local_government_area'])

            # Execute the query with parameters
            wards = frappe.db.sql(ward_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"wards": wards}, "message": "Wards and settlement counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}



    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching LGAs and settlement counts
        lga_query = """
            SELECT 
                lga.name AS lga_name, 
                lga.local_government_area, 
                lga.state, 
                lga.geolocation,
                COUNT(se.name) AS settlement_count 
            FROM `tabLocal Government Area` lga
            LEFT JOIN `tabSettlement` se 
                ON se.local_government_area = lga.name 
                AND se.status = 'Approved' 
                AND se.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            lga_query += " AND se.grid = %s"

        # Add the WHERE clause for state
        lga_query += """
            WHERE lga.state = %s
            GROUP BY lga.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['state'])

            # Execute the query with parameters
            lgas = frappe.db.sql(lga_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and settlement counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}
    
    
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:
    # Ensure required filters are provided
        if not all(key in filters for key in ['project', 'ward', 'local_government_area', 'state']):
            return {"status": "error", "message": "Missing required filters: 'project', 'ward', 'local_government_area', or 'state'."}

        settlement_query = """
            SELECT 
                `name`
            FROM `tabSettlement`
            WHERE `status` = 'Approved' 
                AND `project` = %s
                AND `name` = %s
                AND `ward` = %s 
                AND `local_government_area` = %s 
                AND `state` = %s
        """

        # Add grid filter if provided
        if 'grid' in filters:
            settlement_query += " AND `grid` = %s"

        # Prepare the SQL values dynamically
        sql_values = [filters['project'], filters['settlement'], filters['ward'], filters['local_government_area'], filters['state']]
        if 'grid' in filters:
            sql_values.append(filters['grid'])

        # Execute the query
        try:
            settlements = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)

            if settlements:
            # Add settlement_count = 1 to each record
                for settlement in settlements:
                    settlement["settlement_count"] = 1
            else:
            # Return settlement_count = 0 if no records found
                settlements = [{"name": None, "settlement_count": 0}]

            # Return the result
            return {
                "status": 200,
                "data": {
                    "settlements": settlements
                },
                "message": "Settlements fetched successfully."
            }
        except Exception as e:
            return {
                "status": 400,
                "message": str(e)
            }
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' not in filters:
    # Ensure required filters are provided
        if not all(key in filters for key in ['project', 'ward', 'local_government_area', 'state']):
            return {"status": "error", "message": "Missing required filters: 'project', 'ward', 'local_government_area', or 'state'."}

        settlement_query = """
            SELECT 
                `name`
            FROM `tabSettlement`
            WHERE `status` = 'Approved' 
                AND `project` = %s
                AND `ward` = %s 
                AND `local_government_area` = %s 
                AND `state` = %s
        """

        # Add grid filter if provided
        if 'grid' in filters:
            settlement_query += " AND `grid` = %s"

        # Prepare the SQL values dynamically
        sql_values = [filters['project'], filters['ward'], filters['local_government_area'], filters['state']]
        if 'grid' in filters:
            sql_values.append(filters['grid'])

        # Execute the query
        try:
            settlements = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)

            # Add settlement_count = 1 to each record
            for settlement in settlements:
                settlement["settlement_count"] = 1

            # Return the result
            return {
                "status": 200,
                "data": {
                    "settlements": settlements
                },
                "message": "Settlements fetched successfully."
            }
        except Exception as e:
            return {
                "status": 400,
                "message": str(e)
            }
    return {"status": 400, "message": "Invalid filters or no data available."}


@frappe.whitelist()
def building_dashboard(project=None, grid=None, settlement=None, ward=None, lga=None, state=None, building_type=None, establishment_type=None, health_facility=None):
    """
    Fetch data for the building dashboard.
    Filters applied: user permissions, settlement, ward, lga, state.
    """
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )

    filters = {}
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [perm for perm in user_permissions if perm['allow'] == allow_value]
        if allowed_records:
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    # Handle special filter values
    if building_type == "Residential Only":
        building_type = "Residential"

    elif building_type == "Non Residential Only":
        building_type = "Non-residential"

    elif building_type == "Health Facilities Only":
        building_type = "Non-residential"
        establishment_type = "Health Facility"

    elif building_type == "Schools Only":
        building_type = "Non-residential"
        establishment_type = "School"

    elif building_type == "Churches Only":
        building_type = "Non-residential"
        establishment_type = "Church"

    elif building_type == "Mosques Only":
        building_type = "Non-residential"
        establishment_type = "Mosque"

    # If a specific health facility is selected
    if health_facility:
        building_type = "Non-residential"
        establishment_type = "Health Facility"
        filters['health_facility'] = health_facility

    if project:
        filters['project'] = project
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if building_type:
        filters['building_type'] = building_type
    if establishment_type:
        filters['establishment_type'] = establishment_type

    sql_conditions = []
    sql_values = []
    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    building_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND {where_clause}
    """
    building_count = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)[0]['count']

    if building_count == 0:
        # Return early with default values
        return {
            "status": 200,
            "response": "No data found",
            "data": {
                "building_count": 0,
                "household_count": 0,
                "residential_building_count": 0,
                "building_type": [],
                "building_establishment": [],
                "total_establishment": [],
            }
        }

    residential_building_count_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND building_type = 'Residential' AND {where_clause}
    """
    residential_building_count = frappe.db.sql(residential_building_count_query, tuple(sql_values), as_dict=True)[0]['count']

    # household_query = f"""
    #     SELECT COUNT(*) AS count
    #     FROM `tabHousehold`
    #     WHERE status = 'Approved' AND {where_clause}
    # """
    # household_count = frappe.db.sql(household_query, tuple(sql_values), as_dict=True)[0]['count']

    # Household filters (build only fields relevant to tabHousehold)
    household_filters = {}

    if project:
        household_filters['project'] = project
    if grid:
        household_filters['grid'] = grid
    if settlement:
        household_filters['settlement'] = settlement
    if ward:
        household_filters['ward'] = ward
    if lga:
        household_filters['local_government_area'] = lga
    if state:
        household_filters['state'] = state

    # Construct WHERE clause for Household
    household_conditions = []
    household_values = []

    for key, value in household_filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            household_conditions.append(f"`{key}` IN %s")
            household_values.append(tuple(value[1]))
        else:
            household_conditions.append(f"`{key}` = %s")
            household_values.append(value)

    household_where_clause = " AND ".join(household_conditions) if household_conditions else "1=1"

    # Final Household query
    household_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {household_where_clause}
    """
    household_count = frappe.db.sql(household_query, tuple(household_values), as_dict=True)[0]['count']


    building_type_query = f"""
        SELECT building_type, COUNT(*) AS count
        FROM `tabBuilding`        
        WHERE status = 'Approved' AND {where_clause}
        GROUP BY building_type
    """
    building_type = frappe.db.sql(building_type_query, tuple(sql_values), as_dict=True)

    # Calculate total count
    total_buildings = sum(item["count"] for item in building_type)

    # Calculate percentages and update each item in the result
    for item in building_type:
        item["percentage"] = round((item["count"] / total_buildings) * 100, 2)

    
    building_establishment_query = f"""
        SELECT establishment_type, COUNT(*) AS count
        FROM `tabBuilding`
        WHERE status = 'Approved' AND building_type = 'Non-residential' AND {where_clause}
        GROUP BY establishment_type
    """
    building_establishment = frappe.db.sql(building_establishment_query, tuple(sql_values), as_dict=True)

    # Calculate total count
    total_establishment = sum(item["count"] for item in building_establishment)

    # Calculate percentages and update each item in the result
    for item in building_establishment:
        item["percentage"] = round((item["count"] / total_establishment) * 100, 2)


    
    return {
        "status": 200,
        "response": "Success",
        "data": {
            "building_count": building_count,
            "residential_building_count": residential_building_count,
            "household_count": household_count,
            "building_type": building_type,
            "building_establishment": building_establishment,
            "total_establishment": total_establishment,
            },
        }




@frappe.whitelist()
def distribution_of_building(project=None, grid=None, settlement=None, ward=None, local_government_area=None, state=None, building_type=None, establishment_type=None):
    """
    Fetch hierarchical building data and counts based on filters.
    Includes user permission checks for State, Local Government Area, Ward, and Grid.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    # Initialize filters based on user permissions
    filters = {}
    
    # Handle special filter values
    if building_type == "Residential Only":
        building_type = "Residential"

    elif building_type == "Non Residential Only":
        building_type = "Non-residential"

    elif building_type == "Health Facilities Only":
        building_type = "Non-residential"
        establishment_type = "Health Facility"

    elif building_type == "Schools Only":
        building_type = "Non-residential"
        establishment_type = "School"

    elif building_type == "Churches Only":
        building_type = "Non-residential"
        establishment_type = "Church"

    elif building_type == "Mosques Only":
        building_type = "Non-residential"
        establishment_type = "Mosque"

    # Override filters with directly provided values
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if local_government_area:
        filters['local_government_area'] = local_government_area
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project
    if building_type:
        filters['building_type'] = building_type
    if establishment_type:
        filters['establishment_type'] = establishment_type
   

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    if 'state' not in filters and 'local_government_area' not in filters and 'ward' not in filters and 'settlement' not in filters:
        # Base query for fetching states and settlement counts
        state_query = """
            SELECT 
                st.name, st.state, 
                COUNT(building.name) AS building_count 
            FROM `tabState` st
            LEFT JOIN `tabBuilding` building
                ON building.state = st.name 
                AND building.status = 'Approved' 
                AND building.project = %s
        """
        
        # Initialize query parameters
        query_params = [filters['project']]
        
        # Add grid filter dynamically if provided
        if 'grid' in filters:
            state_query += " AND building.grid = %s"
            query_params.append(filters['grid'])

         # Add additional filters if provided
        if 'building_type' in filters:
            state_query += " AND building.building_type = %s"
            query_params.append(filters['building_type'])

        if 'establishment_type' in filters:
            state_query += " AND building.establishment_type = %s"
            query_params.append(filters['establishment_type'])

        # Finalize the query with GROUP BY clause
        state_query += " GROUP BY st.name" 

        try:
            # Execute the query with the dynamically built parameters
            states = frappe.db.sql(state_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"states": states}, "message": "States and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:

        query_params = [filters['project']]

        # Base query for fetching LGAs and settlement counts
        lga_query = """
            SELECT 
                lga.name AS lga_name, 
                lga.local_government_area, 
                lga.state,
                lga.local_government_area,
                COUNT(building.name) AS building_count 
            FROM `tabLocal Government Area` lga
            LEFT JOIN `tabBuilding` building
                ON building.local_government_area = lga.name 
                AND building.status = 'Approved' 
                AND building.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            lga_query += " AND building.grid = %s"

         # Add additional filters if provided
        if 'building_type' in filters:
            lga_query += " AND building.building_type = %s"
            query_params.append(filters['building_type'])

        if 'establishment_type' in filters:
            lga_query += " AND building.establishment_type = %s"
            query_params.append(filters['establishment_type'])

        # Add the WHERE clause for state
        lga_query += """
            WHERE lga.state = %s
            GROUP BY lga.name
        """
        
        try:
            # # Build parameters dynamically based on grid filter
            # query_params = [filters['project']]
            # if 'grid' in filters:
            #     query_params.append(filters['grid'])
            # query_params.append(filters['state'])

            query_params.append(filters['state'])


            # Execute the query with parameters
            lgas = frappe.db.sql(lga_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' in filters and 'ward' not in filters:

        query_params = [filters['project']]

        # Fetch wards and their settlement counts
        ward_query = """
            SELECT 
                ward.name AS ward_name, 
                ward.ward,
                ward.local_government_area, 
                ward.state,
                COUNT(building.name) AS building_count 
            FROM `tabWard` ward
            LEFT JOIN `tabBuilding` building
                ON building.ward = ward.name 
                AND building.status = 'Approved' 
                AND building.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            ward_query += " AND building.grid = %s"

                 # Add additional filters if provided
        if 'building_type' in filters:
            ward_query += " AND building.building_type = %s"
            query_params.append(filters['building_type'])

        if 'establishment_type' in filters:
            ward_query += " AND building.establishment_type = %s"
            query_params.append(filters['establishment_type'])

        # Add the WHERE clause for lga
        ward_query += """
            WHERE ward.local_government_area = %s
            GROUP BY ward.name
        """
        
        try:
            # # Build parameters dynamically based on grid filter
            # query_params = [filters['project']]
            # if 'grid' in filters:
            #     query_params.append(filters['grid'])
            # query_params.append(filters['local_government_area'])

            query_params.append(filters['local_government_area'])

            # Execute the query with parameters
            wards = frappe.db.sql(ward_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"wards": wards}, "message": "Wards and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}
        

    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' not in filters:

        query_params = [filters['project']]

        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(building.name) AS building_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabBuilding` building
                ON building.settlement = settlement.name 
                AND building.status = 'Approved' 
                AND building.project = %s
        """

        if 'grid' in filters:
            settlement_query += " AND building.grid = %s"
            query_params.append(filters['grid'])

        if 'building_type' in filters:
            settlement_query += " AND building.building_type = %s"
            query_params.append(filters['building_type'])

        if 'establishment_type' in filters:
            settlement_query += " AND building.establishment_type = %s"
            query_params.append(filters['establishment_type'])

        # Final WHERE clause (%s)
        settlement_query += """
            WHERE building.settlement = %s
            GROUP BY settlement.name
        """
        query_params.append(filters['settlement'])   # for the final WHERE clause

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE building.settlement = %s
            GROUP BY settlement.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params.append(filters['ward'])  

            # Execute the query with parameters
            settlements = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"settlements": settlements}, "message": "Settlements and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:

        query_params = [
            filters['project'],
            filters['settlement'] 
        ]

        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(building.name) AS building_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabBuilding` building
                ON building.settlement = settlement.name 
                AND building.status = 'Approved' 
                AND building.project = %s
                AND building.settlement = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND building.grid = %s"

        # Add additional filters if provided
        if 'building_type' in filters:
            settlement_query += " AND building.building_type = %s"
            query_params.append(filters['building_type'])

        if 'establishment_type' in filters:
            settlement_query += " AND building.establishment_type = %s"
            query_params.append(filters['establishment_type'])

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE building.settlement = %s
            GROUP BY settlement.name
        """
        
        try:
            query_params.append(filters['settlement']) 

            # Execute the query with parameters
            settlements = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            if not settlements:
                settlements = [{"name": None, "building_count": 0}]
            
            return {"status": 200, "data": {"settlements": settlements}, "message": "Settlement and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    return {"status": 400, "message": "Invalid filters or no data available."}


@frappe.whitelist()
def children_dashboard(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
    """
    Fetch data for the dashboard: total children, fully vaccinated children, and vaccination percentage.
    Filters applied: user permissions, settlement, ward, lga, state.
    """

    if not project:
        return {
            "message": "Please provide a project to return the data for the dashboard.",
            "status": 400
        }

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to visualize the dashboard, please contact the project manager.",
            "status": 401
        }

    # Fetch User Permissions for different `allow` values
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )

    # Initialize filters
    filters = {}

    # Process user permissions based on `allow` values
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [
            perm for perm in user_permissions if perm['allow'] == allow_value
        ]
        if allowed_records:
            # Prefer the record where `is_default` is 1, else use all records
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    # Override with directly provided filters, if any
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"


    # Query Children Table for Total Children
    children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND {where_clause}
    """
    children_count = frappe.db.sql(children_query, tuple(sql_values), as_dict=True)[0]['count']

    #Query Vaccination Table for Records with children IS NULL
    vaccination_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND {where_clause}
    """
    vaccination_count = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Children Table for Male Children
    male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    male_children_count = frappe.db.sql(male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Children Table for Female Children
    female_children_count = children_count - male_children_count

    # Query Vaccination Table for Records with male children IS NULL
    vaccination_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND gender = 'Male' AND {where_clause}
    """
    vaccination_male_children_count = frappe.db.sql(vaccination_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Children Table for Female Children
    vaccination_female_children_count = vaccination_count - vaccination_male_children_count


    total_male_count = male_children_count + vaccination_male_children_count
    total_female_count = female_children_count + vaccination_female_children_count


    total_children = children_count + vaccination_count
    percentage_male_children = round((total_male_count / total_children) * 100,2) if total_children > 0 else 0
    percentage_female_children = round((total_female_count / total_children) * 100,2) if total_children > 0 else 0

    # Fully Vaccinated (Measles 2) Count from Children Table
    fully_vaccinated_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND status = 'Approved' AND {where_clause}
    """
    fully_vaccinated_count = frappe.db.sql(fully_vaccinated_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Fully Vaccinated (Measles 2) Count from Vaccination Table
    vaccination_fully_vaccinated_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND children IS NULL AND status = 'Approved' AND {where_clause}
    """
    vaccination_fully_vaccinated_count = frappe.db.sql(vaccination_fully_vaccinated_query, tuple(sql_values), as_dict=True)[0]['count']

    total_fully_vaccinated = fully_vaccinated_count + vaccination_fully_vaccinated_count

    # Calculate Percentage
    percentage_fully_vaccinated = (total_fully_vaccinated / total_children) * 100 if total_children > 0 else 0


    # Fully Vaccinated (Measles 2) Male Children Count from Children Table
    fully_vaccinated_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    fully_vaccinated_male_children_count = frappe.db.sql(fully_vaccinated_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Fully Vaccinated (Measles 2) Male Children Count from Vaccination Table
    vaccination_fully_vaccinated_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND children IS NULL AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    vaccination_fully_vaccinated_male_children_count = frappe.db.sql(vaccination_fully_vaccinated_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_fully_vaccinated_male_children = fully_vaccinated_male_children_count + vaccination_fully_vaccinated_male_children_count

    # Fully Vaccinated (Measles 2) Female Children Count from Children Table
    total_fully_vaccinated_female_children = total_fully_vaccinated - total_fully_vaccinated_male_children


    # Vaccinated to Age Count from Children Table
    vaccinated_to_age_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Vaccinated to Age' AND status = 'Approved' AND {where_clause}
    """
    vaccinated_to_age_count = frappe.db.sql(vaccinated_to_age_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Vaccinated to Age Count from Vaccination Table
    vaccination_vaccinated_to_age_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Vaccinated to Age' AND children IS NULL AND status = 'Approved' AND {where_clause}
    """
    vaccination_fully_vaccinated_to_age_count = frappe.db.sql(vaccination_vaccinated_to_age_query, tuple(sql_values), as_dict=True)[0]['count']

    total_vaccinated_to_age = vaccinated_to_age_count + vaccination_fully_vaccinated_to_age_count

    # Calculate Percentage
    percentage_vaccinated_to_age = (total_vaccinated_to_age / total_children) * 100 if total_children > 0 else 0


    # Vaccinated to Age Male Children Count from Children Table
    vaccinated_to_age_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Vaccinated to Age' AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    vaccinated_to_age_male_children_count = frappe.db.sql(vaccinated_to_age_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Vaccinated to Age Male Children Count from Vaccination Table
    vaccination_vaccinated_to_age_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Vaccinated to Age' AND children IS NULL AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    vaccination_vaccinated_to_age_male_children_count = frappe.db.sql(vaccination_vaccinated_to_age_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_vaccinated_to_age_male_children = vaccinated_to_age_male_children_count + vaccination_vaccinated_to_age_male_children_count

    # Vaccinated to Age Female Children Count from Children Table
    total_vaccinated_to_age_female_children = total_vaccinated_to_age - total_vaccinated_to_age_male_children

    # Under Immunized Count from Children Table
    under_immunized_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Under Immunized' AND status = 'Approved' AND {where_clause}
    """
    under_immunized_count = frappe.db.sql(under_immunized_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Under Immunized Count from Vaccination Table
    vaccination_under_immunized_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Under Immunized' AND children IS NULL AND status = 'Approved' AND {where_clause}
    """
    vaccination_under_immunized_count = frappe.db.sql(vaccination_under_immunized_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_under_immunized = under_immunized_count + vaccination_under_immunized_count

    # Calculate Percentage
    percentage_under_immunized = (total_under_immunized / total_children) * 100 if total_children > 0 else 0


    # Under Immunized Male Children Count from Children Table
    under_immunized_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE vaccination_status = 'Under Immunized' AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    under_immunized_male_children_count = frappe.db.sql(under_immunized_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Under Immunized Male Children Count from Vaccination Table
    vaccination_under_immunized_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Under Immunized' AND children IS NULL AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    vaccination_under_immunized_male_children_count = frappe.db.sql(vaccination_under_immunized_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_under_immunized_male_children = under_immunized_male_children_count + vaccination_under_immunized_male_children_count

    # Under Immunized Female Children Count from Children Table
    total_under_immunized_female_children = total_under_immunized - total_under_immunized_male_children

    # Query Children Table for Zero Dose Children
    zero_dose_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND {where_clause}
    """
    zero_dose_children_count = frappe.db.sql(zero_dose_children_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Vaccination Table for Zero Dose Children
    vaccination_zero_dose_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Zero Dose' AND children IS NULL AND status = 'Approved' AND {where_clause}
    """
    vaccination_zero_dose_children_count = frappe.db.sql(vaccination_zero_dose_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_zero_dose = zero_dose_children_count + vaccination_zero_dose_children_count

    # Query Children Table for Zero Dose Male Children
    zero_dose_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND gender = 'Male' AND {where_clause}
    """
    zero_dose_male_children_count = frappe.db.sql(zero_dose_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    #Query Vaccination Table for Zero Dose Male Children
    vaccination_zero_dose_male_children_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabVaccination`
        WHERE vaccination_status = 'Zero Dose' AND children IS NULL AND status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    vaccination_zero_dose_male_children_count = frappe.db.sql(vaccination_zero_dose_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    total_zero_dose_male_children = zero_dose_male_children_count + vaccination_zero_dose_male_children_count

    # Calculate Zero Dose Female Children
    total_zero_dose_female_children = total_zero_dose - total_zero_dose_male_children

     # Calculate Percentage
    percentage_zero_dose = (total_zero_dose / total_children) * 100 if total_children > 0 else 0






    # Step 1: Fetch vaccination status from Children table
    children_vaccination_query = f"""
        SELECT vaccination_status, COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND vaccination_status IS NOT NULL AND {where_clause}
        GROUP BY vaccination_status
    """
    children_vaccination_data = frappe.db.sql(children_vaccination_query, tuple(sql_values), as_dict=True)

    # Step 2: Fetch vaccination status from Vaccination table where children is Null
    vaccination_query = f"""
        SELECT vaccination_status, COUNT(*) AS count
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND vaccination_status IS NOT NULL AND {where_clause}
        GROUP BY vaccination_status
    """
    vaccination_data = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)

    # Step 3: Combine the data and group by vaccination_status
    vaccination_status_distribution = {}

    # Add data from Children table
    for record in children_vaccination_data:
        vaccination_status = record["vaccination_status"]
        count = record["count"]
        vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

    # Add data from Vaccination table
    for record in vaccination_data:
        vaccination_status = record["vaccination_status"]
        count = record["count"]
        vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

    # Step 4: Format the data for output
    total_records = sum(vaccination_status_distribution.values())
    formatted_vaccination_status_distribution = [
        {
            "vaccination_status": status,
            "count": count,
            "percentage": round((count / total_records) * 100, 2) if total_records > 0 else 0
        }
        for status, count in vaccination_status_distribution.items()
    ]

    
    # Fetch records from Children table with age calculation
    children_age_query = f"""
        SELECT 
            name, 
            date_of_birth,
            TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age
        FROM `tabChildren`
        WHERE status = 'Approved' AND {where_clause}
    """
    children_age_records = frappe.db.sql(children_age_query, tuple(sql_values), as_dict=True)

    # Fetch records from Vaccination table with age calculation
    vaccination_age_query = f"""
        SELECT 
            name, 
            date_of_birth,
            TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age
        FROM `tabVaccination`
        WHERE status = 'Approved' AND children IS NULL AND {where_clause}
    """
    vaccination_age_records = frappe.db.sql(vaccination_age_query, tuple(sql_values), as_dict=True)

    # Combine results
    combined_data = children_age_records + vaccination_age_records
    # Duplicate sql_values for the second WHERE clause in the UNION
    duplicated_sql_values = sql_values * 2

    # Adjust the age distribution query
    age_distribution_query = f"""
        SELECT 
            SUM(CASE WHEN DATEDIFF(CURDATE(), date_of_birth) / 365 < 2 THEN 1 ELSE 0 END) AS below_2_years,
            SUM(CASE WHEN DATEDIFF(CURDATE(), date_of_birth) / 365 BETWEEN 2 AND 5 THEN 1 ELSE 0 END) AS between_2_and_5_years,
            SUM(CASE WHEN DATEDIFF(CURDATE(), date_of_birth) / 365 > 5 THEN 1 ELSE 0 END) AS above_5_years
        FROM (
            SELECT name, date_of_birth 
            FROM `tabChildren` 
            WHERE status = 'Approved' AND {where_clause}
            
            UNION ALL
            
            SELECT name, date_of_birth 
            FROM `tabVaccination` 
            WHERE status = 'Approved' AND children IS NULL AND {where_clause}
        ) AS combined_data
    """

    # Execute the query with duplicated_sql_values
    age_distribution = frappe.db.sql(age_distribution_query, tuple(duplicated_sql_values), as_dict=True)[0]

    # Extract counts and calculate percentages
    below_2 = age_distribution["below_2_years"] or 0
    between_2_and_5 = age_distribution["between_2_and_5_years"] or 0
    above_5 = age_distribution["above_5_years"] or 0
    total_count = below_2 + between_2_and_5 + above_5

    # Avoid division by zero
    if total_count > 0:
        below_2_percentage = round((below_2 / total_count) * 100, 2)
        between_2_and_5_percentage = round((between_2_and_5 / total_count) * 100, 2)
        above_5_percentage = round((above_5 / total_count) * 100, 2)
    else:
        below_2_percentage = 0
        between_2_and_5_percentage = 0
        above_5_percentage = 0

    return {
        "status": 200,
        "response": "Success",
        "data": {
        "total_children": total_children,
        "total_male_count": total_male_count,
        "total_female_count": total_female_count,
        "fully_vaccinated_children": total_fully_vaccinated,
        "total_fully_vaccinated_male_children": total_fully_vaccinated_male_children,
        "total_fully_vaccinated_female_children": total_fully_vaccinated_female_children,
        "percentage_fully_vaccinated": round(percentage_fully_vaccinated, 2),
        "vaccinated_to_age_children": total_vaccinated_to_age,
        "percentage_vaccinated_to_age": round(percentage_vaccinated_to_age, 2),
        "total_vaccinated_to_age_male_children": total_vaccinated_to_age_male_children,
        "total_vaccinated_to_age_female_children": total_vaccinated_to_age_female_children,
        "total_under_immunized": total_under_immunized,
        "percentage_under_immunized": round(percentage_under_immunized, 2),
        "total_under_immunized_male_children": total_under_immunized_male_children,
        "total_under_immunized_female_children": total_under_immunized_female_children,
        "total_zero_dose": total_zero_dose,
        "percentage_zero_dose": round(percentage_zero_dose, 2),
        "total_zero_dose_male_children": total_zero_dose_male_children, 
        "total_zero_dose_female_children": total_zero_dose_female_children,
        "formatted_vaccination_status_distribution": formatted_vaccination_status_distribution,
        "gender_distribution_of_children": {
            "male": {"gender": "Male", "total": total_male_count, "percentage": percentage_male_children},
            "female": {"gender": "Female", "total": total_female_count, "percentage": percentage_female_children},
        },
        "age_distribution": {
            "Below 2 Years": {
                "count": below_2,
                "percentage": below_2_percentage
            },
            "Between 2 and 5 Years": {
                "count": between_2_and_5,
                "percentage": between_2_and_5_percentage
            },
            "Above 5 Years": {
                "count": above_5,
                "percentage": above_5_percentage
            },
        },

      }
    }


@frappe.whitelist()
def distribution_of_children(project=None, grid=None, settlement=None, ward=None, local_government_area=None, state=None):
    """
    Fetch hierarchical children data and counts based on filters.
    Includes user permission checks for State, Local Government Area, Ward, and Grid.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    # Initialize filters based on user permissions
    filters = {}
    # filters = {"project": project}

    # Override filters with directly provided values
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if local_government_area:
        filters['local_government_area'] = local_government_area
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project
   

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    if 'state' not in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching states and settlement counts
        state_query = """
            SELECT 
                st.name, st.state, 
                COUNT(children.name) AS children_count 
            FROM `tabState` st
            LEFT JOIN `tabChildren` children
                ON children.state = st.name 
                AND children.status = 'Approved' 
                AND children.project = %s
        """
        
        # Initialize query parameters
        query_params = [filters['project']]
        
        # Add grid filter dynamically if provided
        if 'grid' in filters:
            state_query += " AND children.grid = %s"
            query_params.append(filters['grid'])

        # Finalize the query with GROUP BY clause
        state_query += " GROUP BY st.name"

        try:
            # Execute the query with the dynamically built parameters
            states = frappe.db.sql(state_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"states": states}, "message": "States and children counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching LGAs and settlement counts
        lga_query = """
            SELECT 
                lga.name AS lga_name, 
                lga.local_government_area, 
                lga.state,
                COUNT(children.name) AS children_count 
            FROM `tabLocal Government Area` lga
            LEFT JOIN `tabChildren` children
                ON children.local_government_area = lga.name 
                AND children.status = 'Approved' 
                AND children.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            lga_query += " AND children.grid = %s"

        # Add the WHERE clause for state
        lga_query += """
            WHERE lga.state = %s
            GROUP BY lga.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['state'])

            # Execute the query with parameters
            lgas = frappe.db.sql(lga_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and children counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' in filters and 'ward' not in filters:
        # Fetch wards and their settlement counts
        ward_query = """
            SELECT 
                ward.name AS ward_name, 
                ward.ward,
                ward.local_government_area, 
                ward.state,
                COUNT(children.name) AS children_count 
            FROM `tabWard` ward
            LEFT JOIN `tabChildren` children
                ON children.ward = ward.name 
                AND children.status = 'Approved' 
                AND children.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            ward_query += " AND children.grid = %s"

        # Add the WHERE clause for lga
        ward_query += """
            WHERE ward.local_government_area = %s
            GROUP BY ward.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['local_government_area'])

            # Execute the query with parameters
            wards = frappe.db.sql(ward_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"wards": wards}, "message": "Wards and children counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}
        

    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' not in filters:
        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(children.name) AS children_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabChildren` children
                ON children.settlement = settlement.name 
                AND children.status = 'Approved' 
                AND children.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND children.grid = %s"

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE settlement.ward = %s
            GROUP BY settlement.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['ward'])  # Correctly use 'ward' instead of 'state'

            # Execute the query with parameters
            settlement = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"settlements": settlement}, "message": "Settlements and children counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:
        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(children.name) AS children_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabChildren` children
                ON children.settlement = settlement.name 
                AND children.status = 'Approved' 
                AND children.project = %s
                AND children.settlement = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND children.grid = %s"

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE children.settlement = %s
            GROUP BY settlement.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project'], filters['settlement']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['settlement']) 

            # Execute the query with parameters
            settlements = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            if not settlements:
                settlements = [{"name": None, "children_count": 0}]
            
            return {"status": 200, "data": {"settlement": settlements}, "message": "Settlement and children counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    return {"status": 400, "message": "Invalid filters or no data available."}


@frappe.whitelist()
def household_dashboard(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
    """
    Fetch data for the dashboard: total children, fully vaccinated children, and vaccination percentage.
    Filters applied: user permissions, settlement, ward, lga, state.
    """

    if not project:
        return {
            "message": "Please provide a project to return the data for the dashboard.",
            "status": 400
        }

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to visualize the dashboard, please contact the project manager.",
            "status": 401
        }

    # Fetch User Permissions for different `allow` values
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user},
        fields=['allow', 'for_value', 'is_default']
    )

    # Initialize filters
    filters = {}

    # Process user permissions based on `allow` values
    for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
        allowed_records = [
            perm for perm in user_permissions if perm['allow'] == allow_value
        ]
        if allowed_records:
            # Prefer the record where `is_default` is 1, else use all records
            default_record = next((perm for perm in allowed_records if perm['is_default']), None)
            if default_record:
                filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
            else:
                filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

    # Override with directly provided filters, if any
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    query = f"""
        SELECT 
            COUNT(*) AS total_households,
            SUM(CASE WHEN gender_of_household_head = 'Male' THEN 1 ELSE 0 END) AS male_heads,
            SUM(how_many_people_live_in_the_household) AS total_people,
            SUM(how_many_household_members_are_below_5) AS under_5_children,
            GROUP_CONCAT(name) AS household_names,

            -- Count households where all children are fully vaccinated (flag set previously)
            SUM(has_all_fully_vaccinated_children) AS fully_vaccinated_households

        FROM `tabHousehold` h
        WHERE h.status = 'Approved' AND {where_clause}
    """
    result = frappe.db.sql(query, tuple(sql_values), as_dict=True)[0]


    # Extract values
    total_household_count = result['total_households'] or 0
    male_household_head_count = result['male_heads'] or 0
    female_household_head_count = total_household_count - male_household_head_count

    total_people_count = result['total_people'] or 0
    under_5_children_count = result['under_5_children'] or 0
    fully_vaccinated_count = result['fully_vaccinated_households'] or 0

    # Calculate percentage of under-5 children
    percentage_under_5_children = (
        round((under_5_children_count / total_people_count) * 100, 0)
        if total_people_count > 0 else 0
    )

    # Calculate percentage
    percentage_fully_vaccinated = (
        round((fully_vaccinated_count / total_household_count) * 100, 0)
        if total_household_count > 0 else 0
    )


    # Rebuild approved_households as a list of dicts (to preserve API format)
    approved_households = [{"name": name} for name in (result['household_names'] or "").split(",") if name]

    # Query Household Table for distribution of households
    household_distribution_query = """
        WITH filtered_households AS (
            SELECT 
                gender_of_household_head,
                educational_level_of_household_head,
                average_monthly_income,
                is_the_household_head_employed,
                industry_of_employment,
                do_you_take_your_childchildren_to_the_facility_for_ri_services,
                is_the_household_residing_in_a_rented_apartment
            FROM `tabHousehold`
            WHERE status = 'Approved' AND {where_conditions}
        )
        -- Gender distribution
        SELECT 
            'Gender' AS distribution_type,
            gender_of_household_head AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'Gender'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY gender_of_household_head

        UNION ALL

        -- Education distribution
        SELECT 
            'Education' AS distribution_type,
            educational_level_of_household_head AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'Education'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY educational_level_of_household_head

        UNION ALL

        -- Average Monthly Income distribution
        SELECT 
            'Income' AS distribution_type,
            average_monthly_income AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'Income'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY average_monthly_income

        UNION ALL

        -- Employment Status distribution
        SELECT 
            'Employment' AS distribution_type,
            is_the_household_head_employed AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'Employment'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY is_the_household_head_employed

        UNION ALL

        -- Employment Industry (only employed heads)
        SELECT 
            'EmploymentIndustry' AS distribution_type,
            industry_of_employment AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'EmploymentIndustry'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        WHERE is_the_household_head_employed = 'Yes'
        GROUP BY industry_of_employment

        UNION ALL

        -- RI Compliance
        SELECT 
            'RICompliance' AS distribution_type,
            do_you_take_your_childchildren_to_the_facility_for_ri_services AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'RICompliance'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY do_you_take_your_childchildren_to_the_facility_for_ri_services

        UNION ALL

        -- Rent Status
        SELECT 
            'RentStatus' AS distribution_type,
            is_the_household_residing_in_a_rented_apartment AS label,
            COUNT(*) AS count,
            COALESCE(
                ROUND(
                    (COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY 'RentStatus'), 0)),
                    2
                ),
                0
            ) AS percentage
        FROM filtered_households
        GROUP BY is_the_household_residing_in_a_rented_apartment

        UNION ALL

        -- Total count of employed household heads 
        SELECT
            'TotalEmployed' AS distribution_type,
            'EmployedHeads' AS label,
            COUNT(*) AS count,
            100.0 AS percentage
        FROM filtered_households
        WHERE is_the_household_head_employed = 'Yes';

    """
    # household_distribution_query = """
    #     WITH base AS (
    #         SELECT
    #             gender_of_household_head,
    #             educational_level_of_household_head,
    #             average_monthly_income,
    #             is_the_household_head_employed,
    #             industry_of_employment,
    #             do_you_take_your_childchildren_to_the_facility_for_ri_services AS ri_services,
    #             is_the_household_residing_in_a_rented_apartment AS rented
    #         FROM `tabHousehold` USE INDEX (
    #             idx_status_gender,
    #             idx_status_education,
    #             idx_status_income,
    #             idx_status_employment,
    #             idx_status_employment_industry,
    #             idx_status_ri,
    #             idx_status_rent
    #         )
    #         WHERE status = 'Approved' AND {where_conditions}
    #     ),
    #     totals AS (
    #         SELECT
    #             COUNT(*) AS total,
    #             SUM(is_the_household_head_employed = 'Yes') AS total_employed
    #         FROM base
    #     ),
    #     dist AS (
    #         SELECT
    #             gender_of_household_head AS gender,
    #             educational_level_of_household_head AS education,
    #             average_monthly_income AS income,
    #             is_the_household_head_employed AS employed,
    #             CASE WHEN is_the_household_head_employed = 'Yes' THEN industry_of_employment END AS industry,
    #             ri_services AS ri,
    #             rented AS rent,
    #             COUNT(*) AS row_count
    #         FROM base
    #         GROUP BY
    #             gender_of_household_head,
    #             educational_level_of_household_head,
    #             average_monthly_income,
    #             is_the_household_head_employed,
    #             industry_of_employment,
    #             ri_services,
    #             rented
    #     )
    #     SELECT distribution_type, label, count, percentage FROM (
    #         -- Gender
    #         SELECT
    #             'Gender' AS distribution_type,
    #             gender AS label,
    #             COUNT(*) AS count,
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2) AS percentage
    #         FROM dist
    #         GROUP BY gender

    #         UNION ALL

    #         -- Education
    #         SELECT
    #             'Education',
    #             education,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2)
    #         FROM dist
    #         GROUP BY education

    #         UNION ALL

    #         -- Income
    #         SELECT
    #             'Income',
    #             income,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2)
    #         FROM dist
    #         GROUP BY income

    #         UNION ALL

    #         -- Employment
    #         SELECT
    #             'Employment',
    #             employed,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2)
    #         FROM dist
    #         GROUP BY employed

    #         UNION ALL

    #         -- Industry (only employed)
    #         SELECT
    #             'EmploymentIndustry',
    #             industry,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / NULLIF((SELECT total_employed FROM totals), 0), 2)
    #         FROM dist
    #         WHERE industry IS NOT NULL
    #         GROUP BY industry

    #         UNION ALL

    #         -- RI Compliance
    #         SELECT
    #             'RICompliance',
    #             ri,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2)
    #         FROM dist
    #         GROUP BY ri

    #         UNION ALL

    #         -- Rent
    #         SELECT
    #             'RentStatus',
    #             rent,
    #             COUNT(*),
    #             ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2)
    #         FROM dist
    #         GROUP BY rent

    #         UNION ALL

    #         -- Total employed heads
    #         SELECT
    #             'TotalEmployed',
    #             'EmployedHeads',
    #             (SELECT total_employed FROM totals),
    #             100.0
    #     ) final;
    # """


    # Run the query with a single scan
    results = frappe.db.sql(
        household_distribution_query.format(where_conditions=where_clause),
        tuple(sql_values),
        as_dict=True
    )

    # Split results into the seven datasets for the dashboard
    household_gender_distribution = [
        {"gender_of_household_head": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "Gender"
    ]

    household_educational_level_distribution = [
        {"educational_level_of_household_head": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "Education"
    ]

    household_average_monthly_income_distribution = [
        {"average_monthly_income": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "Income"
    ]

    household_employment_status_distribution = [
        {"is_the_household_head_employed": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "Employment"
    ]

    household_employment_industry_distribution = [
        {"industry_of_employment": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "EmploymentIndustry"
    ]

    household_children_ri_compliance_distribution = [
        {"do_you_take_your_childchildren_to_the_facility_for_ri_services": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "RICompliance"
    ]

    household_rent_status_distribution = [
        {"is_the_household_residing_in_a_rented_apartment": r["label"], "count": r["count"], "percentage": r["percentage"]}
        for r in results if r["distribution_type"] == "RentStatus"
    ]

    total_household_employment_industry_for_query = next(
    (r["count"] for r in results if r["distribution_type"] == "TotalEmployed"),
    0
    )




    return {
        "status": 200,
        "response": "Success",
        "data": {
            "total_household_count": total_household_count,
            "male_household_head_count": male_household_head_count,
            "female_household_head_count": female_household_head_count,
            "population_of_households": total_people_count,
            "under_5_children_count": under_5_children_count,
            "percentage_under_5_children": percentage_under_5_children,
            "fully_vaccinated_households_count": fully_vaccinated_count,
            "percentage_fully_vaccinated": percentage_fully_vaccinated,
            "household_gender_distribution": household_gender_distribution,
            "household_educational_level_distribution": household_educational_level_distribution,
            "household_average_monthly_income_distribution": household_average_monthly_income_distribution,
            "household_employment_status_distribution": household_employment_status_distribution,
            "household_employment_industry_distribution": household_employment_industry_distribution,
            "total_household_employment_industry": total_household_employment_industry_for_query,
            "household_children_ri_compliance_distribution": household_children_ri_compliance_distribution,
            "household_rent_status_distribution": household_rent_status_distribution
        }
    }



@frappe.whitelist()
def distribution_of_household(project=None, grid=None, settlement=None, ward=None, local_government_area=None, state=None):
    """
    Fetch hierarchical household data and counts based on filters.
    Includes user permission checks for State, Local Government Area, Ward, and Grid.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the necessary role to visualize the dashboard, please contact the project manager.",
            "status": "error"
        }

    if not project:
        return {"status": 400, "message": "Project is required."}

    # Initialize filters based on user permissions
    filters = {}
    # filters = {"project": project}

    # Override filters with directly provided values
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if local_government_area:
        filters['local_government_area'] = local_government_area
    if state:
        filters['state'] = state
    if project:
        filters['project'] = project
   

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    if 'state' not in filters and 'local_government_area' not in filters and 'ward' not in filters and 'settlement' not in filters:
        # Base query for fetching states and settlement counts
        state_query = """
            SELECT 
                st.name, st.state, 
                COUNT(household.name) AS household_count 
            FROM `tabState` st
            LEFT JOIN `tabHousehold` household
                ON household.state = st.name 
                AND household.status = 'Approved' 
                AND household.project = %s
        """
        
        # Initialize query parameters
        query_params = [filters['project']]
        
        # Add grid filter dynamically if provided
        if 'grid' in filters:
            state_query += " AND household.grid = %s"
            query_params.append(filters['grid'])

        # Finalize the query with GROUP BY clause
        state_query += " GROUP BY st.name"

        try:
            # Execute the query with the dynamically built parameters
            states = frappe.db.sql(state_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"states": states}, "message": "States and household counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:
        # Base query for fetching LGAs and settlement counts
        lga_query = """
            SELECT 
                lga.name AS lga_name, 
                lga.local_government_area, 
                lga.state,
                COUNT(household.name) AS household_count 
            FROM `tabLocal Government Area` lga
            LEFT JOIN `tabHousehold` household
                ON household.local_government_area = lga.name 
                AND household.status = 'Approved' 
                AND household.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            lga_query += " AND household.grid = %s"

        # Add the WHERE clause for state
        lga_query += """
            WHERE lga.state = %s
            GROUP BY lga.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['state'])

            # Execute the query with parameters
            lgas = frappe.db.sql(lga_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and household counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' in filters and 'ward' not in filters:
        # Fetch wards and their settlement counts
        ward_query = """
            SELECT 
                ward.name AS ward_name, 
                ward.ward,
                ward.local_government_area, 
                ward.state,
                COUNT(household.name) AS household_count 
            FROM `tabWard` ward
            LEFT JOIN `tabHousehold` household
                ON household.ward = ward.name 
                AND household.status = 'Approved' 
                AND household.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            ward_query += " AND household.grid = %s"

        # Add the WHERE clause for lga
        ward_query += """
            WHERE ward.local_government_area = %s
            GROUP BY ward.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['local_government_area'])

            # Execute the query with parameters
            wards = frappe.db.sql(ward_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"wards": wards}, "message": "Wards and household counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}
        

    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' not in filters:
        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(household.name) AS household_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabHousehold` household
                ON household.settlement = settlement.name 
                AND household.status = 'Approved' 
                AND household.project = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND household.grid = %s"

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE settlement.ward = %s
            GROUP BY settlement.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['ward'])  # Correctly use 'ward' instead of 'state'

            # Execute the query with parameters
            settlement = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"settlements": settlement}, "message": "Settlements and household counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:
        # Base query for fetching LGAs and settlement counts
        settlement_query = """
            SELECT 
                settlement.name,
                COUNT(household.name) AS household_count 
            FROM `tabSettlement` settlement
            LEFT JOIN `tabHousehold` household
                ON household.settlement = settlement.name 
                AND household.status = 'Approved' 
                AND household.project = %s
                AND household.settlement = %s
        """
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND household.grid = %s"

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE household.settlement = %s
            GROUP BY settlement.name
        """
        
        try:
            # Build parameters dynamically based on grid filter
            query_params = [filters['project'], filters['settlement']]
            if 'grid' in filters:
                query_params.append(filters['grid'])
            query_params.append(filters['settlement']) 

            # Execute the query with parameters
            settlements = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            if not settlements:
                settlements = [{"name": None, "household_count": 0}]
            
            return {"status": 200, "data": {"settlement": settlements}, "message": "Settlement and household counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    return {"status": 400, "message": "Invalid filters or no data available."}


@frappe.whitelist()
def settlement_map(grid=None, settlement=None, ward=None, lga=None, state=None):
    """
    Fetch data for the settlement map:
    Filters applied: state, lga, ward, settlement, grid (all optional).
    """
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": 401
        }

    # Check if the user has the "Map Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to view the map, please contact the project manager.",
            "status": 401
        }

    # Initialize filters
    filters = {}

    # Add optional filters
    if grid:
        filters['grid'] = grid
    if settlement:
        filters['settlement'] = settlement
    if ward:
        filters['ward'] = ward
    if lga:
        filters['local_government_area'] = lga
    if state:
        filters['state'] = state

    # Prepare SQL filter conditions
    sql_conditions = []
    sql_values = []

    for key, value in filters.items():
        if isinstance(value, tuple) and value[0] == 'in':
            sql_conditions.append(f"`{key}` IN %s")
            sql_values.append(tuple(value[1]))
        else:
            sql_conditions.append(f"`{key}` = %s")
            sql_values.append(value)

    where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"

    # Query the Building table for residential buildings
    settlement_query = f"""
        SELECT name, response_geolocation, type_of_settlement, archetype_for_rural, archetype_for_urban
        FROM `tabSettlement`
        WHERE status = 'Approved' AND {where_clause}
    """
    try:
        settlement_data = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)
    except Exception as e:
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error"
        }

    return {
        "status": 200,
        "response": "Success",
        "data": settlement_data
    }
