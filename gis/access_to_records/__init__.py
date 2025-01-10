import frappe
from frappe import _
import requests
import json
import random

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource, save_image
)

def get_team(user):
  filt = {'user': user}

  project_team = frappe.db.sql(f""" 
    SELECT * FROM `tabProject Team` WHERE user = %(user)s AND enabled = 1
  """, filt, as_dict=True)
  if project_team:
    return project_team[0]
  
  return None

def get_fields(parent):
  filt = {'name': parent}
  fields = frappe.db.sql(f""" 
    SELECT name, docstatus, parent, fieldname, 
    label, fieldtype, options, hidden, reqd, read_only, depends_on, permlevel,
    mandatory_depends_on, read_only_depends_on, `default`, idx 
    FROM tabDocField
    WHERE parent = %(name)s AND label != '' 
    ORDER BY idx ASC 
    """,
    filt, as_dict=True)
  
  return fields  

@frappe.whitelist()
def projects():

  # Get the logged-in user
  user = frappe.session.user
  if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": "error"}

  team = get_team(user);
  if(team):
    filt = {'name': team.parent}
    project = frappe.db.sql(f""" 
      SELECT name, project, close_data_collection, enable_geofencing  
      FROM `tabProject` WHERE name = %(name)s ORDER BY idx ASC 
    """, filt, as_dict=True)
  else:
    project = []

  return set_res(projects=project)

@frappe.whitelist()
def forms(project):
  filt = {'project': project}
  project_form = frappe.db.sql(f""" 
    SELECT idx, document_type as form, parent as project 
    FROM `tabDoctype Table` WHERE parent = '{project}' ORDER BY idx ASC 
  """, filt, as_dict=True)

  for n in range(0, len(project_form)):
    form = project_form[n];
    form['fields'] = get_fields(form.form)
    project_form[n] = form

  return project_form


@frappe.whitelist()
def projects_for_dashboard_viewers():
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "Please login to access view the dashboard",
            "status": 401
        }

    # Fetch projects for the logged-in user
    users_projects = frappe.db.sql(
        """
        SELECT DISTINCT parent 
        FROM `tabAssignees` 
        WHERE user = %(user)s
        """,
        {"user": user},
        as_dict=True
    )

    # Filter projects that exist in the Project table
    project_names = [project.parent for project in users_projects]

    if project_names:
        valid_projects = frappe.db.sql(
            """
            SELECT name 
            FROM `tabProject` 
            WHERE name IN %(project_names)s
            """,
            {"project_names": tuple(project_names)},
            as_dict=True
        )

        if not valid_projects:
            return {
                "message": "The user has not been granted access to any projects, please contact the project manager.",
                "status": 404
            }

        valid_project_names = [project.name for project in valid_projects]

        return {
            "message": "Projects fetched successfully",
            "status": 200,
            "data": valid_project_names
        }

    return {
        "message": "The user has not been granted access to any projects, please contact the project manager.",
        "status": 404
    }

@frappe.whitelist()
def outreach_forms(project):
  filt = {'project': project}
  project_form = frappe.db.sql(f""" 
    SELECT idx, document_type as form, parent as project 
    FROM `tabOutreach Doctype Table` WHERE parent = '{project}' ORDER BY idx ASC 
  """, filt, as_dict=True)

  for n in range(0, len(project_form)):
    form = project_form[n];
    form['fields'] = get_fields(form.form)
    project_form[n] = form

  return project_form

@frappe.whitelist()
def grids():
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": 401
        }

    # Fetch grid assignees where user matches the logged-in user
    grid_record = frappe.db.sql(
        """
        SELECT DISTINCT parent 
        FROM `tabAssignees` 
        WHERE user = %(user)s
        """,
        {"user": user},
        as_dict=True
    )

    if not grid_record:
        return {
            "message": "User does not have an assigned grid, please contact a supervisor.",
            "status": 404
        }
    
    grids = frappe.db.sql(
        """
        SELECT * 
        FROM `tabGrid` 
        WHERE name = %(grid)s
        """,
        {"grid": grid_record[0].parent},
        as_dict=True
    )

    # # Extract parent values
    # parent_values = [record["parent"] for record in grid_records]

    # return {
    #     "status": 200,
    #     "data": {
    #         "assigned_projects": parent_values
    #     }
    # }


    # Extract the parent (Grid name)
    # grid_name = grid_record[0]["parent"]

    # Fetch the geolocation_kyow field value from the Grid doctype
    # geolocation = frappe.db.get_value("Grid", grid_name, "geolocation_kyow")

    # return {
    #     "status": 200,
    #     "data": {
    #         "assigned_grid": grid_name,
    #         "grid_geolocation": geolocation
    #     }
    # }

    # set_res(data=grids)
    set_res(data={'grids': grids, 'assignees': grid_record})





