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
def update_building_geolocation():
    try:
        # Fetch the Building record with the specified name
        # building = frappe.get_doc("Settlement", "Sunshine Homes")
        building = frappe.get_doc("Settlement", "Supervisor Training")
        # Update the geolocation field
        # print(building.response_geolocation)
        # print(building.geolocation)
        # print(building.geolocation_kyow)
        
        # building.response_geolocation = None
        # building.geolocation = None
        
       
        # building.geolocation = building.response_geolocation 

        #Set the geolocation field in the required GeoJSON format
        # building.geolocation = json.dumps({
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
                        # "coordinates": [7.476275, 8.97323]  # Longitude first, then Latitude (Sunsine Homes)
                        "coordinates": [6.553486, 9.591894]  # Longitude first, then Latitude (Haske Hotel, Niger)
                        # "coordinates": [7.4951, 9.0579]  # Longitude first, then Latitude (Asokoro)
                        # "coordinates": [6.1532668192084, 8.99168425242635]  # Longitude first, then Latitude (Alukusu)

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
import re


@frappe.whitelist()
def fetch_odk_data():
    # print("Function fetch_odk_data_program is executed.")

    mapping_dict = {
        #Facilities
        "PHC (B) \nAlukusu": "Alukusu Primary Health Center-Sidisaba-Katcha",
        "BHC Katcha": "BHC Katcha-Katcha-Katcha-Niger",
        "PHC Babangona": "PHC Babangona-Tegina West-Rafi-Niger",
        "Alala PHCC": "Alala PHCC-Tunga Wawa-Kontagora-Niger",
        "PHC Gabi": "PHC Gabi-Dzwafu-Katcha-Niger",
        "Mabono PHC": "Mabono PHC-Gulbiboka-Mariga-Niger",
        "Comprehensive health centre Beri": "Comprehensive health centre Beri-Beri-Mariga-Niger",
        "PHC \nMantuntun": "PHC  Mantuntun-Bisanti-Katcha-Niger",
        "Kanpanin Waya PHCC": "Kanpanin Waya PHCC-Usalle-Kontagora-Niger",
        "Kawo Model PHCC": "Kawo Model PHCC-Kawo-Kontagora-Niger",
        "Madangyen PHCC": "Madangyen PHCC-Tunga Wawa-Kontagora-Niger",
        "BHC Mariga": "BHC Mariga-Inkwai-Mariga-Niger",
        "PHCC Kwana": "Kwana Health Center-Tegina West-Rafi",
        "PHC Sabo mariga": "PHC Sabo mariga-Tegina West-Rafi-Niger",
        "Madangyn PHC": "Madangyn PHC-Tunga Wawa-Kontagora-Niger",
        "Tunga Wawa PHCC": "Tunga Wawa PHCC-Tunga Wawa-Kontagora-Niger",
        "Gulbinboka PHC": "Gulbinboka PHC-Gulbiboka-Mariga-Niger",
        "MCH Pandogori": "PHCC  pandogori-Kongoma Central-Rafi-Niger",
        "PHC Gimi": "PHC Gimi-Tegina Central-Rafi-Niger",
        "Masaha PHCC": "Masaha PHCC-Madara-Kontagora-Niger",
        "PHC Shadadi": "PHC Shadadi-Bangi-Mariga-Niger",
        "MCH Bangi": "MCH Bangi-Bangi-Mariga-Niger",
        "Tukura Primary Health Centre": "Tukura Primary Health Centre-Arewa-Kontagora-Niger",
        "Kaswan garba PHC": "Kaswan garba PHC-Igwama-Mariga-Niger",
        "Nasarawa PHCC": "Nasarawa PHCC-Kudu-Kontagora-Niger",
        "PHC Mayaki Legbodza": "PHC MAYAKI LEGBOZHA TIFIN-Essa-Katcha-Niger",
        "Ishanga PHC": "Ishanga PHC-Kakihum-Mariga-Niger",
        "RIJINYAN NGWAMATSE PHCC": "RIJINYAN NGWAMATSE PHCC-Ngwamatse-Kontagora-Niger",
        "PHCC Tegina": "PHCC Tegina-Tegina Central-Rafi-Niger",
        "PHCC  pandogori": "PHCC  pandogori-Kongoma Central-Rafi-Niger",
        "PHC Kakihum": "PHC Kakihum-Kakihum-Mariga-Niger",
        "Kampanin Bobi PHC": "Kampanin Bobi PHC-Bobi-Mariga-Niger",
        "PHC Matari": "PHC Matari-Bobi-Mariga-Niger",
        "Essa PHC": "PHC MAYAKI LEGBOZHA TIFIN-Essa-Katcha-Niger",

        #Settlements
        "ALUKUSU B": "Alukusu B",
        "NDALADA": "Ndalada",
        "UNG. AUDU": "Ung Audu",
        "CECEKO": "CECEKO",
        "GABI": "Gabi",
        "DZANGBODO": "Dzangbodo",
        "EMITSOWA": "Emitsowa",
        "ALUKUSU B": "Alukusu B",
        "MANTUTUN": "Mantuntun",
        "AMINA WOYE": "Amina Woye",
        "TUKURA B": "Tukura B",
        "RIGASA": "Rigasa",
        "ROAD SAFETY AREA": "Road safety Area",
        "KANWURI": "Kanwuri",
        "Masaha": "Masaha",
        "RIJINYAN NGWAMATSE ": "Rijinyan Ngwamatse",
        "UNG. AUDU": "Ung Audu",
        "UNG. SULE A": "Ung Sule A",
        "Unguwan usman": "Usman A",
        "TSANGAYA": "Tsangaya",
        "UNG. SARKIN TASHA": "Ung Sarkin Tasha",
        "TUNGA NA UKU": "Tunga Na Uku",
        "UNG. YANGA": "Ung Yanga",
        "bakin kasuwa": "Bakin Kasuwa",
        "MAGANDU SABO": "Magandu Sabo",
        "UNGUWAN ALHAJI DANLAMI": "Unguwan Alhaji Danlami",
        "UNG UKATA": "Ung Ukata",
        "UNGUWAN GALADIMA": "UNGUWAN GALADIMA",
        "MAGAMA": "Magama",
        "GANGARE": "Gangare",
        

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

                        odk_child_id = data.get("__id", "")
                        print ("ODK Child ID:", odk_child_id)

                        care_givers_surname = data.get("surName_of_the_caregiver", "")
                        if care_givers_surname == None:
                            care_givers_surname = "N/A"
                        care_givers_surname = re.sub(r'[^a-zA-Z0-9]', '', care_givers_surname)
                        print ("Caregiver's Surname:", care_givers_surname)
                        care_givers_firstname = data.get("FirstName_of_the_caregiver", "")
                        if care_givers_firstname == None:
                            care_givers_firstname = "N/A"
                        care_givers_firstname = re.sub(r'[^a-zA-Z0-9]', '', care_givers_firstname)
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
                        if last_name == None:
                            last_name = "N/A"
                        last_name = re.sub(r'[^a-zA-Z0-9]', '', last_name)
                        print ("Last Name:", last_name)
                        first_name = data.get("firstName_of_the_child", "")
                        if first_name == None:
                            first_name = "N/A"
                        first_name = re.sub(r'[^a-zA-Z0-9]', '', first_name)
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
                        
                        
                        # Load the list of specific odk_child_id to skip from a file
                        skip_file_path = "/home/frappe/frappe-bench/apps/gis/gis/skip_odk_child_ids.txt"
                        with open(skip_file_path, "r") as file:
                            skip_odk_child_ids = [line.strip() for line in file.readlines()]

                        parent_id_skip_file_path = "/home/frappe/frappe-bench/apps/gis/gis/skip_odk_parent_ids.txt"
                        with open(parent_id_skip_file_path, "r") as file:
                            skip_odk_parent_ids = [line.strip() for line in file.readlines()]

                        # Check if a record with the same odk_child_id already exists
                        existing_record = frappe.db.exists("Vaccination", {"odk_child_id": odk_child_id})
                        if existing_record or odk_child_id in skip_odk_child_ids or odk_parent_id in skip_odk_parent_ids:
                            print(f"Record with odk_child_id {odk_child_id} already exists or is in the skip list. Skipping...")
                            continue
                        try:
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
                            building_record = frappe.db.get_all("Building", {"health_facility": facility}, ["name"], limit=1)
                            vaccination.building = building_record[0].name if building_record else None
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
                            vaccination.full_name = f"{first_name} {last_name}"
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
                        except Exception as e:
                            print(f"Error: {e}, settlement: {settlement}, facility: {facility}, id: {odk_child_id}")
                            frappe.log_error(f"Error: {e}, {odk_child_id}")
                            
                            # Write the odk_child_id to the skip file
                            with open(skip_file_path, "a") as file:
                                file.write(f"{odk_child_id}\n")
                            
                            # return "Error: " + str(e)
                            pass
                            

                        
                    

                

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
    odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*&$top=5000"
    form_id = "Vaccination%20Team%20Tool"
    username = frappe.get_site_config().get("odk_username")
    password = frappe.get_site_config().get("odk_password")

    return pull_vaccination_data(odk_server_url, form_id, username, password)


def update_building_geolocation_from_health_facility(doc, method):
    if doc.health_facility:
        health_facility = frappe.get_doc("Facility", doc.health_facility)
        try:
            # Parse the health facility geolocation JSON
            facility_geolocation = json.loads(health_facility.geolocation)
            coordinates = facility_geolocation.get("geometry", {}).get("coordinates", [])
            
            if coordinates and len(coordinates) == 2:
                try:
                    # Ensure that both longitude and latitude are floats
                    lon = float(coordinates[0])
                    lat = float(coordinates[1])
                except ValueError:
                    frappe.log_error("Coordinates conversion error: {}".format(coordinates), 
                                       "Geolocation Update Error")
                    return

                # Create the GeoJSON FeatureCollection with numeric values
                formatted_geolocation = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [lon, lat]  # Longitude first, then Latitude
                            }
                        }
                    ]
                }
                
                # Save the formatted geolocation to the building document
                doc.geolocation = json.dumps(formatted_geolocation)
                doc.response_geolocation = json.dumps(formatted_geolocation)
        except json.JSONDecodeError:
            frappe.log_error("Invalid JSON format in health facility geolocation", 
                               "Geolocation Update Error")

