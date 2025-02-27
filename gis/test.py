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
    FROM `tabDocField`
    WHERE parent = 'Building'
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
        building = frappe.get_doc("Building", "RTRR5644 - testing the mic")
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
                        # "coordinates": [7.475866, 9.042452]  # Longitude first, then Latitude (Sydani)
                        "coordinates": [7.4042, 9.1099]  # Longitude first, then Latitude (Gwarinpa)
                        # "coordinates": [7.4951, 9.0579]  # Longitude first, then Latitude (Asokoro)

                    }
                }
            ]
        })
        
        # Save the changes
        building.save()
        
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

# @frappe.whitelist()
# def get_building_data(building):
#     """
#     Fetch data for a given building, including pictures, approved households, and approved children in those households.
#     If the building is not residential, fetch vaccination records instead.

#     Args:
#         building (str): The name of the building.

#     Returns:
#         dict: Building data with associated households and children or vaccination records.
#     """

#     # Get the logged-in user
#     user = frappe.session.user
#     if user == "Guest":
#         return {
#             "message": "You must be logged in to access this data.",
#             "status": "error"
#         }

#     # Check if the user has the "Dashboard Viewer" role
#     user_roles = frappe.get_roles(user)
#     if "Dashboard Viewer" not in user_roles:
#         return {
#             "message": "You do not have the required role to view the map, please contact the project manager.",
#             "status": "error"
#         }

#     if not building:
#         return {
#             "message": "Building name is required.",
#             "status": 400
#         }
    
#     # Fetch building details including type and pictures
#     building_data = frappe.db.get_value(
#         "Building",
#         building,
#         ["building_picture", "building_picture_2", "building_type"],
#         as_dict=True
#     )

#     if not building_data:
#         return {
#             "message": f"No building found with name: {building}",
#             "status": 404
#         }

#     # Fetch approved vaccination records for the building
#     today = date.today()
#     vaccinations = frappe.db.sql(
#         """
#         SELECT full_name, date_of_birth, vaccination_status, vaccination_date, next_vaccination_date, gender
#         FROM `tabVaccination`
#         WHERE building = %(building)s AND status = 'Approved' AND children is NULL
#         """,
#         {"building": building},
#         as_dict=True
#     )

#     # Fetch approved children for the building
#     children = frappe.db.sql(
#         """
#         SELECT full_name, date_of_birth, vaccination_status, last_vaccination_date, next_vaccination, gender
#         FROM `tabChild`
#         WHERE building = %(building)s AND status = 'Approved'
#         """,
#         {"building": building},
#         as_dict=True
#     )

#     children_and_vaccination_data = [
#         {
#             "full_name": record["full_name"],
#             "vaccination_status": record["vaccination_status"],
#             "vaccination_date": record["vaccination_date"],
#             "next_vaccination_date": record["next_vaccination_date"],
#             "gender": record["gender"],
#             "age": f"{(today.year - record['date_of_birth'].year) - (1 if today.month < record['date_of_birth'].month or (today.month == record['date_of_birth'].month and today.day < record['date_of_birth'].day) else 0)} years, {((today.month - record['date_of_birth'].month) % 12 if today.day >= record['date_of_birth'].day else (today.month - record['date_of_birth'].month - 1) % 12)} months"
#                     if record["date_of_birth"] else "Unknown"
            
#         }
#         for record in vaccinations
#     ]

#     return {
#         "status": 200,
#         "data": {
#             "building": {
#                 "name": building,
#                 "building_picture": building_data.get("building_picture"),
#                 "building_picture_2": building_data.get("building_picture_2"),
#                 "children_and_vaccination_data": children_and_vaccination_data
#             }
#         }
#     }


import frappe
from datetime import date

@frappe.whitelist()
def get_building_data(building):
    """
    Fetch data for a given building, including pictures, approved households, and approved children in those households.
    If the building is not residential, fetch vaccination records instead.

    Args:
        building (str): The name of the building.

    Returns:
        dict: Building data with associated households and children or vaccination records.
    """

    # Get the logged-in user
    user = frappe.session.user
    if user == "Guest":
        return {
            "message": "You must be logged in to access this data.",
            "status": "error"
        }

    # Check if the user has the "Dashboard Viewer" role
    if "Dashboard Viewer" not in frappe.get_roles(user):
        return {
            "message": "You do not have the required role to view the map, please contact the project manager.",
            "status": "error"
        }

    if not building:
        return {
            "message": "Building name is required.",
            "status": 400
        }
    
    # Fetch building details including type and pictures
    building_data = frappe.db.get_value(
        "Building",
        building,
        ["building_picture", "building_picture_2", "building_type"],
        as_dict=True
    )

    if not building_data:
        return {
            "message": f"No building found with name: {building}",
            "status": 404
        }

    # Fetch both children and vaccination records in a single query
    combined_records = frappe.db.sql(
        """
        SELECT 
            full_name, 
            date_of_birth, 
            gender, 
            vaccination_status, 
            COALESCE(vaccination_date, last_vaccination_date) AS vaccination_date,
            next_vaccination_date,
            household
        FROM (
            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                vaccination_date, 
                next_vaccination_date,
                NULL AS last_vaccination_date,
                household
            FROM `tabVaccination`
            WHERE building = %(building)s AND status = 'Approved' AND children IS NULL AND building IS NOT NULL
            
            UNION ALL

            SELECT 
                full_name, 
                date_of_birth, 
                gender, 
                vaccination_status, 
                NULL AS vaccination_date,
                next_vaccination_date AS next_vaccination_date,
                last_vaccination_date,
                household
            FROM `tabChildren`
            WHERE building = %(building)s AND status = 'Approved'
        ) AS combined_data
        """,
        {"building": building},
        as_dict=True
    )

    # Calculate age and structure data
    today = date.today()
    formatted_data = [
        {
            "full_name": record["full_name"],
            "gender": record["gender"],
            "vaccination_status": record["vaccination_status"],
            "vaccination_date": record["vaccination_date"],
            "next_vaccination_date": record["next_vaccination_date"],
            "date_of_birth": record["date_of_birth"],
            "age": (
                f"{(today.year - record['date_of_birth'].year) - (1 if today.month < record['date_of_birth'].month or (today.month == record['date_of_birth'].month and today.day < record['date_of_birth'].day) else 0)} years, "
                f"{((today.month - record['date_of_birth'].month) % 12 if today.day >= record['date_of_birth'].day else (today.month - record['date_of_birth'].month - 1) % 12)} months"
                if record["date_of_birth"] else "Unknown"
            ),
            "household_head": frappe.db.get_value("Household", record["household"], "name_of_household_head")
        }
        for record in combined_records
    ]

    return {
        "status": 200,
        "data": {
            "building": {
                "name": building,
                "building_picture": building_data.get("building_picture"),
                "building_picture_2": building_data.get("building_picture_2"),
                "children_and_vaccination_data": formatted_data
            }
        }
    }
