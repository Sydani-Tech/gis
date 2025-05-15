
import frappe
import random
from datetime import datetime, timedelta

# Predefined questions with Doctype, Field, and Expected Data Type
QUESTIONS = {
    "building_number_match": {
        "question": "Does the building number match with the enumerated data?",
        "doctype": "Building",
        "field": "building_number",
        "type": "Data"
    },
    "building_address_match": {
        "question": "Does the building address match with the enumerated data?",
        "doctype": "Building",
        "field": "building_address",
        "type": "Data"
    },
    "household_in_building_match": {
        "question": "Does the number of households in this building as reported by enumerator match the observed number?",
        "doctype": "Building",
        "field": "how_many_households_occupy_this_building",
        "type": "Int"
    },
    "household_head_match": {
        "question": "Does the name of the head of household match with the enumerated data?",
        "doctype": "Household",
        "field": "name_of_household_head",
        "type": "Data"
    },
    "under_5_children_count": {
        "question": "Is this the correct number of under 5 children in the household?",
        "doctype": "Household",
        "field": "how_many_household_members_are_below_5",
        "type": "Int"
    },
    "child_first_name_match": {
        "question": "Is this the correct first name of one of the under 5 children in the household?",
        "doctype": "Children",
        "field": "first_name",
        "type": "Data"
    },
    "child_last_name_match": {
        "question": "Is this the correct last name of the same under 5 child in the household?",
        "doctype": "Children",
        "field": "last_name",
        "type": "Data"
    },
    "child_gender_match": {
        "question": "Is this the correct gender of the child?",
        "doctype": "Children",
        "field": "gender",
        "type": "Select",
        "options": ["Male", "Female"]
    },
    "child_dob_match": {
        "question": "Is this the correct date of birth of the child?",
        "doctype": "Children",
        "field": "date_of_birth",
        "type": "Date"
    },
    "child_vaccines_match": {
        "question": "Are these the correct vaccines that have been taken by the child?",
        "doctype": "Children",
        "field": "vaccines_taken",
        "type": "Table"
    }
}

@frappe.whitelist()
def get_builing_validation_questions(building_name):
    """
    Fetches responses for validation questions based on a building.
    - Randomly selects a Household (`status="Submitted"`) for the given Building.
    - Randomly selects a Child (`status="Submitted"`) for the found Household.
    - Returns structured validation data.
    
    :param building_name: Name of the Building.
    :return: Dictionary of questions with their fetched values and types.
    """
    responses = {}

    # Fetch Building Information
    building = frappe.db.get_value("Building", building_name, ["building_number", "building_address", "how_many_households_occupy_this_building"], as_dict=True)

    if not building:
        return {"error": f"Building '{building_name}' not found"}

    # Process Building-related questions
    for key, item in QUESTIONS.items():
        if item["doctype"] == "Building":
            responses[key] = {
                "question": item["question"],
                "value": building.get(item["field"]),
                "type": item["type"],
                # "options": item.get("options", [])
                "options": item["options"] if "options" in item else []
            }

    # Fetch all Households where status is "Submitted" for the given Building
    households = frappe.db.get_list("Household", filters={"building": building_name, "status": "Submitted"}, 
                                    fields=["name", "name_of_household_head", "how_many_household_members_are_below_5"],
                                    ignore_permissions=True)
  

    if not households:
        return responses  # No household found, return what we have

    # Randomly select one Household
    household = random.choice(households)

    # Process Household-related questions
    for key, item in QUESTIONS.items():
        if item["doctype"] == "Household":
            responses[key] = {
                "question": item["question"],
                "value": household.get(item["field"]),
                "type": item["type"],
                "options": item["options"] if "options" in item else []
            }

    import ast
    # Fetch all Children where status is "Submitted" for the selected Household
    children = frappe.db.sql("""
        SELECT name, first_name, last_name, full_name, gender, date_of_birth, vaccines_taken
        FROM `tabChildren`
        WHERE household = %s AND status = 'Submitted'
    """, household["name"], as_dict=True)
    
    # for child in children:
    #     vaccines_str = child.get("vaccines_taken", "[]")
    #     child["vaccines_taken"] = reformat_vaccines_taken(vaccines_str)

    for child in children:
        vaccines_str = child.get("vaccines_taken", "").strip("[]").strip()
        if vaccines_str:
            parsed_list = [v.strip() for v in vaccines_str.split(",")]
            child["vaccines_taken"] = parsed_list
        else:
            child["vaccines_taken"] = []


    if not children:
        return responses  # No child found, return what we have

    # Randomly select one Child
    child = random.choice(children)

    # Process Children-related questions
    for key, item in QUESTIONS.items():
        if item["doctype"] == "Children":
            responses[key] = {
                "question": item["question"],
                "value": child.get(item["field"]),
                "type": item["type"],
                "options": item["options"] if "options" in item else []
            }

    return responses