@frappe.whitelist()
def grid_settlements(grid_id):
    user = frappe.session.user

    grid_settlement = frappe.db.sql(
        """
        SELECT 
            g.name AS grid_id, 
            g.location AS grid_location, 
            g.geolocation_kyow AS grid_geolocation, 
            st.name, 
            st.type_of_settlement, 
            st.ward AS ward, 
            st.local_government_area, 
            st.state, 
            st.country
        FROM `tabGrid` g 
        JOIN `tabSettlement` st 
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(st.facility_geolocation)
             )
        WHERE g.name = %s AND st.status = 'Approved'
        """,
        grid_id,
        as_dict=True
    )

    unapproved_owner_settlement = frappe.db.sql(
        """
        SELECT 
            g.name AS grid_id, 
            g.location AS grid_location, 
            g.geolocation_kyow AS grid_geolocation, 
            st.name, 
            st.type_of_settlement, 
            st.ward AS ward, 
            st.local_government_area, 
            st.state, 
            st.country
        FROM `tabGrid` g 
        JOIN `tabSettlement` st 
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(st.facility_geolocation)
             )
        WHERE g.name = %s AND st.status IN ('Returned', 'Submitted') AND st.owner = %s
        """,
        (grid_id, user),
        as_dict=True
    )


    settlement = unapproved_owner_settlement + grid_settlement

    return set_res(settlement=settlement)



