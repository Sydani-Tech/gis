// Copyright (c) 2024, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Household", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Household', {
    refresh(frm) {
        var userRoles = frappe.user_roles;
        var allowedRoles = ["Supervisor", "Project Team", "System Manager"];
        var hasAllowedRoles = allowedRoles.some(role => userRoles.includes(role));
        if ((  frm.doc.status === "Submitted" || frm.doc.status === "Draft") && hasAllowedRoles) {
            frm.add_custom_button(__('Approve'), function () {
                frm.set_value('status', 'Approved');
                frm.save();
            });
            frm.add_custom_button(__('Return'), function () {
                frm.set_value('status', 'Returned');
                frm.save();
            });
        }
    }
});