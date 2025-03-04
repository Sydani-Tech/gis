
import frappe
from frappe.utils import get_datetime, getdate, today, date_diff
import json

# def update_vaccinations_administered_on_children_record(doc, method):
#     """
#     Updates the last vaccination date, status, and vaccine child table in the Children record
#     when a Vaccination record is approved.
#     """
#     if doc.status != "Approved" or not doc.children:
#         # frappe.msgprint("Vaccination status is not approved or children field is missing.")
#         return
    
#     # frappe.msgprint(f"Processing Vaccination for child: {doc.children}, Status: {doc.status}")
    
#     approved_vaccinations = frappe.get_all(
#         "Vaccination",
#         filters={
#             "status": "Approved",
#             "children": doc.children
#         },
#         fields=["name", "vaccination_date"]
#     )
    
#     # frappe.msgprint(f"Approved Vaccinations: {approved_vaccinations}")
    
#     child_record = frappe.get_doc("Children", doc.children)
#     current_vaccination_date = get_datetime(doc.vaccination_date)
    
#     if len(approved_vaccinations) == 1 or current_vaccination_date >= max(
#         get_datetime(v["vaccination_date"]) for v in approved_vaccinations
#     ):
#         # frappe.msgprint("Updating Children record with latest vaccination data.")
#         child_record.last_vaccination_date = doc.vaccination_date
        
#         existing_vaccines = {vaccine.vaccine for vaccine in child_record.get("last_vaccine_administered")}

#         if not existing_vaccines:
#             child_record.append("last_vaccine_administered", {
#                 "vaccine": vaccine.vaccine,
#                 })
#             # frappe.msgprint(f"Added vaccine: {vaccine.vaccine} to child record {child_record.name}")

#         else:
#             for vaccine in doc.get("last_vaccines_administered"):
#                 if vaccine.vaccine not in existing_vaccines:
#                     child_record.append("last_vaccine_administered", {
#                         "vaccine": vaccine.vaccine,
#                     })
#                     frappe.msgprint(f"Added vaccine: {vaccine.vaccine} to child record {child_record.name}")
        
#         child_record.save()
#         frappe.msgprint(f"Updated Children record: {child_record.name}")


def update_vaccinations_administered_on_children_record(doc, method):
    """
    Updates the last vaccination date, status, and vaccine child table in the Children record
    when a Vaccination record is approved.
    """
    if doc.status != "Approved" or not doc.children:
        return

    approved_vaccinations = frappe.get_all(
        "Vaccination",
        filters={"status": "Approved", "children": doc.children},
        fields=["name", "vaccination_date"]
    )

    child_record = frappe.get_doc("Children", doc.children)
    current_vaccination_date = get_datetime(doc.vaccination_date)

    if len(approved_vaccinations) == 1 or current_vaccination_date >= max(
        get_datetime(v["vaccination_date"]) for v in approved_vaccinations
    ):
        child_record.last_vaccination_date = doc.vaccination_date
        child_record.next_vaccination_date = doc.next_vaccination_date

        existing_vaccines = {vaccine.vaccine for vaccine in child_record.get("last_vaccine_administered", [])}

        if doc.get("last_vaccines_administered"):  # Check if the child table is not empty
            for vaccine in doc.get("last_vaccines_administered"):
                if vaccine.vaccine and vaccine.vaccine not in existing_vaccines:
                    child_record.append("last_vaccine_administered", {
                        "vaccine": vaccine.vaccine,
                    })
                    frappe.msgprint(f"Added vaccine: {vaccine.vaccine} to child record {child_record.name}")

        child_record.save()
        frappe.msgprint(f"Updated Children record: {child_record.name}")



