
import requests
import frappe
import datetime
import re
import json
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
        fields=["name", "full_name", "date_of_birth", "gender", "ward"]
    )
    
    for vaccination in vaccinations:
        children_records = frappe.get_all(
            "Children", 
            filters={
                "status": "Approved", 
                "date_of_birth": vaccination["date_of_birth"], 
                "gender": vaccination["gender"], 
                "ward": vaccination["ward"]
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

            

def update_approved_records():
    approved_vaccinations = frappe.get_all("Vaccination", {"status": "Approved"}, ["name"])
    for vaccination in approved_vaccinations:
        doc = frappe.get_doc("Vaccination", vaccination.name)
        doc.status = "Approved"
        doc.save()
    frappe.db.commit()

    approved_children = frappe.get_all("Children", {"status": "Approved"}, ["name"])
    for child in approved_children:
        doc = frappe.get_doc("Children", child.name)
        doc.status = "Approved"
        doc.save()
    frappe.db.commit()


def update_building_vaccination_status():
    """
    Updates the vaccination status of all buildings where status is 'Approved'
    based on the vaccination status of children and vaccinations.
    """

    # Fetch all approved buildings
    approved_buildings = frappe.get_all(
        "Building",
        filters={"status": "Approved"},
        fields=["name"]
    )

    for building in approved_buildings:
        building_name = building["name"]

        # Fetch all approved children in the building
        children_in_the_building = frappe.get_all(
            "Children",
            filters={"status": "Approved", "building": building_name},
            fields=["name", "vaccination_status"]
        )

        # Count total children and their vaccinated status
        total_children = len(children_in_the_building)
        children_vaccination_status = sum(
            1 for child in children_in_the_building
            if child["vaccination_status"] in ["Vaccinated to Age", "Fully Vaccinated (Measles 2)"]
        )

        # Fetch all approved vaccinations in the building (not linked to children)
        vaccinations_in_the_building = frappe.get_all(
            "Vaccination",
            filters={"status": "Approved", "building": building_name, "children": ""},
            fields=["name", "vaccination_status"]
        )

        # Count total vaccinations and vaccinated status
        total_vaccinations = len(vaccinations_in_the_building)
        vaccination_status = sum(
            1 for vaccination in vaccinations_in_the_building
            if vaccination["vaccination_status"] in ["Vaccinated to Age", "Fully Vaccinated (Measles 2)"]
        )

        # Calculate the combined percentage
        combined_percentage = round(
            ((children_vaccination_status + vaccination_status) / (total_children + total_vaccinations)) * 100
        ) if (total_children + total_vaccinations) > 0 else 0

        # Update the building record
        frappe.db.set_value("Building", building_name, "percentage_of_vaccinated_children", combined_percentage)

    frappe.db.commit()
def set_enumerated_vaccination_status():
    """
    Maintains the original vaccination status of Children.
    """

    # Fetch all children with a null enumerated vaccination status
    children = frappe.db.sql(
        """
        SELECT name, vaccination_status, enumerated_vaccination_status
        FROM `tabChildren`
        WHERE enumerated_vaccination_status IS Null
        """
    )

    for child in children:
        enumerated_vaccination_status = child[1]
        child_name = child[0]
        # Update the enumerated vaccination status
        frappe.db.set_value("Children", child_name, "enumerated_vaccination_status", enumerated_vaccination_status)
    frappe.db.commit()

def create_missing_facility_buildings():
    facilities = frappe.get_all("Facility", filters={"selected_facility": 1}, fields=["name", "facility_name", "ward", "longitude", "latitude"])

    for facility in facilities:
        # Check if buildings exist for the facility
        building_count = frappe.db.count("Building", filters={"health_facility": facility.name})
        if building_count > 0:
            continue  # Facility already has buildings

        # Check for matching settlements
        settlements = frappe.get_all(
            "Settlement",
            filters={
                "name_of_nearest_facility_to_settlement": facility.name,
                "ward": facility.ward,
                "status": "Approved"
            },
            fields=["name"],
            limit=1
        )

        if not settlements:
            continue  # No matching settlement, skip this facility

        for settlement in settlements:
            building = frappe.new_doc("Building")
            building.building_number = "001"
            building.building_address = facility.facility_name
            building.street_name = facility.name.replace("-", ", ")
            building.describe_the_building = facility.facility_name
            building.building_type = "Non-residential"
            building.establishment_type = "Health Facility"
            building.health_facility = facility.name
            building.settlement = settlement.name
            building.status = "Approved"
            building.project = "STRICAN - Phase 2"
            building.longitude = facility.longitude
            building.latitude = facility.latitude

            # Create GeoJSON Point
            building.geolocation = json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [facility.longitude, facility.latitude]
                    }
                }]
            })

            building.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Created Building for Facility: {facility.name} in Settlement: {settlement.name}")




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
                            vaccination.care_givers_name = f"{care_givers_firstname} {care_givers_surname}"
                            vaccination.care_givers_phone_no = care_givers_phone_no
                            vaccination.care_givers_date_of_birth = care_givers_date_of_birth
                            vaccination.last_name = last_name
                            vaccination.first_name = first_name
                            vaccination.full_name = f"{first_name} {last_name}"
                            vaccination.date_of_birth = date_of_birth
                            vaccination.gender = gender
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
    # odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*&$top=5000"
    odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*"
    form_id = "Vaccination%20Team%20Tool"
    username = frappe.get_site_config().get("odk_username")
    password = frappe.get_site_config().get("odk_password")

    return pull_vaccination_data(odk_server_url, form_id, username, password)

