app_name = "gis"
app_title = "GIS frappe app"
app_publisher = "Sydani Technologies"
app_description = "Custom frappe app to manage the GIS software"
app_email = "admin@sydani.org"
app_license = "mit"
# required_apps = []

#Fixtures
fixtures = [
    {"dt": "DocType", "filters": [["name", "in", ["Children", "Vaccination", "Household", "Building", "State", "Local Government Area", "Ward", "Facility", "Settlement", "Grid Doctypes", "Grid Assignees", "Grid", "Project", "Project Team", "Grid Creator"]]]},
    {"dt": "Role", "filters": [["name", "in", ["Enumerator", "Project Team", "Supervisor", "Project Manager", "Outreach Worker", "Dashboard Viewer"]]]},
    {"dt": "Local Government Area"},
    {"dt": "State"},
    {"dt": "Ward"},
	{"dt": "Server Script"},
    # {"dt": "Facility"},
    # {"dt": "Settlement"},
    # {"dt": "Building"},
    # {"dt": "Project"}
]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/gis/css/gis.css"
# app_include_js = "/assets/gis/js/gis.js"

# include js, css files in header of web template
# web_include_css = "/assets/gis/css/gis.css"
# web_include_js = "/assets/gis/js/gis.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "gis/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "gis/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "gis.utils.jinja_methods",
#	"filters": "gis.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "gis.install.before_install"
# after_install = "gis.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "gis.uninstall.before_uninstall"
# after_uninstall = "gis.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "gis.utils.before_app_install"
# after_app_install = "gis.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "gis.utils.before_app_uninstall"
# after_app_uninstall = "gis.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "gis.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# "*": {
	# 	"on_update": "gis.data.doctype.children.children.get_full_name",
		# "on_cancel": "method",
		# "on_trash": "method"
	# }
    # "Children": {"before_save": "gis.test.update_children_vaccination"},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"gis.tasks.all"
#	],
#	"daily": [
#		"gis.tasks.daily"
#	],
#	"hourly": [
#		"gis.tasks.hourly"
#	],
#	"weekly": [
#		"gis.tasks.weekly"
#	],
#	"monthly": [
#		"gis.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "gis.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "gis.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "gis.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["gis.utils.before_request"]
# after_request = ["gis.utils.after_request"]

# Job Events
# ----------
# before_job = ["gis.utils.before_job"]
# after_job = ["gis.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"gis.auth.validate"
# ]