@frappe.whitelist()
def grid_buildings(grid_id):
    bldngs = frappe.db.sql(
        """
        SELECT 
            g.name as grid_id, 
            g.location as grid_location, 
            g.geolocation_kyow as grid_geolocation, 
            b.name, 
            b.building_number, 
            b.building_address,
            b.settlement, 
            b.ward, 
            b.local_government_area, 
            b.state, 
            b.country 
        FROM `tabGrid` g
        JOIN `tabBuilding` b
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(b.geolocation)
             ) 
        WHERE g.name = %s AND b.status = 'Approved'
        """,
        (grid_id,),
        as_dict=True
    )

    unapproved_owner_buildings = frappe.db.sql(
        """
        SELECT 
            g.name as grid_id, 
            g.location as grid_location, 
            g.geolocation_kyow as grid_geolocation, 
            b.name, 
            b.building_number, 
            b.building_address,
            b.settlement, 
            b.ward, 
            b.local_government_area, 
            b.state, 
            b.country 
        FROM `tabGrid` g
        JOIN `tabBuilding` b
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(b.geolocation)
             ) 
        WHERE g.name = %s AND b.status IN ('Returned', 'Submitted') AND b.owner = %s
        """,
        (grid_id, frappe.session.user),
        as_dict=True
    )

    bldngs = unapproved_owner_buildings + bldngs

    return set_res(buildings=bldngs)


