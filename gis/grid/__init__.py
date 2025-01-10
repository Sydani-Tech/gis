import frappe
from frappe import _
import requests
import json

from gis.functions import (
  is_valid_email,set_error,generate_keys,reset_user_password,
  set_res,create_user,read_json_as_dict,fetch_db_resource, save_image
)

@frappe.whitelist()
def grid_states(grid_id):
  states = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, s.state as grid_state, s.country as grid_country 
    FROM `tabGrid` g
    JOIN `tabState` s
    ON ST_Contains(
      ST_GeomFromGeoJSON(
        JSON_EXTRACT(g.geolocation_kyow, '$.features[0].geometry')
      ),
      ST_GeomFromGeoJSON(
          JSON_EXTRACT(s.geolocation, '$.geometry')
      )
    ) 
    WHERE g.name = '{grid_id}'
  """, as_dict=True)

  return set_res(states=states)

@frappe.whitelist()
def grid_lgas(grid_id):
  lgas = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, l.name as grid_lga, l.state as grid_state, l.country as grid_country 
    FROM `tabGrid` g
    JOIN `tabLocal Government Area` l
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(l.geolocation)
    ) 
    WHERE g.name = '{grid_id}'
  """, as_dict=True)

  return set_res(lgas=lgas)

@frappe.whitelist()
def grid_wards(grid_id):
  wards = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, w.name as name, w.ward, w.local_government_area, w.state, w.country 
    FROM `tabGrid` g 
    JOIN `tabWard` w
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(w.geolocation)
    ) 
    WHERE g.name = '{grid_id}'
  """, as_dict=True)

  return set_res(wards=wards)



@frappe.whitelist()
def grid_settlements(grid_id):
  settlement = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, st.name, st.type_of_settlement, st.ward as ward, st.local_government_area, st.state, st.country
    FROM `tabGrid` g 
    JOIN `tabSettlement` st
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(st.facility_geolocation)
    ) 
    WHERE g.name = '{grid_id}' AND st.status = 'Approved'
  """, as_dict=True)

  return set_res(settlement=settlement)

@frappe.whitelist()
def grid_facilities(grid_id):
  fcs = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, f.name as name, f.facility_name, f.facility_address, f.ward,
    f.local_government_area, f.state, f.country 
    FROM `tabGrid` g
    JOIN `tabFacility` f
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(f.geolocation)
    ) 
    WHERE g.name = '{grid_id}'
  """, as_dict=True)

  return set_res(facilities=fcs)


@frappe.whitelist()
def grid_buildings(grid_id):
  bldngs = frappe.db.sql(f"""
    SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, b.name, b.building_number, b.building_address,
    b.settlement, b.ward, b.local_government_area, b.state, b.country 
    FROM `tabGrid` g
    JOIN `tabBuilding` b
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(b.geolocation)
    ) 
    WHERE g.name = '{grid_id}' AND b.status = 'Approved'
  """, as_dict=True)

  return set_res(buildings=bldngs)



@frappe.whitelist()
def grid_households(grid_id):
  # bldngs = frappe.db.sql(f"""
  #   SELECT g.name as grid_id, g.location as grid_location, g.geolocation_kyow as grid_geolocation, hs.name_of_household_head, hs.building as household_building,
  #   hs.settlement as household_settlement, hs.ward as household_ward, hs.local_government_area as household_lga, hs.state as household_state, hs.country as household_country 
  #   FROM `tabGrid` g
  #   JOIN `tabHousehold` hs
  #   ON ST_Contains(
  #     ST_GeomFromGeoJSON(g.geolocation_kyow),
  #     ST_GeomFromGeoJSON(hs.geolocation)
  #   ) 
  #   WHERE g.name = '{grid_id}'
  # """, as_dict=True)

  households = frappe.db.sql(f"""
    SELECT g.name as grid_id,
    hs.settlement as settlement,  hs.phone_number as phone_number, hs.name_of_household_head as name_of_household_head, hs.building as building, hs.ward as ward, hs.name as name 
    FROM `tabGrid` g
    JOIN `tabHousehold` hs
    ON ST_Contains(
      ST_GeomFromGeoJSON(g.geolocation_kyow),
      ST_GeomFromGeoJSON(hs.geolocation)
    ) 
    WHERE g.name = '{grid_id}' AND hs.status = 'Approved'
  """, as_dict=True)

  return set_res(households=households)

  # ST_GeomFromText(CONCAT('POINT(', b.geolocation, ')'))
