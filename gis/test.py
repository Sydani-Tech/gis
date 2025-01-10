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
def test_fields():
  fields = frappe.db.sql(f""" 
    SELECT *
    FROM `tabUser Permission`
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
  proj = kwargs ['project']

  img_name = f"vaccination_card-{proj.replace(' ', '-')}-{random.randint(1001, 9999)}.jpg"
#   img2_name = f"{b_num}-{proj.replace(' ', '-')}-{random.randint(1001, 9999)}.jpg"

  take_a_picture_of_the_health_card = save_image(frappe.request, 'take_a_picture_of_the_health_card', img_name)
#   building_picture_2 = save_image(frappe.request, 'building_picture_2', img2_name)

  vaccination = frappe.get_doc({
    "doctype": "Vaccination",
    "first_name": kwargs["first_name"],
    "middle_name": kwargs.get("middle_name"),
    "last_name": kwargs.get("last_name"),    
    "date_of_birth": kwargs["date_of_birth"],
    "gender": kwargs["gender"],
    "care_givers_name": kwargs["care_givers_name"],
    "care_givers_phone_no": kwargs["care_givers_phone_no"],
    "household": kwargs["household"],
    "next_vaccination_date": kwargs["next_vaccination_date"],
    "vaccination_status": kwargs["vaccination_status"],
    "does_the_child_have_a_child_health_card": kwargs["does_the_child_have_a_child_health_card"],
    "did_you_administer_the_child_health_card": kwargs.get("did_you_administer_the_child_health_card"),
    "take_a_picture_of_the_health_card": kwargs.get("take_a_picture_of_the_health_card"),
    "why_were_health_cards_not_given": kwargs.get("why_were_health_cards_not_given"),
    "facility": kwargs["facility"],
    "geolocation": kwargs.get("geolocation"),
    "response_id": kwargs["response_id"],
    "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
    "project": kwargs["project"],
    "grid": kwargs["grid"],
    # "start_time": kwargs["start_time"],
    # "end_time": kwargs["end_time"],
    "response_geolocation": kwargs.get("response_geolocation"),
    "take_a_picture_of_the_health_card": take_a_picture_of_the_health_card,
   
  })

  try:
    vaccination.save(ignore_permissions=True);
    set_res(data=vaccination)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})



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
    






import frappe
from frappe.utils import get_datetime

def update_children_vaccination(doc, method):
    """
    Before Save hook for Vaccination Doctype:
    - If status is 'Approved', check existing records and update related Children record.
    """
    if doc.status != "Approved":
        return

    # Fetch all Vaccination records for the same child with status Approved
    approved_vaccinations = frappe.get_all(
        "Vaccination",
        filters={"status": "Approved", "children": doc.children},
        fields=["name", "vaccination_date"]
    )

    if not approved_vaccinations:
        # No other approved records; update from Children record
        child_record = frappe.get_doc("Children", doc.children)
        doc.vaccination_date = child_record.last_vaccination_date
        doc.vaccination_status = child_record.vaccination_status
    else:
        # Compare vaccination dates to determine the latest
        current_vaccination_date = get_datetime(doc.vaccination_date)
        latest_vaccination_date = max(
            get_datetime(v["vaccination_date"]) for v in approved_vaccinations
        )

        # Update Children record if the current record is the latest
        if current_vaccination_date > latest_vaccination_date:
            child_record = frappe.get_doc("Children", doc.children)
            child_record.last_vaccination_date = doc.vaccination_date
            child_record.vaccination_status = doc.vaccination_status
            child_record.save()



@frappe.whitelist()
def save_vaccination(**kwargs):
    # Check if 'name' (record ID) is provided for updating an existing record
    record_name = kwargs.get("name")
    proj = kwargs["project"]
    
    # Handle optional image upload
    take_a_picture_of_the_health_card = None
    if frappe.request and 'take_a_picture_of_the_health_card' in frappe.request.files:
        img_name = f"vaccination_card-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"
        take_a_picture_of_the_health_card = save_image(frappe.request, 'take_a_picture_of_the_health_card', img_name)
    
    try:
        # If 'name' is provided, fetch the existing record
        if record_name:
            vaccination = frappe.get_doc("Vaccination", record_name)
            
            # Update fields
            vaccination.update({
                "first_name": kwargs["first_name"],
                "middle_name": kwargs.get("middle_name"),
                "last_name": kwargs.get("last_name"),
                "date_of_birth": kwargs["date_of_birth"],
                "gender": kwargs["gender"],
                "care_givers_name": kwargs["care_givers_name"],
                "care_givers_phone_no": kwargs["care_givers_phone_no"],
                "household": kwargs["household"],
                "vaccination_date": kwargs["vaccination_date"],
                "next_vaccination_date": kwargs["next_vaccination_date"],
                "vaccination_status": kwargs["vaccination_status"],
                "does_the_child_have_a_child_health_card": kwargs["does_the_child_have_a_child_health_card"],
                "did_you_administer_the_child_health_card": kwargs.get("did_you_administer_the_child_health_card"),
                "why_were_health_cards_not_given": kwargs.get("why_were_health_cards_not_given"),
                "facility": kwargs["facility"],
                "geolocation": kwargs.get("geolocation"),
                "response_id": kwargs["response_id"],
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
                "status": kwargs.get("status", "Submitted"),
            })
            # Only update image if provided
            if take_a_picture_of_the_health_card:
                vaccination.take_a_picture_of_the_health_card = take_a_picture_of_the_health_card
        else:
            # Create a new record if 'name' is not provided
            vaccination = frappe.get_doc({
                "doctype": "Vaccination",
                "first_name": kwargs["first_name"],
                "middle_name": kwargs.get("middle_name"),
                "last_name": kwargs.get("last_name"),
                "date_of_birth": kwargs["date_of_birth"],
                "gender": kwargs["gender"],
                "care_givers_name": kwargs["care_givers_name"],
                "care_givers_phone_no": kwargs["care_givers_phone_no"],
                "household": kwargs["household"],
                "vaccination_date": kwargs["vaccination_date"],
                "next_vaccination_date": kwargs["next_vaccination_date"],
                "vaccination_status": kwargs["vaccination_status"],
                "does_the_child_have_a_child_health_card": kwargs["does_the_child_have_a_child_health_card"],
                "did_you_administer_the_child_health_card": kwargs.get("did_you_administer_the_child_health_card"),
                "take_a_picture_of_the_health_card": take_a_picture_of_the_health_card,
                "why_were_health_cards_not_given": kwargs.get("why_were_health_cards_not_given"),
                "facility": kwargs["facility"],
                "geolocation": kwargs.get("geolocation"),
                "response_id": kwargs["response_id"],
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
                "status": kwargs.get("status", "Submitted"),
            })
        
        # Save the record
        vaccination.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Vaccination record saved successfully.",
            "status": 200
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Vaccination Save Error")
        return {
            "message": "An error occurred while saving the Vaccination record, ensure that you are passing all required fields.",
            "status": 400,
            "error": str(e)
        }


@frappe.whitelist()
def save_household(**kwargs):
    record_name = kwargs.get("name")  # Check if a record ID is provided for updating

    try:
        if record_name:
            # Fetch the existing record
            household = frappe.get_doc("Household", record_name)

            # Update fields
            household.update({
                "name_of_household_head": kwargs["name_of_household_head"],
                "gender_of_household_head": kwargs["gender_of_household_head"],
                "date_of_birth_of_household_head": kwargs["date_of_birth_of_household_head"],
                "phone_number": kwargs["phone_number"],
                "educational_level_of_household_head": kwargs["educational_level_of_household_head"],
                "is_the_household_head_employed": kwargs["is_the_household_head_employed"],
                "industry_of_employment": kwargs.get("industry_of_employment"),
                "average_monthly_income": kwargs.get("average_monthly_income"),
                "is_the_household_residing_in_a_rented_apartment": kwargs["is_the_household_residing_in_a_rented_apartment"],
                "how_many_household_members_are_above_18": kwargs["how_many_household_members_are_above_18"],
                "how_many_household_members_are_between_15_and_18_years": kwargs["how_many_household_members_are_between_15_and_18_years"],
                "how_many_household_members_are_between_9_and_14_years": kwargs["how_many_household_members_are_between_9_and_14_years"],
                "how_many_household_members_are_between_5_and_8_years": kwargs["how_many_household_members_are_between_5_and_8_years"],
                "how_many_household_members_are_below_5": kwargs["how_many_household_members_are_below_5"],
                "most_common_illness_within_the_last_year": kwargs["most_common_illness_within_the_last_year"],
                "if_others_specify": kwargs.get("if_others_specify"),
                "what_is_the_nearest_facility": kwargs["what_is_the_nearest_facility"],
                "how_far_is_the_nearest_facility": kwargs["how_far_is_the_nearest_facility"],
                "do_you_take_your_childchildren_to_the_facility_for_ri_services": kwargs["do_you_take_your_childchildren_to_the_facility_for_ri_services"],
                "please_state_why": kwargs.get("please_state_why"),
                "geolocation": kwargs["geolocation"],
                "building": kwargs["building"],
                "comment_to_supervisor": kwargs["comment_to_supervisor"],
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
            household = frappe.get_doc({
                "doctype": "Household",
                "name_of_household_head": kwargs["name_of_household_head"],
                "gender_of_household_head": kwargs["gender_of_household_head"],
                "date_of_birth_of_household_head": kwargs["date_of_birth_of_household_head"],
                "phone_number": kwargs["phone_number"],
                "educational_level_of_household_head": kwargs["educational_level_of_household_head"],
                "is_the_household_head_employed": kwargs["is_the_household_head_employed"],
                "industry_of_employment": kwargs.get("industry_of_employment"),
                "average_monthly_income": kwargs.get("average_monthly_income"),
                "is_the_household_residing_in_a_rented_apartment": kwargs["is_the_household_residing_in_a_rented_apartment"],
                "how_many_household_members_are_above_18": kwargs["how_many_household_members_are_above_18"],
                "how_many_household_members_are_between_15_and_18_years": kwargs["how_many_household_members_are_between_15_and_18_years"],
                "how_many_household_members_are_between_9_and_14_years": kwargs["how_many_household_members_are_between_9_and_14_years"],
                "how_many_household_members_are_between_5_and_8_years": kwargs["how_many_household_members_are_between_5_and_8_years"],
                "how_many_household_members_are_below_5": kwargs["how_many_household_members_are_below_5"],
                "most_common_illness_within_the_last_year": kwargs["most_common_illness_within_the_last_year"],
                "if_others_specify": kwargs.get("if_others_specify"),
                "what_is_the_nearest_facility": kwargs["what_is_the_nearest_facility"],
                "how_far_is_the_nearest_facility": kwargs["how_far_is_the_nearest_facility"],
                "do_you_take_your_childchildren_to_the_facility_for_ri_services": kwargs["do_you_take_your_childchildren_to_the_facility_for_ri_services"],
                "please_state_why": kwargs.get("please_state_why"),
                "geolocation": kwargs["geolocation"],
                "building": kwargs["building"],
                "comment_to_supervisor": kwargs["comment_to_supervisor"],
                "project": kwargs["project"],
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"]
            })
        
        # Save the record
        household.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Household record saved successfully.",
            "status": 200
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Household Save Error")
        return {
            "message": "An error occurred while saving the Household record, ensure that you are passing all required fields.",
            "status": 400,
            "error": str(e)
        }

@frappe.whitelist()
def save_children(**kwargs):
    record_name = kwargs.get("name")  # Check if 'name' (record ID) is provided for updating an existing record
    
    try:
        # If 'name' is provided, fetch the existing record
        if record_name:
            children = frappe.get_doc("Children", record_name)
            
            # Update fields
            children.update({
                "household": kwargs["household"],
                "first_name": kwargs["first_name"],
                "middle_name": kwargs.get("middle_name"),
                "last_name": kwargs["last_name"],
                "date_of_birth": kwargs["date_of_birth"],
                "gender": kwargs["gender"],
                "vaccination_status": kwargs["vaccination_status"],
                "last_vaccine_administered": kwargs["last_vaccine_administered"],
                "geolocation": kwargs["geolocation"],
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
            })
        else:
            # Create a new record if 'name' is not provided
            children = frappe.get_doc({
                "doctype": "Children",
                "household": kwargs["household"],
                "first_name": kwargs["first_name"],
                "middle_name": kwargs.get("middle_name"),
                "last_name": kwargs["last_name"],
                "date_of_birth": kwargs["date_of_birth"],
                "gender": kwargs["gender"],
                "vaccination_status": kwargs["vaccination_status"],
                "last_vaccine_administered": kwargs["last_vaccine_administered"],
                "geolocation": kwargs["geolocation"],
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
            })
        
        # Save the record
        children.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Children record saved successfully.",
            "status": 200
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Children Save Error")
        return {
            "message": "An error occurred while saving the Children record, ensure that you are passing all required fields.",
            "status": 400,
            "error": str(e)
        }

@frappe.whitelist()
def save_building(**kwargs):
    record_name = kwargs.get("name")  # Check if 'name' (record ID) is provided for updating an existing record

    try:
        # Generate image names
        b_num = kwargs["building_number"]
        proj = kwargs["project"]
        img1_name = f"{b_num}-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"
        img2_name = f"{b_num}-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"

        building_picture = save_image(frappe.request, 'building_picture', img1_name)
        building_picture_2 = save_image(frappe.request, 'building_picture_2', img2_name)

        # If 'name' is provided, fetch the existing record for updating
        if record_name:
            building = frappe.get_doc("Building", record_name)
            building.update({
                "building_number": kwargs["building_number"],
                "building_type": kwargs["building_type"],
                "establishment_type": kwargs.get("establishment_type"),
                "health_facility": kwargs.get("health_facility"),
                "how_many_households_occupy_this_building": kwargs.get("how_many_households_occupy_this_building"),
                "building_address": kwargs["building_address"],
                "describe_the_building": kwargs["describe_the_building"],
                "street_name": kwargs["street_name"],
                "response_id": kwargs["response_id"],
                "settlement": kwargs["settlement"],
                "comments_to_supervisor": kwargs["comments_to_supervisor"],
                "project": kwargs["project"],
                "status": kwargs["status"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "building_picture": building_picture,
                "building_picture_2": building_picture_2,
                "response_geolocation": kwargs["response_geolocation"],
            })
        else:
            # Create a new record if 'name' is not provided
            building = frappe.get_doc({
                "doctype": "Building",
                "building_number": kwargs["building_number"],
                "building_type": kwargs["building_type"],
                "establishment_type": kwargs.get("establishment_type"),
                "health_facility": kwargs.get("health_facility"),
                "how_many_households_occupy_this_building": kwargs.get("how_many_households_occupy_this_building"),
                "building_address": kwargs["building_address"],
                "describe_the_building": kwargs["describe_the_building"],
                "street_name": kwargs["street_name"],
                "response_id": kwargs["response_id"],
                "settlement": kwargs["settlement"],
                "comments_to_supervisor": kwargs["comments_to_supervisor"],
                "project": kwargs["project"],
                "status": kwargs["status"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "building_picture": building_picture,
                "building_picture_2": building_picture_2,
                "response_geolocation": kwargs["response_geolocation"],
            })

        # Save the record
        building.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Building record saved successfully.",
            "status": 200,
            "data": building
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Building Save Error")
        return {
            "message": "An error occurred while saving the Building record. Ensure all required fields are provided.",
            "status": 400,
            "error": str(e)
        }

@frappe.whitelist()
def save_settlement(**kwargs):
    record_name = kwargs.get("name")  # Check if 'name' (record ID) is provided for updating an existing record

    try:
        # If 'name' is provided, fetch the existing record for updating
        if record_name:
            settlement = frappe.get_doc("Settlement", record_name)
            settlement.update({
                "name_of_settlement": kwargs["name_of_settlement"],
                "type_of_settlement": kwargs["type_of_settlement"],
                "archetype_for_rural": kwargs.get("archetype_for_rural"),
                "archetype_for_urban": kwargs.get("archetype_for_urban"),
                "name_of_settlementcommunity_head": kwargs["name_of_settlementcommunity_head"],
                "contact_of_settlementcommunity_head": kwargs["contact_of_settlementcommunity_head"],
                "name_of_disease_surveillance_community_informant": kwargs["name_of_disease_surveillance_community_informant"],
                "names_of_other_influential_members_within_settlement": kwargs["names_of_other_influential_members_within_settlement"],
                "name_of_nearest_facility_to_settlement": kwargs["name_of_nearest_facility_to_settlement"],
                "is_there_a_vdc": kwargs["is_there_a_vdc"],
                "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"],
                "ward": kwargs["ward"],
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
            })
        else:
            # Create a new record if 'name' is not provided
            settlement = frappe.get_doc({
                "doctype": "Settlement",
                "name_of_settlement": kwargs["name_of_settlement"],
                "type_of_settlement": kwargs["type_of_settlement"],
                "archetype_for_rural": kwargs.get("archetype_for_rural"),
                "archetype_for_urban": kwargs.get("archetype_for_urban"),
                "name_of_settlementcommunity_head": kwargs["name_of_settlementcommunity_head"],
                "contact_of_settlementcommunity_head": kwargs["contact_of_settlementcommunity_head"],
                "name_of_disease_surveillance_community_informant": kwargs["name_of_disease_surveillance_community_informant"],
                "names_of_other_influential_members_within_settlement": kwargs["names_of_other_influential_members_within_settlement"],
                "name_of_nearest_facility_to_settlement": kwargs["name_of_nearest_facility_to_settlement"],
                "is_there_a_vdc": kwargs["is_there_a_vdc"],
                "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"],
                "ward": kwargs["ward"],
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
            })

        # Save the record
        settlement.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "message": "Settlement record saved successfully.",
            "status": 200,
            "data": settlement
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Settlement Save Error")
        return {
            "message": "An error occurred while saving the Settlement record. Ensure all required fields are provided.",
            "status": 400,
            "error": str(e)
        }
