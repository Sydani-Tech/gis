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

@frappe.whitelist()
def states(stateName=None):
# Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

    fields = ['name', 'state', 'country', 'geolocation']
    filters = {}

    if stateName:
        filters['name'] = stateName

    # Check User Permissions for the provided user
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'State'},
        fields=['for_value']
    )

    if user_permissions:
        # Extract the list of allowed states from user permissions
        allowed_states = [permission['for_value'] for permission in user_permissions]
        filters['name'] = ['in', allowed_states]

    # Fetch the states based on the filters
    states = fetch_db_resource(doc='State', fields=fields, filters=filters)

    # Sort the fetched states alphabetically by name
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
        settlements = settlements[:20]
        set_res(settlements=settlements)
    else:
        set_res(message="No settlements found.")


# @frappe.whitelist()
# def overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
#     """
#     Fetch data for the dashboard: total children, fully vaccinated children, and vaccination percentage.
#     Filters applied: user permissions, settlement, ward, lga, state.
#     """

#     if not project:
#         return {
#             "message": "Please provide a project to return the data for the dashboard.",
#             "status": 400
#         }

#     # Get the logged-in user
#     user = frappe.session.user
#     if user == "Guest":
#         return {"message": "You must be logged in to access this data.", "status": 401}
    
#     # Check if the user has the "Dashboard Viewer" role
#     user_roles = frappe.get_roles(user)
#     if "Dashboard Viewer" not in user_roles:
#         return {
#             "message": "You do not have the required role to visualize the dashboard, please contact the project manager.",
#             "status": 401
#         }

#     # Fetch User Permissions for different `allow` values
#     user_permissions = frappe.get_all(
#         'User Permission',
#         filters={'user': user},
#         fields=['allow', 'for_value', 'is_default']
#     )

#     # Initialize filters
#     filters = {}

#     # Process user permissions based on `allow` values
#     for allow_value in ['State', 'Local Government Area', 'Ward', 'Settlement']:
#         allowed_records = [
#             perm for perm in user_permissions if perm['allow'] == allow_value
#         ]
#         if allowed_records:
#             # Prefer the record where `is_default` is 1, else use all records
#             default_record = next((perm for perm in allowed_records if perm['is_default']), None)
#             if default_record:
#                 filters[allow_value.lower().replace(" ", "_")] = default_record['for_value']
#             else:
#                 filters[allow_value.lower().replace(" ", "_")] = ('in', [perm['for_value'] for perm in allowed_records])

#     # Override with directly provided filters, if any
#     if grid:
#         filters['grid'] = grid
#     if settlement:
#         filters['settlement'] = settlement
#     if ward:
#         filters['ward'] = ward
#     if lga:
#         filters['local_government_area'] = lga
#     if state:
#         filters['state'] = state
#     if project:
#         filters['project'] = project

#     # Prepare SQL filter conditions
#     sql_conditions = []
#     sql_values = []

#     for key, value in filters.items():
#         if isinstance(value, tuple) and value[0] == 'in':
#             sql_conditions.append(f"`{key}` IN %s")
#             sql_values.append(tuple(value[1]))
#         else:
#             sql_conditions.append(f"`{key}` = %s")
#             sql_values.append(value)

#     where_clause = " AND ".join(sql_conditions) if sql_conditions else "1=1"


#     # Query Children Table for Total Children
#     children_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE status = 'Approved' AND {where_clause}
#     """
#     children_count = frappe.db.sql(children_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Vaccination Table for Records with children IS NULL
#     vaccination_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabVaccination`
#         WHERE status = 'Approved' AND children IS NULL AND {where_clause}
#     """
#     vaccination_count = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)[0]['count']

#     total_children = children_count + vaccination_count

#     # Fully Vaccinated (Measles 2) Count from Children Table
#     fully_vaccinated_children_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND status = 'Approved' AND {where_clause}
#     """
#     fully_vaccinated_count = frappe.db.sql(fully_vaccinated_children_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Fully Vaccinated (Measles 2) Count from Vaccination Table
#     vaccination_fully_vaccinated_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabVaccination`
#         WHERE vaccination_status = 'Fully Vaccinated (Measles 2)' AND children IS NULL AND status = 'Approved' AND {where_clause}
#     """
#     vaccination_fully_vaccinated_count = frappe.db.sql(vaccination_fully_vaccinated_query, tuple(sql_values), as_dict=True)[0]['count']

