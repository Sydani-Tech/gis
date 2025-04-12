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
    label, fieldtype, options, hidden, reqd, read_only, depends_on, permlevel, description,
    mandatory_depends_on, read_only_depends_on, `default`, idx 
    FROM tabDocField
    WHERE parent = %(name)s AND label != '' 
    ORDER BY idx ASC 
    """,
    filt, as_dict=True)
  
  return fields  

# @frappe.whitelist()
# def projects():

#   # Get the logged-in user
#   user = frappe.session.user
#   if user == "Guest":
#         return {"message": "You must be logged in to access this data.", "status": "error"}

#   team = get_team(user);
#   if(team):
#     filt = {'name': team.parent}
#     project = frappe.db.sql(f""" 
#       SELECT name, project, close_data_collection, enable_geofencing  
#       FROM `tabProject` WHERE name = %(name)s ORDER BY idx ASC 
#     """, filt, as_dict=True)
#   else:
#     project = []

#   return set_res(projects=project)

@frappe.whitelist()
def projects():
    try:
        # Get the logged-in user
        user = frappe.session.user
        if user == "Guest":
            return {"message": "You must be logged in to access this data.", "status": "error"}

        # Fetch projects where the user is listed in the Assignees child table
        project = frappe.db.sql(
            """
            SELECT 
                p.name, 
                p.project, 
                p.close_data_collection, 
                p.enable_geofencing
            FROM 
                `tabProject` p
            JOIN 
                `tabAssignees` a ON p.name = a.parent
            WHERE 
                a.user = %(user)s
            ORDER BY 
                p.idx ASC
            """,
            {"user": user},
            as_dict=True
        )

        # Return success message
        return set_res(projects=project)

    except Exception as e:
        # Return error message in case of exception
        return {"message": f"An error occurred: {str(e)}", "status": "error"}




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

# @frappe.whitelist()
# def grids():
#     user = frappe.session.user
#     if user == "Guest":
#         return {
#             "message": "You must be logged in to access this data.",
#             "status": 401
#         }

#     # Fetch grid assignees where user matches the logged-in user
#     grid_record = frappe.db.sql(
#         """
#         SELECT DISTINCT parent 
#         FROM `tabGrid Assignees` 
#         WHERE user = %(user)s
#         """,
#         {"user": user},
#         as_dict=True
#     )

#     if not grid_record:
#         return {
#             "message": "User does not have an assigned grid, please contact a supervisor.",
#             "status": 404
#         }
    
#     grids = frappe.db.sql(
#         """
#         SELECT *
#         FROM `tabGrid` 
#         WHERE name = %(grid)s
#         """,
#         {"grid": grid_record[0].parent},
#         as_dict=True
#     )

#     # # Extract parent values
#     # parent_values = [record["parent"] for record in grid_records]

#     # return {
#     #     "status": 200,
#     #     "data": {
#     #         "assigned_projects": parent_values
#     #     }
#     # }


#     # Extract the parent (Grid name)
#     # grid_name = grid_record[0]["parent"]

#     # Fetch the geolocation_kyow field value from the Grid doctype
#     # geolocation = frappe.db.get_value("Grid", grid_name, "geolocation_kyow")

#     # return {
#     #     "status": 200,
#     #     "data": {
#     #         "assigned_grid": grid_name,
#     #         "grid_geolocation": geolocation
#     #     }
#     # }