def reformat_vaccines_taken(vaccines_str):
            # Remove the surrounding brackets
            content = vaccines_str.strip('[]')
            if not content:
                return '[]'
            # Split the string into items, trim whitespace, and enclose each in double quotes
            items = ['"{}"'.format(item.strip()) for item in content.split(',')]
            # Join the items with commas and enclose in square brackets
            return '[{}]'.format(', '.join(items))

import frappe
import math
import itertools

@frappe.whitelist()
def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
    """
    Fetches all submitted buildings filtered by Grid or Ward, validates them, 
    and selects 10% (rounded up) of valid buildings, ensuring rotation through Settlements.

    :param grid: The Grid filter (optional).
    :param ward: The Ward filter (optional).
    :return: Dictionary containing all buildings and the systematically selected buildings.
    """
    #Confirm that start_date and end_date is not None
    if start_date is None or end_date is None:
        return {"error": "Start Date and End Date are required."}

    # Fetch all Approved Settlements in the selected Grid or Ward
    settlement_filters = {"status": "Approved"}
    if grid:
        settlement_filters["grid"] = grid
    if ward:
        settlement_filters["ward"] = ward

    settlements = frappe.db.sql("""
        SELECT name
        FROM `tabSettlement`
        WHERE status = 'Approved'
        {grid_filter}
        {ward_filter}
    """.format(
        grid_filter=f"AND grid = '{grid}'" if grid else "",
        ward_filter=f"AND ward = '{ward}'" if ward else ""
    ), as_dict=True)

    if not settlements:
        return {"error": "No approved settlements found with the given filter."}

    settlement_names = [s["name"] for s in settlements]
    # print("Approved Settlements: ", settlement_names)

    # Fetch all submitted buildings within the given Grid or Ward
    building_filters = {"status": "Submitted"}
    if grid:
        building_filters["grid"] = grid
    if ward:
        building_filters["ward"] = ward

    # # buildings = frappe.db.get_list("Building", filters=building_filters, fields=["name", "settlement", "owner", "geolocation"])

    # buildings = frappe.db.sql("""
    #     SELECT name, settlement, owner, geolocation, building_picture, building_picture_2
    #     FROM `tabBuilding`
    #     WHERE status = 'Submitted'
    #     {grid_filter}
    #     {ward_filter}
    # """.format(
    #     grid_filter=f"AND grid = '{grid}'" if grid else "",
    #     ward_filter=f"AND ward = '{ward}'" if ward else ""
    # ), as_dict=True)

    # Assume start_date and end_date are passed as date strings: "YYYY-MM-DD"
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    # Safely construct filters for SQL
    grid_filter = f"AND grid = %(grid)s" if grid else ""
    ward_filter = f"AND ward = %(ward)s" if ward else ""
    date_filter = "AND end_time IS NOT NULL AND end_time BETWEEN %(start_datetime)s AND %(end_datetime)s"
    # date_filter = "AND end_time IS NOT NULL AND end_time BETWEEN %(start_date)s AND %(end_date)s"

    buildings = frappe.db.sql(f"""
        SELECT name, settlement, owner, geolocation, building_picture, building_picture_2
        FROM `tabBuilding`
        WHERE status = 'Submitted'
        {grid_filter}
        {ward_filter}
        {date_filter}
    """, 
    {
        "grid": grid,
        "ward": ward,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime
        # "start_date": start_date,
        # "end_date": end_date
    }, as_dict=True)

    # print("Total Buildings: ", len(buildings))

    if not buildings:
        return {"error": "No buildings found with the given filter. Try extending the date range."}

    valid_buildings = []

    for building in buildings:
        # Check if the building's settlement is in the approved list
        if building["settlement"] not in settlement_names:
            continue

        # Ensure the building has at least one valid Household
        households = frappe.db.get_list(
            "Household",
            filters={"building": building["name"], "status": "Submitted"},
            fields=["name"]
        )

        if not households:
            continue  # Skip if no valid household

        # Ensure the building has at least one valid Child
        children = frappe.db.get_list(
            "Children",
            filters={"building": building["name"], "household": ["in", [h["name"] for h in households]], "status": "Submitted"},
            fields=["name"]
        )

        if children:
            valid_buildings.append(building)  # Only add if children exist

    total_valid = len(valid_buildings)
    # print("Valid Buildings: ", total_valid)
    if total_valid == 0:
        return {
            "all_buildings": [{"form": "Building", **b} for b in buildings],
            "selected_buildings": []
        }

    # Determine the number of buildings to select (10% rounded up)
    selected_count = math.ceil(len(buildings) * 0.1)

    # print("Selected Buildings: ", selected_count)

    # Sort valid buildings by Settlement
    buildings_by_settlement = {s: [] for s in settlement_names}
    for building in valid_buildings:
        buildings_by_settlement[building["settlement"]].append(building)

    # Rotate through settlements to evenly distribute selections
    selected_buildings = []
    settlement_cycle = itertools.cycle(settlement_names)  # Cycle through settlements

    while len(selected_buildings) < selected_count:
        settlement = next(settlement_cycle)

        if buildings_by_settlement[settlement]:
            selected_buildings.append(buildings_by_settlement[settlement].pop(0))

        # Break if no more valid buildings remain
        if all(len(b) == 0 for b in buildings_by_settlement.values()):
            break

    return {
        # "message": "Buildings fetched successfully.",
        # "status": 200,
        # "settlement": settlement_names,
        # "total_valid_buildings": total_valid,
        # "total_buildings": len(buildings),
        "all_buildings": [{"form": "Building", **b} for b in buildings],
        "selected_buildings": [{"form": "Building", **b} for b in selected_buildings]
    }

