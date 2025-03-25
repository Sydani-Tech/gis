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
