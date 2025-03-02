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



def test_queries():
    # Query Household Table for distribution of households by gender
    household_gender_query = f"""
      SELECT gender_of_household_head, COUNT(*) AS count
      FROM `tabHousehold`
      WHERE status = 'Approved' AND project = 'STRICAN - Phase 2' AND state = 'Federal Capital Territory' AND local_government_area = 'Municipal Area Council-Fct' AND ward = 'Kabusa-Municipal Area Council-Fct' AND settlement = 'Sunshine Homes'
      GROUP BY gender_of_household_head
    """
    household_gender_distribution = frappe.db.sql(household_gender_query, as_dict=True)

    # Calculate percentages
    total_households = sum(item['count'] for item in household_gender_distribution)
    for item in household_gender_distribution:
      item['percentage'] = round((item['count'] / total_households) * 100, 2) if total_households > 0 else 0

    return {
      'household_gender_distribution': household_gender_distribution
    }

@frappe.whitelist()
def update_building_geolocation():
    try:
        # Fetch the Building record with the specified name
        building = frappe.get_doc("Building", "1 - Alukusu Primary Health Center, Sidisaba ward, Katcha LGA, Niger state")
        # building = frappe.get_doc("Building", "2 - The street wey I belong")
        # Update the geolocation field
        # print(building.geolocation)
        print(building.response_geolocation)
        
        # building.response_geolocation = None
        # building.geolocation = None
        
        #Set the geolocation field in the required GeoJSON format
        building.response_geolocation = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        # "coordinates": [7.475866, 9.042452]  # Longitude first, then Latitude (Sydani)
                        # "coordinates": [7.4042, 9.1099]  # Longitude first, then Latitude (Gwarinpa)
                        # "coordinates": [7.4951, 9.0579]  # Longitude first, then Latitude (Asokoro)
                        "coordinates": [6.1532668192084, 8.99168425242635]  # Longitude first, then Latitude (Alukusu)

                    }
                }
            ]
        })
        
        # Save the changes
        building.save()
        
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

# @frappe.whitelist()
# def get_building_data(building):
#     """
#     Fetch data for a given building, including pictures, approved households, and approved children in those households.
#     If the building is not residential, fetch vaccination records instead.

#     Args:
#         building (str): The name of the building.

#     Returns:
#         dict: Building data with associated households and children or vaccination records.
#     """

#     # Get the logged-in user
#     user = frappe.session.user
#     if user == "Guest":
#         return {
#             "message": "You must be logged in to access this data.",
#             "status": "error"
#         }

#     # Check if the user has the "Dashboard Viewer" role
#     user_roles = frappe.get_roles(user)
#     if "Dashboard Viewer" not in user_roles:
#         return {
#             "message": "You do not have the required role to view the map, please contact the project manager.",
#             "status": "error"
#         }

#     if not building:
#         return {
#             "message": "Building name is required.",
#             "status": 400
#         }
    
#     # Fetch building details including type and pictures
#     building_data = frappe.db.get_value(
#         "Building",
#         building,
#         ["building_picture", "building_picture_2", "building_type"],
#         as_dict=True
#     )

#     if not building_data:
#         return {
#             "message": f"No building found with name: {building}",
#             "status": 404
#         }

#     # Fetch approved vaccination records for the building
#     today = date.today()
#     vaccinations = frappe.db.sql(
#         """
#         SELECT full_name, date_of_birth, vaccination_status, vaccination_date, next_vaccination_date, gender
#         FROM `tabVaccination`
#         WHERE building = %(building)s AND status = 'Approved' AND children is NULL
#         """,
#         {"building": building},
#         as_dict=True
#     )

#     # Fetch approved children for the building
#     children = frappe.db.sql(
#         """
#         SELECT full_name, date_of_birth, vaccination_status, last_vaccination_date, next_vaccination, gender
#         FROM `tabChild`
#         WHERE building = %(building)s AND status = 'Approved'
#         """,
#         {"building": building},
#         as_dict=True
#     )