@frappe.whitelist()
def get_enumeration_validation_summaries(name=None):
    """
    Fetches all Enumeration Validation Summaries for the logged-in user.
    """

    user = frappe.session.user
    if user == "Guest":
        return {"error": "You must be logged in to access this data."}

    # Check if the user has the "Enumeration Validator" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
            "status": 401
        }
    # # If a name is provided, fetch that specific summary
    # if name:
    #     results = frappe.db.sql("""
    #         SELECT 
    #             parent.name, 
    #             parent.ward, 
    #             parent.local_government_area, 
    #             parent.state, 
    #             parent.validator, 
    #             parent.status,
    #             parent.modified
    #         FROM `tabEnumeration Validation Summary` AS parent
    #         WHERE parent.name = %s AND parent.validator = %s
    #     """, (name, user), as_dict=True)

    #     if not results:
    #         return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}


    if name:
        results = frappe.db.sql("""
            SELECT 
                parent.name, 
                parent.ward, 
                parent.local_government_area, 
                parent.state, 
                parent.validator, 
                parent.status,
                parent.modified
            FROM `tabEnumeration Validation Summary` AS parent
            WHERE parent.name = %s AND parent.validator = %s
        """, (name, user), as_dict=True)

        if results:
            ward_name = frappe.get_value("Ward", results[0].ward, "ward")
            lga_name = frappe.get_value("Local Government Area", results[0].local_government_area, "local_government_area")
            results[0]["ward_name"] = ward_name
            results[0]["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}

    else:
        # Fetch all summaries for the logged-in user
        results = frappe.db.sql("""
                    SELECT 
                        parent.name, 
                        parent.ward, 
                        parent.local_government_area, 
                        parent.state, 
                        parent.validator, 
                        parent.status,
                        parent.modified
                    FROM `tabEnumeration Validation Summary` AS parent
                    WHERE parent.validator = %s
                    ORDER BY parent.creation DESC
                """, (user,), as_dict=True)
        
        if results:

            for row in results:
                ward_name = frappe.get_value("Ward", row.ward, "ward")
                lga_name = frappe.get_value("Local Government Area", row.local_government_area, "local_government_area")

                row["ward_name"] = ward_name
                row["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summaries found for the user. Please contact your supervisor.", "status": 404}


    # Add child records as a dictionary under each parent

    for row in results:
        child_records = frappe.db.get_list(
            "Enumeration Sample Responses",
            filters={"parent": row["name"]},
            fields=["record AS building_name", "status AS building_validation_status", "geolocation AS building_geolocation"],
            ignore_permissions=True
        )
        for building in child_records:

            if row.get("status") == "Pending":
                building_details = get_building_details(building["building_name"])
                building_questions = building_details.get("data", {}) if building_details else {}
                building["building_questions"] = building_questions

        row["buildings"] = child_records  # Assign child records under 'buildings'


    return {
        "message": "Enumeration Validation Summaries fetched successfully.",
        "status": 200,
        "data": results

    }


@frappe.whitelist()
def get_building_details(building_name):

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Enumeration Validator" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
            "status": 401
        }

    try:
        builing_validation_questions = get_builing_validation_questions(building_name=building_name)
        return {
            "message": "Building details fetched successfully.",
            "status": 200,
            "data": builing_validation_questions
        }
    except Exception as e:
        import traceback
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error",
            "traceback": traceback.format_exc()
        }

