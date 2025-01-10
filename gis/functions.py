import frappe
from frappe import _
from frappe.utils.password import update_password
from datetime import datetime, timedelta
import requests
import random
import time
import re
import json
import os


session = requests.Session()

def sanitize_input(input_str):
  return re.sub(r'\W', '', input_str)

def auth_perm(doctype, ptype, docid):
  if 'StripeAdmin' in frappe.get_roles():
    return True

def is_valid_date_format(input_str):
  # Define the regular expression pattern for 'YYYY-MM-DD' format
  date_pattern = r'^\d{4}-\d{2}-\d{2}$'
  # Check if the input string matches the pattern
  return re.match(date_pattern, input_str) is not None

# convert date to dhis period and period to date

def is_valid_email(email):
  email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  return re.match(email_pattern, email) is not None

def convert_date(date_str, to='date'):
  if to == 'date':
    date_obj = datetime.strptime(date_str, "%Y-%m")
    # Add the day component to the date
    date_with_day = date_obj.replace(day=1)
    # Convert the date back to string format
    return date_with_day.strftime("%Y-%m-%d")
  elif to == 'period':
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_with_day = date_obj.replace(day=1)
    return date_with_day.strftime("%Y-%m")

def auto_dates():
  dateTo = datetime.now().replace(day=1).strftime('%Y-%m-%d')
  dateFrom = datetime.now().replace(day=1) - timedelta(days=124)
  dateFrom = dateFrom.replace(day=1).strftime('%Y-%m-%d')
  dateFrom = '2023-01-01'
  dateTo = '2023-04-01'
  return {'from': dateFrom, 'to': dateTo}

def generate_keys(user):
  user_doc = frappe.get_doc("User", user)
  sid = frappe.session.user
 
  if frappe.cache().get_value(user):
    user_doc.api_secret = frappe.cache.get_value(user)
    user_doc.sid = frappe.cache.get_value(f'{user}_sid')
  else:
    api_secret = frappe.generate_hash(length=15)
    frappe.cache().set_value(user, api_secret)
    frappe.cache().set_value(f'{user}_sid', sid)
    user_doc.api_secret = frappe.cache.get_value(user)

    # api_key = frappe.generate_hash(length=32)
    # api_secret = frappe.generate_hash(length=32)

  if not user_doc.api_key:
    user_doc.api_key = frappe.generate_hash(length=15)
  
  usr_data = {
    'api_key': user_doc.api_key,
    'api_secret': user_doc.api_secret,
    'username': user_doc.username,
    'email': user_doc.email
  }

  user_doc.save(ignore_permissions=True)
  
  # u.api_secret = frappe.cache.get_value(user)
  # return u.api_secret
  # return frappe.cache.get_value(user);
  return usr_data

def get_date_range(start_date_str, end_date_str):
  if is_valid_date_format(start_date_str) == False:
      return []
  if is_valid_date_format(end_date_str) == False:
      return []
  # Convert the date strings to datetime objects and set the day component to 1
  start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(day=1)
  end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(day=1)

  # Initialize an empty list to store the dates
  date_range = []

  # Loop through the months and add the first day of each month to the list
  current_date = start_date

  while current_date <= end_date:
      date_range.append(current_date.strftime('%Y-%m-%d'))
      current_date = current_date + timedelta(days=31)
      current_date = current_date.replace(day=1)
  return date_range


def set_error(code):
    message = ''

    if code == 401:
        message = 'Authentication Error'
    elif code == 403:
        message = "You dont have permission to access the requested resource"
    elif code == 404:
        message = 'No record found'
    elif code == 505:
        message = 'Internal Server Error'

    frappe.response.message = message
    frappe.response.code = code


def set_res(**kwargs):
  if 'error' in kwargs:
    return set_error(kwargs['error'])
  
  frappe.response.message = 'Success'
  frappe.response.status = 200
  for key, val in kwargs.items():
    frappe.response[key] = val

def fetch_db_resource(stmt=None, var=None, doc=None, fields=None, filters=None):
  try:
    data = None

    if stmt and var:
      data = frappe.db.sql(stmt, var, as_dict=True)
    elif stmt:
       data = frappe.db.sql(stmt, as_dict=True)
    elif doc:
      data = frappe.db.get_all(doc, fields=fields, filters=filters)
    
    if len(data) > 0:
      return data
    else:
      set_error(code=404)
  except:
    set_error(code=505)
  return

def save_image(request, field_name, img_name):

  uploaded_file = request.files[field_name]
  if uploaded_file:
    save_path = os.path.join(os.path.expanduser('~'), 
    'frappe-bench/sites/gis.sydani.org/public/files', 
    img_name)

    with open(save_path, 'wb') as new_file:
      new_file.write(uploaded_file.read())

    return f"/files/{img_name}"
  else:
    return "";
  

# def get_proxies():
#   proxy_url = 'https://free-proxy-list.net/'
#   response = requests.get(proxy_url)
#   soup = BeautifulSoup(response.text, 'html.parser')
#   table = soup.find('textarea', onclick='select(this)')
#   table = table.text.split(' ', 1)
#   table = table[1].split('\n')
#   table = table[3:-1]
 
#   return table

# def get_rand_proxy():
#   proxies = get_proxies()
#   if session.proxies:
#       print('proxy')
#   return random.choice(proxies)

def reset_user_password(user_email, new_password):
    print(new_password)
    user = frappe.get_doc("User", user_email)
    if user:
        update_password(user.name, new_password)
        return f"Password reset for user: {user_email}"
    else:
        return f"User not found: {user_email}"

def add_role_permissions(role):
    doc_permitted = [
        'Grid Creator',
        'State',
        'Local Government Area',
        'Ward',
        'Facility',
        'Grid Doctypes',
        'Grid',
        'Assignees'
    ]

    for doc in doc_permitted:
        if not frappe.db.get_value('Custom DocPerm', dict(parent=doc, role=role,
		permlevel=0, if_owner=0)):

            custom_docperm = frappe.get_doc({
                "doctype":"Custom DocPerm",
                "__islocal": 1,
                "parent": doc,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": 0,
                'read': 1,
            })
            custom_docperm.save()
            frappe.db.commit()


def create_user(names):
  for name in names:
    firstname = name['Name'].split(' ')[0].title()
    lastname = name['Name'].split(' ')[1].title()
    username = name['Email']
    password = f'{firstname.lower()}@8867'

    if not 'role' in name:
      role = 'GISAdmin'
    else:
      role = name['role']

    role_name = frappe.get_value('Role', {'role_name': role}, 'name')
    if not role_name:
        
      new_role = frappe.get_doc({
        'doctype': 'Role',
        'role_name': role,
        'desk_access': 0  # Set to 1 if you want Desk access for this role
      })

      new_role.insert()
      frappe.db.commit()

      role_name = new_role.name
      add_role_permissions(role_name)

    new_user = frappe.get_doc({
      "doctype": "User",
      "email": username,
      "first_name": firstname,
      "last_name": lastname,
      "password": password,
      "roles": [{'role': role_name}]
    })

    new_user.insert()
    frappe.db.commit()

    print({'email': username, 'password': password})
    reset_user_password(username, password)

def read_json_as_dict(file_path):
    with open(file_path, 'r') as file:
      data = json.load(file)
    return data

def create_admin():
  create_user([{"Name": "Gis Admin", "Email": "gis.admin@sydani.org"}])