@frappe.whitelist()
def grid_households(grid_id):
    households = frappe.db.sql(
        """
        SELECT 
            g.name as grid_id,
            hs.settlement as settlement,  
            hs.phone_number as phone_number, 
            hs.name_of_household_head as name_of_household_head, 
            hs.building as building, 
            hs.ward as ward, 
            hs.name as name 
        FROM `tabGrid` g
        JOIN `tabHousehold` hs
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(hs.geolocation)
             ) 
        WHERE g.name = %s AND hs.status = 'Approved'
        """,
        (grid_id,),
        as_dict=True
    )

    unapproved_owner_households = frappe.db.sql(
        """
        SELECT 
            g.name as grid_id,
            hs.settlement as settlement,  
            hs.phone_number as phone_number, 
            hs.name_of_household_head as name_of_household_head, 
            hs.building as building, 
            hs.ward as ward, 
            hs.name as name 
        FROM `tabGrid` g
        JOIN `tabHousehold` hs
          ON ST_Contains(
                ST_GeomFromGeoJSON(g.geolocation_kyow),
                ST_GeomFromGeoJSON(hs.geolocation)
             ) 
        WHERE g.name = %s AND hs.status IN ('Returned', 'Submitted') AND hs.owner = %s
        """,
        (grid_id, frappe.session.user),
        as_dict=True
    )

    households = unapproved_owner_households + households

    return set_res(households=households)

import frappe
from difflib import SequenceMatcher

def find_best_match(vaccination, children_records):
    """Find the best matching Children record based on full_name similarity."""
    best_match = None
    highest_ratio = 0
    
    for child in children_records:
        match_ratio = SequenceMatcher(None, vaccination.full_name, child.full_name).ratio()
        if match_ratio > highest_ratio:
            highest_ratio = match_ratio
            best_match = child
    
    return best_match

def has_sufficient_name_match(vaccination_name, child_name):
    """Check if there is a sufficient match between the names by comparing word occurrences."""
    vaccination_words = set(vaccination_name.lower().split())
    child_words = set(child_name.lower().split())
    common_words = vaccination_words.intersection(child_words)

    return len(common_words) >= 2  # Adjust threshold as needed

def match_vaccination_to_children():
    """Matches Vaccination records with Children records based on given criteria."""
    vaccinations = frappe.get_all(
        "Vaccination", 
        filters={"status": "Approved", "children": ("is", "not set")},
        fields=["name", "full_name", "date_of_birth", "gender", "settlement"]
    )
    
    for vaccination in vaccinations:
        children_records = frappe.get_all(
            "Children", 
            filters={
                "status": "Approved", 
                "date_of_birth": vaccination["date_of_birth"], 
                "gender": vaccination["gender"], 
                "settlement": vaccination["settlement"]
            },
            fields=["name", "full_name"]
        )
        
        # Filter based on name similarity using word matching
        matching_children = [child for child in children_records if has_sufficient_name_match(vaccination["full_name"], child["full_name"])]
        
        if not matching_children:
            continue
        
        best_match = find_best_match(vaccination, matching_children)
        
        if best_match:
            frappe.db.set_value("Vaccination", vaccination["name"], "children", best_match["name"])
            frappe.db.commit()