@frappe.whitelist()
# def get_buildings_to_validate_and_save(grid=None, ward=None):
def get_buildings_to_validate_and_save(ward=None, start_date=None, end_date=None):

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your Supervisor.",
            "status": 401
        }
    
    # Check if ward is provided
    if not ward:
        return {
            "message": "Select a Ward to create a validation summary.",
            "status": 400
        }
    
    # Check if start date is provided
    if not start_date:
        return {
            "message": "Select a Start Date to create a validation summary.",
            "status": 400
        }
    
    # Check if end date is provided
    if not end_date:
        return {
            "message": "Select an End Date to create a validation summary.",
            "status": 400
        }
    
    existing_summaries = frappe.get_all(
        "Enumeration Validation Summary",
        filters={"validator": user, "status": ["in", ["Pending"]]},
        fields=["name"]
    )

    # if existing_summaries:
    #     return {
    #         "message": "You already have a pending validation summary. Please complete it before starting a new one.",
    #         "status": 400
    #     }
    

    try:

        # Ensure only one of grid or ward is supplied
        # if (grid and ward) or (not grid and not ward):
        # if (grid and ward):
        #     return {
        #         "message": "Please provide either Grid or Ward, but not both.",
        #         "status": 400
        #     }

        # Get buildings to validate
        # buildings_to_validate = get_buildings(grid=grid, ward=ward)
        buildings_to_validate = get_buildings(ward=ward, start_date=start_date, end_date=end_date)

        # Early exit if no buildings were found
        if buildings_to_validate.get("error") == "No buildings found with the given filter. Try extending the date range.":
            return {
                "message": buildings_to_validate["error"],
                "status": 404
    }

        # Create and save Enumeration Validation Summary
        summary = frappe.new_doc("Enumeration Validation Summary")

        # if grid:
        #     # Fetch the ward value from the Grid doctype
        #     grid_doc = frappe.get_doc("Grid", grid)
        #     summary.grid = grid
        #     summary.ward = grid_doc.ward
        # else:
        #     summary.ward = ward

        summary.ward = ward
        summary.validator = frappe.session.user
        summary.start_date = start_date
        summary.end_date = end_date
        summary.status = "Pending"

        # Append all buildings
        for building in buildings_to_validate.get("all_buildings", []):
            summary.append("records_under_validation", {
                "doctype_name": building.get("form"),
                "record": building.get("name"),
                "settlement": building.get("settlement"),
                "enumerator": building.get("owner"),
                "status": "Pending",
            })

        # Append selected buildings
        for building in buildings_to_validate.get("selected_buildings", []):
            summary.append("enumeration_sample_responses", {
                "doctype_name": building.get("form"),
                "record": building.get("name"),
                "settlement": building.get("settlement"),
                "enumerator": building.get("owner"),
                "geolocation": building.get("geolocation"),
                "status": "Pending",
            })

        summary.insert(ignore_permissions=True)
        summary.save()

        return {
            "message": "Enumeration validation data saved successfully.",
            "status": 200,
            "Enumeration Validation Summary": summary.name,
            "buildings_to_validate": buildings_to_validate,
        }

    except Exception as e:
        # frappe.log_error(f"Error in get_buildings_to_validate_and_save: {str(e)}", "Error")
        import traceback
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error",
            "ward": ward,
            "traceback": traceback.format_exc()
        }   

