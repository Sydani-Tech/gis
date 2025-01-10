# Copyright (c) 2024, Sydani Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Children(Document):
	pass

# def amalgamate_name(self):
#         """
#         Amalgamates first_name, middle_name (if present), and last_name
#         into a full name and stores it in a custom field 'full_name'.
#         """
#         full_name = f"{self.first_name} {self.middle_name} {self.last_name}" if self.middle_name else f"{self.first_name} {self.last_name}"
#         self.full_name = full_name.strip()