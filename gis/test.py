import frappe
import random
from frappe import _
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
    FROM `tabVaccination`
    WHERE name = '02pv3hi7p3'
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
        building = frappe.get_doc("Building", "1 - 1422 Independence Avenue")
        # building = frappe.get_doc("Building", "2 - The street wey I belong")
        # Update the geolocation field
        print(building.geolocation)
        
        building.geolocation = None
        
        #Set the geolocation field in the required GeoJSON format
        building.geolocation = json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [7.475866, 9.042452]  # Longitude first, then Latitude
                    }
                }
            ]
        })
        
        # Save the changes
        # building.save()
        
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




@frappe.whitelist()
def save_vaccination(**kwargs):
    import random

    proj = kwargs.get("project", "")
    img_name = f"vaccination_card-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"

    try:
        # Save the health card image
        take_a_picture_of_the_health_card = save_image(frappe.request, 'take_a_picture_of_the_health_card', img_name)
    except Exception as e:
        return {
            "status": 400,
            "message": "Please attach a .jpg or .png image of your health card to the 'take a picture of the health card' field.",
            "error": str(e)
        }

    record_name = kwargs.get("name")  # Check if 'name' is provided for updating an existing record

    try:
        if record_name:
            # Fetch the existing record for updating
            vaccination = frappe.get_doc("Vaccination", record_name)
        else:
            # Create a new record if 'name' is not provided
            vaccination = frappe.get_doc({
                "doctype": "Vaccination",
                "project": kwargs.get("project"),
            })

        # Update fields for both new and existing records
        vaccination.update({
            "first_name": kwargs.get("first_name"),
            "middle_name": kwargs.get("middle_name"),
            "last_name": kwargs.get("last_name"),
            "date_of_birth": kwargs.get("date_of_birth"),
            "gender": kwargs.get("gender"),
            "care_givers_name": kwargs.get("care_givers_name"),
            "care_givers_phone_no": kwargs.get("care_givers_phone_no"),
            "household": kwargs.get("household"),
            "was_the_child_vaccinated_during_this_program": kwargs.get("was_the_child_vaccinated_during_this_program"),
            "vaccination_date": kwargs.get("vaccination_date"),
            "next_vaccination_date": kwargs.get("next_vaccination_date"),
            "vaccination_status": kwargs.get("vaccination_status"),
            "does_the_child_have_a_child_health_card": kwargs.get("does_the_child_have_a_child_health_card"),
            "did_you_administer_the_child_health_card": kwargs.get("did_you_administer_the_child_health_card"),
            "take_a_picture_of_the_health_card": take_a_picture_of_the_health_card,
            "why_were_health_cards_not_given": kwargs.get("why_were_health_cards_not_given"),
            "facility": kwargs.get("facility"),
            "geolocation": kwargs.get("geolocation"),
            "response_id": kwargs.get("response_id"),
            "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
            "grid": kwargs.get("grid"),
            "start_time": kwargs.get("start_time"),
            "end_time": kwargs.get("end_time"),
            "response_geolocation": kwargs.get("response_geolocation"),
            "status": kwargs.get("status", "Submitted"),
        })


    # # Populate child table with `last_vaccines_administered` values
        if "last_vaccines_administered" in kwargs:
            vaccination.last_vaccines_administered = []  # Clear existing entries
            last_vaccines_administered = kwargs["last_vaccines_administered"]

            # Ensure last_vaccines_administered is a string before processing
            if isinstance(last_vaccines_administered, str):
                # Parse the string into a list of vaccines
                vaccines = [v.strip() for v in last_vaccines_administered.strip("[]").split(",") if v.strip()]

                if vaccines:  # Only append rows if there are valid entries
                    for vaccine in vaccines:
                        vaccination.append("last_vaccines_administered", {"vaccine": vaccine})
                else:
                    # Skip appending to the child table if no valid vaccines are provided
                    # frappe.msgprint("No vaccines provided to save in the child table.", alert=True)
                    pass
            else:
                frappe.throw("The last_vaccines_administered field must be a properly formatted string in the format [IPV 2, MEN A, Measles 2, PENTA 1].")


        # Save the record
        vaccination.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "message": "Vaccination record saved successfully.",
            "status": 200,
            "data": vaccination
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Vaccination Save Error")
        return {
            "message": "An error occurred while saving the Vaccination record.",
            "status": 400,
            "error": str(e)
        }
    