#     total_fully_vaccinated = fully_vaccinated_count + vaccination_fully_vaccinated_count

#     # Calculate Percentage
#     percentage_fully_vaccinated = (total_fully_vaccinated / total_children) * 100 if total_children > 0 else 0

#     # Query Children Table for Zero Dose Children
#     zero_dose_children_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND {where_clause}
#     """
#     zero_dose_children_count = frappe.db.sql(zero_dose_children_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Children Table for Zero Dose Male Children
#     zero_dose_male_children_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND gender = 'Male' AND {where_clause}
#     """
#     zero_dose_male_children_count = frappe.db.sql(zero_dose_male_children_query, tuple(sql_values), as_dict=True)[0]['count']

    
#     # Query Children Table for Zero Dose Female Children
#     zero_dose_female_children_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE status = 'Approved' AND vaccination_status = 'Zero Dose' AND gender = 'Female' AND {where_clause}
#     """
#     zero_dose_female_children_count = frappe.db.sql(zero_dose_female_children_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Household Table for number of households
#     household_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabHousehold`
#         WHERE status = 'Approved' AND {where_clause}
#     """
#     household_count = frappe.db.sql(household_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Household Table for number of male household heads
#     male_household_head_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabHousehold`
#         WHERE status = 'Approved' AND gender_of_household_head = 'Male' AND {where_clause}
#     """
#     male_household_head_count = frappe.db.sql(male_household_head_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Household Table for number of female household heads
#     female_household_head_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabHousehold`
#         WHERE status = 'Approved' AND gender_of_household_head = 'Female' AND {where_clause}
#     """
#     female_household_head_count = frappe.db.sql(female_household_head_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Building Table for number of buildings
#     building_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabBuilding`
#         WHERE status = 'Approved' AND {where_clause}
#     """
#     building_count = frappe.db.sql(building_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Building Table for number of residential buildings
#     residential_building_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabBuilding`
#         WHERE status = 'Approved' AND building_type = 'Residential' AND {where_clause}
#     """
#     residential_building_count = frappe.db.sql(residential_building_query, tuple(sql_values), as_dict=True)[0]['count']
#     residential_building_percentage = (residential_building_count / building_count) * 100 if building_count > 0 else 0

#     # Query Settlement Table for number of settlements
#     settlement_query = f"""
#         SELECT COUNT(*) AS count
#         FROM `tabSettlement`
#         WHERE status = 'Approved' AND {where_clause}
#     """
#     settlement_count = frappe.db.sql(settlement_query, tuple(sql_values), as_dict=True)[0]['count']

#     # Query Household Table for distribution of households by gender
#     household_gender_query = f"""
#       SELECT gender_of_household_head, COUNT(*) AS count
#       FROM `tabHousehold`
#       WHERE status = 'Approved' AND {where_clause}
#       GROUP BY gender_of_household_head
#     """
#     household_gender_distribution = frappe.db.sql(household_gender_query, tuple(sql_values), as_dict=True)

#     # Calculate percentages
#     total_households = sum(item['count'] for item in household_gender_distribution)
#     for item in household_gender_distribution:
#       item['percentage'] = round((item['count'] / total_households) * 100, 2) if total_households > 0 else 0


#     # Query Building Table for distribution of establishments by type
#     establishment_type_query = f"""
#       SELECT establishment_type, COUNT(*) AS count
#       FROM `tabBuilding`
#       WHERE status = 'Approved' AND establishment_type IS NOT NULL AND building_type = 'Non-Residential' AND {where_clause}
#       GROUP BY establishment_type
#     """
#     non_residential_building_distribution = frappe.db.sql(establishment_type_query, tuple(sql_values), as_dict=True)
#     # Calculate percentages
#     non_residential_buildings = sum(item['count'] for item in non_residential_building_distribution)
#     for item in non_residential_building_distribution:
#       item['percentage'] = round((item['count'] / non_residential_buildings) * 100, 0) if non_residential_buildings > 0 else 0

#     # Query to fetch population distribution
#     house_query = f"""
#         SELECT 
#             how_many_household_members_are_above_18,
#             how_many_household_members_are_between_15_and_18_years,
#             how_many_household_members_are_between_9_and_14_years,
#             how_many_household_members_are_between_5_and_8_years,
#             how_many_household_members_are_below_5,
#             creation
#         FROM `tabHousehold`
#         WHERE status = 'Approved' AND {where_clause}
#     """
#     house_records = frappe.db.sql(house_query, tuple(sql_values), as_dict=True)

