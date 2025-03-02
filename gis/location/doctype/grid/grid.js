// Copyright (c) 2024, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Grid", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Grid", {
    refresh(frm) {
        frm.set_query("location_type", function () {
            return {
                filters: {
                    name: ["in", ["Country", "State", "Local Government Area", "Ward"]]
                }
            };
        });
    }
});
