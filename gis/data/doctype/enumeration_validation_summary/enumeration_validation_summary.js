// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt


frappe.ui.form.on("Enumeration Validation Summary", {
    refresh: function (frm) {
        // Ensure child table is loaded
        if (frm.fields_dict["records_under_validation"] && frm.fields_dict["records_under_validation"].grid) {
            frm.fields_dict["records_under_validation"].grid.grid_rows.forEach(row => {
                let doc = row.doc; // Get row data
                let $row = $(row.row); // Get row element

                // Define colors based on status
                let color_map = {
                    "Pending": "#fff3cd",  // Light Yellow
                    "Approved": "#d4edda", // Light Green
                    "Returned": "#f8d7da"  // Light Red
                };

                // Apply background color if status exists
                if (color_map[doc.status]) {
                    $row.css("background-color", color_map[doc.status]);
                } else {
                    $row.css("background-color", ""); // Reset if no match
                }
            });
        }

        if (frm.fields_dict["enumeration_sample_responses"] && frm.fields_dict["enumeration_sample_responses"].grid) {
            frm.fields_dict["enumeration_sample_responses"].grid.grid_rows.forEach(row => {
                let doc = row.doc; // Get row data
                let $row = $(row.row); // Get row element

                // Define colors based on status
                let color_map = {
                    "Pending": "#fff3cd",  // Light Yellow
                    "Approved": "#d4edda", // Light Green
                    "Returned": "#f8d7da"  // Light Red
                };

                // Apply background color if status exists
                if (color_map[doc.status]) {
                    $row.css("background-color", color_map[doc.status]);
                } else {
                    $row.css("background-color", ""); // Reset if no match
                }
            });
        }

        if (!frm.is_dirty() && frm.doc.docstatus === 0) {
            frm.add_custom_button('Submit Now', () => {
                frappe.confirm(
                    'Are you sure you want to submit this document?',
                    () => {
                        frm.save('Submit');
                    }
                );
            }, 'Actions');
        }
    },

    on_submit: function (frm) {
        frappe.msgprint({
            title: __("Success"),
            message: __("Records updated successfully! Reloading..."),
            indicator: "green"
        });

        setTimeout(() => {
            location.reload();
        }, 2000); // Reload after 2 seconds
    },
    after_save: function (frm) {
        frappe.msgprint({
            title: __("Success"),
            message: __("Records updated successfully! Reloading..."),
            indicator: "green"
        });

        setTimeout(() => {
            location.reload();
        }, 2000); // Reload after 2 seconds
    }
});


frappe.ui.form.on('Enumeration Validation Summary', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch Buildings to Validate"), function () {
                if (!frm.doc.ward || !frm.doc.start_date || !frm.doc.end_date) {
                    frappe.msgprint("Please specify a Ward and a date range before fetching buildings to validate.");
                    return;
                }

                frm.clear_table("enumeration_sample_responses");
                frm.clear_table("records_under_validation");

                frappe.call({
                    method: "gis.enumeration_validation.get_buildings",
                    args: {
                        ward: frm.doc.ward,
                        start_date: frm.doc.start_date,
                        end_date: frm.doc.end_date
                    },
                    callback: function (r) {

                        if (!r.message) {
                            frappe.msgprint("No data returned from server.");
                            return;
                        }
                        console.log("Response from server:", r.message);

                        const selected = r.message.selected_buildings || [];
                        const all = r.message.all_buildings || [];

                        if (selected.length === 0 && all.length === 0) {
                            frappe.msgprint("No buildings found for the specified filters.");
                            return;
                        }

                        selected.forEach(building => {
                            frm.add_child("enumeration_sample_responses", {
                                doctype_name: "Building",
                                status: "Pending",
                                record: building.name,
                                settlement: building.settlement,
                                enumerator: building.owner,
                                geolocation: building.geolocation,
                                building_picture: building.building_picture,
                                building_picture_2: building.building_picture_2
                            });
                        });

                        all.forEach(building => {
                            frm.add_child("records_under_validation", {
                                doctype_name: "Building",
                                status: "Pending",
                                record: building.name,
                                settlement: building.settlement,
                                enumerator: building.owner,
                            });
                        });

                        frm.refresh_field("enumeration_sample_responses");
                        frm.refresh_field("records_under_validation");
                        frappe.msgprint("Buildings successfully fetched and populated.");
                    },
                    error: function () {
                        frappe.hide_progress();
                        frappe.msgprint("An error occurred while fetching buildings.");
                    }
                });
            });
        }
    }
});