#     # Current year
#     current_year = datetime.now().year

#     # Initialize totals for each category
#     population_distribution = {
#         "above_18": 0,
#         "between_15_and_18": 0,
#         "between_9_and_14": 0,
#         "between_5_and_8": 0,
#         "below_5": 0,
#     }

#     # Process each record
#     for record in house_records:
#         # Sum up the population for this record
#         above_18 = record.get("how_many_household_members_are_above_18", 0)
#         between_15_and_18 = record.get("how_many_household_members_are_between_15_and_18_years", 0)
#         between_9_and_14 = record.get("how_many_household_members_are_between_9_and_14_years", 0)
#         between_5_and_8 = record.get("how_many_household_members_are_between_5_and_8_years", 0)
#         below_5 = record.get("how_many_household_members_are_below_5", 0)

#         # Add to totals
#         population_distribution["above_18"] += above_18
#         population_distribution["between_15_and_18"] += between_15_and_18
#         population_distribution["between_9_and_14"] += between_9_and_14
#         population_distribution["between_5_and_8"] += between_5_and_8
#         population_distribution["below_5"] += below_5

#     # Calculate total population
#     total_population = sum(population_distribution.values())

#     # Calculate percentages for distribution
#     for key in population_distribution:
#         population_distribution[key] = {
#             "count": population_distribution[key],
#             "percentage": round((population_distribution[key] / total_population) * 100, 2) if total_population > 0 else 0
#         }
    
#     # Convert the population_distribution dictionary into the desired format
#     formatted_population_distribution = [
#         {
#             "population_type": "Above 18",
#             "count": population_distribution["above_18"]["count"],
#             "percentage": population_distribution["above_18"]["percentage"]
#         },
#         {
#             "population_type": "Between 15 and 18",
#             "count": population_distribution["between_15_and_18"]["count"],
#             "percentage": population_distribution["between_15_and_18"]["percentage"]
#         },
#         {
#             "population_type": "Between 9 and 14",
#             "count": population_distribution["between_9_and_14"]["count"],
#             "percentage": population_distribution["between_9_and_14"]["percentage"]
#         },
#         {
#             "population_type": "Between 5 and 8",
#             "count": population_distribution["between_5_and_8"]["count"],
#             "percentage": population_distribution["between_5_and_8"]["percentage"]
#         },
#         {
#             "population_type": "Below 5",
#             "count": population_distribution["below_5"]["count"],
#             "percentage": population_distribution["below_5"]["percentage"]
#         }
#     ]

#     # Step 1: Fetch vaccination status from Children table
#     children_vaccination_query = f"""
#         SELECT vaccination_status, COUNT(*) AS count
#         FROM `tabChildren`
#         WHERE status = 'Approved' AND vaccination_status IS NOT NULL AND {where_clause}
#         GROUP BY vaccination_status
#     """
#     children_vaccination_data = frappe.db.sql(children_vaccination_query, tuple(sql_values), as_dict=True)

#     # Step 2: Fetch vaccination status from Vaccination table where children is Null
#     vaccination_query = f"""
#         SELECT vaccination_status, COUNT(*) AS count
#         FROM `tabVaccination`
#         WHERE status = 'Approved' AND children IS NULL AND vaccination_status IS NOT NULL AND {where_clause}
#         GROUP BY vaccination_status
#     """
#     vaccination_data = frappe.db.sql(vaccination_query, tuple(sql_values), as_dict=True)

#     # Step 3: Combine the data and group by vaccination_status
#     vaccination_status_distribution = {}

#     # Add data from Children table
#     for record in children_vaccination_data:
#         vaccination_status = record["vaccination_status"]
#         count = record["count"]
#         vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

#     # Add data from Vaccination table
#     for record in vaccination_data:
#         vaccination_status = record["vaccination_status"]
#         count = record["count"]
#         vaccination_status_distribution[vaccination_status] = vaccination_status_distribution.get(vaccination_status, 0) + count

#     # Step 4: Format the data for output
#     total_records = sum(vaccination_status_distribution.values())
#     formatted_vaccination_status_distribution = [
#         {
#             "vaccination_status": status,
#             "count": count,
#             "percentage": round((count / total_records) * 100, 2) if total_records > 0 else 0
#         }
#         for status, count in vaccination_status_distribution.items()
#     ]

