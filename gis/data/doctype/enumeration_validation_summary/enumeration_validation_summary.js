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

        highlightSampleResponsesRows(frm);

        if (!frm.is_dirty() && frm.doc.docstatus === 0) {
            frm.add_custom_button('Submit Now', () => {
                frappe.confirm(
                    'Are you sure you want to submit this document?',
                    () => {
                        frm.save('Submit');
                    }
                );
            }, 'Actions');
            frm.add_custom_button('Discard Validation', () => {
                frappe.confirm(
                    'Are you sure you want to DISCARD this document?',
                    () => {
                        frm.set_value('status', 'Discarded');
                        frm.save();
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

                        const selected = r.message.selected_buildings || [];
                        const all = r.message.all_buildings || [];

                        if (selected.length === 0 && all.length === 0) {
                            frappe.msgprint("No buildings found for the specified filters.");
                            return;
                        }

                        // --- Handle enumeration_sample_responses ---
                        const newSelectedNames = new Set(selected.map(b => b.name));
                        frm.doc.enumeration_sample_responses = (frm.doc.enumeration_sample_responses || [])
                            .filter(row => newSelectedNames.has(row.record));

                        const existingSelected = new Set(frm.doc.enumeration_sample_responses.map(row => row.record));
                        selected.forEach(building => {
                            if (!existingSelected.has(building.name)) {
                                frm.add_child("enumeration_sample_responses", {
                                    doctype_name: "Building",
                                    status: "Pending",
                                    record: building.name,
                                    settlement: building.settlement,
                                    enumerator: building.owner,
                                    geolocation: building.geolocation,
                                    building_picture: building.building_picture,
                                    building_picture_2: building.building_picture_2,
                                    response_geolocation: null,
                                    building_geolocation_updated_from_validation: 0,
                                    last_modified: frappe.datetime.now_datetime()
                                });
                            }
                        });
                        frm.refresh_field("enumeration_sample_responses");

                        // --- Handle records_under_validation ---

                        frm.clear_table("records_under_validation"); // Clear existing rows
                        const newAllNames = new Set(all.map(b => b.name));
                        frm.doc.records_under_validation = (frm.doc.records_under_validation || [])
                            .filter(row => newAllNames.has(row.record));

                        const existingAll = new Set(frm.doc.records_under_validation.map(row => row.record));
                        all.forEach(building => {
                            if (!existingAll.has(building.name)) {
                                frm.add_child("records_under_validation", {
                                    doctype_name: "Building",
                                    status: "Pending",
                                    record: building.name,
                                    settlement: building.settlement,
                                    enumerator: building.owner,
                                    response_geolocation: null,
                                    building_geolocation_updated_from_validation: 0
                                });
                            }
                        });
                        frm.refresh_field("records_under_validation");

                        frappe.msgprint("Buildings successfully synced (preserving existing rows).");
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

frappe.ui.form.on("Enumeration Sample Responses", {
    status: function (frm, cdt, cdn) {
        // Ensure child table is loaded
        frappe.model.set_value(cdt, cdn, "last_modified", frappe.datetime.now_datetime());
        highlightSampleResponsesRows(frm);
    },
    refresh: function (frm, cdt, cdn) {
        // Ensure child table is loaded
        highlightSampleResponsesRows(frm);
    }
});

function highlightSampleResponsesRows(frm) {
    if (frm.fields_dict["enumeration_sample_responses"] && frm.fields_dict["enumeration_sample_responses"].grid) {
        frm.fields_dict["enumeration_sample_responses"].grid.grid_rows.forEach(row => {
            let doc = row.doc; // Row data
            let $row = $(row.row); // Row element

            // Define colors for the whole row based on status
            let color_map = {
                "Pending": "#fff3cd",  // Light Yellow
                "Approved": "#d4edda", // Light Green
                "Returned": "#f8d7da"  // Light Red
            };

            // Apply row background color based on status
            if (color_map[doc.status]) {
                $row.css("background-color", color_map[doc.status]);
            } else {
                $row.css("background-color", ""); // Reset if no match
            }

            // Highlight ONLY the `update_building_geolocation` cell if geolocation is updated
            let $geoCell = $row.find('[data-fieldname="update_building_geolocation"]');
            if (doc.building_geolocation_updated_from_validation === 1) {
                $geoCell.css("background-color", "#cce5ff");  // Light Blue for updated
            } else {
                // Reset to row's background color (inherit from row)
                $geoCell.css("background-color", color_map[doc.status] || "");
            }
        });
    }
}

frappe.ui.form.on('Enumeration Sample Responses', {
    update_building_geolocation: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        frappe.confirm(
            `Are you sure you want to update the geolocation for Building <b>${row.record}</b>?`,
            function () {
                frappe.call({
                    method: "frappe.client.set_value",
                    args: {
                        doctype: "Building",
                        name: row.record,
                        fieldname: {
                            geolocation: row.response_geolocation
                        }
                    },
                    callback: function (response) {
                        if (!response.exc) {
                            frappe.model.set_value(cdt, cdn, "building_geolocation_updated_from_validation", 1);
                            frappe.msgprint(__('Building geolocation updated successfully.'));
                        } else {
                            frappe.msgprint(__('Failed to update geolocation.'));
                        }
                    }
                });
            },
            function () {
                frappe.msgprint(__('Update cancelled.'));
            }
        );
    }
});

