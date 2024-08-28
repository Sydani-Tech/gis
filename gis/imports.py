

@frappe.whitelist(allow_guest=True)
def states():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_states.geojson'
  json_dict = read_json_as_dict(file_name)

  for state in json_dict['features']:
    geolocation = json.dumps(state)
    st = frappe.get_doc({
      'doctype': 'State',
      'state': state['properties']['statename'],
      'geolocation': geolocation
    })
    st.save()
    frappe.db.commit()
    print(state['properties']['statename'], ' -> done')
    

  # st = frappe.get_doc('State', 'Cross River')
  # print(st.geolocation)

@frappe.whitelist(allow_guest=True)
def lgas():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_lgas.geojson'
  json_dict = read_json_as_dict(file_name)

  for lga in json_dict['features']:
    geolocation = json.dumps(lga)
    lg = frappe.get_doc({
      'doctype': 'Local Government Area',
      'local_government_area': lga['properties']['lganame'],
      'state': lga['properties']['statename'],
      'geolocation': geolocation
    })
    try:
      lg.save()
      frappe.db.commit()
      print(lga['properties']['lganame'], ' -> done')
    except Exception as e:
      print(e)
    

@frappe.whitelist(allow_guest=True)
def wards():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_wards.geojson'
  json_dict = read_json_as_dict(file_name)

  for ward in json_dict['features']:
    geolocation = json.dumps(ward)
    wrd = frappe.get_doc({
      'doctype': 'Ward',
      'ward': ward['properties']['wardname'],
      'local_government_area': f"{ward['properties']['lganame']}-{ward['properties']['statename']}",
      'state': ward['properties']['statename'],
      'geolocation': geolocation
    })

    try:
      wrd.save()
      frappe.db.commit()
      print(ward['properties']['wardname'], ' -> done')
    except Exception as e:
      print(e)

@frappe.whitelist(allow_guest=True)
def facilities():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_facilities.geojson'
  json_dict = read_json_as_dict(file_name)

  for facility in json_dict['features']:
    geolocation = json.dumps(facility)
    facility_address = f"{facility['properties']['prmry_name']}, {facility['properties']['wardname']} ward, {facility['properties']['lganame']} LGA, {facility['properties']['statename']} state"
    fct = frappe.get_doc({
      'doctype': 'Facility',
      'facility_name': facility['properties']['prmry_name'],
      'facility_address': facility_address,
      'ward': f"{facility['properties']['wardname']}-{facility['properties']['lganame']}-{facility['properties']['statename']}",
      'local_government_area': f"{facility['properties']['lganame']}-{facility['properties']['statename']}",
      'state': facility['properties']['statename'],
      'geolocation': geolocation,
      'country': 'Nigeria'
    })

    try:
      fct.save()
      frappe.db.commit()
      print(facility['properties']['prmry_name'], ' -> done')
    except Exception as e:
      print(e)