@frappe.whitelist()
def get_wards_to_validate():
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your Supervisor.",
            "status": 401
        }

    # Initialize filters
    filters = {}

    # Check User Permissions for the provided user
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Ward'},
        fields=['for_value']
    )

    if user_permissions:
        # Extract the list of allowed wards from user permissions
        allowed_wards = [permission['for_value'] for permission in user_permissions]
        allowed_wards = frappe.get_all(
            'Ward',
            filters={'name': ['in', allowed_wards]},
            fields=['name', 'ward']
        )

    # If no user permissions, fetch all wards in the specified local government areas
    else:
        allowed_wards = frappe.get_all(
        'Ward', 
        filters={'local_government_area': ['in', ['Borgu-Niger', 'Bosso-Niger', 'Mokwa-Niger', 'Rijau-Niger', 'Shiroro-Niger', 'Wushishi-Niger']]},
        fields=['name', 'ward']
            )

    return {
        "message": "Wards fetched successfully.",
        "status": 200,
        "data": allowed_wards
    }

@frappe.whitelist()
def get_grids_to_validate():
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your Supervisor.",
            "status": 401
        }


    # Initialize filters
    filters = {}
    # Check User Permissions for the provided user
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Grid'},
        fields=['for_value']
    )

    if user_permissions:
        # Extract the list of allowed wards from user permissions
        allowed_grids = [permission['for_value'] for permission in user_permissions]
        allowed_grids = frappe.get_all(
            'Grid',
            filters={'name': ['in', allowed_grids]},
            fields=['name', "title", 'ward']
        )

    # If no user permissions, fetch all wards in the specified local government areas
    else:
        return {
            "message": "No grid has been assigned to you, choose a Ward to validate instead or reach out to your supervisor.",
            "status": 401
            
        }

    return {
        "message": "Grids fetched successfully.",
        "status": 200,
        "data": allowed_grids
    }

import frappe
from frappe.exceptions import DoesNotExistError

@frappe.whitelist()
def submit_vaccine_enumeration_responses(doc_name, buildings):
    """
    Update child table records for a given parent document.

    Args:
    - doc_name (str): Name of the parent document.
    - buildings (list): List of dicts containing:
        - record (str): Building name
        - status (str): Status to update
        - validation_responses (str): Response after validation exercise

    Returns:
    - JSON response with success or failure message.
    """
    if isinstance(buildings, str):
        # Convert JSON string to list if needed (for REST API compatibility)
        import json
        buildings = json.loads(buildings)

    try:
        # Fetch the parent document
        parent_doc = frappe.get_doc("Enumeration Validation Summary", doc_name)

        # Check if the child table exists
        if not hasattr(parent_doc, "enumeration_sample_responses"):
            return {"error": "Child table not found in parent document."}

        updated_buildings = []  # Track updated rows

        # Create a mapping of buildings for quick lookup
        buildings_map = {b["record"]: b for b in buildings}

        # Iterate over child table records
        for row in parent_doc.enumeration_sample_responses:
            if row.record in buildings_map:  # Match building
                row.status = buildings_map[row.record]["status"]
                # validation_message = prettify_validation_responses(buildings_map[row.record]["validation_responses"])
                
                # row.validation_responses = validation_message
                row.validation_responses = buildings_map[row.record]["validation_responses"]

                # sample_row = parent_doc.enumeration_sample_responses[0]
                # message = prettify_validation_responses(sample_row.validation_responses)

                updated_buildings.append(row.record)

        # Save updates
        parent_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "message": f"Successfully updated {len(updated_buildings)} buildings in {doc_name}.",
            "updated_buildings": updated_buildings
        }

    except DoesNotExistError:
        return {"error": f"Document {doc_name} not found."}
    except Exception as e:
        return {"error": str(e)}


