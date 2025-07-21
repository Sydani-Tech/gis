// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt

frappe.listview_settings['Issue'] = {
    filters: [["status", "!=", "Resolved"]],
    onload: function (listview) {
        // Optional: highlight unresolved issues
        listview.page.set_title("Unresolved Issues");
    }
}


frappe.ui.form.on('Issue', {
    refresh(frm) {
        const roles = frappe.user_roles;
        const can_manage = roles.includes("Project Team") || roles.includes("System Manager");
        const is_saved = !frm.is_new();

        // Clear previous indicators
        frm.dashboard.clear_headline();

        // Add status indicator near title
        const status_colors = {
            "Open": "orange",
            "Replied": "blue",
            "On Hold": "yellow",
            "Resolved": "green"
        };

        if (frm.doc.status) {
            frm.dashboard.set_headline(
                `<span class="indicator ${status_colors[frm.doc.status]}"> ${frm.doc.status} </span>`
            );
        }

        // Role-based custom buttons
        if (can_manage && is_saved && frm.doc.status !== "Resolved") {
            frm.add_custom_button("Close", () => {
                frm.set_value("status", "Resolved");
                frm.save();
            });

            frm.add_custom_button("Put On Hold", () => {
                frm.set_value("status", "On Hold");
                frm.save();
            });
        }

        if (can_manage && frm.doc.status === "Resolved") {
            frm.add_custom_button("Reopen", () => {
                frm.set_value("status", "Open");
                frm.save();
            });
        }
    }
});
