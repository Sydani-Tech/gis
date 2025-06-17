
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

    # Continue with thevaccination response
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
def get_vaccinations(health_facility=None, start_date=None, end_date=None):
    
    """
    Fetches vaccinations based on the provided health facility.
    """

    if not health_facility:
        return {"error": "Please provide a health facility."}
    if not start_date:
        return {"error": "Please provide a start date."}
    if not end_date:
        return {"error": "Please provide an end date."}
       
    
    vaccinations = frappe.db.sql("""
        SELECT name, facility, owner, full_name, last_name, first_name, date_of_birth, gender, vaccination_date, vaccines_taken
        FROM `tabVaccination`
        WHERE status = 'Submitted'
        AND facility = %s
        AND vaccination_date BETWEEN %s AND %s
    """, (health_facility, start_date, end_date), as_dict=True)


    # Check if any vaccinations were found
    if not vaccinations:
        return {"error": "No vaccinations found for the provided criteria. Try extending the date range."}

    return {
        "vaccinations": vaccinations
    }

@frappe.whitelist()
def get_vaccination_validation_summaries(name=None):
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
    

    if name:
        # Fetch a specific Vaccination Validation Summary
        results = frappe.db.sql("""
            SELECT 
                parent.name, 
                parent.health_facility,             
                parent.validator, 
                parent.status,
                parent.start_date,
                parent.end_date,
                parent.ward, 
                parent.local_government_area, 
                parent.state, 
                parent.modified
            FROM `tabVaccination Validation Summary` AS parent
            WHERE parent.name = %s AND parent.validator = %s
        """, (name, user), as_dict=True)

        if results:
            health_facility_name = frappe.get_value("Facility", results[0].health_facility, "facility_name")
            ward_name = frappe.get_value("Ward", results[0].ward, "ward")
            lga_name = frappe.get_value("Local Government Area", results[0].local_government_area, "local_government_area")
            results[0]["health_facility_name"] = health_facility_name
            results[0]["ward_name"] = ward_name
            results[0]["local_government_area_name"] = lga_name
        else:
            return {"message": "No Enumeration Validation summary found with the provided name.", "status": 404}

    else:
        # Fetch all Vaccination Validation Summaries for the logged-in user
        results = frappe.db.sql("""
            SELECT 
                parent.name, 
                parent.health_facility,             
                parent.validator, 
                parent.status,
                parent.start_date,
                parent.end_date,
                parent.ward, 
                parent.local_government_area, 
                parent.state, 
                parent.modified
            FROM `tabVaccination Validation Summary` AS parent
            WHERE parent.validator = %s
            ORDER BY parent.creation DESC
        """, (user,), as_dict=True)

        if results:

            for row in results:
                health_facility_name = frappe.get_value("Facility", row.health_facility, "facility_name")
                ward_name = frappe.get_value("Ward", row.ward, "ward")
                lga_name = frappe.get_value("Local Government Area", row.local_government_area, "local_government_area")

                row["health_facility_name"] = health_facility_name
                row["ward_name"] = ward_name
                row["local_government_area_name"] = lga_name
        else:
            return {"message": "No Vaccination Validation summaries found for the user. Please contact your supervisor.", "status": 404}

    # Add child records as a dictionary under each parent
    for row in results:

        if row.get("status") == "Pending":
            child_records = frappe.db.get_list(
                "Vaccinations Under Validation",
                filters={"parent": row["name"]},
                fields=["vaccination", "full_name", "gender", "date_of_birth", "vaccines_administered", "validation_answers", "last_modified", "status AS vaccination_validation_status"],
                ignore_permissions=True
            )

            for vaccination_record in child_records:
                vaccination_questions = get_vaccination_validation_questions(vaccination_record["vaccination"])
                vaccination_record["vaccination_questions"] = vaccination_questions

            row["vaccinations"] = child_records  # Assign child records under 'vaccinations'

        #else return empty list
        else:
            row["vaccinations"] = []
            
    return {
        "message": "Enumeration Validation Summaries fetched successfully.",
        "status": 200,
        "data": results

    }

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