def process_vaccination_status_and_next_vaccination(doc, method):
    # Initialize a list to store vaccine records
    vaccine_records = []

    # Iterate through the child table `last_vaccines_administered`
    for vaccine_entry in doc.get("last_vaccines_administered", []):
        if vaccine_entry.get("vaccine"):
            # Append the value of `vaccine` to the list
            vaccine_records.append(vaccine_entry.get("vaccine"))

    # Print vaccine records for debugging
    frappe.msgprint(f"Vaccine Records: {vaccine_records}")

    # Format the list into a string in the required format
    doc.vaccines_taken = "[" + ", ".join(vaccine_records) + "]"

    # Calculate the age in weeks
    date_of_birth = frappe.utils.getdate(doc.date_of_birth)
    current_date = frappe.utils.getdate(frappe.utils.today())
    age_in_days = frappe.utils.date_diff(current_date, date_of_birth)
    age_in_weeks = age_in_days // 7

    # Print age for debugging
    frappe.msgprint(f"Age in Weeks: {age_in_weeks}")

    # Set vaccination_status based on conditions
    if not vaccine_records:
        doc.vaccination_status = "Never Vaccinated"
    elif (
        ("PENTA 1" not in vaccine_records and 
         "PENTA 2" not in vaccine_records and 
         "PENTA 3" not in vaccine_records) and age_in_weeks > 6
    ):
        doc.vaccination_status = "Zero Dose"
    elif (
        (age_in_weeks >= 10 and ("PENTA 2" not in vaccine_records and "PENTA 3" not in vaccine_records)) or
        (age_in_weeks >= 14 and "PENTA 3" not in vaccine_records) or
        (age_in_weeks >= 36 and "VIT A" not in vaccine_records) or
        (age_in_weeks >= 48 and "Measles 1" not in vaccine_records) or
        (age_in_weeks >= 60 and "Measles 2" not in vaccine_records)
    ):
        doc.vaccination_status = "Under Immunized"
    elif (
        (age_in_weeks >= 3 and age_in_weeks <= 6 and "BCG" in vaccine_records) or
        (age_in_weeks >= 6 and age_in_weeks <= 10 and "PENTA 1" in vaccine_records) or
        (age_in_weeks >= 10 and age_in_weeks <= 14 and "PENTA 2" in vaccine_records) or
        (age_in_weeks >= 14 and age_in_weeks <= 36 and "PENTA 3" in vaccine_records) or
        (age_in_weeks >= 36 and age_in_weeks <= 48 and "VIT A" in vaccine_records) or
        (age_in_weeks >= 48 and age_in_weeks <= 60 and "Measles 1" in vaccine_records)
    ):
        doc.vaccination_status = "Vaccinated to Age"
    elif age_in_weeks > 60 and "Measles 2" in vaccine_records:
        doc.vaccination_status = "Fully Vaccinated (Measles 2)"

    # Determine the next vaccination date based on administered vaccines
    vaccination_date = frappe.utils.getdate(doc.vaccination_date)
    frappe.msgprint(f"Vaccination Date: {vaccination_date}")

    if set(vaccine_records).issubset({"BCG", "HEP B0", "OPV 0"}):
        doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 42)  # 6 weeks
        
    elif (
        "PENTA 1" in vaccine_records or "ROTA 1" in vaccine_records or "PCV 1" in vaccine_records or 
        "OPV 1" in vaccine_records or "IPV 1" in vaccine_records
    ):
        if not (
            "PENTA 2" in vaccine_records or "ROTA 2" in vaccine_records or "PCV 2" in vaccine_records or 
            "OPV 2" in vaccine_records or "PENTA 3" in vaccine_records or "ROTA 3" in vaccine_records or 
            "PCV 3" in vaccine_records or "OPV 3" in vaccine_records or "IPV 2" in vaccine_records or 
            "VIT A" in vaccine_records or "Measles 1" in vaccine_records or "Yellow Fever" in vaccine_records or 
            "Men A" in vaccine_records or "Measles 2" in vaccine_records
        ):
            doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 28)  # 4 weeks
    elif (
        "PENTA 2" in vaccine_records or "ROTA 2" in vaccine_records or "PCV 2" in vaccine_records or "OPV 2" in vaccine_records
    ):
        if not (
            "PENTA 3" in vaccine_records or "ROTA 3" in vaccine_records or "PCV 3" in vaccine_records or 
            "OPV 3" in vaccine_records or "IPV 2" in vaccine_records or "VIT A" in vaccine_records or 
            "Measles 1" in vaccine_records or "Yellow Fever" in vaccine_records or "Men A" in vaccine_records or 
            "Measles 2" in vaccine_records
        ):
            doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 28)  # 4 weeks
    elif (
        "PENTA 3" in vaccine_records or "ROTA 3" in vaccine_records or "PCV 3" in vaccine_records or "OPV 3" in vaccine_records or "IPV 2" in vaccine_records
    ):
        if not (
            "VIT A" in vaccine_records or "Men A" in vaccine_records or 
            "Measles 1" in vaccine_records or "Yellow Fever" in vaccine_records or "Measles 2" in vaccine_records
        ):
            doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 154)  # 22 weeks
    elif "VIT A" in vaccine_records:
        if not (
            "Men A" in vaccine_records or "Measles 1" in vaccine_records or 
            "Yellow Fever" in vaccine_records or "Measles 2" in vaccine_records
        ):
            doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 84)  # 12 weeks
    elif (
        "Measles 1" in vaccine_records or "Yellow Fever" in vaccine_records or "MEN A" in vaccine_records
    ):
        if not (
            "Measles 2" in vaccine_records
        ):
            doc.next_vaccination_date = frappe.utils.add_days(vaccination_date, 84)  # 12 weeks
    elif "Measles 2" in vaccine_records:
        doc.next_vaccination_date = None