#     return {
#         "status": 200,
#         "response": "Success",
#         "data": {
#         "total_children": total_children,
#         "fully_vaccinated_children": total_fully_vaccinated,
#         "percentage_fully_vaccinated": round(percentage_fully_vaccinated, 2),
#         "zero_dose_children": zero_dose_children_count,
#         "zero_dose_male_children": zero_dose_male_children_count, 
#         "zero_dose_female_children": zero_dose_female_children_count,
#         "household_count": household_count,
#         "male_household_head_count": male_household_head_count,
#         "female_household_head_count": female_household_head_count,
#         "building_count": building_count,
#         "residential_building_percentage": residential_building_percentage,
#         "settlement_count": settlement_count,
#         "household_gender_distribution": household_gender_distribution,
#         "non_residential_building_distribution": non_residential_building_distribution,
#         "non_residential_buildings": non_residential_buildings,
#         "formatted_population_distribution": formatted_population_distribution,
#         "total_population": total_population,
#         "formatted_vaccination_status_distribution": formatted_vaccination_status_distribution
#       }
#     }

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
def map_overview(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
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
    building_query = f"""
        SELECT name, percentage_of_vaccinated_children, geolocation, building_type, establishment_type, health_facility
        FROM `tabBuilding`
        WHERE status = 'Approved' AND {where_clause}
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

    Args:
        building (str): The name of the building.

    Returns:
        dict: Building data with associated households and children.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": "error"
        }

    # Check if the user has the "Map Viewer" role
    user_roles = frappe.get_roles(user)
    if "Dashboard Viewer" not in user_roles:
        return {
            "message": "You do not have the required role to view the map, please contact the project manager.",
            "status": "error"
        }

    if not building:
        return {
            "message": "Building name is required.",
            "status": 400
        }
    

    # Fetch building pictures
    building_data = frappe.db.get_value(
        "Building",
        building,
        ["building_picture", "building_picture_2"],
        as_dict=True
    )

    if not building_data:
        return {
            "message": f"No building found with name: {building}",
            "status": 404
        }

    # Fetch households associated with the building
    households = frappe.db.sql(
        """
        SELECT name, name_of_household_head
        FROM `tabHousehold`
        WHERE building = %(building)s AND status = 'Approved'
        """,
        {"building": building},
        as_dict=True
    )

    # Fetch children associated with each household
    households_with_children = []
    for household in households:
        children = frappe.db.sql(
            """
            SELECT name, full_name, date_of_birth, gender, vaccination_status
            FROM `tabChildren`
            WHERE household = %(household)s AND status = 'Approved'
            """,
            {"household": household["name"]},
            as_dict=True
        )
        households_with_children.append({
            "household": household["name_of_household_head"],
            "children": children
        })

    today = date.today()

    return {
    "status": 200,
    "data": {
        "building": {
            "name": building,
            "building_picture": building_data.get("building_picture"),
            "building_picture_2": building_data.get("building_picture_2"),
            "households": [
                {
                    "name_of_household_head": household["name_of_household_head"],
                    "children": [
                        {
                            "name": child["name"],
                            "full_name": child["full_name"],
                            "date_of_birth": child["date_of_birth"],
                            "gender": child["gender"],
                            "vaccination_status": child["vaccination_status"],
                            "age": f"{(today.year - child['date_of_birth'].year) - (1 if today.month < child['date_of_birth'].month or (today.month == child['date_of_birth'].month and today.day < child['date_of_birth'].day) else 0)} years, {((today.month - child['date_of_birth'].month) % 12 if today.day >= child['date_of_birth'].day else (today.month - child['date_of_birth'].month - 1) % 12)} months"
                            if child["date_of_birth"] else "Unknown"
                        }
                        for child in frappe.db.sql(
                            """
                            SELECT name, full_name, date_of_birth, gender, vaccination_status
                            FROM `tabChildren`
                            WHERE household = %(household)s AND status = 'Approved'
                            """,
                            {"household": household["name"]},
                            as_dict=True
                        )
                    ]
                }
                for household in households
            ]
        }
    }
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
            item["percentage"] = (item["count"] / total_vdc_meetings) * 100
        else:
            item["percentage"] = 0


    vdc_periodic_meeting_count_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabSettlement`
        WHERE status = 'Approved' AND is_there_a_vdc = 'Yes' AND {where_clause}
    """
    vdc_periodic_meeting_count = frappe.db.sql(vdc_periodic_meeting_count_query, tuple(sql_values), as_dict=True)[0]['count']

    # archetype_group_query = f"""
    #     SELECT archetype_for_rural, archetype_for_urban, COUNT(*) AS count
    #     FROM `tabSettlement`
    #     WHERE status = 'Approved' AND {where_clause}
    #     GROUP BY archetype_for_rural, archetype_for_urban
    # """
    # archetype_group_result = frappe.db.sql(archetype_group_query, tuple(sql_values), as_dict=True)
    # archetype_groups = {}
    # for record in archetype_group_result:
    #     archetype = record["archetype_for_rural"] or record["archetype_for_urban"]
    #     if archetype not in archetype_groups:
    #         archetype_groups[archetype] = 0
    #     archetype_groups[archetype] += record["count"]
    # archetype_percentages = {k: round((v / settlement_count) * 100, 1) for k, v in archetype_groups.items()}

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
def building_dashboard(project=None, grid=None, settlement=None, ward=None, lga=None, state=None):
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
            }
        }

    household_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    household_count = frappe.db.sql(household_query, tuple(sql_values), as_dict=True)[0]['count']

    
    return {
        "status": 200,
        "response": "Success",
        "data": {
            "building_count": building_count,
            "household_count": household_count,
            },
        }




