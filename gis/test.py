import frappe
import random
from frappe import _
from frappe.utils.data import today
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



@frappe.whitelist()
def update_building_geolocation():
    try:
        # Fetch the Building record with the specified name
        building = frappe.get_doc("Grid", "vuha6hqe62")
        # building = frappe.get_doc("Building", "11c - Nsikak Edet Crescent")
        # Update the geolocation field
        # print(building.response_geolocation)
        # print(building.geolocation)
        print(building.geolocation_kyow)
        
        # building.response_geolocation = None
        # building.geolocation = None
        
       
        # building.geolocation = building.response_geolocation 

        # Set the geolocation field in the required GeoJSON format
        # building.geolocation = json.dumps({
        # # building.response_geolocation = json.dumps({
        #     "type": "FeatureCollection",
        #     "features": [
        #         {
        #             "type": "Feature",
        #             "properties": {},
        #             "geometry": {
        #                 "type": "Point",
        #                 # "coordinates": [7.475866, 9.042452]  # Longitude first, then Latitude (Sydani)
        #                 # "coordinates": [7.4042, 9.1099]  # Longitude first, then Latitude (Gwarinpa)
        #                 # "coordinates": [7.476275, 8.97323]  # Longitude first, then Latitude (Sunsine Homes)
        #                 # "coordinates": [6.553486, 9.591894]  # Longitude first, then Latitude (Haske Hotel, Niger)
        #                 # "coordinates": [7.4951, 9.0579]  # Longitude first, then Latitude (Asokoro)
        #                 # "coordinates": [6.1532668192084, 8.99168425242635]  # Longitude first, then Latitude (Alukusu)
        #                 "coordinates": [7.14320, 8.93120]  # Longitude first, then Latitude (Grid 1, Gui)

        #             }
        #         }
        #     ]
        # })
        
        
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

import frappe
from frappe.utils import getdate, date_diff, today

# def update_child_vaccination_status(doc, method):
#     """
#     Updates the vaccination status of a child based on administered vaccines and age.
#     """
#     vaccine_records = []
#     # frappe.msgprint(f"Processing Child Vaccination Status for: {doc.name}")
    
#     # Iterate through the child table `last_vaccine_administered`
#     for vaccine_entry in doc.get("last_vaccine_administered", []):
#         if vaccine_entry.get("vaccine"):
#             # Append the value of `vaccine` to the list
#             vaccine_records.append(vaccine_entry.get("vaccine"))
    
#     # Print vaccine records for debugging
#     # frappe.msgprint(f"Vaccine Records: {vaccine_records}")
    
#     # Format the list into a string in the required format
#     doc.vaccines_taken = "[" + ", ".join(vaccine_records) + "]"
    
#     # Calculate the age in weeks
#     date_of_birth = getdate(doc.date_of_birth)
#     current_date = getdate(today())
#     age_in_days = date_diff(current_date, date_of_birth)
#     age_in_weeks = age_in_days // 7
    
#     # Print age for debugging
#     # frappe.msgprint(f"Age in Weeks: {age_in_weeks}")
    
#     # Set vaccination_status based on conditions
#     if not vaccine_records:
#         # If no vaccines have been administered
#         doc.vaccination_status = "Never Vaccinated"
       
    
#     elif (
#         ("PENTA 1" not in vaccine_records and 
#          "PENTA 2" not in vaccine_records and 
#          "PENTA 3" not in vaccine_records) and age_in_weeks > 6
#     ):
#         doc.vaccination_status = "Zero Dose"
    
#     elif (
#         (age_in_weeks >= 10 and ("PENTA 2" not in vaccine_records and "PENTA 3" not in vaccine_records)) or
#         (age_in_weeks >= 14 and "PENTA 3" not in vaccine_records) or
#         (age_in_weeks >= 36 and "VIT A" not in vaccine_records) or
#         (age_in_weeks >= 48 and "Measles 1" not in vaccine_records) or
#         (age_in_weeks >= 60 and "Measles 2" not in vaccine_records)
#     ):
#         # If missing age-appropriate vaccines for "Under Immunized" conditions
#         doc.vaccination_status = "Under Immunized"

#     elif (
#         (age_in_weeks >= 0 and age_in_weeks <= 6 and "BCG" in vaccine_records) or
#         (age_in_weeks >= 0 and age_in_weeks <= 6 and "HEP B0" in vaccine_records) or
#         (age_in_weeks >= 0 and age_in_weeks <= 6 and "OPV 0" in vaccine_records) or
#         (age_in_weeks >= 6 and age_in_weeks <= 10 and "PENTA 1" in vaccine_records) or
#         (age_in_weeks >= 10 and age_in_weeks <= 14 and "PENTA 2" in vaccine_records) or
#         (age_in_weeks >= 14 and age_in_weeks <= 36 and "PENTA 3" in vaccine_records) or
#         (age_in_weeks >= 36 and age_in_weeks <= 48 and "VIT A" in vaccine_records) or
#         (age_in_weeks >= 48 and age_in_weeks <= 60 and "Measles 1" in vaccine_records)
#     ):
#         doc.vaccination_status = "Vaccinated to Age"

    
#     elif age_in_weeks > 60 and "Measles 2" in vaccine_records:
#         # If Measles 2 is administered after 60 weeks
#         doc.vaccination_status = "Fully Vaccinated (Measles 2)"
    