def autoset_ward(doc, method):
    # frappe.msgprint(f"Processing Ward for Vaccination: {doc.name}")
    # Check if response_geolocation is empty or invalid
    response_geolocation = doc.get('response_geolocation')
    # frappe.msgprint(f"Response Geolocation: {response_geolocation}")
    if response_geolocation and response_geolocation.strip():
        ward = frappe.db.sql(f"""
            SELECT ward, name, local_government_area, state, country, geolocation FROM `tabWard` WHERE ST_Contains(
                ST_GeomFromGeoJSON(geolocation),
                ST_GeomFromGeoJSON('{response_geolocation}')
            )
            LIMIT 1
        """, as_dict=True)

        if ward:
            doc.ward = ward[0]['name']
            doc.local_government_area = ward[0]['local_government_area']
            doc.state = ward[0]['state']
            doc.country = ward[0]['country']
            # frappe.msgprint(f"Assigned Ward: {ward[0]['name']}")
            # frappe.msgprint(f"Assigned Ward: {ward[0]['local_government_area']}")
            # frappe.msgprint(f"Assigned Ward: {ward[0]['state']}")
            # frappe.msgprint(f"Assigned Ward: {ward[0]['country']}")
            

def autoset_nearest_facility(doc, method):
    """
    Finds the nearest facility within 5 km.
    """
    response_geolocation = doc.get('response_geolocation')

    # Debug: Check if response_geolocation is present
    if response_geolocation is None or (isinstance(response_geolocation, str) and not response_geolocation.strip()):
        frappe.msgprint("No valid response_geolocation provided, skipping ward and facility assignment.")
        return

    frappe.msgprint(f"Processing geolocation: {response_geolocation}")

    try:
        # Fetch the nearest facility within 5000000 meters (5000 km)
        facility = frappe.db.sql(f"""
            SELECT facility_name, name, geolocation, 
                   ST_Distance_Sphere(
                       ST_GeomFromGeoJSON(geolocation),
                       ST_GeomFromGeoJSON(
                           JSON_EXTRACT(
                               JSON_EXTRACT('{response_geolocation}', '$.features[0].geometry'),
                               '$'
                           )
                       )
                   ) as distance
            FROM `tabFacility`
            WHERE ST_Distance_Sphere(
                      ST_GeomFromGeoJSON(geolocation),
                      ST_GeomFromGeoJSON(
                          JSON_EXTRACT(
                              JSON_EXTRACT('{response_geolocation}', '$.features[0].geometry'),
                              '$'
                          )
                      )
                  ) <= 5000000
            ORDER BY distance ASC
            LIMIT 1
        """, as_dict=True)

        if facility:
            nearest_facility = facility[0]['name']
            distance_km = round(facility[0]['distance'] / 1000, 3)  # Convert meters to kilometers
            
            doc.name_of_nearest_facility_to_settlement = nearest_facility
            doc.distance_from_settlement_to_facility = distance_km

            frappe.msgprint(f"Nearest Facility: {nearest_facility}, Distance: {distance_km} km")
        else:
            frappe.msgprint("No facility found within 5000 km.")

    except Exception as e:
        frappe.msgprint(f"Error in assigning facility: {str(e)}", indicator="red")