#     children_and_vaccination_data = [
#         {
#             "full_name": record["full_name"],
#             "vaccination_status": record["vaccination_status"],
#             "vaccination_date": record["vaccination_date"],
#             "next_vaccination_date": record["next_vaccination_date"],
#             "gender": record["gender"],
#             "age": f"{(today.year - record['date_of_birth'].year) - (1 if today.month < record['date_of_birth'].month or (today.month == record['date_of_birth'].month and today.day < record['date_of_birth'].day) else 0)} years, {((today.month - record['date_of_birth'].month) % 12 if today.day >= record['date_of_birth'].day else (today.month - record['date_of_birth'].month - 1) % 12)} months"
#                     if record["date_of_birth"] else "Unknown"
            
#         }
#         for record in vaccinations
#     ]

#     return {
#         "status": 200,
#         "data": {
#             "building": {
#                 "name": building,
#                 "building_picture": building_data.get("building_picture"),
#                 "building_picture_2": building_data.get("building_picture_2"),
#                 "children_and_vaccination_data": children_and_vaccination_data
#             }
#         }
#     }


import frappe
from datetime import date

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
        ["building_picture", "building_picture_2", "building_type"],
        as_dict=True
    )

    if not building_data:
        return {
            "message": f"No building found with name: {building}",
            "status": 404
        }

    # Fetch both children and vaccination records in a single query
    combined_records = frappe.db.sql(
        """
        SELECT 
            full_name, 
            date_of_birth, 
            gender, 
            vaccination_status, 
            COALESCE(vaccination_date, last_vaccination_date) AS vaccination_date,
            next_vaccination_date,
            household
        FROM (
            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                vaccination_date, 
                next_vaccination_date,
                NULL AS last_vaccination_date,
                household
            FROM `tabVaccination`
            WHERE building = %(building)s AND status = 'Approved' AND children IS NULL AND building IS NOT NULL
            
            UNION ALL

            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                NULL AS vaccination_date,
                next_vaccination_date AS next_vaccination_date,
                last_vaccination_date,
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
            "vaccination_date": record["vaccination_date"],
            "next_vaccination_date": record["next_vaccination_date"],
            "date_of_birth": record["date_of_birth"],
            "age": (
                f"{(today.year - record['date_of_birth'].year) - (1 if today.month < record['date_of_birth'].month or (today.month == record['date_of_birth'].month and today.day < record['date_of_birth'].day) else 0)} years, "
                f"{((today.month - record['date_of_birth'].month) % 12 if today.day >= record['date_of_birth'].day else (today.month - record['date_of_birth'].month - 1) % 12)} months"
                if record["date_of_birth"] else "Unknown"
            ),
            "household_head": frappe.db.get_value("Household", record["household"], "name_of_household_head")
        }
        for record in combined_records
    ]

    return {
        "status": 200,
        "data": {
            "building": {
                "name": building,
                "building_picture": building_data.get("building_picture"),
                "building_picture_2": building_data.get("building_picture_2"),
                "children_and_vaccination_data": formatted_data
            }
        }
    }

import requests
import frappe
import datetime


@frappe.whitelist()
def fetch_odk_data():
    # print("Function fetch_odk_data_program is executed.")

    mapping_dict = {
        #Facilities
        "PHC (B) \nAlukusu": "Alukusu Primary Health Center-Sidisaba-Katcha",
        "BHC Katcha": "BHC Katcha-Katcha-Katcha-Niger",

        #Settlements
        "ALUKUSU B": "Alukusu B",
        "NDALADA": "Ndalada",
        "UNG. AUDU": "Ung Audu",

        #Vaccines
        "HEP_B0": "HEP B0",
        "OPV0": "OPV 0",
        "OPV1": "OPV 1",
        "OPV2": "OPV 2",
        "OPV3": "OPV 3",
        "PCV_1": "PCV 1",
        "PCV2": "PCV 2",
        "PCV3": "PCV 3",
        "IPV1": "IPV 1",
        "IPV2": "IPV 2",
        "ROTA1": "ROTA 1",
        "ROTA2": "ROTA 2",
        "ROTA3": "ROTA 3",
        "VIT_A": "VIT A",
        "MEN_A": "MEN A",
        "MEASLES_1": "Measles 1",
        "MEASLES_2": "Measles 2",
        "YELLOW_FEVER": "Yellow Fever",
        "BCG": "BCG",
        "PENTA_1": "PENTA 1",
        "PENTA2": "PENTA 2",    
        "PENTA3": "PENTA 3",

        #Type of Vaccination Post:
        "OUTREACH TEAM": "Outreach Team",
        "Mobile Team": "Mobile Team",
        "Special Team": "Special Team",

        #Gender
        "male": "Male",
        "female": "Female",
        # Add more mappings as needed
    }

    def transform_values(value):
        if value in mapping_dict:
            return mapping_dict[value]
        else:
            return value

    def pull_vaccination_data(odk_server_url, form_id, username, password):
        try:
            # print("Attempting to fetch data from ODK server.")
            response = requests.get(odk_server_url.format(FORM_ID=form_id), auth=(username, password))
            # print("Response Status Code:", response.status_code)
            # print("Response Content:", response.content)

            if response.status_code == 200:
                for item in response.json()["value"]:
                    instance_id = item.get("meta", {}).get("instanceID", "")
                    # print("Instance ID:", instance_id)

                    # Print the item to understand the structure and identify the keys
                    # print("ODK item:", item)

                    # Mapping and transformation
                    vaccination_date = item.get("Enter_the_date", "")
                    print ("Date:", vaccination_date)
                    # review_state = item.get("__system", {}).get("reviewState", "")
                    # print ("Review State:", review_state)
                    vaccinators_name = item.get("Please_input_your_name", "")
                    print ("Vaccinator's Name:", vaccinators_name)
                    vaccinators_phone_number = item.get("please_input_your_phone_number", "")
                    print ("Vaccinator's Phone Number:", vaccinators_phone_number)
                    team_code = item.get("Team_code", "")
                    print ("Team Code:", team_code)

                    grid_record = frappe.db.get_all("Grid", {"title": team_code}, ["name"], limit=1)
                    grid = grid_record[0].name if grid_record else None
                    print("Grid:", grid)

                    settlement = transform_values(item.get("settlement", ""))
                    print ("Settlement:", settlement)
                    facility = transform_values(item.get("facility", ""))
                    print ("Facility:", facility)
                    type_of_vaccination_post = transform_values(item.get("Type_of_vaccination_post", ""))
                    print ("Type of Vaccination Post:", type_of_vaccination_post)
                    geolocation = item.get("Record_your_current_location")
                    if geolocation:
                        formatted_geolocation = json.dumps({
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "properties": {
                                        "accuracy": geolocation.get("properties", {}).get("accuracy")
                                    },
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": geolocation.get("coordinates")[:2]  # Only take longitude and latitude
                                    }
                                }
                            ]
                        })
                        # print("Formatted Geolocation:", formatted_geolocation)
                    else:
                        formatted_geolocation = None
                    print("Geolocation:", formatted_geolocation)
                    start_time = item.get("start", "")
                    start_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                    print("Start Time:", start_time)

                    end_time = item.get("end", "")
                    end_time = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    print ("End Time:", end_time)
                    odk_parent_id = item.get("__id", "")
                    print ("ODK Parent ID:", odk_parent_id)
                    

                    #Actual Data
                    group_dp5rd99 = item.get("group_dp5rd99", {})

                    for data in item.get("group_dp5rd99", []):
                        care_givers_surname = data.get("surName_of_the_caregiver", "")
                        print ("Caregiver's Surname:", care_givers_surname)
                        care_givers_firstname = data.get("FirstName_of_the_caregiver", "")
                        print ("Caregiver's Firstname:", care_givers_firstname)
                        care_givers_phone_no = data.get("Care_giver_Mai_angwa_phone_number", "")
                        print ("Caregiver's Phone Number:", care_givers_phone_no)
                        care_givers_age = data.get("Age_of_the_caregiver_number", "")
                        # Calculate date of birth from age
                        if care_givers_age:
                            try:
                                today = datetime.date.today()
                                care_givers_date_of_birth = datetime.date(today.year - int(care_givers_age), 1, 1)
                            except ValueError:
                                care_givers_date_of_birth = None
                        else:
                            care_givers_date_of_birth = None
                        print("Caregiver's Date of Birth:", care_givers_date_of_birth)
                        
                        
                        last_name = data.get("surName_of_the_child", "")
                        print ("Last Name:", last_name)
                        first_name = data.get("firstName_of_the_child", "")
                        print ("First Name:", first_name)
                        date_of_birth = data.get("Date_of_birth_of_the_child", "")
                        print ("Date of Birth:", date_of_birth)
                        gender = transform_values(data.get("What_is_the_gender_of_the_child_", ""))
                        print ("Gender:", gender)
                        vaccines_taken = data.get("Select_the_vaccines_that_were_given", "")
                        vaccines_taken_list = [transform_values(vaccine.strip()) for vaccine in vaccines_taken.split()]
                        print ("Vaccines Taken:", vaccines_taken_list)
                        does_the_child_have_a_child_health_card = data.get("Child_have_health_card", "")
                        print ("Does the child have a health card:", does_the_child_have_a_child_health_card)
                        
                        did_you_administer_the_child_health_card = data.get("administer_child_health_card", "")
                        if did_you_administer_the_child_health_card == None:
                            did_you_administer_the_child_health_card = "No"
                        

                        print ("Did you administer the child health card:", did_you_administer_the_child_health_card)
                        why_were_health_cards_not_given = data.get("Why_were_health_cards_not_given", "")
                        print ("Why were health cards not given:", why_were_health_cards_not_given)
                        odk_child_id = data.get("__id", "")
                        print ("ODK Child ID:", odk_child_id)
                        
                        # Check if a record with the same odk_child_id already exists
                        existing_record = frappe.db.exists("Vaccination", {"odk_child_id": odk_child_id})
                        if existing_record:
                            print(f"Record with odk_child_id {odk_child_id} already exists. Skipping...")
                            continue

                        # Insert data into Vaccination table
                        vaccination = frappe.new_doc("Vaccination")
                        vaccination.vaccination_date = vaccination_date
                        vaccination.vaccinators_name = vaccinators_name
                        vaccination.vaccinators_phone_number = vaccinators_phone_number
                        vaccination.team_code = team_code
                        vaccination.settlement = settlement
                        vaccination.grid = grid
                        vaccination.ward = frappe.db.get_value("Settlement", {"name": settlement}, "ward")
                        vaccination.local_government_area = frappe.db.get_value("Settlement", {"name": settlement}, "local_government_area")
                        vaccination.state = frappe.db.get_value("Settlement", {"name": settlement}, "state")
                        vaccination.country = frappe.db.get_value("Settlement", {"name": settlement}, "country")
                        vaccination.facility = facility
                        vaccination.building = frappe.db.get_all("Building", {"health_facility": facility}, ["name"])[0].name, ""
                        vaccination.type_of_vaccination_post = type_of_vaccination_post
                        vaccination.geolocation = formatted_geolocation
                        vaccination.response_geolocation = formatted_geolocation
                        vaccination.start_time = start_time
                        vaccination.end_time = end_time
                        vaccination.odk_parent_id = odk_parent_id
                        vaccination.care_givers_surname = care_givers_surname
                        vaccination.care_givers_firstname = care_givers_firstname
                        vaccination.care_givers_phone_no = care_givers_phone_no
                        vaccination.care_givers_date_of_birth = care_givers_date_of_birth
                        vaccination.last_name = last_name
                        vaccination.first_name = first_name
                        vaccination.date_of_birth = date_of_birth
                        vaccination.gender = gender
                        # vaccination.vaccines_taken = vaccines_taken
                        for vaccine in vaccines_taken_list:
                            vaccination.append("last_vaccines_administered", {"vaccine": vaccine})
                        vaccination.does_the_child_have_a_child_health_card = does_the_child_have_a_child_health_card
                        vaccination.did_you_administer_the_child_health_card = did_you_administer_the_child_health_card
                        vaccination.why_were_health_cards_not_given = why_were_health_cards_not_given
                        vaccination.odk_child_id = odk_child_id
                        vaccination.status = "Submitted"
                        vaccination.project = "STRICAN - Phase 2"
                        vaccination.was_the_child_vaccinated_during_this_program = "Yes"

                        vaccination.insert(ignore_permissions=True)
                        vaccination.save()
                        

                        
                    

                

                    # print("Records inserted successfully.")

                return "Data fetched successfully"
            else:
                return "Error fetching data from ODK server"
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return "Error: " + str(e)
        except Exception as e:
            print("Error:", str(e))
            return "Error: " + str(e)

    # Replace the following placeholders with your actual values
    # odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$top=1"
    odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*&$top=1"
    form_id = "Vaccination%20Team%20Tool"
    username = "admin@sydani.org"
    password = "@A35dDGaa%1334"

    return pull_vaccination_data(odk_server_url, form_id, username, password)



def get_all_grids():
    return frappe.db.get_all("Grid", fields=["name", "title"])