# def prettify_validation_responses(validation_responses):
#     if not validation_responses:
#         return "No responses available."

#     prettified_message = ""

#     for idx, response in enumerate(validation_responses):
#         question = response.get("question", "Unknown question")
#         original_value = response.get("value", "N/A")
#         validated_value = response.get("updatedValue")
#         validation_verdict = response.get("booleanValue")
#         # response_type = response.get("type")
#         # options = response.get("options", [])

#         # Add spacing between questions
#         if idx > 0:
#             prettified_message += "<br><br>"

#         # Header (question in bold)
#         prettified_message += f"<strong>{question}</strong><br>"

#         # Value
#         prettified_message += f"• Original Value: {original_value}<br>"

#         # Boolean Value as human-friendly label
#         if validation_verdict is not None:
#             status_text = "Correct" if validation_verdict else "Incorrect"
#             prettified_message += f"• Validation Verdict: {status_text}<br>"

#         # Updated Value (if exists)
#         if validated_value:
#             prettified_message += f"• Validated Value: {validated_value}<br>"

       

#         # # Type
#         # prettified_message += f"• Type: {response_type}<br>"

#         # # Options (if present and non-empty)
#         # if options:
#         #     prettified_message += f"• Options: {', '.join(options)}<br>"

#     return prettified_message


def prettify_validation_responses(validation_responses):
    prettified_message = ""

    for item in validation_responses:
        question = item.get("question", "")
        original_value = item.get("value", "")
        verdict = "Correct" if not item.get("booleanValue") else "InCorrect"
        color = "#28a745" if verdict == "Correct" else "#dc3545"  # green/red

        prettified_message += (
            f"<p style='margin-bottom: 1em;'>"
            f"<strong>{question}</strong><br>"
            f"• <strong>Original Value:</strong> {original_value}<br>"
            f"• <strong>Validation Verdict:</strong> "
            f"<span style='color: {color}; font-weight: bold;'>{verdict}</span>"
            f"</p>"
        )

    return prettified_message