@frappe.whitelist()
def distribution_of_building(project=None, grid=None, settlement=None, ward=None, local_government_area=None, state=None):
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

        # Finalize the query with GROUP BY clause
        state_query += " GROUP BY st.name"

        try:
            # Execute the query with the dynamically built parameters
            states = frappe.db.sql(state_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"states": states}, "message": "States and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    elif 'state' in filters and 'local_government_area' not in filters and 'ward' not in filters:
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
            return {"status": 200, "data": {"lgas": lgas}, "message": "LGAs and building counts fetched successfully."}
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
            return {"status": 200, "data": {"wards": wards}, "message": "Wards and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}
        

    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' not in filters:
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
        
        # Add grid filter to the LEFT JOIN condition if provided
        if 'grid' in filters:
            settlement_query += " AND building.grid = %s"

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
            settlements = frappe.db.sql(settlement_query, tuple(query_params), as_dict=True)
            return {"status": 200, "data": {"settlements": settlements}, "message": "Settlements and building counts fetched successfully."}
        except Exception as e:
            return {"status": 400, "message": str(e)}

    
    elif 'state' in filters and 'local_government_area' in filters and 'ward' in filters and 'settlement' in filters:
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

        # Add the WHERE clause for ward
        settlement_query += """
            WHERE building.settlement = %s
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
    percentage_male_children = (total_male_count / total_children) * 100 if total_children > 0 else 0
    percentage_female_children = (total_female_count / total_children) * 100 if total_children > 0 else 0

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


    # Query Household Table for number of households
    households_query = f"""
        SELECT COUNT(*) AS count, name
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    total_household_count = frappe.db.sql(households_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of male household heads
    male_household_head_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabChildren`
        WHERE status = 'Approved' AND gender = 'Male' AND {where_clause}
    """
    male_household_head_count = frappe.db.sql(male_household_head_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of female household heads
    female_household_head_count = total_household_count - male_household_head_count

    households_query = f"""
        SELECT COUNT(*) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    total_household_count = frappe.db.sql(households_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of people in households
    household_population_query = f"""
        SELECT SUM(how_many_people_live_in_the_household) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    total_people_count = frappe.db.sql(household_population_query, tuple(sql_values), as_dict=True)[0]['count']

    # Query Household Table for number of under 5 children in households
    under_5_children_query = f"""
        SELECT SUM(how_many_household_members_are_below_5) AS count
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    under_5_children_count = frappe.db.sql(under_5_children_query, tuple(sql_values), as_dict=True)[0]['count']

    #calculate percentage
    percentage_under_5_children = round((under_5_children_count / total_people_count) * 100, 0) if total_people_count > 0 else 0
    
    # Fetch all approved households
    fully_vaccinated_households_query = f"""
        SELECT name
        FROM `tabHousehold`
        WHERE status = 'Approved' AND {where_clause}
    """
    approved_households = frappe.db.sql(fully_vaccinated_households_query, tuple(sql_values), as_dict=True)

    fully_vaccinated_count = 0

    # Iterate through each household
    for household in approved_households:
        # Fetch children linked to the household where status is Approved
        children = frappe.get_all(
            "Children",
            filters={
                "household": household["name"],
                "status": "Approved",
            },
            fields=["vaccination_status"],
        )

        # Check if all children are fully vaccinated for Measles 2
        if children and all(child["vaccination_status"] == "Fully Vaccinated (Measles 2)" for child in children):
            fully_vaccinated_count += 1

    # Calculate percentage
    percentage_fully_vaccinated = round((fully_vaccinated_count / total_household_count) * 100, 0) if total_household_count > 0 else 0

    # Query Household Table for distribution of households by gender
    household_gender_query = f"""
      SELECT gender_of_household_head, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY gender_of_household_head
    """
    household_gender_distribution = frappe.db.sql(household_gender_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_gender_for_query = sum(item['count'] for item in household_gender_distribution)
    for item in household_gender_distribution:
      item['percentage'] = round((item['count'] / total_household_gender_for_query) * 100, 2) if total_household_gender_for_query > 0 else 0

    # Query Household Table for distribution of households by educational level
    household_educational_level_query = f"""
      SELECT educational_level_of_household_head, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY educational_level_of_household_head
    """
    household_educational_level_distribution = frappe.db.sql(household_educational_level_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_education_level_for_query = sum(item['count'] for item in household_educational_level_distribution)
    for item in household_educational_level_distribution:
      item['percentage'] = round((item['count'] / total_household_education_level_for_query) * 100, 2) if total_household_education_level_for_query > 0 else 0

    # Query Household Table for distribution of households by educational level
    household_average_monthly_income_query = f"""
      SELECT average_monthly_income, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY average_monthly_income
    """
    household_average_monthly_income_distribution = frappe.db.sql(household_average_monthly_income_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_average_monthly_income_for_query = sum(item['count'] for item in household_average_monthly_income_distribution)
    for item in household_average_monthly_income_distribution:
      item['percentage'] = round((item['count'] / total_household_average_monthly_income_for_query) * 100, 2) if total_household_average_monthly_income_for_query > 0 else 0


    # Query Household Table for distribution of households employment status
    household_employment_status_query = f"""
      SELECT is_the_household_head_employed, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY is_the_household_head_employed
    """
    household_employment_status_distribution = frappe.db.sql(household_employment_status_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_employment_status_for_query = sum(item['count'] for item in household_employment_status_distribution)
    for item in household_employment_status_distribution:
      item['percentage'] = round((item['count'] / total_household_employment_status_for_query) * 100, 2) if total_household_employment_status_for_query > 0 else 0


    # Query Household Table for distribution of households employment industry
    household_employment_industry_status_query = f"""
      SELECT industry_of_employment, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND is_the_household_head_employed = 'Yes' AND {where_clause}
      GROUP BY industry_of_employment
    """
    household_employment_industry_distribution = frappe.db.sql(household_employment_industry_status_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_employment_industry_for_query = sum(item['count'] for item in household_employment_industry_distribution)
    for item in household_employment_industry_distribution:
      item['percentage'] = round((item['count'] / total_household_employment_industry_for_query) * 100, 2) if total_household_employment_industry_for_query > 0 else 0


    # Query Household Table for distribution of households by RI compliance
    household_children_ri_compliance_query = f"""
      SELECT do_you_take_your_childchildren_to_the_facility_for_ri_services, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY do_you_take_your_childchildren_to_the_facility_for_ri_services
    """
    household_children_ri_compliance_distribution = frappe.db.sql(household_children_ri_compliance_query, tuple(sql_values), as_dict=True)

    # Calculate percentages
    total_household_children_ri_compliance_for_query = sum(item['count'] for item in household_children_ri_compliance_distribution)
    for item in household_children_ri_compliance_distribution:
      item['percentage'] = round((item['count'] / total_household_children_ri_compliance_for_query) * 100, 2) if total_household_children_ri_compliance_for_query > 0 else 0


    # Query Household Table for distribution of households by rent status
    household_rent_status_query = f"""
      SELECT is_the_household_residing_in_a_rented_apartment, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND {where_clause}
      GROUP BY is_the_household_residing_in_a_rented_apartment
    """
    household_rent_status_distribution = frappe.db.sql(household_rent_status_query, tuple(sql_values), as_dict=True)
    
    # Calculate percentages
    total_household_rent_status_for_query = sum(item['count'] for item in household_rent_status_distribution)
    for item in household_rent_status_distribution:
      item['percentage'] = round((item['count'] / total_household_rent_status_for_query) * 100, 2) if total_household_rent_status_for_query > 0 else 0



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

