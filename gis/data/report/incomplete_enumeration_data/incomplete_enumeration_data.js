// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Incomplete Enumeration Data"] = {
	"filters": [
		{
			fieldname: "record_type",
			label: __("Record Type"),
			fieldtype: "Select",
			options: [
				{ "value": "Buildings", "label": __("Buildings") },
				{ "value": "Households", "label": __("Households") },
			],
			default: "Buildings",
			reqd: 1
		},
		// {
		// 	fieldname: "report_type",
		// 	label: __("Report Type"),
		// 	fieldtype: "Select",
		// 	options: [
		// 		{ "value": "Detailed", "label": __("Detailed") },
		// 		{ "value": "Summary", "label": __("Summary") },
		// 	],
		// 	default: "Detailed",
		// 	reqd: 1
		// },
		{
			fieldname: "state",
			label: __("State"),
			fieldtype: "Link",
			options: "State",
			reqd: 0
		},
		{
			fieldname: "local_government_area",
			label: __("Local Government Area"),
			fieldtype: "Link",
			options: "Local Government Area",
			default: "",
			reqd: 0,
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Ward",
			reqd: 0
		},

		{
			fieldname: "settlement",
			label: __("Settlement"),
			fieldtype: "Link",
			options: "Settlement",
			reqd: 0
		},
		{
			fieldname: "grid",
			label: __("Grid"),
			fieldtype: "Link",
			options: "Grid",
			reqd: 0
		},
		{
			fieldname: "enumerator",
			label: __("Enumerator"),
			fieldtype: "Link",
			options: "User",
			reqd: 0
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: [
				{ "value": "", "label": __("") },
				{ "value": "Approved", "label": __("Approved") },
				{ "value": "Submitted", "label": __("Submitted") },
				{ "value": "Returned", "label": __("Returned") },
				{ "value": "Suspended", "label": __("Suspended") },
			],
			reqd: 0
		},

	],
};