def autoset_nearest_facility_household(doc, method):
    """
    Finds the nearest facility within 5000 km.
    """
    response_geolocation = doc.get('response_geolocation')

    # Debug: Check if response_geolocation is present
    if response_geolocation is None or (isinstance(response_geolocation, str) and not response_geolocation.strip()):
        frappe.msgprint("No valid response_geolocation provided, skipping ward and facility assignment.")
        return

    frappe.msgprint(f"Processing geolocation: {response_geolocation}")

    try:
        # Fetch the nearest facility within 5000000 meters (5000 km)
        facility = frappe.db.sql(f"""
            SELECT facility_name, name, geolocation, 
                   ST_Distance_Sphere(
                       ST_GeomFromGeoJSON(geolocation),
                       ST_GeomFromGeoJSON(
                           JSON_EXTRACT(
                               JSON_EXTRACT('{response_geolocation}', '$.features[0].geometry'),
                               '$'
                           )
                       )
                   ) as distance
            FROM `tabFacility`
            WHERE ST_Distance_Sphere(
                      ST_GeomFromGeoJSON(geolocation),
                      ST_GeomFromGeoJSON(
                          JSON_EXTRACT(
                              JSON_EXTRACT('{response_geolocation}', '$.features[0].geometry'),
                              '$'
                          )
                      )
                  ) <= 5000000
            ORDER BY distance ASC
            LIMIT 1
        """, as_dict=True)

        if facility:
            nearest_facility = facility[0]['name']
            distance_km = round(facility[0]['distance'] / 1000, 3)  # Convert meters to kilometers
            
            doc.what_is_the_nearest_facility = nearest_facility
            doc.exact_distance_in_km = distance_km

            if distance_km < 2:
                doc.how_far_is_the_nearest_facility = "< 2KM"
            elif 2 <= distance_km <= 5:
                doc.how_far_is_the_nearest_facility = "2 - 5KM"
            else:
                doc.how_far_is_the_nearest_facility = "> 5KM"

            frappe.msgprint(f"Nearest Facility: {nearest_facility}, Distance: {distance_km} km")
        else:
            frappe.msgprint("No facility found within 5000 km.")

    except Exception as e:
        frappe.msgprint(f"Error in assigning facility: {str(e)}", indicator="red")





def update_child_vaccination_status(doc, method):
    """
    Updates the vaccination status of a child based on administered vaccines and age.
    """
    vaccine_records = []
    
    # Iterate through the child table `last_vaccine_administered`
    for vaccine_entry in doc.get("last_vaccine_administered", []):
        if vaccine_entry.get("vaccine"):
            # Append the value of `vaccine` to the list
            vaccine_records.append(vaccine_entry.get("vaccine"))
    
    # Print vaccine records for debugging
    # frappe.msgprint(f"Vaccine Records: {vaccine_records}")
    
    # Format the list into a string in the required format
    doc.vaccines_taken = "[" + ", ".join(vaccine_records) + "]"
    
    # Calculate the age in weeks
    date_of_birth = getdate(doc.date_of_birth)
    current_date = getdate(today())
    age_in_days = date_diff(current_date, date_of_birth)
    age_in_weeks = age_in_days // 7
    
    # Print age for debugging
    # frappe.msgprint(f"Age in Weeks: {age_in_weeks}")
    
    # Set vaccination_status based on conditions
    if not vaccine_records:
        # If no vaccines have been administered
        doc.vaccination_status = "Never Vaccinated"
    
    elif (
        ("PENTA 1" not in vaccine_records and 
         "PENTA 2" not in vaccine_records and 
         "PENTA 3" not in vaccine_records) and age_in_weeks > 6
    ):
        doc.vaccination_status = "Zero Dose"
    
    elif (
        (age_in_weeks >= 10 and ("PENTA 2" not in vaccine_records and "PENTA 3" not in vaccine_records)) or
        (age_in_weeks >= 14 and "PENTA 3" not in vaccine_records) or
        (age_in_weeks >= 36 and "VIT A" not in vaccine_records) or
        (age_in_weeks >= 48 and "Measles 1" not in vaccine_records) or
        (age_in_weeks >= 60 and "Measles 2" not in vaccine_records)
    ):
        # If missing age-appropriate vaccines for "Under Immunized" conditions
        doc.vaccination_status = "Under Immunized"
    
    elif (
        (age_in_weeks >= 3 and age_in_weeks <= 6 and "BCG" in vaccine_records) or
        (age_in_weeks >= 6 and age_in_weeks <= 10 and "PENTA 1" in vaccine_records) or
        (age_in_weeks >= 10 and age_in_weeks <= 14 and "PENTA 2" in vaccine_records) or
        (age_in_weeks >= 14 and age_in_weeks <= 36 and "PENTA 3" in vaccine_records) or
        (age_in_weeks >= 36 and age_in_weeks <= 48 and "VIT A" in vaccine_records) or
        (age_in_weeks >= 48 and age_in_weeks <= 60 and "Measles 1" in vaccine_records)
    ):
        # If age-appropriate vaccines have been administered for "Vaccinated to Age" conditions
        doc.vaccination_status = "Vaccinated to Age"
    
    elif age_in_weeks > 60 and "Measles 2" in vaccine_records:
        # If Measles 2 is administered after 60 weeks
        doc.vaccination_status = "Fully Vaccinated (Measles 2)"
    
    # Print final vaccination status
    # frappe.msgprint(f"Updated Vaccination Status: {doc.vaccination_status}")

