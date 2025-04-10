
import frappe
import math
import random
import json

# Predefined questions with Doctype, Field, and Expected Data Type
QUESTIONS = {
    "last_name_match": {
        "question": "Does the last name of the child match with the facility data?",
        "doctype": "Vaccination",
        "field": "last_name",
        "type": "Data"
    },
    "first_name_match": {
        "question": "Does the first name of the child match with the facility data",
        "doctype": "Vaccination",
        "field": "first_name",
        "type": "Data"
    },
    "date_of_birth_match": {
        "question": "Does the date of birth of the child match with the facility data?",
        "doctype": "Vaccination",
        "field": "date_of_birth",
        "type": "Date"
    },
    "child_gender_match": {
        "question": "Does the gender of the child match with the facility data?",
        "doctype": "Vaccination",
        "field": "gender",
        "type": "Select",
        "options": ["Male", "Female"]
    },
    "child_vaccines_match": {
        "question": "Does the antigen recorded on the register accurately reflect vaccines administered to the child?",
        "doctype": "Vaccination",
        "field": "vaccines_taken",
        "type": "Table"
    }
}

@frappe.whitelist()
def get_vaccination_validation_questions(vaccination_name):
    """
    Fetches responses for vaccination validation questions.
    - Returns structured validation data.
    
    :param building_name: Name of the Building.
    :return: Dictionary of questions with their fetched values and types.
    """
    responses = {}

    # Fetch Vaccination Information
    vaccination = frappe.db.get_value("Vaccination", vaccination_name, ["last_name", "first_name", "date_of_birth", "gender", "vaccines_taken"], as_dict=True)
    

    if not vaccination:
        return {"error": f"Vaccination '{vaccination_name}' not found"}

    # Continue with building the response
    for key, item in QUESTIONS.items():
        if item["doctype"] == "Vaccination":
            responses[key] = {
                "question": item["question"],
                "value": vaccination.get(item["field"]),
                "type": item["type"],
                "options": item["options"] if "options" in item else []
            }
    return responses


import frappe

@frappe.whitelist()
def get_vaccinations(health_facility=None, start_time=None, end_time=None):
    
    """
    Fetches vaccinations based on the provided health facility.
    """

    if not health_facility:
        return {"error": "Please provide a health facility."}
    if not start_time:
        return {"error": "Please provide a start time."}
    if not end_time:
        return {"error": "Please provide an end time."}
       
    
    vaccinations = frappe.db.sql("""
        SELECT name, facility, owner, full_name, last_name, first_name, date_of_birth, gender, vaccines_taken
        FROM `tabVaccination`
        WHERE status = 'Submitted'
        AND facility = %s
        AND creation BETWEEN %s AND %s
    """, (health_facility, start_time, end_time), as_dict=True)


    # Check if any vaccinations were found
    if not vaccinations:
        return {"error": "No vaccinations found."}

    return {
        "vaccinations": vaccinations
    }

@frappe.whitelist()
def get_vaccination_validation_summaries():
    """
    Fetches all Vaccination Validation Summaries for the logged-in user.
    """

    user = frappe.session.user
    if user == "Guest":
        return {"error": "You must be logged in to access this data."}

    # Check if the user has the "Vaccination Validator" role
    user_roles = frappe.get_roles(user)
    if "Vaccination Validator" not in user_roles:
        return {"error": "You do not have the required role to access this data."}
    

    results = frappe.db.sql("""
        SELECT 
            parent.name, 
            parent.health_facility,             
            parent.validator, 
            parent.status,
            parent.start_time,
            parent.end_time,
            parent.ward, 
            parent.local_government_area, 
            parent.state, 
            parent.modified
        FROM `tabVaccination Validation Summary` AS parent
        WHERE parent.validator = %s
    """, (user,), as_dict=True)

    # Add child records as a dictionary under each parent
    for row in results:
        child_records = frappe.db.get_list(
            "Vaccinations Under Validation",
            filters={"parent": row["name"]},
            fields=["vaccination", "full_name", "status AS vaccination_validation_status"],
            ignore_permissions=True
        )
        row["vaccinations"] = child_records  # Assign child records under 'vaccinations'

    return {
        "message": "Enumeration Validation Summaries fetched successfully.",
        "status": 200,
        "data": results

    }


# @frappe.whitelist()
# def get_buildings_to_validate_and_save(grid=None, ward=None):

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
    