@frappe.whitelist()
def create_vaccination_validation_summary(health_facility=None, start_date=None, end_date=None):

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
    
    # Check if ward is provided
    if not health_facility:
        return {
            "message": "Select a Health Facility to create a validation summary.",
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
        "Vaccination Validation Summary",
        filters={"validator": user, "status": ["in", ["Pending"]]},
        fields=["name"]
    )

    if existing_summaries:
        return {
            "message": "You already have a pending vaccination validation summary. Please complete it before creating a new one.",
            "status": 400
        }
    

    try:

        # Get buildings to validate
        vaccinations_to_validate = get_vaccinations(health_facility=health_facility, start_date=start_date, end_date=end_date)

        # Check if any vaccinations were found
        if "error" in vaccinations_to_validate:
            return {
                "message": vaccinations_to_validate["error"],
                "status": 400,
                "health_facility": health_facility,
                "start_date": start_date,
                "end_date": end_date
            }

        # Create and save Vaccination Validation Summary
        vaccination_validation_summary = frappe.new_doc("Vaccination Validation Summary")
        vaccination_validation_summary.health_facility = health_facility
        vaccination_validation_summary.validator = frappe.session.user
        vaccination_validation_summary.start_date = start_date
        vaccination_validation_summary.end_date = end_date
        vaccination_validation_summary.status = "Pending"
        vaccination_validation_summary.ward = frappe.get_value("Facility", health_facility, "ward")

        # Append all vaccinations to validate
        for vaccination in vaccinations_to_validate.get("vaccinations", []):
            vaccination_validation_summary.append("vaccinations_under_validation", {
                "first_name": vaccination.get("first_name"),
                "last_name": vaccination.get("last_name"),
                "gender": vaccination.get("gender"),
                "date_of_birth": vaccination.get("date_of_birth"),
                "full_name": vaccination.get("full_name"),
                "vaccination": vaccination.get("name"),
                "vaccination_date": vaccination.get("vaccination_date"),
                "vaccines_administered": vaccination.get("vaccines_taken"),
                "vaccinator": vaccination.get("owner"),
                "status": "Pending",
            })
        vaccination_validation_summary.insert(ignore_permissions=True)
        vaccination_validation_summary.save()

        validation_summary = get_vaccination_validation_summaries(name=vaccination_validation_summary.name)

        return {
            "message": "Vaccination validation data created successfully.",
            "status": 200,
            # "Vaccination Validation Summary": vaccination_validation_summary.name,
            # "vaccinations_to_validate": vaccinations_to_validate,
            "validation_summary": validation_summary,
        }

    except Exception as e:
        # frappe.log_error(f"Error in create_vaccination_validation_summary: {str(e)}", "Error")
        import traceback
        return {
            "message": f"Error fetching data: {str(e)}",
            "status": 500,
            "health_facility": health_facility,
            "start_date": start_date,
            "end_date": end_date,
            "vaccination_validation_summary": vaccination_validation_summary,
            "traceback": traceback.format_exc()
        }

@frappe.whitelist()
def submit_vaccine_validation_responses(doc_name, vaccinations):
    """
    Update child table records for a given parent document.

    Args:
    - doc_name (str): Name of the parent document.
    - vaccinations (list): List of dicts containing:
        - vaccination (str): vaccination name
        - status (str): Status to update
        - validation_answers (str): Response after validation exercise
        - last_modified (str): Last modified date

    Returns:
    - JSON response with success or failure message.
    """
    if isinstance(vaccinations, str):
        # Convert JSON string to list if needed (for REST API compatibility)
        import json
        vaccinations = json.loads(vaccinations)

    try:
        # Fetch the parent document
        parent_doc = frappe.get_doc("Vaccination Validation Summary", doc_name)

        # Check if the child table exists
        if not hasattr(parent_doc, "vaccinations_under_validation"):
            return {"error": "Child table not found in parent document."}

        updated_vaccinations = []  # Track updated rows

        # Create a mapping of vaccinations for quick lookup
        vaccinations_map = {b["vaccination"]: b for b in vaccinations}

        # Iterate over child table records
        for row in parent_doc.vaccinations_under_validation:
            if row.vaccination in vaccinations_map:  # Match vaccination name
                row.status = vaccinations_map[row.vaccination]["status"]
                row.validation_answers = vaccinations_map[row.vaccination]["validation_answers"]
                row.last_modified = vaccinations_map[row.vaccination]["last_modified"]
                updated_vaccinations.append(row.vaccination)  # Track updated vaccination names

        # Save updates
        parent_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "message": f"Successfully updated {len(vaccinations_map)} vaccinations in {doc_name}.",
            "vaccinations_map": vaccinations_map,
        }

    except frappe.DoesNotExistError:
        return {"error": f"Vaccination Validation Summary {doc_name} not found."}
    except Exception as e:
        return {"error": str(e)}



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
        # doc.validation_percentage = math.ceil((approved_count / total_rows) * 100)
        doc.validation_percentage = round((approved_count / total_rows) * 100, 0)
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

def process_vaccinations_before_save(doc, method):
    pending_rows = []
    approved_count = 0
    total_rows = len(doc.vaccinations_under_validation)

    vaccinator_data = {}  # Structure: {vaccinator_name: {'approved': x, 'total': y}}

    # 1. Check for pending rows, count approved/corrected, and track vaccinators
    for i, row in enumerate(doc.vaccinations_under_validation, start=1):
        vaccinator = row.vaccinator or "Unknown"
        vaccinator_stats = vaccinator_data.setdefault(vaccinator, {"approved": 0, "total": 0})
        vaccinator_stats["total"] += 1

        if row.status == "Pending":
            pending_rows.append(str(i))
        elif row.status in ("Approved", "Corrected"):
            approved_count += 1
            vaccinator_stats["approved"] += 1

    # 2. Set the overall validation percentage on the main document
    doc.validation_percentage = round((approved_count / total_rows) * 100, 0) if total_rows else 0

    # 3. Clear and populate the child table: vaccination_validation_report
    doc.vaccination_validation_report = []

    for vaccinator, stats in vaccinator_data.items():
        percentage = round((stats["approved"] / stats["total"]) * 100, 0) if stats["total"] else 0
        doc.append("vaccination_validation_report", {
            "team_code": vaccinator,
            "number_of_approved_vaccinations": stats["approved"],
            "total_number_of_vaccinations": stats["total"],
            "validation_percentage": percentage
        })