#Full name of children in the children and vaccination doctype   
def update_full_name(doc, method):
    previous_doc = doc.get_doc_before_save()
    
    # Check if previous_doc exists before accessing its attributes
    if previous_doc and (
        previous_doc.first_name != doc.first_name or
        previous_doc.middle_name != doc.middle_name or
        previous_doc.last_name != doc.last_name
    ):
        first_name = doc.first_name or ""
        middle_name = doc.middle_name or ""
        last_name = doc.last_name or ""

        if middle_name:
            doc.full_name = f"{first_name} {middle_name} {last_name}"
        else:
            doc.full_name = f"{first_name} {last_name}"

#Full name of caregivers in the vaccination doctype   
def update_full_name_care_givers(doc, method):
    previous_doc = doc.get_doc_before_save()
    frappe.msgprint(f"Previous Doc:")
    # Check if previous_doc exists before accessing its attributes
    if previous_doc and (
        previous_doc.care_givers_firstname != doc.care_givers_firstname or
        previous_doc.care_givers_surname != doc.care_givers_surname
    ):
        care_givers_firstname = doc.care_givers_firstname or ""
        care_givers_surname = doc.care_givers_surname or ""
            
        doc.care_givers_name = f"{care_givers_firstname} {care_givers_surname}"

def update_settlement_field(doc, method):
    if not doc.settlement:
        doc.settlement = doc.name_of_settlement
        frappe.msgprint(f"Updated settlement field: {doc.settlement}")

    if doc.settlement != doc.name_of_settlement:
        doc.settlement = doc.name_of_settlement
        frappe.msgprint(f"Updated settlement field: {doc.settlement}")


def update_household_member_count(doc, method):
    """
    Updates the total number of people living in the household if any of the household member age groups change.
    """
    previous_doc = doc.get_doc_before_save()

    # Ensure the previous document state exists before comparison
    if previous_doc and (
        previous_doc.how_many_household_members_are_above_18 != doc.how_many_household_members_are_above_18 or
        previous_doc.how_many_household_members_are_between_15_and_18_years != doc.how_many_household_members_are_between_15_and_18_years or
        previous_doc.how_many_household_members_are_between_9_and_14_years != doc.how_many_household_members_are_between_9_and_14_years or
        previous_doc.how_many_household_members_are_between_5_and_8_years != doc.how_many_household_members_are_between_5_and_8_years or
        previous_doc.how_many_household_members_are_below_5 != doc.how_many_household_members_are_below_5
    ):
        # Calculate total household members
        doc.how_many_people_live_in_the_household = (
            int(doc.how_many_household_members_are_above_18 or 0) +
            int(doc.how_many_household_members_are_between_15_and_18_years or 0) +
            int(doc.how_many_household_members_are_between_9_and_14_years or 0) +
            int(doc.how_many_household_members_are_between_5_and_8_years or 0) +
            int(doc.how_many_household_members_are_below_5 or 0)
        )

        frappe.msgprint(f"Updated total household members: {doc.how_many_people_live_in_the_household}")