#     # Print final vaccination status
#     # frappe.msgprint(f"Updated Vaccination Status: {doc.vaccination_status}")


def update_child_vaccination_status(doc, method):
    """
    Updates the vaccination status of a child based on administered vaccines and age.
    """
    vaccine_records = []
    # frappe.msgprint(f"Processing Child Vaccination Status for: {doc.name}")
    
    # Iterate through the child table `last_vaccine_administered`
    for vaccine_entry in doc.get("last_vaccine_administered", []):
        if vaccine_entry.get("vaccine"):
            # Append the value of `vaccine` to the list
            vaccine_records.append(vaccine_entry.get("vaccine"))
    
    # Print vaccine records for debugging
    frappe.msgprint(f"Vaccine Records: {vaccine_records}")
    
    # Format the list into a string in the required format
    doc.vaccines_taken = "[" + ", ".join(vaccine_records) + "]"
    
    # Calculate the age in weeks
    date_of_birth = getdate(doc.date_of_birth)
    current_date = getdate(today())
    age_in_days = date_diff(current_date, date_of_birth)
    age_in_weeks = age_in_days // 7
    
    # Print age for debugging
    frappe.msgprint(f"Age in Weeks: {age_in_weeks}")
    
    # Set vaccination_status based on conditions
    if not vaccine_records:
        # If no vaccines have been administered
        doc.vaccination_status = "Never Vaccinated"

    elif (
        ("PENTA 1" not in vaccine_records and 
         "PENTA 2" not in vaccine_records and 
         "PENTA 3" not in vaccine_records) and age_in_weeks > 6
    ):
        doc.vaccination_status = "Zero Dose"

    elif (
        (age_in_weeks >= 0 and "BCG" not in vaccine_records) or
        (age_in_weeks >= 0 and "HEP B0" not in vaccine_records) or
        (age_in_weeks >= 0 and "OPV 0" not in vaccine_records) or
        (age_in_weeks >= 6 and "PENTA 1" not in vaccine_records) or
        (age_in_weeks >= 10 and "PENTA 2" not in vaccine_records) or
        (age_in_weeks >= 14 and "PENTA 3" not in vaccine_records) or
        (age_in_weeks >= 24 and "VIT A" not in vaccine_records) or
        (age_in_weeks >= 36 and "Measles 1" not in vaccine_records) or
        (age_in_weeks >= 60 and "Measles 2" not in vaccine_records)
    ):
        # If missing age-appropriate vaccines for "Under Immunized" conditions
        doc.vaccination_status = "Under Immunized" 
    
    elif (
        (age_in_weeks >= 0 and age_in_weeks <= 6 and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records) or
        (age_in_weeks >= 6 and age_in_weeks <= 10 and "PENTA 1" in vaccine_records and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records) or
        (age_in_weeks >= 10 and age_in_weeks <= 14 and "PENTA 2" in vaccine_records and "PENTA 1" in vaccine_records and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records) or
        (age_in_weeks >= 14 and age_in_weeks <= 36 and "PENTA 3" in vaccine_records and "PENTA 2" in vaccine_records and "PENTA 1" in vaccine_records and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records) or
        (age_in_weeks >= 24 and age_in_weeks <= 48 and "VIT A" in vaccine_records and "PENTA 3" in vaccine_records and "PENTA 2" in vaccine_records and "PENTA 1" in vaccine_records and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records) or
        (age_in_weeks >= 36 and age_in_weeks <= 60 and "Measles 1" in vaccine_records and "VIT A" in vaccine_records and "PENTA 3" in vaccine_records and "PENTA 2" in vaccine_records and "PENTA 1" in vaccine_records and "BCG" in vaccine_records and "HEP B0" in vaccine_records and "OPV 0" in vaccine_records)
    ):
        doc.vaccination_status = "Vaccinated to Age"

    elif (
        ("BCG" in vaccine_records) and
        ("HEP B0" in vaccine_records) and
        ("OPV 0" in vaccine_records) and
        ("PENTA 1" in vaccine_records) and
        ("PENTA 2" in vaccine_records) and
        ("PENTA 3" in vaccine_records) and
        ("VIT A" in vaccine_records) and
        ("Measles 1" in vaccine_records) and
        ("Measles 2" in vaccine_records)
    ):
        doc.vaccination_status = "Fully Vaccinated (Measles 2)"
    
    # Print final vaccination status
    frappe.msgprint(f"Updated Vaccination Status: {doc.vaccination_status}")
