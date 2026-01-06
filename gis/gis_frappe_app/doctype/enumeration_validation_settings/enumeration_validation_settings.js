// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Enumeration Validation Settings", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on("Enumeration Validation Settings", {
    refresh: function (frm) {
        // Add a custom button on the form
        frm.add_custom_button(__("Run Enumeration Validation Assignment"), function () {

            // --- Basic validations ---

            const min = frm.doc.minimum_no_of_records || 0;
            const max = frm.doc.maximum_no_of_records || 0;

            if (min < 1) {
                frappe.throw(__("Minimum No. of Records must be at least 1."));
            }

            if (max < 1) {
                frappe.throw(__("Maximum No. of Records must be at least 1."));
            }

            // Optional: you can also enforce max >= min if you like
            // if (max < min) {
            //     frappe.throw(__("Maximum No. of Records cannot be less than Minimum No. of Records."));
            // }

            if (frm.doc.start_date) {
                const start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
                const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

                if (start_date > today) {
                    frappe.throw(__("Start Date cannot be later than today."));
                }
            }

            // --- Call the server method after validations pass ---

            frappe.call({
                method: "gis.enumeration_validation.assign_enumeration_validations",
                args: {
                    // only needed if your Python function expects these;
                    // adjust names to match the function signature
                    start_date_str: frm.doc.start_date,
                    min_count: min,
                    max_count: max
                },
                freeze: true,
                freeze_message: __("Assigning enumeration validations..."),
                callback: function (r) {
                    if (r.message) {
                        // You can pretty-print the response or just show success
                        frappe.msgprint({
                            title: __("Completed"),
                            message: __("Enumeration validations have been assigned."),
                            indicator: "green"
                        });

                    } else {
                        frappe.msgprint({
                            title: __("Enumeration Assignment Result"),
                            message: `<pre style="white-space: pre-wrap;">${JSON.stringify(r.message, null, 2)}</pre>`,
                            indicator: "green"
                        });
                    }

                    frm.reload_doc();
                },
                error: function (err) {
                    // Optional explicit error handler
                    frappe.msgprint({
                        title: __("Error"),
                        message: __("An error occurred while assigning enumerations. Check the server logs."),
                        indicator: "red"
                    });
                }
            });
        });
    }
});

frappe.ui.form.on("Enumeration Validation Settings", {
    minimum_no_of_records: function (frm) {
        let min = frm.doc.minimum_no_of_records;

        if (min == null || min === "") return;

        if (min < 1) {
            frappe.msgprint(__("Minimum No. of Records must be at least 1."));
            frm.set_value("minimum_no_of_records", null);
        }
    },

    maximum_no_of_records: function (frm) {
        let max = frm.doc.maximum_no_of_records;

        if (max == null || max === "") return;

        if (max < 1) {
            frappe.msgprint(__("Maximum No. of Records must be at least 1."));
            frm.set_value("maximum_no_of_records", null);
            return;
        }

        // Optional: enforce max >= min if min is set
        if (frm.doc.minimum_no_of_records && max < frm.doc.minimum_no_of_records) {
            frappe.msgprint(__("Maximum No. of Records cannot be less than Minimum No. of Records."));
            frm.set_value("maximum_no_of_records", null);
        }
    },

    start_date: function (frm) {
        validate_dates(frm);
    },

    end_date: function (frm) {
        validate_dates(frm);
    }
});


function validate_dates(frm) {
    const { start_date, end_date } = frm.doc;

    // If no start_date, nothing to validate yet
    if (start_date) {
        const start = frappe.datetime.str_to_obj(start_date);
        const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());

        // Start date cannot be in the future
        if (start > today) {
            frappe.msgprint(__("Start Date cannot be later than today."));
            frm.set_value("start_date", null);
            return;
        }
    }

    // Only compare range if both dates are present
    if (start_date && end_date) {
        const start = frappe.datetime.str_to_obj(start_date);
        const end = frappe.datetime.str_to_obj(end_date);

        if (end < start) {
            frappe.msgprint(__("End Date cannot be earlier than Start Date."));
            // Clear the field that was just changed (more intuitive UX)
            const last_field = frappe.ui.form.get_last_edited_fieldname
                ? frappe.ui.form.get_last_edited_fieldname()
                : "end_date";

            if (last_field === "start_date") {
                frm.set_value("start_date", null);
            } else {
                frm.set_value("end_date", null);
            }
        }
    }
}