#     existing_summaries = frappe.get_all(
#         "Enumeration Validation Summary",
#         filters={"validator": user, "status": ["in", ["Pending"]]},
#         fields=["name"]
#     )

#     if existing_summaries:
#         return {
#             "message": "You already have a pending validation summary. Please complete it before starting a new one.",
#             "status": 400
#         }
    

#     try:

#         # Ensure only one of grid or ward is supplied
#         if (grid and ward) or (not grid and not ward):
#             return {
#                 "message": "Please provide either Grid or Ward, but not both.",
#                 "status": 400
#             }

#         # Get buildings to validate
#         buildings_to_validate = get_buildings(grid=grid, ward=ward)

#         # Create and save Enumeration Validation Summary
#         summary = frappe.new_doc("Enumeration Validation Summary")

#         if grid:
#             # Fetch the ward value from the Grid doctype
#             grid_doc = frappe.get_doc("Grid", grid)
#             summary.grid = grid
#             summary.ward = grid_doc.ward
#         else:
#             summary.ward = ward

#         summary.start_time = frappe.utils.now_datetime()
#         summary.validator = frappe.session.user
#         summary.status = "Pending"

#         # Append all buildings
#         for building in buildings_to_validate.get("all_buildings", []):
#             summary.append("records_under_validation", {
#                 "doctype_name": building.get("form"),
#                 "record": building.get("name"),
#                 "settlement": building.get("settlement"),
#                 "enumerator": building.get("owner"),
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
#                 "status": "Pending",
#             })

#         summary.insert(ignore_permissions=True)
#         summary.save()

#         return {
#             "message": "Enumeration validation data saved successfully.",
#             "status": 200,
#             "buildings_to_validate": buildings_to_validate,
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
def get_facilities_to_validate():
    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {"message": "You must be logged in to access this data.", "status": 401}
    
    # Check if the user has the "Dashboard Viewer" role
    user_roles = frappe.get_roles(user)
    if "Vaccination Validator" not in user_roles:
        return {
            "message": "You do not have the required role to perform vaccination validation, please contact your Supervisor.",
            "status": 401
        }

    # Initialize filters
    filters = {}

    # Check User Permissions for the provided user
    user_permissions = frappe.get_all(
        'User Permission',
        filters={'user': user, 'allow': 'Facility'},
        fields=['for_value']
    )

    if user_permissions:
        # Extract the list of allowed Facilities from user permissions
        allowed_facilities = [permission['for_value'] for permission in user_permissions]
        allowed_facilities = frappe.get_all(
            'Facility',
            filters={'name': ['in', allowed_facilities]},
            fields=['name', 'facility_name']
        )

    # If no user permissions, fetch all wards in the specified local government areas
    else:
        return {
            "message": "You do not have access to any facilities. Please contact your Supervisor.",
            "status": 401
        }

    return {
        "message": "Facilities fetched successfully.",
        "status": 200,
        "data": allowed_facilities
    }

def process_vaccinations_before_submit(doc, method):
    pending_rows = []
    approved_count = 0
    total_rows = len(doc.vaccinations_under_validation)

    # 1. Check for pending rows and count approved
    for i, row in enumerate(doc.vaccinations_under_validation, start=1):
        if row.status == "Pending":
            pending_rows.append(str(i))
        elif row.status == "Approved":
            approved_count += 1

    # 2. If there are any pending rows, throw an error listing row numbers
    if pending_rows:
        frappe.throw(f"The following rows are still pending validation: {', '.join(pending_rows)}")

    # 3. Set status as Completed
    doc.status = "Completed"

    # 4. Set the validation percentage on the main document
    if total_rows > 0:
        doc.validation_percentage = math.ceil((approved_count / total_rows) * 100)
    else:
        doc.validation_percentage = 0.0

    # 5. Update linked Vaccination records based on each row's status
    for row in doc.vaccinations_under_validation:
        if not row.vaccination:
            continue  # skip if vaccination is not linked

        try:
            vaccination_doc = frappe.get_doc("Vaccination", row.vaccination)
            if row.status == "Approved":
                vaccination_doc.status = "Approved"
            elif row.status == "Returned":
                vaccination_doc.status = "Suspended"
            vaccination_doc.save()
        except frappe.DoesNotExistError:
            frappe.throw(f"Vaccination record not found: {row.vaccination}")
