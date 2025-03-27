// Copyright (c) 2024, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Building", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Building', {
    refresh(frm) {
        var userRoles = frappe.user_roles;
        var allowedRoles = ["Supervisor", "Project Team", "System Manager"];
        var hasAllowedRoles = allowedRoles.some(role => userRoles.includes(role));
        if ((frm.doc.status === "Submitted" || frm.doc.status === "Draft") && hasAllowedRoles) {
            frm.add_custom_button(__('Approve'), function () {
                frm.set_value('status', 'Approved');
                frm.save();
            });
            frm.add_custom_button(__('Return'), function () {
                frm.set_value('status', 'Returned');
                frm.save();
            });
        }
    },
    set_geolocation: function (frm) {

        if (!frm.doc.longitude || !frm.doc.latitude) {
            frappe.msgprint(__("Please enter both Longitude and Latitude."));
            return;
        }

        frappe.call({
            method: "gis.doc_events.format_geolocation",
            args: {
                longitude: frm.doc.longitude,
                latitude: frm.doc.latitude
            },
            callback: function (response) {
                if (response.message) {
                    frm.set_value("geolocation", response.message);
                    frm.save();
                }
            },
            error: function (err) {
                frappe.msgprint(__("Failed to format geolocation. Check inputs."));
            }
        });
    }
});