#script to test the prettify_validation_responses function
def test_prettify_validation_responses():
    validation_responses = [
        [
            {"question": "Does the building number match with the enumerated data?", "value": "5", "updatedValue": None, "type": "Data", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Does the building address match with the enumerated data?", "value": "345 Pineview Plaza", "updatedValue": None, "type": "Data", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Does the number of households in this building as reported by enumerator match the observed number?", "value": "2", "updatedValue": None, "type": "Int", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Does the name of the head of household match with the enumerated data?", "value": "Amaka Onyeka", "updatedValue": None, "type": "Data", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Is this the correct number of under 5 children in the household?", "value": "2", "updatedValue": None, "type": "Int", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Is this the correct first name of one of the under 5 children in the household?", "value": "Chidinma", "updatedValue": None, "type": "Data", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Is this the correct last name of the same under 5 child in the household?", "value": "Nwachukwu", "updatedValue": None, "type": "Data", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Is this the correct gender of the child?", "value": "Female", "updatedValue": None, "type": "Select", "options": ["Male", "Female"], "booleanValue": True, "buildingId": None},
            {"question": "Is this the correct date of birth of the child?", "value": "2022-03-29", "updatedValue": None, "type": "Date", "options": [], "booleanValue": True, "buildingId": None},
            {"question": "Are these the correct vaccines that have been taken by the child?", "value": "[OPV 0, OPV 1, OPV 3]", "updatedValue": None, "type": "Table", "options": [], "booleanValue": True, "buildingId": None}
        ]
    ]

    result = prettify_validation_responses(validation_responses[0])  # Send the actual list of dicts
    print(result)

def update_enumeration_records_from_sample_responses(doc, method):
    # Fetch all sample responses linked to the current document
    sample_responses = frappe.get_all(
        "Enumeration Sample Responses",
        filters={"parent": doc.name},
        fields=["enumerator", "status"]
    )

    # frappe.msgprint(f"Sample responses: {sample_responses}")

    # Fetch all records under validation linked to the current document
    records_under_validation = frappe.get_all(
        "Records Under Validation",
        filters={"parent": doc.name},
        fields=["name", "enumerator", "record", "status"]
    )

    # frappe.msgprint(f"Records under validation: {records_under_validation}")

    # Get a set of enumerators with 'Returned' status
    returned_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Returned"}

    for record in records_under_validation:
        enumerator = record["enumerator"]
        building_name = record["record"]  # 'record' represents the building column

        # Determine new status based on whether the enumerator was marked as Returned
        new_status = "Returned" if enumerator in returned_enumerators else "Approved"

        # Update status in Records Under Validation
        frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

        # Update Building
        frappe.db.set_value("Building", building_name, "status", new_status)

        # Fetch and update Households
        households = frappe.get_all(
            "Household",
            filters={"building": building_name, "status": "Submitted"},
            fields=["name"]
        )
        for household in households:
            frappe.db.set_value("Household", household["name"], "status", new_status)

        # Fetch and update Children
        children = frappe.get_all(
            "Children",
            filters={"building": building_name, "status": "Submitted"},
            fields=["name"]
        )
        for child in children:
            frappe.db.set_value("Children", child["name"], "status", new_status)



    # Commit changes after all updates
    frappe.db.commit()


def update_enumeration_records_from_sample_responses_on_save(doc, method):
    # Fetch all sample responses linked to the current document
    sample_responses = frappe.get_all(
        "Enumeration Sample Responses",
        filters={"parent": doc.name},
        fields=["enumerator", "status"]
    )

    # frappe.msgprint(f"Sample responses: {sample_responses}")

    # Fetch all records under validation linked to the current document
    records_under_validation = frappe.get_all(
        "Records Under Validation",
        filters={"parent": doc.name},
        fields=["name", "enumerator", "record", "status"]
    )

    # frappe.msgprint(f"Records under validation: {records_under_validation}")

    # Get a set of enumerators with 'Returned' status
    returned_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Returned"}
    approved_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Approved"}
    pending_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Pending"}

    for record in records_under_validation:
        enumerator = record["enumerator"]
        building_name = record["record"]  # 'record' represents the building column

        # Determine new status based on whether the enumerator was marked as Returned
        # new_status = "Returned" if enumerator in returned_enumerators else "Approved"
        new_status = "Returned" if enumerator in returned_enumerators else "Approved" if enumerator in approved_enumerators else "Pending"

        # Update status in Records Under Validation
        frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

    # Commit changes after all updates
    frappe.db.commit()

def validate_status_is_approved(doc, method):
    if doc.status != "Completed":
        frappe.throw("Status must be 'Approved' to submit validation.")

    pending_rows = []


    # 1. Check for pending rows and count approved
    for i, row in enumerate(doc.enumeration_sample_responses, start=1):
        if row.status == "Pending":
            pending_rows.append(str(i))

    # 2. If there are any pending rows, throw an error listing row numbers
    if pending_rows:
        frappe.throw(f"The following rows are still pending validation: {', '.join(pending_rows)}")



def test_get_buildings():
    # ward = "City Center 1-Municipal Area Council-Fct"
    ward = None
    grid = "us9fgj3j87"
    start_date = "2025-05-01"
    end_date = "2025-05-06"
    result = get_buildings(ward=ward, grid=grid, start_date=start_date, end_date=end_date)
    print(result)
