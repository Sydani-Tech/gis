
import frappe
import random
from datetime import datetime, timedelta

from gis.doc_events import (extract_geometry_geojson)

# Predefined questions with Doctype, Field, and Expected Data Type
QUESTIONS = {
    "building_response_geolocation": {
        "question": "Please take your current geolocation by pressing the button below",
        "doctype": "Building",
        "field": "geolocation",
        "type": "Geolocation"
    },
    "building_picture": {
        "question": "Please take a picture of the building by pressing the button below",
        "doctype": "Building",
        "field": "building_picture",
        "type": "Attach Image"
    },
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
    building = frappe.db.get_value("Building", building_name, ["building_number", "building_address", "how_many_households_occupy_this_building", "building_picture"], as_dict=True)

    if not building:
        return {"error": f"Building '{building_name}' not found"}

    # Process Building-related questions
    for key, item in QUESTIONS.items():
        if item["doctype"] == "Building":
            responses[key] = {
                "question": item["question"],
                "value": building.get(item["field"]),
                "type": item["type"],
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

# import frappe
# import math
# import itertools

# @frappe.whitelist()
# def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
#     """
#     Fetches all submitted buildings filtered by Grid or Ward, validates them, 
#     and selects 10% (rounded up) of valid buildings, ensuring rotation through Settlements.

#     :param grid: The Grid filter (optional).
#     :param ward: The Ward filter (optional).
#     :return: Dictionary containing all buildings and the systematically selected buildings.
#     """
#     #Confirm that start_date and end_date is not None
#     if start_date is None or end_date is None:
#         return {"error": "Start Date and End Date are required."}

#     # Fetch all Approved Settlements in the selected Grid or Ward
#     settlement_filters = {"status": "Approved"}
#     if grid:
#         settlement_filters["grid"] = grid
#     if ward:
#         settlement_filters["ward"] = ward

#     settlements = frappe.db.sql("""
#         SELECT name
#         FROM `tabSettlement`
#         WHERE status = 'Approved'
#         {grid_filter}
#         {ward_filter}
#     """.format(
#         grid_filter=f"AND grid = '{grid}'" if grid else "",
#         ward_filter=f"AND ward = '{ward}'" if ward else ""
#     ), as_dict=True)

#     if not settlements:
#         return {"error": "No approved settlements found with the given filter."}

#     settlement_names = [s["name"] for s in settlements]

#     # Fetch all submitted buildings within the given Grid or Ward
#     building_filters = {"status": "Submitted"}
#     if grid:
#         building_filters["grid"] = grid
#     if ward:
#         building_filters["ward"] = ward

#     # Assume start_date and end_date are passed as date strings: "YYYY-MM-DD"
#     start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
#     end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

#     # Safely construct filters for SQL
#     grid_filter = f"AND grid = %(grid)s" if grid else ""
#     ward_filter = f"AND ward = %(ward)s" if ward else ""
#     date_filter = "AND end_time IS NOT NULL AND end_time BETWEEN %(start_datetime)s AND %(end_datetime)s"

#     buildings = frappe.db.sql(f"""
#         SELECT name, settlement, owner, geolocation, building_picture, building_picture_2
#         FROM `tabBuilding`
#         WHERE status = 'Submitted'
#         {grid_filter}
#         {ward_filter}
#         {date_filter}
#     """, 
#     {
#         "grid": grid,
#         "ward": ward,
#         "start_datetime": start_datetime,
#         "end_datetime": end_datetime
#     }, as_dict=True)

#     # print("Total Buildings: ", len(buildings))

#     if not buildings:
#         return {"error": "No buildings found with the given filter. Try extending the date range."}

#     valid_buildings = []

#     for building in buildings:
#         # Check if the building's settlement is in the approved list
#         if building["settlement"] not in settlement_names:
#             continue

#         # Ensure the building has at least one valid Household
#         households = frappe.db.get_list(
#             "Household",
#             filters={"building": building["name"], "status": "Submitted"},
#             fields=["name"]
#         )

#         if not households:
#             continue  # Skip if no valid household

#         # Ensure the building has at least one valid Child
#         children = frappe.db.get_list(
#             "Children",
#             filters={"building": building["name"], "household": ["in", [h["name"] for h in households]], "status": "Submitted"},
#             fields=["name"]
#         )

#         if children:
#             valid_buildings.append(building)  # Only add if children exist

#     total_valid = len(valid_buildings)
#     # print("Valid Buildings: ", total_valid)
#     if total_valid == 0:
#         return {
#             "all_buildings": [{"form": "Building", **b} for b in buildings],
#             "selected_buildings": []
#         }

#     # Determine the number of buildings to select (10% rounded up)
#     selected_count = math.ceil(len(buildings) * 0.1)

#     # print("Selected Buildings: ", selected_count)

#     # Sort valid buildings by Settlement
#     buildings_by_settlement = {s: [] for s in settlement_names}
#     for building in valid_buildings:
#         buildings_by_settlement[building["settlement"]].append(building)

#     # Rotate through settlements to evenly distribute selections
#     selected_buildings = []
#     settlement_cycle = itertools.cycle(settlement_names)  # Cycle through settlements

#     while len(selected_buildings) < selected_count:
#         settlement = next(settlement_cycle)

#         if buildings_by_settlement[settlement]:
#             selected_buildings.append(buildings_by_settlement[settlement].pop(0))

#         # Break if no more valid buildings remain
#         if all(len(b) == 0 for b in buildings_by_settlement.values()):
#             break

#     return {
#         # "message": "Buildings fetched successfully.",
#         # "status": 200,
#         # "settlement": settlement_names,
#         # "total_valid_buildings": total_valid,
#         # "total_buildings": len(buildings),
#         "all_buildings": [{"form": "Building", **b} for b in buildings],
#         "selected_buildings": [{"form": "Building", **b} for b in selected_buildings]
#     }


import frappe
import math
import itertools

@frappe.whitelist()
def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
    """
    Fetches all submitted buildings filtered by Grid or Ward, validates them, 
    and selects 100% (rounded up) of valid buildings, ensuring rotation through Settlements.

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
       
        {ward_filter}
    """.format(
        # grid_filter=f"AND grid = '{grid}'" if grid else "",
        ward_filter=f"AND ward = '{ward}'" if ward else ""
    ), as_dict=True)

    if not settlements:
        return {"error": "No approved settlements found with the given filter."}

    settlement_names = [s["name"] for s in settlements]

    # Fetch all submitted buildings within the given Grid or Ward
    building_filters = {"status": "Submitted"}
    if grid:
        building_filters["grid"] = grid
    if ward:
        building_filters["ward"] = ward

    # Assume start_date and end_date are passed as date strings: "YYYY-MM-DD"
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    # Safely construct filters for SQL
    grid_filter = f"AND grid = %(grid)s" if grid else ""
    ward_filter = f"AND ward = %(ward)s" if ward else ""
    date_filter = "AND end_time IS NOT NULL AND end_time BETWEEN %(start_datetime)s AND %(end_datetime)s"

    buildings = frappe.db.sql(f"""
        SELECT name, grid, settlement, owner, geolocation, building_picture, building_picture_2
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
            "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
            "selected_buildings": []
        }

    # Determine the number of buildings to select (100% rounded up)
    selected_count = math.ceil(len(valid_buildings) * 1)

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
        "message": "Buildings fetched successfully.",
        "status": 200,
        # "settlement": settlement_names,
        # "total_valid_buildings": total_valid,
        # "total_buildings": len(buildings),
        # "valid_buildings": [{"form": "Building", **b} for b in valid_buildings],
        "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
        "selected_buildings": [{"form": "Building", **b} for b in valid_buildings]
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
    
    # Check if a specific name is provided
    if name:
        results = frappe.db.sql("""
            SELECT 
                parent.name,
                parent.grid, 
                parent.ward, 
                parent.local_government_area, 
                parent.state, 
                parent.validator, 
                parent.status,
                parent.modified,
                parent.completion_percentage,
                parent.completed_validations,
                parent.total_buildings
            FROM `tabEnumeration Validation Summary` AS parent
            WHERE parent.name = %s AND parent.validator = %s
        """, (name, user), as_dict=True)

        if results:
            grid_name = frappe.get_value("Grid", results[0].grid, "title")
            ward_name = frappe.get_value("Ward", results[0].ward, "ward")
            lga_name = frappe.get_value("Local Government Area", results[0].local_government_area, "local_government_area")
            results[0]["grid_name"] = grid_name
            results[0]["ward_name"] = grid_name if grid_name else ward_name
            results[0]["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}

    else:
        # Fetch all summaries for the logged-in user
        results = frappe.db.sql("""
                    SELECT 
                        parent.name, 
                        parent.grid,
                        parent.ward, 
                        parent.local_government_area, 
                        parent.state,
                        parent.completion_percentage,
                        parent.completed_validations,
                        parent.total_buildings,
                        parent.validator, 
                        parent.status,
                        parent.modified
                    FROM `tabEnumeration Validation Summary` AS parent
                    WHERE parent.validator = %s
                    ORDER BY parent.creation DESC
                """, (user,), as_dict=True)
        
        if results:

            for row in results:
                grid_name = frappe.get_value("Grid", results[0].grid, "title")
                ward_name = frappe.get_value("Ward", row.ward, "ward")
                lga_name = frappe.get_value("Local Government Area", row.local_government_area, "local_government_area")
                
                row["grid_name"] = grid_name
                row["ward_name"] = grid_name if grid_name else ward_name
                row["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summaries found for the user. Please contact your supervisor.", "status": 404}


    # Add child records as a dictionary under each parent

    for row in results:

        if row.get("status") == "Pending":
            child_records = frappe.db.get_list(
                "Enumeration Sample Responses",
                filters={"parent": row["name"]},
                fields=["record AS building_name", "status AS building_validation_status", "settlement", "geolocation AS building_geolocation", "validation_responses", "response_geolocation", "last_modified"],
                ignore_permissions=True
            )
            for building in child_records:
                building_details = get_building_details(building["building_name"])
                building_questions = building_details.get("data", {}) if building_details else {}
                building["building_questions"] = building_questions

            row["buildings"] = child_records  # Assign child records under 'buildings'

        #else return empty list
        else:
            row["buildings"] = []


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

# @frappe.whitelist()
# def get_buildings_to_validate_and_save(ward=None, start_date=None, end_date=None):

#     # Get the logged-in user
#     user = frappe.session.user
#     if user == "Guest":
#         return {"message": "You must be logged in to access this data.", "status": 401}
    
#     # Check if the user has the "Dashboard Viewer" role
#     user_roles = frappe.get_roles(user)
#     if "Enumeration Validator" not in user_roles:
#         return {
#             "message": "You do not have the required role to perform enumeration validation, please contact your Supervisor.",
#             "status": 401
#         }
    
#     # Check if ward is provided
#     if not ward:
#         return {
#             "message": "Select a Ward to create a validation summary.",
#             "status": 400
#         }
    
#     # Check if start date is provided
#     if not start_date:
#         return {
#             "message": "Select a Start Date to create a validation summary.",
#             "status": 400
#         }
    
#     # Check if end date is provided
#     if not end_date:
#         return {
#             "message": "Select an End Date to create a validation summary.",
#             "status": 400
#         }
    
#     existing_summaries = frappe.get_all(
#         "Enumeration Validation Summary",
#         filters={"validator": user, "status": ["in", ["Pending"]]},
#         fields=["name"]
#     )

#     if existing_summaries:
#         return {
#             "message": "You already have a pending enumeration validation summary. Please complete it before creating a new one.",
#             "status": 400
#         }
    

#     try:
#         buildings_to_validate = get_buildings(ward=ward, start_date=start_date, end_date=end_date)

#         # Early exit if no buildings were found
#         if buildings_to_validate.get("error") == "No buildings found with the given filter. Try extending the date range.":
#             return {
#                 "message": buildings_to_validate["error"],
#                 "status": 404
#     }

#         # Create and save Enumeration Validation Summary
#         summary = frappe.new_doc("Enumeration Validation Summary")

#         summary.ward = ward
#         summary.validator = frappe.session.user
#         summary.start_date = start_date
#         summary.end_date = end_date
#         summary.status = "Pending"

#         # Append all buildings
#         for building in buildings_to_validate.get("all_buildings", []):
#             summary.append("records_under_validation", {
#                 "doctype_name": building.get("form"),
#                 "record": building.get("name"),
#                 "settlement": building.get("settlement"),
#                 "enumerator": building.get("owner"),
#                 "geolocation": building.get("geolocation"),
#                 "last_modified": frappe.utils.now(),
#                 "status": "Pending",
#             })

#         # Append selected buildings
#         for building in buildings_to_validate.get("selected_buildings", []):
#             summary.append("enumeration_sample_responses", {
#                 "doctype_name": building.get("form"),
#                 "record": building.get("name"),
#                 "settlement": building.get("settlement"),
#                 "enumerator": building.get("owner"),
#                 "geolocation": building.get("geolocation"),
#                 "response_geolocation": building.get("geolocation"),
#                 "last_modified": frappe.utils.now(),
#                 "status": "Pending",
#             })

#         summary.insert(ignore_permissions=True)
#         summary.save()

#         validation_summary = get_enumeration_validation_summaries(name=summary.name)

#         return {
#             "message": "Enumeration validation data created successfully.",
#             "status": 200,
#             "Enumeration Validation Summary": summary.name,
#             "buildings_to_validate": buildings_to_validate,
#             "validation_summary": validation_summary
#         }

#     except Exception as e:
#         # frappe.log_error(f"Error in get_buildings_to_validate_and_save: {str(e)}", "Error")
#         import traceback
#         return {
#             "message": f"Error fetching data: {str(e)}",
#             "status": "error",
#             "ward": ward,
#             "traceback": traceback.format_exc()
#         }   


@frappe.whitelist()
def get_buildings_to_validate_and_save(ward=None, grid=None, start_date=None, end_date=None):

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
    
    # Check if neither a grid not ward has been provided
    if not ward and not grid:
        return {
            "message": "Provide either a ward or a grid to create a validation summary.",
            "status": 400
        }

    # Check if both a grid and a ward has been provided
    if ward and grid:
        return {
            "message": "Provide only one criteria, a ward or a grid.",
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

    if existing_summaries:
        return {
            "message": "You already have a pending enumeration validation summary. Please complete it before creating a new one.",
            "status": 400
        }
    

    try:
        buildings_to_validate = get_buildings(ward=ward, grid=grid, start_date=start_date, end_date=end_date)

        # Early exit if no buildings were found
        if buildings_to_validate.get("error") == "No buildings found with the given filter. Try extending the date range.":
            return {
                "message": buildings_to_validate["error"],
                "status": 404
    }

        # Create and save Enumeration Validation Summary
        summary = frappe.new_doc("Enumeration Validation Summary")

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
                "geolocation": building.get("geolocation"),
                "last_modified": frappe.utils.now(),
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
                "response_geolocation": building.get("geolocation"),
                "last_modified": frappe.utils.now(),
                "status": "Pending",
            })

        # summary.insert(ignore_permissions=True)
        # summary.save()

        # validation_summary = get_enumeration_validation_summaries(name=summary.name)

        return {
            "message": "Enumeration validation data created successfully.",
            "status": 200,
            "Enumeration Validation Summary": summary.name,
            "buildings_to_validate": buildings_to_validate,
            # "validation_summary": validation_summary
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
import base64
import os
from frappe.utils.file_manager import save_file

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

                row_data = buildings_map[row.record]
                # row.status = row_data["status"]
                row.status = "Returned" if row_data["status"] == "Corrected" else row_data["status"]
                row.validation_responses = row_data["validation_responses"]
                row.response_geolocation = row_data.get("response_geolocation")
                row.last_modified = row_data.get("last_modified")

                # Handle Base64 image inline
                base64_image = row_data.get("enumeration_picture")
                if base64_image:
                
                    # Remove "data:image/..." header if present
                    if base64_image.startswith("data:"):
                        base64_image = base64_image.split(",")[1]

                    # Fix Base64 padding (length must be multiple of 4)
                    missing_padding = len(base64_image) % 4
                    if missing_padding:
                        base64_image += '=' * (4 - missing_padding)

                    # Decode and save file
                    image_bytes = base64.b64decode(base64_image)
                    filename = f"enumeration_{row.record.replace(' ', '_')}.jpg"

                    file_doc = save_file(
                        filename, image_bytes, parent_doc.doctype, parent_doc.name, is_private=0
                    )
                    row.enumeration_picture = file_doc.file_url

                facility_geojson = extract_geometry_geojson(row.geolocation)
                settlement_geojson = extract_geometry_geojson(row.response_geolocation)

                if facility_geojson and settlement_geojson:
                    distance_result = frappe.db.sql("""
                        SELECT ST_Distance_Sphere(
                            ST_GeomFromGeoJSON(%s),
                            ST_GeomFromGeoJSON(%s)
                        ) AS distance
                    """, (facility_geojson, settlement_geojson), as_dict=True)

                    if distance_result and distance_result[0]["distance"] is not None:
                        row.distance = round(distance_result[0]["distance"], 3)

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

# def update_enumeration_records_from_sample_responses(doc, method):
#     # Fetch all sample responses linked to the current document
#     sample_responses = frappe.get_all(
#         "Enumeration Sample Responses",
#         filters={"parent": doc.name},
#         fields=["enumerator", "status"]
#     )

#     # frappe.msgprint(f"Sample responses: {sample_responses}")

#     # Fetch all records under validation linked to the current document
#     records_under_validation = frappe.get_all(
#         "Records Under Validation",
#         filters={"parent": doc.name},
#         fields=["name", "enumerator", "record", "status"]
#     )

#     # frappe.msgprint(f"Records under validation: {records_under_validation}")

#     # Get a set of enumerators with 'Returned' status
#     returned_enumerators = {row["enumerator"] for row in sample_responses if row["status"] in ["Returned", "Corrected"]}

#     for record in records_under_validation:
#         enumerator = record["enumerator"]
#         building_name = record["record"]  # 'record' represents the building column

#         # Determine new status based on whether the enumerator was marked as Returned
#         new_status = "Returned" if enumerator in returned_enumerators else "Approved"

#         # Update status in Records Under Validation
#         frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

#         # Update Building
#         frappe.db.set_value("Building", building_name, "status", new_status)

#         # Fetch and update Households
#         households = frappe.get_all(
#             "Household",
#             filters={"building": building_name, "status": "Submitted"},
#             fields=["name"]
#         )
#         for household in households:
#             frappe.db.set_value("Household", household["name"], "status", new_status)

#         # Fetch and update Children
#         children = frappe.get_all(
#             "Children",
#             filters={"building": building_name, "status": "Submitted"},
#             fields=["name"]
#         )
#         for child in children:
#             frappe.db.set_value("Children", child["name"], "status", new_status)



#     # Commit changes after all updates
#     frappe.db.commit()

def update_enumeration_records_from_sample_responses(doc, method):
    """
    Sync status of records in Records Under Validation with
    the corresponding record in Enumeration Sample Responses.
    """

    # Fetch all sample responses linked to the current document
    sample_responses = frappe.get_all(
        "Enumeration Sample Responses",
        filters={"parent": doc.name},
        fields=["record", "status"]
    )

    # Build a map of record -> status for quick lookup
    sample_status_map = {resp["record"]: resp["status"] for resp in sample_responses}

    # Fetch all records under validation linked to the current document
    records_under_validation = frappe.get_all(
        "Records Under Validation",
        filters={"parent": doc.name},
        fields=["name", "record", "status"]
    )

    for record in records_under_validation:
        record_name = record["record"]
        if record_name in sample_status_map:
            new_status = sample_status_map[record_name]
            frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

            # Update Building
            frappe.db.set_value("Building", record_name, "status", new_status)

            # Fetch and update Households
            households = frappe.get_all(
                "Household",
                filters={"building": record_name, "status": "Submitted"},
                fields=["name"]
            )
            for household in households:
                frappe.db.set_value("Household", household["name"], "status", new_status)

            # Fetch and update Children
            children = frappe.get_all(
                "Children",
                filters={"building": record_name, "status": "Submitted"},
                fields=["name"]
            )
            for child in children:
                frappe.db.set_value("Children", child["name"], "status", new_status)



    # Commit changes after all updates
    frappe.db.commit()


# def update_enumeration_records_from_sample_responses_on_save(doc, method):
#     # Fetch all sample responses linked to the current document
#     sample_responses = frappe.get_all(
#         "Enumeration Sample Responses",
#         filters={"parent": doc.name},
#         fields=["enumerator", "status"]
#     )

#     # frappe.msgprint(f"Sample responses: {sample_responses}")

#     # Fetch all records under validation linked to the current document
#     records_under_validation = frappe.get_all(
#         "Records Under Validation",
#         filters={"parent": doc.name},
#         fields=["name", "enumerator", "record", "status"]
#     )

#     # frappe.msgprint(f"Records under validation: {records_under_validation}")

#     # Get a set of enumerators with 'Returned' status
#     returned_enumerators = {row["enumerator"] for row in sample_responses if row["status"] in ["Returned", "Corrected"]}
#     approved_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Approved"}
#     pending_enumerators = {row["enumerator"] for row in sample_responses if row["status"] == "Pending"}

#     for record in records_under_validation:
#         enumerator = record["enumerator"]
#         building_name = record["record"]  # 'record' represents the building column

#         # Determine new status based on whether the enumerator was marked as Returned
#         # new_status = "Returned" if enumerator in returned_enumerators else "Approved"
#         new_status = "Returned" if enumerator in returned_enumerators else "Approved" if enumerator in approved_enumerators else "Pending"

#         # Update status in Records Under Validation
#         frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

#     # Commit changes after all updates
#     frappe.db.commit()


def update_enumeration_records_from_sample_responses_on_save(doc, method):
    """
    Sync status of records in Records Under Validation with
    the corresponding record in Enumeration Sample Responses.
    """

    # Fetch all sample responses linked to the current document
    sample_responses = frappe.get_all(
        "Enumeration Sample Responses",
        filters={"parent": doc.name},
        fields=["record", "status"]
    )

    # Build a map of record -> status for quick lookup
    sample_status_map = {resp["record"]: resp["status"] for resp in sample_responses}

    # Fetch all records under validation linked to the current document
    records_under_validation = frappe.get_all(
        "Records Under Validation",
        filters={"parent": doc.name},
        fields=["name", "record", "status"]
    )

    for record in records_under_validation:
        record_name = record["record"]
        if record_name in sample_status_map:
            new_status = sample_status_map[record_name]

            # Only update if status has changed
            if record["status"] != new_status:
                frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

    # Commit once at the end
    frappe.db.commit()


def calculate_validation_status(doc, method):
    pending_count = 0
    approved_count = 0
    corrected_count = 0
    returned_count = 0
    total_rows = len(doc.enumeration_sample_responses)

    # Step 1: Aggregate vaccination data by vaccinator
    for row in doc.enumeration_sample_responses:
        if row.status == "Pending":
            pending_count += 1
        elif row.status == "Approved":
            approved_count += 1
        elif row.status == "Corrected":
            corrected_count += 1
        elif row.status == "Returned":
            returned_count += 1

    doc.pending_validations = pending_count
    doc.completed_validations = total_rows - pending_count
    doc.total_buildings = total_rows
    doc.validation_percentage = round(((approved_count + corrected_count) / total_rows) * 100, 0) if total_rows != 0 else 0
    doc.completion_percentage = round((total_rows - pending_count) / total_rows * 100, 0) if total_rows != 0 else 0

    if doc.grid:
        doc.local_government_area = frappe.db.get_value("Grid", doc.grid, "local_government_area")
        doc.state = frappe.db.get_value("Grid", doc.grid, "state")
       
    else:
        doc.local_government_area = frappe.db.get_value("Ward", doc.ward, "local_government_area")
        doc.state = frappe.db.get_value("Ward", doc.grid, "state")

    # frappe.msgprint (f"Pending: {pending_count}, Approved: {approved_count}, Corrected: {corrected_count}, Returned: {returned_count}, Total Rows: {total_rows}, Validation Percentage: {doc.validation_percentage}, Completion Percentage: {doc.completion_percentage}")

def validate_status_is_approved(doc, method):

    pending_rows = []

    # 1. Check for pending rows and count approved
    for i, row in enumerate(doc.enumeration_sample_responses, start=1):
        if row.status == "Pending":
            pending_rows.append(str(i))

    # 2. If there are any pending rows, throw an error listing row numbers
    if pending_rows:
        frappe.throw(f"The following rows are still pending validation: {', '.join(pending_rows)}")
    else:
        doc.status = "Completed"  # Set status to Approved if no pending rows



def test_get_buildings():
    # ward = "City Center 1-Municipal Area Council-Fct"
    ward = None
    grid = "us9fgj3j87"
    start_date = "2025-05-01"
    end_date = "2025-05-06"
    result = get_buildings(ward=ward, grid=grid, start_date=start_date, end_date=end_date)
    print(result)

import frappe
import random
from datetime import datetime, date, timedelta

def _parse_date(s: str) -> date:
    """Parse 'YYYY-MM-DD' or 'DD-MM-YYYY' to date (defaults to 2025-05-01 if missing)."""
    if not s:
        return date(2024, 5, 1)
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    frappe.throw(f"Invalid start_date format: {s}. Use YYYY-MM-DD or DD-MM-YYYY.")
    return date.today()  # unreachable

def _fetch_valid_buildings_sql(grid_name: str, start_d: date, today_d: date, cap: int):
    """
    Single SQL to fetch up to `cap` valid buildings in a grid between start_d and today_d,
    ordered by end_time ASC so we know *when* max_count was reached.
    A building is 'valid' if:
      - Building.status = 'Submitted'
      - Settlement.status = 'Approved'
      - Has ≥1 Household(status='Submitted')
      - Has ≥1 Children(status='Submitted') whose household is among the submitted households for that building
    """
    return frappe.db.sql(
        """
        SELECT
            b.name,
            b.grid,
            b.settlement,
            b.owner,
            b.geolocation,
            b.building_picture,
            b.building_picture_2,
            b.end_time
        FROM `tabBuilding` b
        INNER JOIN `tabSettlement` s
            ON s.name = b.settlement
           AND s.status = 'Approved'
        WHERE b.status = 'Submitted'
          AND b.grid = %(grid)s
          AND b.end_time IS NOT NULL
          AND b.end_time BETWEEN %(start)s AND %(today)s
          AND EXISTS (
                SELECT 1 FROM `tabHousehold` h
                 WHERE h.building = b.name
                   AND h.status = 'Submitted'
          )
          AND EXISTS (
                SELECT 1
                  FROM `tabChildren` c
                 WHERE c.building = b.name
                   AND c.status = 'Submitted'
                   AND c.household IN (
                        SELECT h2.name
                          FROM `tabHousehold` h2
                         WHERE h2.building = b.name
                           AND h2.status = 'Submitted'
                   )
          )
        ORDER BY b.end_time ASC
        LIMIT %(cap)s
        """,
        {
            "grid": grid_name,
            "start": datetime.combine(start_d, datetime.min.time()),
            "today": datetime.combine(today_d, datetime.max.time()),
            "cap": int(cap),
        },
        as_dict=True,
    )

@frappe.whitelist()
def assign_enumeration_validations(start_date_str: str = None, min_count: int = 2, max_count: int = 10):
    """
    Auto-create Enumeration Validation Summary for each validator (user) who has a Ward-level User Permission
    and is not already the validator on a pending Summary.

    Logic:
      - For each (user, ward) User Permission:
          * Skip if user already has a Pending Summary.
          * Pick a random eligible Grid in that ward (enabled=1, vaccination_grid=0, not already pending).
          * Fetch up to `max_count` valid buildings between start_date and today using one SQL.
          * If < min_count → skip this (user, ward).
          * Else create a Summary:
                validator=user
                start_date = parsed start_date
                end_date   = max(end_time) of returned buildings  ← tracks actual cap hit date
                grid       = chosen grid
                status     = "Pending"
            Fill both child tables from the returned buildings.
      - Returns a compact report.

    Notes:
      - No Python call to get_buildings; everything is SQL-based.
      - `end_date` now reflects when the `max_count` (or the last returned building) was reached.
    """
    start_date = _parse_date(start_date_str)
    today = date.today()
    if start_date > today:
        frappe.throw("start_date cannot be in the future.")
    if min_count <= 0 or max_count <= 0:
        frappe.throw("min_count and max_count must be positive integers.")
    if min_count > max_count:
        frappe.throw("min_count cannot be greater than max_count.")

    # Pending summaries → who is busy & which grids are taken
    pending_summaries = frappe.get_all(
        "Enumeration Validation Summary",
        filters={"status": "Pending"},
        fields=["name", "validator", "grid"]
    )
    validators_in_use = {row["validator"] for row in pending_summaries if row.get("validator")}
    pending_grids = {row["grid"] for row in pending_summaries if row.get("grid")}

    # All Ward-level user permissions
    user_perms = frappe.get_all(
        "User Permission",
        filters={"allow": "Ward"},
        fields=["user", "for_value"]
    )
    user_perms = [up for up in user_perms if up.get("user") and up.get("for_value")]
    wards = sorted({up["for_value"] for up in user_perms})
    if not wards:
        return {"created": [], "skipped": {"no_wards": "No User Permission rows for Ward found."}}

    # Preload eligible grids for these wards
    grid_rows = frappe.get_all(
        "Grid",
        filters={
            "enabled": 1,
            "vaccination_grid": 0,
            "ward": ["in", wards]
        },
        fields=["name", "ward"]
    )
    grids_by_ward = {}
    for gr in grid_rows:
        grids_by_ward.setdefault(gr["ward"], []).append(gr["name"])

    created = []
    skipped = {"no_grid_for_ward": [], "validator_busy": [], "not_enough_buildings": [], "errors": []}

    for up in user_perms:
        validator = up["user"]
        ward_name = up["for_value"]

        # Skip if user already has a pending summary
        if validator in validators_in_use:
            skipped["validator_busy"].append({"user": validator, "ward": ward_name})
            continue

        # Grids for this ward, excluding ones already pending
        candidates = [g for g in grids_by_ward.get(ward_name, []) if g not in pending_grids]
        if not candidates:
            skipped["no_grid_for_ward"].append({"user": validator, "ward": ward_name})
            continue

        random.shuffle(candidates)  # simple load spread
        picked_doc = None

        for grid_name in candidates:
            try:
                rows = _fetch_valid_buildings_sql(
                    grid_name=grid_name,
                    start_d=start_date,
                    today_d=today,
                    cap=max_count
                )
            except Exception as e:
                skipped["errors"].append(
                    {"user": validator, "ward": ward_name, "grid": grid_name, "error": str(e)}
                )
                continue

            if len(rows) < int(min_count):
                # Not enough on this grid—try next candidate
                continue

            # Compute actual_end_date from the data returned (tracks when cap was hit or last building date)
            # rows are ordered by end_time ASC; take the last one
            last_end_time = rows[-1]["end_time"] if rows and rows[-1].get("end_time") else None
            actual_end_date = (last_end_time.date() if last_end_time else today)

            try:
                doc = frappe.new_doc("Enumeration Validation Summary")
                doc.validator = validator
                doc.start_date = start_date.isoformat()
                doc.end_date = actual_end_date.isoformat()
                doc.status = "Pending"
                doc.grid = grid_name

                # Fill children from the returned rows
                for b in rows:
                    # enumeration_sample_responses
                    doc.append("enumeration_sample_responses", {
                        "doctype_name": "Building",
                        "record": b.get("name"),
                        "settlement": b.get("settlement"),
                        "enumerator": b.get("owner"),
                        "status": "Pending",
                        "geolocation": b.get("geolocation"),
                        "building_picture": b.get("building_picture"),
                        "building_picture_2": b.get("building_picture_2"),
                    })
                    # records_under_validation
                    doc.append("records_under_validation", {
                        "doctype_name": "Building",
                        "record": b.get("name"),
                        "settlement": b.get("settlement"),
                        "enumerator": b.get("owner"),
                        "status": "Pending",
                    })

                doc.insert(ignore_permissions=True)
                frappe.db.commit()

                created.append({
                    "summary": doc.name,
                    "validator": validator,
                    "grid": grid_name,
                    "start_date": doc.start_date,
                    "end_date": doc.end_date,
                    "count": len(rows),
                })

                # Mark taken in this run
                pending_grids.add(grid_name)
                validators_in_use.add(validator)
                picked_doc = doc
                break  # done for this user

            except Exception as e:
                frappe.db.rollback()
                skipped["errors"].append(
                    {"user": validator, "ward": ward_name, "grid": grid_name, "error": str(e)}
                )
                # Try next candidate grid

        if not picked_doc:
            skipped["not_enough_buildings"].append({"user": validator, "ward": ward_name})

    return {
        "created": created,
        "skipped": skipped,
        "params": {
            "start_date": start_date.isoformat(),
            "min_count": int(min_count),
            "max_count": int(max_count),
        }
    }
