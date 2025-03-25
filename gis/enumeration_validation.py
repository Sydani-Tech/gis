
import frappe
import random

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

    # Fetch all Children where status is "Submitted" for the selected Household
    children = frappe.db.sql("""
        SELECT name, first_name, last_name, full_name, gender, date_of_birth, vaccines_taken
        FROM `tabChildren`
        WHERE household = %s AND status = 'Submitted'
    """, household["name"], as_dict=True)
    
    # frappe.msgprint(children)
    

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

import frappe
import math
import itertools

@frappe.whitelist()
def get_buildings(grid=None, ward=None):
    """
    Fetches all submitted buildings filtered by Grid or Ward, validates them, 
    and selects 10% (rounded up) of valid buildings, ensuring rotation through Settlements.

    :param grid: The Grid filter (optional).
    :param ward: The Ward filter (optional).
    :return: Dictionary containing all buildings and the systematically selected buildings.
    """

    if not grid and not ward:
        return {"error": "Please provide either Grid or Ward as a filter."}

    # Fetch all Approved Settlements in the selected Grid or Ward
    settlement_filters = {"status": "Approved"}
    if grid:
        settlement_filters["grid"] = grid
    if ward:
        settlement_filters["ward"] = ward

    

    settlements = frappe.db.get_list("Settlement", filters=settlement_filters, fields=["name"])

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

    buildings = frappe.db.get_list("Building", filters=building_filters, fields=["name", "settlement", "owner"])
    # print("Total Buildings: ", len(buildings))

    if not buildings:
        return {"error": "No buildings found with the given filter."}

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
        "all_buildings": [{"form": "Building", **b} for b in buildings],
        "selected_buildings": [{"form": "Building", **b} for b in selected_buildings]
    }

@frappe.whitelist()
def get_enumeration_validation_summaries():
    """
    Fetches all Enumeration Validation Summaries for the logged-in user.
    """

    user = frappe.session.user
    if user == "Guest":
        return {"error": "You must be logged in to access this data."}

    

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
    """, (user,), as_dict=True)

    # Add child records as a dictionary under each parent
    for row in results:
        child_records = frappe.db.get_list(
            "Enumeration Sample Responses",
            filters={"parent": row["name"]},
            fields=["record AS building_name", "status AS building_validation_status"],
            ignore_permissions=True
        )
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
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error"
        }


@frappe.whitelist()
def get_buildings_to_validate_and_save(ward):

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Enumeration Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
            "status": 401
        }
    
    existing_summaries = frappe.get_all(
        "Enumeration Validation Summary",
        filters={"validator": user, "status": ["in", ["Pending"]]},
        fields=["name"]
    )

    if existing_summaries:
        return {
            "message": "You already have a pending validation summary. Please complete it before starting a new one.",
            "status": 400
        }
   
    try:
        buildings_to_validate = get_buildings(ward=ward)
        # frappe.msgprint(buildings_to_validate)

        # Save everything to an Enumeration Validation Summary doctype
        summary = frappe.new_doc("Enumeration Validation Summary")

        summary.ward = "City Center 1-Municipal Area Council-Fct"
        summary.start_time = frappe.utils.now_datetime()
        summary.validator = frappe.session.user
        summary.status = "Pending"

        for building in buildings_to_validate["all_buildings"]:
            summary.append("records_under_validation", {
                "doctype_name": building["form"],
                "record": building["name"],
                "settlement": building["settlement"],
                "enumerator": building["owner"]
            })

        for building in buildings_to_validate["selected_buildings"]:
            summary.append("enumeration_sample_responses", {
                "doctype_name": building["form"],
                "record": building["name"],
                "settlement": building["settlement"],
                "enumerator": building["owner"]
            })

        summary.insert(ignore_permissions=True)
        summary.save()

    
        return {
            "message": "Enumeration validation data saved successfully.",
            "status": 200
        }
    except Exception as e:
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": "error"
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
            "message": "You do not have the required role to perform enumeration validation, please contact your supervisor.",
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
                row.validation_responses = buildings_map[row.record]["validation_responses"]
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

    for record in records_under_validation:
        enumerator = record["enumerator"]
        building_name = record["record"]  # 'record' represents the building column

        # Determine new status based on whether the enumerator was marked as Returned
        new_status = "Returned" if enumerator in returned_enumerators else "Approved"

        # Update status in Records Under Validation
        frappe.db.set_value("Records Under Validation", record["name"], "status", new_status)

    # Commit changes after all updates
    frappe.db.commit()

def validate_status_is_approved(doc, method):
    if doc.status != "Approved":
        frappe.throw("Status must be 'Approved' to submit validation.")
