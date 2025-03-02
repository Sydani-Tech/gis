// Copyright (c) 2024, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Facility", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Facility", {
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