def update_building_vaccination_status(doc, method):
    """
    Updates the vaccination status of a building based on the vaccination status of vaccinations and children.
    """

    if doc.status == "Approved" and doc.building:
        # Fetch all children in the same building with status Approved
        children_in_the_building = frappe.get_all(
            "Children",
            filters={
                "status": "Approved",
                "building": doc.building
            },
            fields=["name", "vaccination_status"]
        )

        # Count total children and their vaccinated status
        total_children = len(children_in_the_building)
        children_vaccination_status = sum(1 for child in children_in_the_building 
                                if child["vaccination_status"] in ["Vaccinated to Age", "Fully Vaccinated (Measles 2)"])


        # Fetch all vaccinations in the same building with status Approved
        vaccinations_in_the_building = frappe.get_all(
            "Vaccination",
            filters={
                "status": "Approved",
                "building": doc.building,
                "children": ""
            },
            fields=["name", "vaccination_status"]
        )

        # Count total vaccinations and vaccinated status
        total_vaccinations = len(vaccinations_in_the_building)
        vaccination_status = sum(1 for vaccination in vaccinations_in_the_building 
                                    if vaccination["vaccination_status"] in ["Vaccinated to Age", "Fully Vaccinated (Measles 2)"])
        

        # Calculate the combined percentage
        combined_percentage = round(((children_vaccination_status + vaccination_status) / (total_children + total_vaccinations)) * 100) if (total_children + total_vaccinations) > 0 else 0


        # Update the percentage in the building record
        building_record = frappe.get_doc("Building", doc.building)
        building_record.percentage_of_vaccinated_children = combined_percentage
        building_record.save()
        # frappe.msgprint(f"Total Children: {total_children}, Vaccinated Children: {children_vaccination_status}")
        # frappe.msgprint(f"Total Vaccinations: {total_vaccinations}, Vaccinated Vaccinations: {vaccination_status}")
        # frappe.msgprint(f"Updated Building {doc.building} with percentage: {combined_percentage}%")




def set_geolocation_of_grids(doc, method):
    """
    Fetches the geolocation from the referenced doctype and sets it 
    to the 'geolocation_kyow' field in the 'Grid' doctype.
    """
    # frappe.msgprint(f"Fetching geolocation for {doc.location} from {doc.location_type}")
    if not doc.location_type or not doc.location:
        frappe.throw("Both 'Location Type' and 'Location' fields are required.")
        return  # Exit if required fields are missing

    # Fetch geolocation from the referenced doctype
    try:
        location_doc = frappe.get_doc(doc.location_type, doc.location)
        if hasattr(location_doc, "geolocation"):
            doc.geolocation_kyow = location_doc.geolocation
            # frappe.msgprint(f"Geolocation set for {doc.location} from {doc.location_type}")
        else:
            frappe.throw(f"Geolocation field not found in {doc.location_type}")

    except frappe.DoesNotExistError:
        frappe.throw(f"{doc.location_type} '{doc.location}' does not exist.")
    except Exception as e:
        frappe.throw(f"Error fetching geolocation: {str(e)}")



def validate_facilities_in_buildings(doc, method):
    """
    Prevents multiple buildings from having the same facility in the 'Grid' doctype.
    """
    frappe.msgprint(f"Validating facility in building: {doc.name}")
    if not doc.health_facility:
        return  # Skip validation if facility is not set

    # Check if another record exists with the same facility but a different name
    existing = frappe.db.exists("Building", {"health_facility": doc.health_facility, "name": ["!=", doc.name]})

    if existing:
        frappe.throw(f"A record with facility '{doc.health_facility}' already exists. Each facility must be unique.")



@frappe.whitelist()
def format_geolocation(longitude, latitude):
    """
    Converts longitude and latitude into Frappe's GeoJSON Point format.
    """
    if not longitude or not latitude:
        frappe.throw("Longitude and Latitude are required.")

    try:
        
        geolocation = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                       
                        "coordinates": [longitude, latitude]  # Longitude first, then Latitude

                    }
                }
            ]
        })


        return geolocation
    except ValueError:
        frappe.throw("Invalid longitude or latitude format.")



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
