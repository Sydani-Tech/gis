
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
    "pregnant_women_in_household_match": {
        "question": "Is this the correct number of pregnant women in this household??",
        "doctype": "Household",
        "field": "how_many_pregnant_women_are_there",
        "type": "Int"
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
                                    fields=["name", "name_of_household_head", "how_many_household_members_are_below_5", "how_many_pregnant_women_are_there"],
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


# import frappe
# import math
# import itertools

# @frappe.whitelist()
# def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
#     """
#     Fetches all submitted buildings filtered by Grid or Ward, validates them, 
#     and selects 100% (rounded up) of valid buildings, ensuring rotation through Settlements.

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
       
#         {ward_filter}
#     """.format(
#         # grid_filter=f"AND grid = '{grid}'" if grid else "",
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
#         SELECT name, grid, settlement, owner, building_type, geolocation, building_picture, building_picture_2
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

#         if not households and building["building_type"] == "Residential":
#             continue  # Skip if no valid household
#         elif households or building["building_type"] != "Residential":
#             valid_buildings.append(building)  # Add residential buildings with households and all non-residential buildings

#         # # Ensure the building has at least one valid Child
#         # children = frappe.db.get_list(
#         #     "Children",
#         #     filters={"building": building["name"], "household": ["in", [h["name"] for h in households]], "status": "Submitted"},
#         #     fields=["name"]
#         # )

#         # if children:
#         #     valid_buildings.append(building)  # Only add if children exist
        

#     total_valid = len(valid_buildings)
#     # print("Valid Buildings: ", total_valid)
#     if total_valid == 0:
#         return {
#             "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
#             "selected_buildings": []
#         }

#     # Determine the number of buildings to select (100% rounded up)
#     selected_count = math.ceil(len(valid_buildings) * 1)

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
#         "message": "Buildings fetched successfully.",
#         "status": 200,
#         # "settlement": settlement_names,
#         # "total_valid_buildings": total_valid,
#         # "total_buildings": len(buildings),
#         # "valid_buildings": [{"form": "Building", **b} for b in valid_buildings],
#         "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
#         "selected_buildings": [{"form": "Building", **b} for b in valid_buildings]
#     }

# import frappe
# import math
# import itertools
# from datetime import datetime, timedelta

# @frappe.whitelist()
# def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
#     """
#     Fetches all submitted buildings filtered by Grid or Ward, validates them,
#     and selects 10% (rounded up) of valid buildings, ensuring rotation through Settlements.

#     New validity rules:
#     1. Non-residential building:
#        - building_type = "Non-residential"
#        - status = "Submitted"
#        - end_time in date range
#        - settlement is Approved (and matches grid/ward filters)
#     2. Residential building:
#        - building_type = "Residential"
#        - status = "Submitted"
#        - end_time in date range
#        - settlement is Approved
#        - has at least one Submitted Household
#        - has NO Submitted Children in those households
#     """

#     # Confirm that start_date and end_date are not None
#     if start_date is None or end_date is None:
#         return {"error": "Start Date and End Date are required."}

#     # ---- 1) Fetch approved Settlements in the selected Grid or Ward ----
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

#     # ---- 2) Fetch Buildings (basic filter: Submitted + date range + grid/ward) ----
#     start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
#     end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

#     grid_filter = f"AND grid = %(grid)s" if grid else ""
#     ward_filter = f"AND ward = %(ward)s" if ward else ""
#     date_filter = "AND end_time IS NOT NULL AND end_time BETWEEN %(start_datetime)s AND %(end_datetime)s"

#     buildings = frappe.db.sql(f"""
#         SELECT
#             name,
#             settlement,
#             owner,
#             geolocation,
#             building_picture,
#             building_picture_2,
#             building_type
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

#     if not buildings:
#         return {"error": "No buildings found with the given filter. Try extending the date range."}

#     # ---- 3) Determine "valid" buildings based on your new rules ----
#     valid_buildings = []

#     for building in buildings:
#         # Must belong to an approved settlement
#         if building["settlement"] not in settlement_names:
#             continue

#         btype = (building.get("building_type") or "").strip()

#         # 3.1 Non-residential: accept directly if in approved settlement
#         if btype == "Non-residential":
#             valid_buildings.append(building)
#             continue

#         # 3.2 Residential: must have Submitted household, and NO Submitted children

#         if btype == "Residential":
#             # Fetch Submitted households in this building
#             households = frappe.db.get_list(
#                 "Household",
#                 filters={"building": building["name"], "status": "Submitted"},
#                 fields=["name"],
#             )

#             # If no submitted households → skip this building
#             if not households:
#                 continue

#             # If we get here, there is at least one Submitted household → valid
#             valid_buildings.append(building)

#     total_valid = len(valid_buildings)

#     if total_valid == 0:
#         return {
#             "all_buildings": [{"form": "Building", **b} for b in buildings],
#             "selected_buildings": []
#         }

#     # ---- 4) Select 10% (rounded up) of valid buildings, distributed across settlements ----
#     selected_count = math.ceil(len(valid_buildings) * 0.1)

#     # Group valid buildings by settlement
#     buildings_by_settlement = {s: [] for s in settlement_names}
#     for building in valid_buildings:
#         buildings_by_settlement[building["settlement"]].append(building)

#     selected_buildings = []
#     settlement_cycle = itertools.cycle(settlement_names)

#     while len(selected_buildings) < selected_count:
#         settlement = next(settlement_cycle)

#         if buildings_by_settlement[settlement]:
#             selected_buildings.append(buildings_by_settlement[settlement].pop(0))

#         # Stop if we’ve exhausted all valid buildings
#         if all(len(b) == 0 for b in buildings_by_settlement.values()):
#             break

#     return {
#         "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
#         "selected_buildings": [{"form": "Building", **b} for b in selected_buildings],
#     }

import frappe
import math
from datetime import datetime, timedelta

@frappe.whitelist()
def get_buildings(ward=None, start_date=None, end_date=None, grid=None):
    """
    Fetches all submitted buildings filtered by Grid or Ward, validates them,
    and then selects 10% (rounded up) of *each enumerator's* valid buildings.

    New validity rules:
    1. Non-residential building:
       - building_type = "Non-residential"
       - status = "Submitted"
       - end_time in date range
       - settlement is Approved (and matches grid/ward filters)
    2. Residential building:
       - building_type = "Residential"
       - status = "Submitted"
       - end_time in date range
       - settlement is Approved
       - has at least one Submitted Household
    Selection rules:
       - Group valid buildings by `owner` (enumerator)
       - For each owner, select ceil(10% of their valid buildings)
    """

    # Confirm that start_date and end_date are not None
    if start_date is None or end_date is None:
        return {"error": "Start Date and End Date are required."}

    # ---- 1) Fetch approved Settlements in the selected Grid or Ward ----
    settlements = frappe.db.sql(
        """
        SELECT name
        FROM `tabSettlement`
        WHERE status = 'Approved'
        {grid_filter}
        {ward_filter}
        """.format(
            grid_filter=f"AND grid = '{grid}'" if grid else "",
            ward_filter=f"AND ward = '{ward}'" if ward else "",
        ),
        as_dict=True,
    )

    if not settlements:
        return {"error": "No approved settlements found with the given filter."}

    settlement_names = [s["name"] for s in settlements]

    # ---- 2) Fetch Buildings (basic filter: Submitted + date range + grid/ward) ----
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = (
        datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
    )

    grid_filter = "AND grid = %(grid)s" if grid else ""
    ward_filter = "AND ward = %(ward)s" if ward else ""
    date_filter = (
        "AND end_time IS NOT NULL AND end_time BETWEEN %(start_datetime)s AND %(end_datetime)s"
    )

    buildings = frappe.db.sql(
        f"""
        SELECT
            name,
            settlement,
            owner,
            geolocation,
            building_picture,
            building_picture_2,
            building_type
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
            "end_datetime": end_datetime,
        },
        as_dict=True,
    )

    if not buildings:
        return {
            "error": "No buildings found with the given filter. Try extending the date range."
        }

    # ---- 3) Determine "valid" buildings based on your rules ----
    valid_buildings = []

    for building in buildings:
        # Must belong to an approved settlement
        if building["settlement"] not in settlement_names:
            continue

        btype = (building.get("building_type") or "").strip()

        # 3.1 Non-residential: accept directly if in approved settlement
        if btype == "Non-residential":
            valid_buildings.append(building)
            continue

        # 3.2 Residential: must have at least one Submitted household
        if btype == "Residential":
            households = frappe.db.get_list(
                "Household",
                filters={"building": building["name"], "status": "Submitted"},
                fields=["name"],
            )

            # If no submitted households → skip this building
            if not households:
                continue

            # If we get here, there is at least one Submitted household → valid
            valid_buildings.append(building)

    total_valid = len(valid_buildings)

    if total_valid == 0:
        return {
            "all_buildings": [{"form": "Building", **b} for b in buildings],
            "selected_buildings": [],
        }

    # ---- 4) Select 10% (rounded up) per enumerator (owner) ----
    # Group valid buildings by owner
    buildings_by_owner = {}
    for b in valid_buildings:
        owner = b.get("owner") or ""
        if not owner:
            # If you want to include owner-less buildings in a separate group,
            # you can handle that here instead of skipping.
            continue
        buildings_by_owner.setdefault(owner, []).append(b)

    selected_buildings = []

    for owner, owner_buildings in buildings_by_owner.items():
        n = len(owner_buildings)
        # ceil(10% of this enumerator's buildings), at least 1
        to_pick = max(1, math.ceil(n * 0.10))
        # Take the first N; if you want randomness, you could shuffle first
        selected_buildings.extend(owner_buildings[:to_pick])

    return {
        "all_buildings": [{"form": "Building", **b} for b in valid_buildings],
        "selected_buildings": [{"form": "Building", **b} for b in selected_buildings],
    }



# @frappe.whitelist()
# def get_enumeration_validation_summaries(name=None):
#     """
#     Fetches all Enumeration Validation Summaries for the logged-in user.
#     """

#     user = frappe.session.user
#     if user == "Guest":
#         return {"error": "You must be logged in to access this data."}

#     # Check if the user has the "Enumeration Validator" role
#     user_roles = frappe.get_roles(user)
#     if "Enumeration Validator" not in user_roles:
#         return {
#             "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
#             "status": 401
#         }
    
#     # Check if a specific name is provided
#     if name:
#         results = frappe.db.sql("""
#             SELECT 
#                 parent.name,
#                 parent.grid, 
#                 parent.ward, 
#                 parent.local_government_area, 
#                 parent.state, 
#                 parent.validator, 
#                 parent.status,
#                 parent.modified,
#                 parent.completion_percentage,
#                 parent.completed_validations,
#                 parent.total_buildings
#             FROM `tabEnumeration Validation Summary` AS parent
#             WHERE parent.name = %s AND parent.validator = %s
#         """, (name, user), as_dict=True)

#         if results:
#             grid_name = frappe.get_value("Grid", results[0].grid, "title")
#             ward_name = frappe.get_value("Ward", results[0].ward, "ward")
#             lga_name = frappe.get_value("Local Government Area", results[0].local_government_area, "local_government_area")
#             results[0]["grid_name"] = grid_name
#             results[0]["ward_name"] = grid_name if grid_name else ward_name
#             results[0]["local_government_area_name"] = lga_name
#         else:
#             return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}

#     else:
#         # Fetch all summaries for the logged-in user
#         results = frappe.db.sql("""
#                     SELECT 
#                         parent.name, 
#                         parent.grid,
#                         parent.ward, 
#                         parent.local_government_area, 
#                         parent.state,
#                         parent.completion_percentage,
#                         parent.completed_validations,
#                         parent.total_buildings,
#                         parent.validator, 
#                         parent.status,
#                         parent.modified
#                     FROM `tabEnumeration Validation Summary` AS parent
#                     WHERE parent.validator = %s
#                     ORDER BY parent.creation DESC
#                 """, (user,), as_dict=True)
        
#         if results:

#             for row in results:
#                 grid_name = frappe.get_value("Grid", results[0].grid, "title")
#                 ward_name = frappe.get_value("Ward", row.ward, "ward")
#                 lga_name = frappe.get_value("Local Government Area", row.local_government_area, "local_government_area")
                
#                 row["grid_name"] = grid_name
#                 row["ward_name"] = grid_name if grid_name else ward_name
#                 row["local_government_area_name"] = lga_name
#         else:
#             return {"message": "No Enumeration Validation summaries found for the user. Please contact your supervisor.", "status": 404}


#     # Add child records as a dictionary under each parent

#     for row in results:

#         if row.get("status") == "Pending":
#             child_records = frappe.db.get_list(
#                 "Enumeration Sample Responses",
#                 filters={"parent": row["name"]},
#                 fields=["record AS building_name", "status AS building_validation_status", "settlement", "geolocation AS building_geolocation", "validation_responses", "response_geolocation", "last_modified"],
#                 ignore_permissions=True
#             )
#             for building in child_records:
#                 building_details = get_building_details(building["building_name"])
#                 building_questions = building_details.get("data", {}) if building_details else {}
#                 building["building_questions"] = building_questions

#             row["buildings"] = child_records  # Assign child records under 'buildings'

#         #else return empty list
#         else:
#             row["buildings"] = []


#     return {
#         "message": "Enumeration Validation Summaries fetched successfully.",
#         "status": 200,
#         "data": results

#     }


import json
import re
import frappe

# ---- Helper: sanitize validation_responses ----
BASE64_IMG_PREFIX_RE = re.compile(r"^\s*data:image\/[A-Za-z0-9.+-]+;base64,", re.IGNORECASE)

def _sanitize_validation_responses_str(vr: str | None) -> str | None:
    """
    Remove base64 image payloads from 'updatedValue' in the stringified JSON array.
    Keeps structure identical, but sets updatedValue=None when it contains data:image...;base64,...
    """
    if not vr:
        return vr
    try:
        data = json.loads(vr)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    uv = item.get("updatedValue")
                    if isinstance(uv, str) and BASE64_IMG_PREFIX_RE.match(uv):
                        item["updatedValue"] = None
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        # If malformed JSON, return original to avoid breaking clients.
        return vr


@frappe.whitelist()
def get_enumeration_validation_summaries(name=None):
    """
    Fetch Enumeration Validation Summaries for the logged-in user.
    - Uses a single SQL to fetch children for all Pending summaries.
    - Sanitizes 'validation_responses' by removing base64 image payloads in updatedValue.
    - Preserves your existing behavior of calling get_building_details(...) to attach building_questions.
    """

    user = frappe.session.user
    if user == "Guest":
        return {"error": "You must be logged in to access this data."}

    # Require Enumeration Validator role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
            "status": 401,
        }

    # --- Fetch parent summaries ---
    if name:
        results = frappe.db.sql(
            """
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
            """,
            (name, user),
            as_dict=True,
        )

        if results:
            grid_name = frappe.get_value("Grid", results[0].grid, "title")
            ward_name = frappe.get_value("Ward", results[0].ward, "ward")
            lga_name = frappe.get_value("Local Government Area", results[0].local_government_area, "local_government_area")
            results[0]["grid_name"] = grid_name if grid_name else ward_name
            results[0]["ward_name"] = ward_name if ward_name else grid_name
            results[0]["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}

    else:
        results = frappe.db.sql(
            """
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
            """,
            (user,),
            as_dict=True,
        )

        if results:
            for row in results:
                grid_name = frappe.get_value("Grid", row.grid, "title")
                ward_name = frappe.get_value("Ward", row.ward, "ward")
                lga_name = frappe.get_value("Local Government Area", row.local_government_area, "local_government_area")
                row["grid_name"] = grid_name
                row["ward_name"] = grid_name if grid_name else ward_name
                row["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summaries found for the user. Please contact your supervisor.", "status": 404}

    # --- Fetch child rows for all Pending summaries in one SQL ---
    pending_names = [r["name"] for r in results if r.get("status") == "Pending"]

    if pending_names:
        # Single SQL for all children
        children = frappe.db.sql(
            """
            SELECT
                parent,
                `record` AS building_name,
                `status` AS building_validation_status,
                settlement,
                geolocation AS building_geolocation,
                validation_responses,
                response_geolocation,
                last_modified
            FROM `tabEnumeration Sample Responses`
            WHERE parent IN %(parents)s
            """,
            {"parents": tuple(pending_names)},
            as_dict=True,
        )

        # Sanitize validation_responses
        for ch in children:
            ch["validation_responses"] = _sanitize_validation_responses_str(ch.get("validation_responses"))

        # Group children by parent summary
        by_parent = {}
        for ch in children:
            by_parent.setdefault(ch["parent"], []).append(ch)

        # Attach + preserve building_questions enrichment
        for row in results:
            if row.get("status") == "Pending":
                child_records = by_parent.get(row["name"], [])
                # Keep your per-building enrichment
                for b in child_records:
                    building_details = get_building_details(b["building_name"])
                    building_questions = building_details.get("data", {}) if building_details else {}
                    b["building_questions"] = building_questions
                row["buildings"] = child_records
            else:
                row["buildings"] = []
    else:
        # No pending summaries; set empty lists
        for row in results:
            row["buildings"] = []

    return {
        "message": "Enumeration Validation Summaries fetched successfully.",
        "status": 200,
        "data": results,
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

# def update_enumeration_records_from_sample_responses(doc, method):
#     """
#     Sync status of records in Records Under Validation with
#     the corresponding record in Enumeration Sample Responses.
#     """

#     # Fetch all sample responses linked to the current document
#     sample_responses = frappe.get_all(
#         "Enumeration Sample Responses",
#         filters={"parent": doc.name},
#         fields=["record", "status"]
#     )

#     # Build a map of record -> status for quick lookup
#     sample_status_map = {resp["record"]: resp["status"] for resp in sample_responses}

#     # Fetch all records under validation linked to the current document
#     records_under_validation = frappe.get_all(
#         "Records Under Validation",
#         filters={"parent": doc.name},
#         fields=["name", "record", "status"]
#     )

#     for record in records_under_validation:
#         record_name = record["record"]
#         if record_name in sample_status_map:
#             new_status = sample_status_map[record_name]
#             frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

#             # Update Building
#             frappe.db.set_value("Building", record_name, "status", new_status)

#             # Fetch and update Households
#             households = frappe.get_all(
#                 "Household",
#                 filters={"building": record_name, "status": "Submitted"},
#                 fields=["name"]
#             )
#             for household in households:
#                 frappe.db.set_value("Household", household["name"], "status", new_status)

#             # Fetch and update Children
#             children = frappe.get_all(
#                 "Children",
#                 filters={"building": record_name, "status": "Submitted"},
#                 fields=["name"]
#             )
#             for child in children:
#                 frappe.db.set_value("Children", child["name"], "status", new_status)



#     # Commit changes after all updates
#     frappe.db.commit()


# gis/enumeration_validation.py
import frappe
from typing import Dict, List


def update_enumeration_records_from_sample_responses(doc, method):
    """
    Lightweight submit handler: enqueue the real work on the 'long' queue so the UI doesn't block.
    """
    if not getattr(doc, "name", None):
        return

    frappe.enqueue(
        "gis.enumeration_validation._update_enumeration_records_job",
        queue="long",
        job_name=f"EV Sync: {doc.name}",
        enqueue_after_commit=True,
        summary_name=doc.name,
    )


def _update_enumeration_records_job(summary_name: str):
    """
    Background job:
      - Read Records Under Validation (RUV) for this summary
      - For each RUV row, use its current status (no sample response lookup)
      - Bulk update:
          * Building.status  = RUV.status
          * Household.status = RUV.status  (only where current status = 'Submitted')
          * Children.status  = RUV.status  (only where current status = 'Submitted')
    """
    stats = {
        "ruv_rows": 0,
        "groups": 0,
        "buildings_updated": 0,
        "households_updated": 0,
        "children_updated": 0,
    }

    try:
        # 1) Load RUV rows (record=Building name, status=current status to propagate)
        ruv_rows = frappe.get_all(
            "Records Under Validation",
            filters={"parent": summary_name},
            fields=["record", "status"],
            ignore_permissions=True,
        )
        stats["ruv_rows"] = len(ruv_rows)
        if not ruv_rows:
            frappe.logger().info(f"[EV Sync] {summary_name}: no RUV rows; nothing to do.")
            return

        # 2) Group target building names by the RUV status (so we can bulk-update per status)
        by_status: Dict[str, List[str]] = {}
        for r in ruv_rows:
            bname = r.get("record")
            st = r.get("status")
            if not bname or not st:
                continue
            by_status.setdefault(st, []).append(bname)

        stats["groups"] = len(by_status)

        if not by_status:
            frappe.logger().info(f"[EV Sync] {summary_name}: no valid records to update.")
            return

        # 3) Bulk updates per status
        for st, names in by_status.items():
            if not names:
                continue
            names_tuple = tuple(set(names))  # de-duplicate

            user = frappe.session.user

            # Buildings
            frappe.db.sql(
                """
                UPDATE `tabBuilding`
                SET status = %(st)s,
                    modified = NOW(),
                    modified_by = %(user)s
                WHERE name IN %(names)s
                """,
                {"st": st, "names": names_tuple, "user": user},
            )
            stats["buildings_updated"] += frappe.db.sql("SELECT ROW_COUNT()")[0][0]

            # Households under those buildings (only if currently 'Submitted')
            frappe.db.sql(
                """
                UPDATE `tabHousehold`
                SET status = %(st)s,
                    modified = NOW(),
                    modified_by = %(user)s
                WHERE building IN %(names)s
                AND status = 'Submitted'
                """,
                {"st": st, "names": names_tuple, "user": user},
            )
            stats["households_updated"] += frappe.db.sql("SELECT ROW_COUNT()")[0][0]

            # Children under those buildings (only if currently 'Submitted')
            frappe.db.sql(
                """
                UPDATE `tabChildren`
                SET status = %(st)s,
                    modified = NOW(),
                    modified_by = %(user)s
                WHERE building IN %(names)s
                AND status = 'Submitted'
                """,
                {"st": st, "names": names_tuple, "user": user},
            )
            stats["children_updated"] += frappe.db.sql("SELECT ROW_COUNT()")[0][0]


        frappe.db.commit()
        frappe.logger().info(f"[EV Sync] {summary_name} done: {stats}")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"[EV Sync] {summary_name} failed: {e}",
            "Enumeration Validation Sync Error",
        )



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
    returned_enumerators = {row["enumerator"] for row in sample_responses if row["status"] in ["Returned", "Corrected"]}
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


# def update_enumeration_records_from_sample_responses_on_save(doc, method):
#     """
#     Sync status of records in Records Under Validation with
#     the corresponding record in Enumeration Sample Responses.
#     """

#     # Fetch all sample responses linked to the current document
#     sample_responses = frappe.get_all(
#         "Enumeration Sample Responses",
#         filters={"parent": doc.name},
#         fields=["record", "status"]
#     )

#     # Build a map of record -> status for quick lookup
#     sample_status_map = {resp["record"]: resp["status"] for resp in sample_responses}

#     # Fetch all records under validation linked to the current document
#     records_under_validation = frappe.get_all(
#         "Records Under Validation",
#         filters={"parent": doc.name},
#         fields=["name", "record", "status"]
#     )

#     for record in records_under_validation:
#         record_name = record["record"]
#         if record_name in sample_status_map:
#             new_status = sample_status_map[record_name]

#             # Only update if status has changed
#             if record["status"] != new_status:
#                 frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

#     # Commit once at the end
#     frappe.db.commit()


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



# import frappe
# from datetime import datetime, date, timedelta
# from frappe.utils import now

# # ---------------------------
# # Helpers
# # ---------------------------

# def _parse_date(s: str) -> date:
#     """Parse 'YYYY-MM-DD' or 'DD-MM-YYYY' to date; default 2025-08-01."""
#     if not s:
#         return date(2025, 8, 1)
#     s = s.strip()
#     for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
#         try:
#             return datetime.strptime(s, fmt).date()
#         except ValueError:
#             pass
#     frappe.throw(f"Invalid start_date format: {s}. Use YYYY-MM-DD or DD-MM-YYYY.")
#     return date.today()  # unreachable

# def _chunked_bulk_insert(doctype: str, fields: list[str], values: list[list], chunk_size: int = 1000):
#     """Avoid max_allowed_packet issues; safe no-op for empty values."""
#     if not values:
#         return
#     for i in range(0, len(values), chunk_size):
#         frappe.db.bulk_insert(doctype, fields, values[i:i+chunk_size])

# def _fetch_valid_buildings_sql_window(*, grid_name: str, start_ts: datetime, end_ts_excl: datetime, cap: int) -> list[dict]:
#     """
#     Pure SQL fetch of 'valid' buildings within a NON-overlapping window:
#       - Building.status = 'Submitted'
#       - Building.grid = grid_name
#       - end_time >= start_ts AND end_time < end_ts_excl (note: '<' end boundary)
#       - end_time IS NOT NULL
#       - Settlement.status = 'Approved'
#       - EXISTS Household(status='Submitted') and Children(status='Submitted')
#     Returns up to `cap` rows ordered by end_time ASC.
#     """
#     rows = frappe.db.sql(
#         """
#         SELECT
#             b.name,
#             b.settlement,
#             b.owner,
#             b.geolocation,
#             b.building_picture,
#             b.building_picture_2,
#             b.end_time
#         FROM `tabBuilding` AS b USE INDEX (idx_building_grid_status_endtime)
#         WHERE b.status = 'Submitted'
#           AND b.grid = %(grid)s
#           AND b.end_time IS NOT NULL
#           AND b.end_time >= %(start_ts)s
#           AND b.end_time <  %(end_ts)s
#           AND EXISTS (
#                 SELECT 1 FROM `tabSettlement` s USE INDEX (idx_settlement_status_name)
#                 WHERE s.name = b.settlement AND s.status = 'Approved'
#           )
#           AND EXISTS (
#                 SELECT 1 FROM `tabHousehold` h USE INDEX (building_status)
#                 WHERE h.building = b.name AND h.status = 'Submitted' LIMIT 1
#           )
#           AND EXISTS (
#                 SELECT 1 FROM `tabChildren` c USE INDEX (building_status_household)
#                 WHERE c.building = b.name AND c.status = 'Submitted' LIMIT 1
#           )
#         ORDER BY b.end_time ASC
#         LIMIT %(limit)s
#         """,
#         {
#             "grid": grid_name,
#             "start_ts": start_ts,
#             "end_ts": end_ts_excl,
#             "limit": int(cap),
#         },
#         as_dict=True,
#     )
#     return rows


# # ---------------------------
# # Main function (drop-in)
# # ---------------------------

# @frappe.whitelist()
# def assign_enumeration_validations(start_date_str: str | None = None, min_count: int = 15, max_count: int = 125):
#     """
#     Optimized enumerations assignment with unique, windowed fetch:
#       - Non-overlapping 7-day windows to avoid duplicate buildings.
#       - Skips grids that can't reach min_count (no padding).
#       - Sets parent.total_buildings to count of unique valid buildings.
#       - Bulk inserts children.

#     Also preloads:
#       - Pending validators/grids via SQL
#       - Candidate grids per ward via SQL
#     """

#     # -------- Parse dates / guards --------
#     start_date = _parse_date(start_date_str)
#     today = date.today()
#     if start_date > today:
#         frappe.throw("start_date cannot be in the future.")

#     # -------- SQL preload pending validators & grids --------
#     pending_rows = frappe.db.sql(
#         """
#         SELECT validator, grid
#         FROM `tabEnumeration Validation Summary` USE INDEX (status_validator_grid)
#         WHERE status = 'Pending'
#         """,
#         as_dict=True,
#     )
#     validators_in_use = {r["validator"] for r in pending_rows if r.get("validator")}
#     pending_grids = {r["grid"] for r in pending_rows if r.get("grid")}

#     # -------- User-permission (Ward) --------
#     user_perms = frappe.get_all(
#         "User Permission",
#         filters={"allow": "Ward"},
#         fields=["user", "for_value"],
#     )
#     user_perms = [up for up in user_perms if up.get("user") and up.get("for_value")]
#     if not user_perms:
#         return {"created": [], "skipped": {"no_wards": "No User Permission rows for Ward found."}}

#     wards = sorted({up["for_value"] for up in user_perms})

#     # -------- Preload candidate grids for all wards via SQL --------
#     grid_rows = frappe.db.sql(
#         """
#         SELECT name, ward
#         FROM `tabGrid` USE INDEX (ward_enabled_vacc)
#         WHERE enabled = 1
#           AND vaccination_grid = 0
#           AND ward IN %(wards)s
#         """,
#         {"wards": tuple(wards)},
#         as_dict=True,
#     )
#     grids_by_ward: dict[str, list[str]] = {}
#     for gr in grid_rows:
#         grids_by_ward.setdefault(gr["ward"], []).append(gr["name"])

#     created = []
#     skipped = {"no_grid_for_ward": [], "validator_busy": [], "not_enough_buildings": [], "errors": []}

#     # -------- Iterate each (user, ward) --------
#     for up in user_perms:
#         validator = up["user"]
#         ward_name = up["for_value"]

#         # Skip if already has a pending summary
#         if validator in validators_in_use:
#             skipped["validator_busy"].append({"user": validator, "ward": ward_name})
#             continue

#         # Candidate grids for the ward
#         candidates = [g for g in grids_by_ward.get(ward_name, []) if g not in pending_grids]
#         if not candidates:
#             skipped["no_grid_for_ward"].append({"user": validator, "ward": ward_name})
#             continue

#         picked_summary_name = None

#         # Deterministic iteration (no shuffle)
#         for grid_name in candidates:
#             try:
#                 # Slide in non-overlapping 7-day windows; collect unique until min_count/max_count or today
#                 # Window [ws, we): inclusive start, exclusive end
#                 window_start = datetime.combine(start_date, datetime.min.time())
#                 window_end = datetime.combine(min(start_date + timedelta(days=7), today) + timedelta(days=1), datetime.min.time())
#                 all_rows: list[dict] = []
#                 seen: set[str] = set()
#                 actual_end_date = window_end.date() - timedelta(days=1)

#                 while True:
#                     need = max_count - len(all_rows)
#                     if need <= 0:
#                         break

#                     batch = _fetch_valid_buildings_sql_window(
#                         grid_name=grid_name,
#                         start_ts=window_start,
#                         end_ts_excl=window_end,
#                         cap=need,
#                     )

#                     # Deduplicate by building name
#                     new_items = []
#                     for r in batch:
#                         nm = r["name"]
#                         if nm in seen:
#                             continue
#                         seen.add(nm)
#                         new_items.append(r)

#                     if new_items:
#                         all_rows.extend(new_items)
#                         # Track the *actual* end date reached (from the last row’s end_time)
#                         last_dt = new_items[-1]["end_time"]
#                         if last_dt:
#                             actual_end_date = max(actual_end_date, last_dt.date())

#                     # If we've met min_count, we can stop early (still no duplicates)
#                     if len(all_rows) >= int(min_count):
#                         break

#                     # Advance the window; stop if we've reached today's window already
#                     next_start_day = (window_end.date())  # since window_end is exclusive, this is the next day
#                     if next_start_day > today:
#                         break

#                     window_start = datetime.combine(next_start_day, datetime.min.time())
#                     next_end_day = min(next_start_day + timedelta(days=7), today)
#                     window_end = datetime.combine(next_end_day + timedelta(days=1), datetime.min.time())

#                     # If window_start has passed today, break
#                     if window_start.date() > today:
#                         break

#                 # Decide if this grid qualifies (no padding)
#                 if len(all_rows) < int(min_count):
#                     # Try next candidate grid
#                     continue

#                 # ------------- Create parent & bulk insert children -------------
#                 parent = frappe.get_doc({
#                     "doctype": "Enumeration Validation Summary",
#                     "validator": validator,
#                     "start_date": start_date.isoformat(),
#                     "end_date": actual_end_date.isoformat(),  # actual end date reached
#                     "status": "Pending",
#                     "grid": grid_name,
#                     "total_buildings": len(all_rows), 
#                     "pending_validations": len(all_rows),         # set total to count of unique valid buildings
#                 })
#                 parent.flags.ignore_mandatory = True
#                 parent.insert(ignore_permissions=True)
#                 summary_name = parent.name

#                 # Prepare child rows
#                 ts = now()
#                 owner = frappe.session.user

#                 # Child: Enumeration Sample Responses
#                 esr_fields = [
#                     "name","owner","creation","modified","last_modified","modified_by",
#                     "parent","parenttype","parentfield","idx","docstatus",
#                     "doctype_name","record","settlement","enumerator","status",
#                     "geolocation","building_picture","building_picture_2",
#                 ]
#                 esr_values = []
#                 for idx, b in enumerate(all_rows, start=1):
#                     esr_values.append([
#                         frappe.generate_hash(length=12),
#                         owner, ts, ts, ts, owner,
#                         summary_name, "Enumeration Validation Summary", "enumeration_sample_responses", idx, 0,
#                         "Building", b.get("name"), b.get("settlement"), b.get("owner"), "Pending",
#                         b.get("geolocation"), b.get("building_picture"), b.get("building_picture_2"),
#                     ])

#                 # Child: Records Under Validation
#                 ruv_fields = [
#                     "name","owner","creation","modified","modified_by",
#                     "parent","parenttype","parentfield","idx","docstatus",
#                     "doctype_name","record","settlement","enumerator","status",
#                 ]
#                 ruv_values = []
#                 for idx, b in enumerate(all_rows, start=1):
#                     ruv_values.append([
#                         frappe.generate_hash(length=12),
#                         owner, ts, ts, owner,
#                         summary_name, "Enumeration Validation Summary", "records_under_validation", idx, 0,
#                         "Building", b.get("name"), b.get("settlement"), b.get("owner"), "Pending",
#                     ])

#                 # Bulk insert children
#                 _chunked_bulk_insert("Enumeration Sample Responses", esr_fields, esr_values)
#                 _chunked_bulk_insert("Records Under Validation", ruv_fields, ruv_values)

#                 # --- compute & persist rollups on the parent ---
#                 pending = len(all_rows)
#                 total = len(all_rows)

#                 frappe.db.set_value(
#                     "Enumeration Validation Summary",
#                     summary_name,
#                     {
#                         "pending_validations": pending,
#                         "total_buildings": total,
#                     },
#                     update_modified=False,  # avoid bumping modified if you prefer
#                 )

#                 # reflect the values in the object we’re about to echo back
#                 parent.reload()


#                 frappe.db.commit()

#                 created.append({
#                     "summary": summary_name,
#                     "validator": validator,
#                     "grid": grid_name,
#                     "start_date": parent.start_date,
#                     "end_date": parent.end_date,
#                     "count": len(all_rows),
#                     "total_buildings": len(all_rows),
#                     "pending_validations": len(all_rows),
#                 })

#                 # Mark as in-use to avoid duplicates in this run
#                 pending_grids.add(grid_name)
#                 validators_in_use.add(validator)
#                 picked_summary_name = summary_name
#                 break

#             except Exception as e:
#                 frappe.db.rollback()
#                 skipped["errors"].append(
#                     {"user": validator, "ward": ward_name, "grid": grid_name, "error": str(e)}
#                 )
#                 # try next candidate

#         if not picked_summary_name:
#             skipped["not_enough_buildings"].append({"user": validator, "ward": ward_name})

#     return {
#         "created": created,
#         "skipped": skipped,
#         "params": {
#             "start_date": start_date.isoformat(),
#             "min_count": int(min_count),
#             "max_count": int(max_count),
#         },
#     }


import math
import itertools
import frappe
from datetime import datetime, date, timedelta
from frappe.utils import now, getdate


# ---------------------------
# Helpers
# ---------------------------

def _parse_date(s: str | None, fallback: date | None = None) -> date:
    """Parse 'YYYY-MM-DD' or 'DD-MM-YYYY' to date; if empty use fallback or 2025-08-01."""
    if not s:
        return fallback or date(2025, 8, 1)
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    frappe.throw(f"Invalid date format: {s}. Use YYYY-MM-DD or DD-MM-YYYY.")
    return date.today()  # unreachable


def _chunked_bulk_insert(doctype: str, fields: list[str], values: list[list], chunk_size: int = 1000):
    """Avoid max_allowed_packet issues; safe no-op for empty values."""
    if not values:
        return
    for i in range(0, len(values), chunk_size):
        frappe.db.bulk_insert(doctype, fields, values[i:i + chunk_size])


def _fetch_valid_buildings_sql_window(
    *, ward_name: str, start_ts: datetime, end_ts_excl: datetime, cap: int
) -> list[dict]:
    """
    Fetch 'valid' buildings in a ward, within a NON-overlapping time window.

    Common conditions:
      - b.status = 'Submitted'
      - b.ward   = ward_name
      - b.end_time IS NOT NULL AND start_ts <= end_time < end_ts_excl
      - b.settlement is Approved

    Valid building logic:

      1) Non-residential:
         - b.building_type = 'Non-residential'
         - No Household / Children requirement.

      2) Residential:
         - b.building_type = 'Residential'
         - EXISTS at least one Household:
              h.building = b.name AND h.status = 'Submitted'
         - Children are irrelevant (whether they exist or not, still valid).

    Returns up to `cap` rows ordered by end_time ASC.
    """

    rows = frappe.db.sql(
        """
        SELECT
            b.name,
            b.settlement,
            b.owner,
            b.geolocation,
            b.building_picture,
            b.building_picture_2,
            b.end_time,
            b.building_type
        FROM `tabBuilding` AS b
        WHERE b.status = 'Submitted'
          AND b.ward = %(ward)s
          AND b.end_time IS NOT NULL
          AND b.end_time >= %(start_ts)s
          AND b.end_time <  %(end_ts)s
          AND EXISTS (
                SELECT 1 FROM `tabSettlement` s
                WHERE s.name = b.settlement AND s.status = 'Approved'
          )
          AND (
                -- Non-residential: accept as long as it passes the common filters above
                (b.building_type = 'Non-residential')

                OR

                -- Residential: must have at least one Submitted Household
                (
                    b.building_type = 'Residential'
                    AND EXISTS (
                        SELECT 1 FROM `tabHousehold` h
                        WHERE h.building = b.name AND h.status = 'Submitted' LIMIT 1
                    )
                )
          )
        ORDER BY b.end_time ASC
        LIMIT %(limit)s
        """,
        {
            "ward": ward_name,
            "start_ts": start_ts,
            "end_ts": end_ts_excl,
            "limit": int(cap),
        },
        as_dict=True,
    )
    return rows


# # ---------------------------
# # Main function (per WARD)
# # ---------------------------

# @frappe.whitelist()
# def assign_enumeration_validations():
#     """
#     Assign Enumeration Validation Summary per (validator, ward), using global settings from
#     the Single doctype "Enumeration Validation Settings".

#     Settings used:
#       - minimum_no_of_records  -> min_count
#       - maximum_no_of_records  -> max_count
#       - start_date             -> global start date
#       - end_date               -> global end date (if empty, defaults to today)

#     Behaviour:
#       - Per *ward* only (grids are ignored).
#       - Uses Buildings in that ward that pass the validity rules in _fetch_valid_buildings_sql_window.
#       - Slides non-overlapping 7-day windows over [start_date, end_date_limit].
#       - Collects unique valid buildings until:
#           min_count <= N <= max_count, or data exhausted.
#       - Creates ONE Enumeration Validation Summary per validator+ward if min_count met.
#       - Records Under Validation = ALL valid buildings.
#       - Enumeration Sample Responses = 10% of valid buildings (rounded up),
#         sampled across approved Settlements in that ward in a round-robin fashion.
#       - Updates Enumeration Validation Settings.result_from_last_run with a human-readable summary.
#     """

#     # -------- Load settings from Single doctype --------
#     settings = frappe.get_single("Enumeration Validation Settings")

#     # Dates from settings (can be Date or string)
#     start_date = _parse_date(str(settings.start_date) if settings.start_date else None)

#     today = date.today()
#     if start_date > today:
#         frappe.throw("Start Date in Enumeration Validation Settings cannot be in the future.")

#     # If there is no end_date in settings, use today
#     if settings.end_date:
#         end_setting = getdate(settings.end_date)
#         end_date_limit = min(end_setting, today)
#     else:
#         end_date_limit = today

#     if start_date > end_date_limit:
#         frappe.throw("Start Date is after End Date / today. Please adjust Enumeration Validation Settings.")

#     # Counts from settings
#     min_count = int(settings.minimum_no_of_records or 15)
#     max_count = int(settings.maximum_no_of_records or 125)
#     if max_count < min_count:
#         frappe.throw("maximum_no_of_records must be >= minimum_no_of_records in Enumeration Validation Settings.")

#     # -------- SQL preload pending validators & wards --------
#     pending_rows = frappe.db.sql(
#         """
#         SELECT validator, ward
#         FROM `tabEnumeration Validation Summary`
#         WHERE status = 'Pending'
#         """,
#         as_dict=True,
#     )
#     validators_in_use = {r["validator"] for r in pending_rows if r.get("validator")}
#     wards_in_use = {r["ward"] for r in pending_rows if r.get("ward")}

#     # -------- User-permission (Ward) --------
#     user_perms = frappe.get_all(
#         "User Permission",
#         filters={"allow": "Ward"},
#         fields=["user", "for_value"],
#     )
#     user_perms = [up for up in user_perms if up.get("user") and up.get("for_value")]
#     if not user_perms:
#         return {"created": [], "skipped": {"no_wards": "No User Permission rows for Ward found."}}

#     created = []
#     skipped = {
#         "no_wards": [],
#         "validator_busy": [],
#         "ward_in_use": [],
#         "not_enough_buildings": [],
#         "errors": [],
#     }

#     # -------- Iterate each (user, ward) --------
#     for up in user_perms:
#         validator = up["user"]
#         ward_name = up["for_value"]

#         # 1) Skip if validator already has a Pending summary anywhere
#         if validator in validators_in_use:
#             skipped["validator_busy"].append({"user": validator, "ward": ward_name})
#             continue

#         # 2) Skip if this ward already has a Pending summary
#         if ward_name in wards_in_use:
#             skipped["ward_in_use"].append({"user": validator, "ward": ward_name})
#             continue

#         try:
#             # -------- Slide non-overlapping 7-day windows over [start_date, end_date_limit] --------
#             window_start = datetime.combine(start_date, datetime.min.time())
#             first_block_end_day = min(start_date + timedelta(days=7), end_date_limit)
#             window_end = datetime.combine(first_block_end_day + timedelta(days=1), datetime.min.time())

#             all_rows: list[dict] = []
#             seen: set[str] = set()
#             actual_end_date = start_date

#             while True:
#                 need = max_count - len(all_rows)
#                 if need <= 0:
#                     break

#                 batch = _fetch_valid_buildings_sql_window(
#                     ward_name=ward_name,
#                     start_ts=window_start,
#                     end_ts_excl=window_end,
#                     cap=need,
#                 )

#                 # Deduplicate by building name
#                 new_items = []
#                 for r in batch:
#                     nm = r["name"]
#                     if nm in seen:
#                         continue
#                     seen.add(nm)
#                     new_items.append(r)

#                 if new_items:
#                     all_rows.extend(new_items)
#                     last_dt = new_items[-1]["end_time"]
#                     if last_dt:
#                         last_date = min(last_dt.date(), end_date_limit)
#                         if last_date > actual_end_date:
#                             actual_end_date = last_date

#                 # If we've met min_count, we can stop early
#                 if len(all_rows) >= min_count:
#                     break

#                 # Advance to the next non-overlapping window
#                 next_start_day = window_end.date()  # window_end is exclusive; this is the next day
#                 if next_start_day > end_date_limit:
#                     break

#                 window_start = datetime.combine(next_start_day, datetime.min.time())
#                 next_end_day = min(next_start_day + timedelta(days=7), end_date_limit)
#                 window_end = datetime.combine(next_end_day + timedelta(days=1), datetime.min.time())

#                 if window_start.date() > end_date_limit:
#                     break

#             # Decide if this ward qualifies (no padding)
#             if len(all_rows) < min_count:
#                 skipped["not_enough_buildings"].append({"user": validator, "ward": ward_name})
#                 continue

#             if actual_end_date < start_date:
#                 actual_end_date = end_date_limit

#             total_buildings = len(all_rows)

#             # -------- Determine sample buildings = 10% of all_rows (ceil) --------
#             sample_count = max(1, math.ceil(total_buildings * 0.10))

#             # Fetch approved settlements in this ward (for round-robin sampling)
#             settlement_rows = frappe.db.get_all(
#                 "Settlement",
#                 filters={"ward": ward_name, "status": "Approved"},
#                 fields=["name"],
#             )
#             settlement_names = [s["name"] for s in settlement_rows]

#             # Fallback: if for some reason there are no settlements from query,
#             # derive from the buildings themselves.
#             if not settlement_names:
#                 settlement_names = sorted({b.get("settlement") for b in all_rows if b.get("settlement")})

#             # Group buildings by settlement
#             buildings_by_settlement: dict[str, list[dict]] = {s: [] for s in settlement_names}
#             for b in all_rows:
#                 s_name = b.get("settlement")
#                 if s_name:
#                     buildings_by_settlement.setdefault(s_name, []).append(b)

#             # Round-robin selection across settlements
#             selected_sample_buildings: list[dict] = []
#             if settlement_names and total_buildings > 0:
#                 cycle_settlements = itertools.cycle(settlement_names)
#                 while len(selected_sample_buildings) < sample_count:
#                     s = next(cycle_settlements)
#                     bucket = buildings_by_settlement.get(s, [])
#                     if bucket:
#                         selected_sample_buildings.append(bucket.pop(0))

#                     # Safety: if all buckets are empty, break
#                     if all(len(lst) == 0 for lst in buildings_by_settlement.values()):
#                         break
#             else:
#                 # If somehow no settlements, just take first sample_count buildings
#                 selected_sample_buildings = all_rows[:sample_count]

#             # ------------- Create parent & bulk insert children -------------
#             parent = frappe.get_doc({
#                 "doctype": "Enumeration Validation Summary",
#                 "validator": validator,
#                 "start_date": start_date.isoformat(),
#                 "end_date": actual_end_date.isoformat(),
#                 "status": "Pending",
#                 "ward": ward_name,
#                 "total_buildings": total_buildings,
#                 "pending_validations": total_buildings,
#             })
#             parent.flags.ignore_mandatory = True
#             parent.insert(ignore_permissions=True)
#             summary_name = parent.name

#             ts = now()
#             owner = frappe.session.user

#             # -------- Child: Enumeration Sample Responses (10% sample) --------
#             esr_fields = [
#                 "name", "owner", "creation", "modified", "last_modified", "modified_by",
#                 "parent", "parenttype", "parentfield", "idx", "docstatus",
#                 "doctype_name", "record", "settlement", "enumerator", "status",
#                 "geolocation", "building_picture", "building_picture_2",
#             ]
#             esr_values = []
#             for idx, b in enumerate(selected_sample_buildings, start=1):
#                 esr_values.append([
#                     frappe.generate_hash(length=12),  # child row name
#                     owner, ts, ts, ts, owner,
#                     summary_name, "Enumeration Validation Summary", "enumeration_sample_responses", idx, 0,
#                     "Building",                      # doctype_name
#                     b.get("name"),                   # record
#                     b.get("settlement"),             # settlement
#                     b.get("owner"),                  # enumerator
#                     "Pending",                       # status
#                     b.get("geolocation"),            # geolocation
#                     b.get("building_picture"),       # building_picture
#                     b.get("building_picture_2"),     # building_picture_2
#                 ])

#             # -------- Child: Records Under Validation (all valid buildings) --------
#             ruv_fields = [
#                 "name", "owner", "creation", "modified", "modified_by",
#                 "parent", "parenttype", "parentfield", "idx", "docstatus",
#                 "doctype_name", "record", "settlement", "enumerator", "status",
#             ]
#             ruv_values = []
#             for idx, b in enumerate(all_rows, start=1):
#                 ruv_values.append([
#                     frappe.generate_hash(length=12),  # child row name
#                     owner, ts, ts, owner,
#                     summary_name, "Enumeration Validation Summary", "records_under_validation", idx, 0,
#                     "Building",                      # doctype_name
#                     b.get("name"),                   # record
#                     b.get("settlement"),
#                     b.get("owner"),
#                     "Pending",
#                 ])

#             # Bulk insert children
#             _chunked_bulk_insert("Enumeration Sample Responses", esr_fields, esr_values)
#             _chunked_bulk_insert("Records Under Validation", ruv_fields, ruv_values)

#             frappe.db.set_value(
#                 "Enumeration Validation Summary",
#                 summary_name,
#                 {
#                     "pending_validations": total_buildings,
#                     "total_buildings": total_buildings,
#                 },
#                 update_modified=False,
#             )

#             parent.reload()
#             frappe.db.commit()

#             created.append({
#                 "summary": summary_name,
#                 "validator": validator,
#                 "ward": ward_name,
#                 "start_date": parent.start_date,
#                 "end_date": parent.end_date,
#                 "count": total_buildings,
#                 "total_buildings": total_buildings,
#                 "pending_validations": total_buildings,
#                 "sampled_buildings": len(selected_sample_buildings),
#             })

#             wards_in_use.add(ward_name)
#             validators_in_use.add(validator)

#         except Exception as e:
#             frappe.db.rollback()
#             skipped["errors"].append(
#                 {"user": validator, "ward": ward_name, "error": str(e)}
#             )

#     # -------- Update Enumeration Validation Settings.result_from_last_run --------
#     run_time = now()
#     lines = []
#     lines.append(f"Last Run: {run_time}")
#     lines.append("")
#     lines.append(f"Total Summaries Created: {len(created)}")
#     lines.append("")

#     if created:
#         lines.append("Created Summaries:")
#         for c in created:
#             lines.append(
#                 f"- Summary: {c['summary']}\n"
#                 f"  Validator: {c['validator']}\n"
#                 f"  Ward: {c['ward']}\n"
#                 f"  Start Date: {c['start_date']}\n"
#                 f"  End Date: {c['end_date']}\n"
#                 f"  Total Buildings: {c['total_buildings']}\n"
#                 f"  Sampled (Enumeration Sample Responses): {c['sampled_buildings']}"
#             )
#         lines.append("")

#     lines.append("Skipped:")
#     for key, entries in skipped.items():
#         lines.append(f"  {key}: {len(entries)}")
#         for e in entries[:10]:  # cap detail so text field doesn't explode
#             line_bits = [f"    - {e}"]
#             lines.extend(line_bits)
#         if len(entries) > 10:
#             lines.append(f"    ... (+{len(entries) - 10} more)")

#     result_text = "\n".join(lines)

#     # Update the Single doctype field
#     frappe.db.set_value(
#         "Enumeration Validation Settings",
#         None,  # name for Single doctypes
#         "result_from_last_run",
#         result_text,
#     )

#     return {
#         "created": created,
#         "skipped": skipped,
#         "params": {
#             "start_date": start_date.isoformat(),
#             "end_date_limit": end_date_limit.isoformat(),
#             "min_count": int(min_count),
#             "max_count": int(max_count),
#         },
#     }

# ---------------------------
# Main function (per WARD)
# ---------------------------

@frappe.whitelist()
def assign_enumeration_validations():
    """
    Assign Enumeration Validation Summary per (validator, ward), using global settings from
    the Single doctype "Enumeration Validation Settings".

    Settings used:
      - minimum_no_of_records  -> min_count
      - maximum_no_of_records  -> max_count
      - start_date             -> global start date
      - end_date               -> global end date (if empty, defaults to today)

    Behaviour:
      - Per *ward* only (grids are ignored).
      - Uses Buildings in that ward that pass the validity rules in _fetch_valid_buildings_sql_window.
      - Slides non-overlapping 7-day windows over [start_date, end_date_limit].
      - Collects unique valid buildings until:
          min_count <= N <= max_count, or data exhausted.
      - Creates ONE Enumeration Validation Summary per validator+ward if min_count met.
      - Records Under Validation = ALL valid buildings.
      - Enumeration Sample Responses = 10% of valid buildings per enumerator (owner),
        i.e. for each owner, ceil(10% of their valid buildings).
      - Updates Enumeration Validation Settings.result_from_last_run with a human-readable summary.
    """

    # -------- Load settings from Single doctype --------
    settings = frappe.get_single("Enumeration Validation Settings")

    # Dates from settings (can be Date or string)
    start_date = _parse_date(str(settings.start_date) if settings.start_date else None)

    today = date.today()
    if start_date > today:
        frappe.throw("Start Date in Enumeration Validation Settings cannot be in the future.")

    # If there is no end_date in settings, use today
    if settings.end_date:
        end_setting = getdate(settings.end_date)
        end_date_limit = min(end_setting, today)
    else:
        end_date_limit = today

    if start_date > end_date_limit:
        frappe.throw("Start Date is after End Date / today. Please adjust Enumeration Validation Settings.")

    # Counts from settings
    min_count = int(settings.minimum_no_of_records or 15)
    max_count = int(settings.maximum_no_of_records or 125)
    if max_count < min_count:
        frappe.throw("maximum_no_of_records must be >= minimum_no_of_records in Enumeration Validation Settings.")

    # -------- SQL preload pending validators & wards --------
    pending_rows = frappe.db.sql(
        """
        SELECT validator, ward
        FROM `tabEnumeration Validation Summary`
        WHERE status = 'Pending'
        """,
        as_dict=True,
    )
    validators_in_use = {r["validator"] for r in pending_rows if r.get("validator")}
    wards_in_use = {r["ward"] for r in pending_rows if r.get("ward")}

    # -------- User-permission (Ward) --------
    user_perms = frappe.get_all(
        "User Permission",
        filters={"allow": "Ward"},
        fields=["user", "for_value"],
    )
    user_perms = [up for up in user_perms if up.get("user") and up.get("for_value")]
    if not user_perms:
        return {"created": [], "skipped": {"no_wards": "No User Permission rows for Ward found."}}

    created = []
    skipped = {
        "no_wards": [],
        "validator_busy": [],
        "ward_in_use": [],
        "not_enough_buildings": [],
        "errors": [],
    }

    # -------- Iterate each (user, ward) --------
    for up in user_perms:
        validator = up["user"]
        ward_name = up["for_value"]

        # 1) Skip if validator already has a Pending summary anywhere
        if validator in validators_in_use:
            skipped["validator_busy"].append({"user": validator, "ward": ward_name})
            continue

        # 2) Skip if this ward already has a Pending summary
        if ward_name in wards_in_use:
            skipped["ward_in_use"].append({"user": validator, "ward": ward_name})
            continue

        try:
            # -------- Slide non-overlapping 7-day windows over [start_date, end_date_limit] --------
            window_start = datetime.combine(start_date, datetime.min.time())
            first_block_end_day = min(start_date + timedelta(days=7), end_date_limit)
            window_end = datetime.combine(first_block_end_day + timedelta(days=1), datetime.min.time())

            all_rows: list[dict] = []
            seen: set[str] = set()
            actual_end_date = start_date

            while True:
                need = max_count - len(all_rows)
                if need <= 0:
                    break

                batch = _fetch_valid_buildings_sql_window(
                    ward_name=ward_name,
                    start_ts=window_start,
                    end_ts_excl=window_end,
                    cap=need,
                )

                # Deduplicate by building name
                new_items = []
                for r in batch:
                    nm = r["name"]
                    if nm in seen:
                        continue
                    seen.add(nm)
                    new_items.append(r)

                if new_items:
                    all_rows.extend(new_items)
                    last_dt = new_items[-1]["end_time"]
                    if last_dt:
                        last_date = min(last_dt.date(), end_date_limit)
                        if last_date > actual_end_date:
                            actual_end_date = last_date

                # If we've met min_count, we can stop early
                if len(all_rows) >= min_count:
                    break

                # Advance to the next non-overlapping window
                next_start_day = window_end.date()  # window_end is exclusive; this is the next day
                if next_start_day > end_date_limit:
                    break

                window_start = datetime.combine(next_start_day, datetime.min.time())
                next_end_day = min(next_start_day + timedelta(days=7), end_date_limit)
                window_end = datetime.combine(next_end_day + timedelta(days=1), datetime.min.time())

                if window_start.date() > end_date_limit:
                    break

            # Decide if this ward qualifies (no padding)
            if len(all_rows) < min_count:
                skipped["not_enough_buildings"].append({"user": validator, "ward": ward_name})
                continue

            if actual_end_date < start_date:
                actual_end_date = end_date_limit

            total_buildings = len(all_rows)

            # -------- Determine sample buildings = 10% per enumerator (owner) --------
            buildings_by_owner: dict[str, list[dict]] = {}
            for b in all_rows:
                owner = (b.get("owner") or "").strip()
                if not owner:
                    # If needed, you can handle owner-less buildings separately
                    continue
                buildings_by_owner.setdefault(owner, []).append(b)

            selected_sample_buildings: list[dict] = []
            for owner, owner_buildings in buildings_by_owner.items():
                n = len(owner_buildings)
                sample_n = max(1, math.ceil(n * 0.10))  # 10% per enumerator, at least 1
                # Deterministic: take first N. Use random.sample(...) if you want randomness.
                selected_sample_buildings.extend(owner_buildings[:sample_n])

            # ------------- Create parent & bulk insert children -------------
            parent = frappe.get_doc({
                "doctype": "Enumeration Validation Summary",
                "validator": validator,
                "start_date": start_date.isoformat(),
                "end_date": actual_end_date.isoformat(),
                "status": "Pending",
                "ward": ward_name,
                "total_buildings": total_buildings,
                "pending_validations": total_buildings,
            })
            parent.flags.ignore_mandatory = True
            parent.insert(ignore_permissions=True)
            summary_name = parent.name

            ts = now()
            owner_user = frappe.session.user

            # -------- Child: Enumeration Sample Responses (10% per enumerator) --------
            esr_fields = [
                "name", "owner", "creation", "modified", "last_modified", "modified_by",
                "parent", "parenttype", "parentfield", "idx", "docstatus",
                "doctype_name", "record", "settlement", "enumerator", "status",
                "geolocation", "building_picture", "building_picture_2",
            ]
            esr_values = []
            for idx, b in enumerate(selected_sample_buildings, start=1):
                esr_values.append([
                    frappe.generate_hash(length=12),  # child row name
                    owner_user, ts, ts, ts, owner_user,
                    summary_name, "Enumeration Validation Summary", "enumeration_sample_responses", idx, 0,
                    "Building",                      # doctype_name
                    b.get("name"),                   # record
                    b.get("settlement"),             # settlement
                    b.get("owner"),                  # enumerator
                    "Pending",                       # status
                    b.get("geolocation"),            # geolocation
                    b.get("building_picture"),       # building_picture
                    b.get("building_picture_2"),     # building_picture_2
                ])

            # -------- Child: Records Under Validation (all valid buildings) --------
            ruv_fields = [
                "name", "owner", "creation", "modified", "modified_by",
                "parent", "parenttype", "parentfield", "idx", "docstatus",
                "doctype_name", "record", "settlement", "enumerator", "status",
            ]
            ruv_values = []
            for idx, b in enumerate(all_rows, start=1):
                ruv_values.append([
                    frappe.generate_hash(length=12),  # child row name
                    owner_user, ts, ts, owner_user,
                    summary_name, "Enumeration Validation Summary", "records_under_validation", idx, 0,
                    "Building",                      # doctype_name
                    b.get("name"),                   # record
                    b.get("settlement"),
                    b.get("owner"),
                    "Pending",
                ])

            # Bulk insert children
            _chunked_bulk_insert("Enumeration Sample Responses", esr_fields, esr_values)
            _chunked_bulk_insert("Records Under Validation", ruv_fields, ruv_values)

            frappe.db.set_value(
                "Enumeration Validation Summary",
                summary_name,
                {
                    "pending_validations": total_buildings,
                    "total_buildings": total_buildings,
                },
                update_modified=False,
            )

            parent.reload()
            frappe.db.commit()

            created.append({
                "summary": summary_name,
                "validator": validator,
                "ward": ward_name,
                "start_date": parent.start_date,
                "end_date": parent.end_date,
                "count": total_buildings,
                "total_buildings": total_buildings,
                "pending_validations": total_buildings,
                "sampled_buildings": len(selected_sample_buildings),
            })

            wards_in_use.add(ward_name)
            validators_in_use.add(validator)

        except Exception as e:
            frappe.db.rollback()
            skipped["errors"].append(
                {"user": validator, "ward": ward_name, "error": str(e)}
            )

    # -------- Update Enumeration Validation Settings.result_from_last_run --------
    run_time = now()
    lines = []
    lines.append(f"Last Run: {run_time}")
    lines.append("")
    lines.append(f"Total Summaries Created: {len(created)}")
    lines.append("")

    if created:
        lines.append("Created Summaries:")
        for c in created:
            lines.append(
                f"- Summary: {c['summary']}\n"
                f"  Validator: {c['validator']}\n"
                f"  Ward: {c['ward']}\n"
                f"  Start Date: {c['start_date']}\n"
                f"  End Date: {c['end_date']}\n"
                f"  Total Buildings: {c['total_buildings']}\n"
                f"  Sampled (Enumeration Sample Responses): {c['sampled_buildings']}"
            )
        lines.append("")

    lines.append("Skipped:")
    for key, entries in skipped.items():
        lines.append(f"  {key}: {len(entries)}")
        for e in entries[:10]:  # cap detail so text field doesn't explode
            lines.append(f"    - {e}")
        if len(entries) > 10:
            lines.append(f"    ... (+{len(entries) - 10} more)")

    result_text = "\n".join(lines)

    frappe.db.set_value(
        "Enumeration Validation Settings",
        None,  # name for Single doctypes
        "result_from_last_run",
        result_text,
    )

    return {
        "created": created,
        "skipped": skipped,
        "params": {
            "start_date": start_date.isoformat(),
            "end_date_limit": end_date_limit.isoformat(),
            "min_count": int(min_count),
            "max_count": int(max_count),
        },
    }




def auto_assign_enumeration_validations():
    # Get the single settings document
    settings = frappe.get_single("Enumeration Validation Settings")

    # If autocreate_summaries is not checked (0 / False), do nothing
    if not settings.autocreate_summaries:
        return

    assignments = assign_enumeration_validations()