@frappe.whitelist()
def save_vaccination_summary(**kwargs):
    record_name = kwargs.get("name")  # Check if a record ID is provided for updating

    try:
        if record_name:
            # Fetch the existing record
            vaccination_summary = frappe.get_doc("Vaccination Summary", record_name)

            # Update fields
            vaccination_summary.update({
                "hep_b_received_in_doses": kwargs["hep_b_received_in_doses"],
                "hep_b_used_in_doses": kwargs["hep_b_used_in_doses"],
                "hep_b_returned_in_doses": kwargs["hep_b_returned_in_doses"],
                "opv_received_in_doses": kwargs["opv_received_in_doses"],
                "opv_used_in_doses": kwargs["opv_used_in_doses"],
                "opv_returned_in_doses": kwargs["opv_returned_in_doses"],
                "penta_received_in_doses": kwargs["penta_received_in_doses"],
                "penta_used_in_doses": kwargs["penta_used_in_doses"],
                "penta_returned_in_doses": kwargs["penta_returned_in_doses"],
                "pcv_received_in_doses": kwargs["pcv_received_in_doses"],
                "pcv_used_in_doses": kwargs["pcv_used_in_doses"],
                "pcv_returned_in_doses": kwargs["pcv_returned_in_doses"],
                "ipv_received_in_doses": kwargs["ipv_received_in_doses"],
                "ipv_used_in_doses": kwargs["ipv_used_in_doses"],
                "ipv_returned_in_doses": kwargs["ipv_returned_in_doses"],
                "bcg_received_in_doses": kwargs["bcg_received_in_doses"],
                "bcg_used_in_doses": kwargs["bcg_used_in_doses"],
                "bcg_returned_in_doses": kwargs["bcg_returned_in_doses"],
                "rota_received_in_doses": kwargs["rota_received_in_doses"],
                "rota_used_in_doses": kwargs["rota_used_in_doses"],
                "rota_returned_in_doses": kwargs["rota_returned_in_doses"],
                "vit_a_received_in_doses": kwargs["vit_a_received_in_doses"],
                "vit_a_used_in_doses": kwargs["vit_a_used_in_doses"],
                "vit_a_returned_in_doses": kwargs["vit_a_returned_in_doses"],
                "measles_received_in_doses": kwargs["measles_received_in_doses"],
                "measles_used_in_doses": kwargs["measles_used_in_doses"],
                "measles_returned_in_doses": kwargs["measles_returned_in_doses"],
                "yellow_fever_received_in_doses": kwargs["yellow_fever_received_in_doses"],
                "yellow_fever_used_in_doses": kwargs["yellow_fever_used_in_doses"],
                "yellow_fever_returned_in_doses": kwargs["yellow_fever_returned_in_doses"],
                "has_the_team_recorded_aefi_cases_today": kwargs["has_the_team_recorded_aefi_cases_today"],
                "how_many_recorded_serious_aefi_cases_recorded": kwargs.get("how_many_recorded_serious_aefi_cases_recorded"),
                "how_many_recorded_nonserious_aefi_cases_recorded": kwargs.get("how_many_recorded_nonserious_aefi_cases_recorded"),
                "did_you_face_any_challenge": kwargs["did_you_face_any_challenge"],
                "please_state_the_challenges_faced": kwargs.get("please_state_the_challenges_faced"),
                "did_you_receive_any_supervisor_today": kwargs["did_you_receive_any_supervisor_today"],
                "what_is_the_name_of_the_supervisor": kwargs.get("what_is_the_name_of_the_supervisor"),
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "project": kwargs["project"],
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"]
            })
        else:
            # Create a new record if 'name' is not provided
            vaccination_summary = frappe.get_doc({
                "doctype": "Vaccination Summary",
                "hep_b_received_in_doses": kwargs["hep_b_received_in_doses"],
                "hep_b_used_in_doses": kwargs["hep_b_used_in_doses"],
                "hep_b_returned_in_doses": kwargs["hep_b_returned_in_doses"],
                "opv_received_in_doses": kwargs["opv_received_in_doses"],
                "opv_used_in_doses": kwargs["opv_used_in_doses"],
                "opv_returned_in_doses": kwargs["opv_returned_in_doses"],
                "penta_received_in_doses": kwargs["penta_received_in_doses"],
                "penta_used_in_doses": kwargs["penta_used_in_doses"],
                "penta_returned_in_doses": kwargs["penta_returned_in_doses"],
                "pcv_received_in_doses": kwargs["pcv_received_in_doses"],
                "pcv_used_in_doses": kwargs["pcv_used_in_doses"],
                "pcv_returned_in_doses": kwargs["pcv_returned_in_doses"],
                "ipv_received_in_doses": kwargs["ipv_received_in_doses"],
                "ipv_used_in_doses": kwargs["ipv_used_in_doses"],
                "ipv_returned_in_doses": kwargs["ipv_returned_in_doses"],
                "bcg_received_in_doses": kwargs["bcg_received_in_doses"],
                "bcg_used_in_doses": kwargs["bcg_used_in_doses"],
                "bcg_returned_in_doses": kwargs["bcg_returned_in_doses"],
                "rota_received_in_doses": kwargs["rota_received_in_doses"],
                "rota_used_in_doses": kwargs["rota_used_in_doses"],
                "rota_returned_in_doses": kwargs["rota_returned_in_doses"],
                "vit_a_received_in_doses": kwargs["vit_a_received_in_doses"],
                "vit_a_used_in_doses": kwargs["vit_a_used_in_doses"],
                "vit_a_returned_in_doses": kwargs["vit_a_returned_in_doses"],
                "measles_received_in_doses": kwargs["measles_received_in_doses"],
                "measles_used_in_doses": kwargs["measles_used_in_doses"],
                "measles_returned_in_doses": kwargs["measles_returned_in_doses"],
                "yellow_fever_received_in_doses": kwargs["yellow_fever_received_in_doses"],
                "yellow_fever_used_in_doses": kwargs["yellow_fever_used_in_doses"],
                "yellow_fever_returned_in_doses": kwargs["yellow_fever_returned_in_doses"],
                "has_the_team_recorded_aefi_cases_today": kwargs["has_the_team_recorded_aefi_cases_today"],
                "how_many_recorded_serious_aefi_cases_recorded": kwargs.get("how_many_recorded_serious_aefi_cases_recorded"),
                "how_many_recorded_nonserious_aefi_cases_recorded": kwargs.get("how_many_recorded_nonserious_aefi_cases_recorded"),
                "did_you_face_any_challenge": kwargs["did_you_face_any_challenge"],
                "please_state_the_challenges_faced": kwargs.get("please_state_the_challenges_faced"),
                "did_you_receive_any_supervisor_today": kwargs["did_you_receive_any_supervisor_today"],
                "what_is_the_name_of_the_supervisor": kwargs.get("what_is_the_name_of_the_supervisor"),
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "project": kwargs["project"],
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"]
            })
        import json

        # # Handle `serious_aefi_table` as a child table
        if "serious_aefi_table" in kwargs:
            vaccination_summary.serious_aefi_table = []  # Clear existing entries by default
            serious_aefi_table = kwargs["serious_aefi_table"]

            if isinstance(serious_aefi_table, list):
                # Process directly if it's already a list
                for serious_aefi in serious_aefi_table:
                    serious_aefi = serious_aefi.strip()  # Ensure no trailing spaces
                    if serious_aefi:  # Only add non-empty serious_aefis
                        vaccination_summary.append("serious_aefi", {"serious_aefi": serious_aefi})

            elif isinstance(serious_aefi_table, str):
                try:
                    # Parse the string into a list using `json.loads`
                    serious_aefis = json.loads(serious_aefi_table)
                    if isinstance(serious_aefis, list):
                        for serious_aefi in serious_aefis:
                            serious_aefi = serious_aefi.strip()  # Ensure no trailing spaces
                            if serious_aefi:  # Only add non-empty serious_aefis
                                vaccination_summary.append("serious_aefi_table", {"serious_aefi": serious_aefi})
                    else:
                        frappe.throw("The serious_aefi_table field must contain a valid list of serious_aefis.")
                except json.JSONDecodeError:
                    frappe.throw("The serious_aefi_table field must be a JSON array in the format [\"Paralysis\", \"Anaphylactic Shock\", \"Neck Stiffness\"].")
            else:
                frappe.throw("The serious_aefi_table field must be a list or a JSON string in the format [\"Paralysis\", \"Anaphylactic Shock\", \"Neck Stiffness\"].")

        import json

        # # Handle `non_serious_aefi_table` as a child table
        if "non_serious_aefi_table" in kwargs:
            vaccination_summary.non_serious_aefi_table = []  # Clear existing entries by default
            non_serious_aefi_table = kwargs["non_serious_aefi_table"]

            if isinstance(non_serious_aefi_table, list):
                # Process directly if it's already a list
                for non_serious_aefi in non_serious_aefi_table:
                    non_serious_aefi = non_serious_aefi.strip()  # Ensure no trailing spaces
                    if non_serious_aefi:  # Only add non-empty serious_aefis
                        vaccination_summary.append("non_serious_aefi", {"non_serious_aefi": non_serious_aefi})

            elif isinstance(non_serious_aefi_table, str):
                try:
                    # Parse the string into a list using `json.loads`
                    non_serious_aefis = json.loads(non_serious_aefi_table)
                    if isinstance(non_serious_aefis, list):
                        for non_serious_aefi in non_serious_aefis:
                            non_serious_aefi = non_serious_aefi.strip()  # Ensure no trailing spaces
                            if non_serious_aefi:  # Only add non-empty serious_aefis
                                vaccination_summary.append("non_serious_aefi_table", {"non_serious_aefi": non_serious_aefi})
                    else:
                        frappe.throw("The non_serious_aefi_table field must contain a valid list of serious_aefis.")
                except json.JSONDecodeError:
                    frappe.throw("The non_serious_aefi_table field must be a JSON array in the format [\"Fever\", \"Crying\"].")
            else:
                frappe.throw("The non_serious_aefi_table field must be a list or a JSON string in the format [\"Fever\", \"Crying\"].")



        # Save the record
        vaccination_summary.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Vaccination summary record saved successfully.",
            "status": 200
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Vaccination Summary Save Error")
        return {
            "message": "An error occurred while saving the Vaccination summary record, ensure that you are passing all required fields.",
            "status": 400,
            "error": str(e)
        }