@frappe.whitelist()
def save_building(**kwargs):
  b_num = kwargs['building_number']
  b_type = kwargs['building_type']
  st_name = kwargs['settlement']
  proj = kwargs ['project']

  img1_name = f"{b_num}-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"
  img2_name = f"{b_num}-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"

  building_picture = save_image(frappe.request, 'building_picture', img1_name)
  building_picture_2 = save_image(frappe.request, 'building_picture_2', img2_name)

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
    # "geolocation": kwargs["geolocation"],
    "response_id": kwargs["response_id"],
    "settlement": kwargs["settlement"],
    "comments_to_supervisor": kwargs["comments_to_supervisor"],
    "project": kwargs["project"],
    "status": kwargs["status"],
    "grid": kwargs["grid"],
    "start_time": kwargs["start_time"],
    "end_time": kwargs["end_time"],
    # "response_geolocation": kwargs["response_geolocation"],
    "building_picture": building_picture,
    "building_picture_2": building_picture_2,
    "response_geolocation": kwargs["response_geolocation"]
  })

  try:
    building.save(ignore_permissions=True);
    set_res(data=building)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})

@frappe.whitelist()
def save_household(**kwargs):
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
    # "please_state_why": kwargs["please_state_why"],
    "please_state_why": kwargs.get("please_state_why"),
    # "are_there_children_below_the_age_of_5_years": kwargs["are_there_children_below_the_age_of_5_years"],
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

  try:
    household.save(ignore_permissions=True);
    set_res(data=household)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})

@frappe.whitelist()
def save_children(**kwargs):
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
    # "building": kwargs["building"],
    "geolocation": kwargs["geolocation"],
    "response_id": kwargs["response_id"],
    "status": kwargs["status"], 
    "project": kwargs["project"],
    "grid": kwargs["grid"],
    "start_time": kwargs["start_time"],
    "end_time": kwargs["end_time"],
    "project": kwargs["project"],
    "response_geolocation": kwargs["response_geolocation"]
  })

  try:
    children.save(ignore_permissions=True);
    set_res(data=children)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})


@frappe.whitelist()
def save_settlement(**kwargs):
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
    # "settlement_geolocation": kwargs["settlement_geolocation"],
    # "facility_geolocation": kwargs["facility_geolocation"],
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
    "response_geolocation": kwargs["response_geolocation"]
  })
  
  try:
    settlement.save(ignore_permissions=True);
    set_res(data=settlement)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})

@frappe.whitelist()
def save_vaccination(**kwargs):
  proj = kwargs ['project']

  # try:
  #   img_name = f"vaccination_card-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"
  #   take_a_picture_of_the_health_card = save_image(frappe.request, 'take_a_picture_of_the_health_card', img_name)
  # except Exception as e:
  #   # return set_res(data={"error": 400, 'error_message': "Please attach a .jpg or .png image of your health card to the 'take a picture of the health card' field."})
  #   return {"status": 400, 'message': "Please attach a .jpg or .png image of your health card to the 'take a picture of the health card' field."}
    
  
  img_name = f"vaccination_card-{proj.replace(' ', '-')}-{random.randint(1001, 999999)}.jpg"
  take_a_picture_of_the_health_card = save_image(frappe.request, 'take_a_picture_of_the_health_card', img_name)
  
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
    # "take_a_picture_of_the_health_card": take_a_picture_of_the_health_card if 'take_a_picture_of_the_health_card' in kwargs else None,
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

  try:
    vaccination.save(ignore_permissions=True);
    # set_res(data={"error": 400, "message": "Vaccination record saved successfully", "data": vaccination})
    set_res(data=vaccination)
  except Exception as e:
    set_res(data={"error": 505, 'error_message': e})
    # return {"status": 505, 'message': e}



def test_fields():
  fields = frappe.db.sql(f""" 
    SELECT *
    FROM tabDocField
    WHERE parent =  'Building'""",
    as_dict=True)
  
  return fields  

def get_f():
  f = frappe.db.sql(f"""
    SELECT * FROM `tabSettlement`
  """, as_dict=True)
  return f