#     # set_res(data=grids)
#     set_res(data={'grids': grids, 'assignees': grid_record})


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
        FROM `tabGrid Assignees` 
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
        SELECT g.*, p.project, p.close_data_collection, p.enable_geofencing
        FROM `tabGrid` g
        JOIN `tabProject` p ON g.project = p.name
        WHERE g.name = %(grid)s
        """,
        {"grid": grid_record[0].parent},
        as_dict=True
    )
    
    # set_res(data=grids)
    set_res(data={'grids': grids, 'assignees': grid_record})



@frappe.whitelist()
def save_children(**kwargs):
    record_name = kwargs.get("name")  # Check if 'name' (record ID) is provided for updating an existing record
    
    try:
        # If 'name' is provided, fetch the existing record
        if record_name:
            children = frappe.get_doc("Children", record_name)
        else:
            # Create a new record if 'name' is not provided
            full_name = f"{kwargs['first_name']} {kwargs.get('middle_name', '')} {kwargs['last_name']}".strip()
            children = frappe.get_doc({
                "doctype": "Children",
                "household": kwargs["household"],
                "first_name": kwargs["first_name"],
                "middle_name": kwargs.get("middle_name"),
                "last_name": kwargs["last_name"],
                "full_name": full_name,
                "date_of_birth": kwargs["date_of_birth"],
                "gender": kwargs["gender"],
                "does_the_child_have_a_vaccination_card": kwargs["does_the_child_have_a_vaccination_card"],
                # "vaccination_status": kwargs["vaccination_status"],
                "geolocation": kwargs["geolocation"],
                "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
                "response_id": kwargs["response_id"],
                "status": kwargs["status"],
                "project": kwargs["project"],
                "grid": kwargs["grid"],
                "start_time": kwargs["start_time"],
                "end_time": kwargs["end_time"],
                "response_geolocation": kwargs["response_geolocation"],
            })

        # Update common fields
        children.update({
            "household": kwargs["household"],
            "first_name": kwargs["first_name"],
            "middle_name": kwargs.get("middle_name"),
            "last_name": kwargs["last_name"],
            "date_of_birth": kwargs["date_of_birth"],
            "gender": kwargs["gender"],
            "does_the_child_have_a_vaccination_card": kwargs["does_the_child_have_a_vaccination_card"],
            # "vaccination_status": kwargs["vaccination_status"],
            "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
            "geolocation": kwargs["geolocation"],
            "response_id": kwargs["response_id"],
            "status": kwargs["status"],
            "project": kwargs["project"],
            "grid": kwargs["grid"],
            "start_time": kwargs["start_time"],
            "end_time": kwargs["end_time"],
            "response_geolocation": kwargs["response_geolocation"],
        })

        import json

        # Handle `last_vaccine_administered` as a child table
        if "last_vaccine_administered" in kwargs:
            children.last_vaccine_administered = []  # Clear existing entries by default
            last_vaccine_administered = kwargs["last_vaccine_administered"]

            if isinstance(last_vaccine_administered, list):
                # If it's already a list, check for valid entries
                for vaccine in last_vaccine_administered:
                    vaccine = vaccine.strip()  # Ensure no trailing spaces
                    if vaccine:  # Only add non-empty vaccines
                        children.append("last_vaccine_administered", {"vaccine": vaccine})

            elif isinstance(last_vaccine_administered, str):
                try:
                    # Parse the string into a list using `json.loads`
                    vaccines = json.loads(last_vaccine_administered)
                    if isinstance(vaccines, list):
                        for vaccine in vaccines:
                            vaccine = vaccine.strip()  # Ensure no trailing spaces
                            if vaccine:  # Only add non-empty vaccines
                                children.append("last_vaccine_administered", {"vaccine": vaccine})
                    else:
                        frappe.throw("The last_vaccine_administered field must contain a valid list of vaccines.")
                except json.JSONDecodeError:
                    frappe.throw("The last_vaccine_administered field must be a JSON array in the format [\"HEP B0\", \"BCG\", \"OPV 0\", \"PENTA 1\", \"ROTA 1\"].")
            else:
                frappe.throw("The last_vaccine_administered field must be a list or a JSON string in the format [\"HEP B0\", \"BCG\", \"OPV 0\", \"PENTA 1\"].")




        # Save the record
        children.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "message": "Children record saved successfully.",
            "status": 200,
            "data": children
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Children Save Error")
        return {
            "message": "An error occurred while saving the Children record. Ensure that you are passing all required fields.",
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
                "industry_of_employment": kwargs["industry_of_employment"] if kwargs["is_the_household_head_employed"] == "Yes" else "",
                "average_monthly_income": kwargs["average_monthly_income"] if kwargs["is_the_household_head_employed"] == "Yes" else "",
                # "industry_of_employment": kwargs.get("industry_of_employment"),
                # "average_monthly_income": kwargs.get("average_monthly_income"),
                "is_the_household_residing_in_a_rented_apartment": kwargs["is_the_household_residing_in_a_rented_apartment"],
                "are_there_any_pregnant_women_in_the_household": kwargs["are_there_any_pregnant_women_in_the_household"],
                "how_many_pregnant_women_are_there": kwargs["how_many_pregnant_women_are_there"] if kwargs["are_there_any_pregnant_women_in_the_household"] == "Yes" else 0,
                # "how_many_pregnant_women_are_there": kwargs.get("how_many_pregnant_women_are_there"),
                "how_many_household_members_are_above_18": kwargs["how_many_household_members_are_above_18"],
                "how_many_household_members_are_between_15_and_18_years": kwargs["how_many_household_members_are_between_15_and_18_years"],
                "how_many_household_members_are_between_9_and_14_years": kwargs["how_many_household_members_are_between_9_and_14_years"],
                "how_many_household_members_are_between_5_and_8_years": kwargs["how_many_household_members_are_between_5_and_8_years"],
                "how_many_household_members_are_below_5": kwargs["how_many_household_members_are_below_5"],
                "how_many_people_live_in_the_household": sum([
                    int(kwargs.get("how_many_household_members_are_below_5", 0)),
                    int(kwargs.get("how_many_household_members_are_between_5_and_8_years", 0)),
                    int(kwargs.get("how_many_household_members_are_between_9_and_14_years", 0)),
                    int(kwargs.get("how_many_household_members_are_between_15_and_18_years", 0)),
                    int(kwargs.get("how_many_household_members_are_above_18", 0))
                ]),
                "most_common_illness_within_the_last_year": kwargs["most_common_illness_within_the_last_year"],
                "if_others_specify": kwargs.get("if_others_specify"),
                # "what_is_the_nearest_facility": kwargs["what_is_the_nearest_facility"],
                # "how_far_is_the_nearest_facility": kwargs["how_far_is_the_nearest_facility"],
                "do_you_take_your_childchildren_to_the_facility_for_ri_services": kwargs["do_you_take_your_childchildren_to_the_facility_for_ri_services"],
                "please_state_why": kwargs["please_state_why"] if kwargs["do_you_take_your_childchildren_to_the_facility_for_ri_services"] == "No" else "",
                # "please_state_why": kwargs.get("please_state_why"),
                # "geolocation": kwargs["geolocation"],
                "building": kwargs["building"],
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
                "are_there_any_pregnant_women_in_the_household": kwargs["are_there_any_pregnant_women_in_the_household"],
                "how_many_pregnant_women_are_there": kwargs.get("how_many_pregnant_women_are_there"),
                "how_many_household_members_are_above_18": kwargs["how_many_household_members_are_above_18"],
                "how_many_household_members_are_between_15_and_18_years": kwargs["how_many_household_members_are_between_15_and_18_years"],
                "how_many_household_members_are_between_9_and_14_years": kwargs["how_many_household_members_are_between_9_and_14_years"],
                "how_many_household_members_are_between_5_and_8_years": kwargs["how_many_household_members_are_between_5_and_8_years"],
                "how_many_household_members_are_below_5": kwargs["how_many_household_members_are_below_5"],
                "how_many_people_live_in_the_household": sum([
                    int(kwargs.get("how_many_household_members_are_below_5", 0)),
                    int(kwargs.get("how_many_household_members_are_between_5_and_8_years", 0)),
                    int(kwargs.get("how_many_household_members_are_between_9_and_14_years", 0)),
                    int(kwargs.get("how_many_household_members_are_between_15_and_18_years", 0)),
                    int(kwargs.get("how_many_household_members_are_above_18", 0))
                ]),
                "most_common_illness_within_the_last_year": kwargs["most_common_illness_within_the_last_year"],
                "if_others_specify": kwargs.get("if_others_specify"),
                # "what_is_the_nearest_facility": kwargs["what_is_the_nearest_facility"],
                # "how_far_is_the_nearest_facility": kwargs["how_far_is_the_nearest_facility"],
                "do_you_take_your_childchildren_to_the_facility_for_ri_services": kwargs["do_you_take_your_childchildren_to_the_facility_for_ri_services"],
                "please_state_why": kwargs.get("please_state_why"),
                # "geolocation": kwargs["geolocation"],
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
                "geolocation": kwargs["geolocation"],
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
                "geolocation": kwargs["geolocation"],
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
                "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"] if kwargs["is_there_a_vdc"] == "Yes" else "",
                # "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"],
                # "ward": kwargs["ward"],
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
                "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"] if kwargs["is_there_a_vdc"] == "Yes" else "",
                # "how_often_does_the_vdc_meet": kwargs["how_often_does_the_vdc_meet"],
                # "ward": kwargs["ward"],
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

        full_name = f"{kwargs['first_name']} {kwargs.get('middle_name', '')} {kwargs['last_name']}".strip()
        type_of_vaccination_post = kwargs.get("type_of_vaccination_post"),
        if type_of_vaccination_post == "Mobile Team":
            building = frappe.get_value("Household", kwargs.get("household"), "building")
        else:
            building = frappe.db.get_value("Building", {"health_facility": kwargs.get("facility")}, "name") or ""

        # Update fields for both new and existing records
        vaccination.update({
            "first_name": kwargs.get("first_name"),
            "middle_name": kwargs.get("middle_name"),
            "last_name": kwargs.get("last_name"),
            "full_name": full_name,
            "date_of_birth": kwargs.get("date_of_birth"),
            "gender": kwargs.get("gender"),
            "care_givers_name": f"{kwargs.get('care_givers_firstname', '')} {kwargs.get('care_givers_surname', '')}".strip(),
            "care_givers_firstname": kwargs.get("care_givers_firstname"),
            "care_givers_surname": kwargs.get("care_givers_surname"),
            "care_givers_date_of_birth": kwargs.get("care_givers_date_of_birth"),
            "care_givers_phone_no": kwargs.get("care_givers_phone_no"),
            "household": kwargs.get("household"),
            "building": building,
            "was_the_child_vaccinated_during_this_program": kwargs.get("was_the_child_vaccinated_during_this_program"),
            "vaccination_date": kwargs.get("vaccination_date"),
            # "next_vaccination_date": kwargs.get("next_vaccination_date"),
            # "vaccination_status": kwargs.get("vaccination_status"),
            "does_the_child_have_a_child_health_card": kwargs.get("does_the_child_have_a_child_health_card"),
            "did_you_administer_the_child_health_card": kwargs.get("did_you_administer_the_child_health_card"),
            "take_a_picture_of_the_health_card": take_a_picture_of_the_health_card,
            "why_were_health_cards_not_given": kwargs.get("why_were_health_cards_not_given"),
            "facility": kwargs.get("facility"),
            "type_of_vaccination_post": kwargs.get("type_of_vaccination_post"),
            "geolocation": kwargs.get("geolocation"),
            "response_id": kwargs.get("response_id"),
            "comment_to_supervisor": kwargs.get("comment_to_supervisor"),
            "settlement": kwargs.get("settlement"),
            "grid": kwargs.get("grid"),
            "start_time": kwargs.get("start_time"),
            "end_time": kwargs.get("end_time"),
            "response_geolocation": kwargs.get("response_geolocation"),
            "status": kwargs.get("status", "Submitted"),
        })

        import json

        # Handle `last_vaccines_administered` as a child table
        if "last_vaccines_administered" in kwargs:
            vaccination.last_vaccines_administered = []  # Clear existing entries by default
            last_vaccines_administered = kwargs["last_vaccines_administered"]

            if isinstance(last_vaccines_administered, list):
                # Process directly if it's already a list
                if last_vaccines_administered:  # Only append rows if there are valid entries
                    for vaccine in last_vaccines_administered:
                        vaccine = vaccine.strip()  # Ensure no trailing spaces
                        if vaccine:  # Only add non-empty vaccines
                            vaccination.append("last_vaccines_administered", {"vaccine": vaccine})

            elif isinstance(last_vaccines_administered, str):
                try:
                    # Parse the string into a list using `json.loads`
                    vaccines = json.loads(last_vaccines_administered)
                    if isinstance(vaccines, list):  # Ensure the parsed result is a list
                        if vaccines:  # Only append rows if there are valid entries
                            for vaccine in vaccines:
                                vaccine = vaccine.strip()  # Ensure no trailing spaces
                                if vaccine:  # Only add non-empty vaccines
                                    vaccination.append("last_vaccines_administered", {"vaccine": vaccine})
                    else:
                        frappe.throw("The last_vaccines_administered field must contain a valid list of vaccines.")
                except json.JSONDecodeError:
                    frappe.throw("The last_vaccines_administered field must be a JSON array in the format [\"HEP B0\", \"BCG\", \"OPV 0\", \"PENTA 1\", \"ROTA 1\"].")
            else:
                frappe.throw("The last_vaccines_administered field must be a list or a JSON string in the format [\"HEP B0\", \"BCG\", \"OPV 0\", \"PENTA 1\"].")

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


@frappe.whitelist(allow_guest=True)  # Allow external access
def create_error_log():
    """API endpoint for external systems to create error logs."""
    try:
        # Parse incoming request data
        data = frappe.local.form_dict

        # Validate required fields
        required_fields = ["error", "method"]
        for field in required_fields:
            if not data.get(field):
                return {"status": "error", "message": _(f"Missing required field: {field}")}

        # Create the Error Log entry
        error_log = frappe.get_doc({
            "doctype": "Error Log",
            "method": data["method"],
            "error": data["error"],
            "trace_id": data.get("trace_id", ""), #Optional reference
            "reference_doctype": data.get("reference_doctype", ""),  # Optional reference
            "reference_name": data.get("reference_doc", "")  # Optional reference
        })
        error_log.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": _("Error Log created successfully"), "log_id": error_log.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in create_error_log API")
        return {"status": "error", "message": str(e)}


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