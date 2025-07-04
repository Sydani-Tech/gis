// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vaccination Validation Summary", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch Vaccinations"), function () {
                if (!frm.doc.health_facility || !frm.doc.start_date || !frm.doc.end_date) {
                    frappe.msgprint("Please select a health facility and start/end date.");
                    return;
                }

                frappe.call({
                    method: "gis.vaccination_validation.get_vaccinations",
                    args: {
                        health_facility: frm.doc.health_facility,
                        start_date: frm.doc.start_date,
                        end_date: frm.doc.end_date
                    },

                    callback: function (r) {
                        const vaccinations = r.message.vaccinations || [];

                        if (!Array.isArray(vaccinations) || vaccinations.length === 0) {
                            frappe.msgprint("No vaccinations found for the selected filters.");
                            return;
                        }

                        const newVaccinationNames = new Set(vaccinations.map(v => v.name));

                        // Remove rows not in newVaccinationNames
                        const currentRows = frm.doc.vaccinations_under_validation || [];
                        frm.doc.vaccinations_under_validation = currentRows.filter(row => {
                            return newVaccinationNames.has(row.vaccination);
                        });
                        frm.refresh_field("vaccinations_under_validation");

                        const existingVaccinations = new Set(
                            (frm.doc.vaccinations_under_validation || []).map(row => row.vaccination)
                        );

                        vaccinations.forEach(vaccination => {
                            if (existingVaccinations.has(vaccination.name)) return;

                            frappe.call({
                                method: "gis.vaccination_validation.get_vaccination_validation_questions",
                                args: {
                                    vaccination_name: vaccination.name
                                },
                                callback: function (res) {
                                    const answers = res.message;
                                    let prettifiedMessage = "";

                                    Object.entries(answers).forEach(([sectionKey, sectionValue], index) => {
                                        const header = sectionKey.replace(/_/g, " ").toUpperCase();
                                        if (index > 0) prettifiedMessage += `<br><br>`;
                                        prettifiedMessage += `<strong>${header}</strong><br>`;

                                        Object.entries(sectionValue).forEach(([fieldKey, fieldValue]) => {
                                            if (fieldKey === "type" || fieldKey === "options") return;
                                            prettifiedMessage += `• ${fieldKey}: ${fieldValue}<br>`;
                                        });
                                    });

                                    frm.add_child("vaccinations_under_validation", {
                                        vaccination: vaccination.name,
                                        vaccinator: vaccination.owner,
                                        full_name: vaccination.full_name,
                                        gender: vaccination.gender,
                                        date_of_birth: vaccination.date_of_birth,
                                        last_name: vaccination.last_name,
                                        first_name: vaccination.first_name,
                                        vaccination_date: vaccination.vaccination_date,
                                        vaccines_administered: vaccination.vaccines_taken,
                                        last_modified: frappe.datetime.now_datetime()
                                    });

                                    frm.refresh_field("vaccinations_under_validation");
                                }
                            });
                        });
                    }

                });
            });
        }

        // Ensure child table is loaded
        if (frm.fields_dict["vaccinations_under_validation"] && frm.fields_dict["vaccinations_under_validation"].grid) {
            frm.fields_dict["vaccinations_under_validation"].grid.grid_rows.forEach(row => {
                let doc = row.doc; // Get row data
                let $row = $(row.row); // Get row element

                // Define colors based on status
                let color_map = {
                    "Pending": "#fff3cd",  // Light Yellow
                    "Approved": "#93e68e", // Deep Green
                    "Corrected": "#d4edda", // Light Green
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

            frm.add_custom_button('Discard', () => {
                frappe.confirm(
                    'Are you sure you want to discard this document?',
                    () => {
                        frm.set_value('status', 'Discarded');
                        frm.save();
                    }
                );
            }, 'Actions');
        }

    }
});


frappe.ui.form.on("Vaccinations Under Validation", {
    status: function (frm, cdt, cdn) {
        // Ensure child table is loaded
        frappe.model.set_value(cdt, cdn, "last_modified", frappe.datetime.now_datetime());
        if (frm.fields_dict["vaccinations_under_validation"] && frm.fields_dict["vaccinations_under_validation"].grid) {
            frm.fields_dict["vaccinations_under_validation"].grid.grid_rows.forEach(row => {
                let doc = row.doc; // Get row data
                let $row = $(row.row); // Get row element

                // Define colors based on status
                let color_map = {
                    "Pending": "#fff3cd",  // Light Yellow
                    "Approved": "#93e68e", // Deep Green
                    "Corrected": "#d4edda", // Light Green
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
    }
});

// frappe.ui.form.on("Vaccination Validation", {
//     refresh(frm) {
//         setup_grid_events(frm);
//         apply_row_colors(frm);
//     },

//     vaccinations_under_validation_on_form_rendered(frm) {
//         // This ensures colors are reapplied when editing child rows
//         apply_row_colors(frm);
//     }
// });

// frappe.ui.form.on("Vaccinations Under Validation", {
//     status(frm, cdt, cdn) {
//         frappe.model.set_value(cdt, cdn, "last_modified", frappe.datetime.now_datetime());
//         apply_row_colors(frm);
//     }
// });

// function setup_grid_events(frm) {
//     const grid = frm.fields_dict["vaccinations_under_validation"]?.grid;
//     if (!grid || grid.__color_events_added) return;

//     grid.__color_events_added = true;

//     // Hook into the grid's refresh when navigating pages
//     const original_refresh = grid.refresh;
//     grid.refresh = function (...args) {
//         const result = original_refresh.apply(this, args);
//         apply_row_colors(frm);
//         return result;
//     };

//     // Hook into pagination buttons
//     ["next_page", "prev_page", "first_page", "last_page"].forEach(event => {
//         const original = grid[event];
//         grid[event] = function (...args) {
//             const result = original.apply(this, args);
//             apply_row_colors(frm);
//             return result;
//         };
//     });
// }

// function apply_row_colors(frm) {
//     const grid = frm.fields_dict["vaccinations_under_validation"]?.grid;
//     if (!grid) return;

//     const color_map = {
//         "Pending": "#fff3cd",    // Light Yellow
//         "Approved": "#93e68e",   // Deep Green
//         "Corrected": "#d4edda",  // Light Green
//         "Returned": "#f8d7da"    // Light Red
//     };

//     grid.grid_rows.forEach(row => {
//         const doc = row.doc;
//         const $row = $(row.row);
//         const color = color_map[doc.status] || "";
//         $row.css("background-color", color);
//     });
// }
