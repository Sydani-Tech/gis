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
                // frm.set_value("vaccinations_under_validation", []);
                frm.clear_table("vaccinations_under_validation");
                frappe.call({
                    method: "gis.vaccination_validation.get_vaccinations",
                    args: {
                        health_facility: frm.doc.health_facility,
                        start_date: frm.doc.start_date,
                        end_date: frm.doc.end_date
                    },

                    callback: function (r) {

                        const vaccinations = r.message.vaccinations || [];

                        // console.log("Final vaccinations array:", vaccinations);

                        if (!Array.isArray(vaccinations) || vaccinations.length === 0) {
                            frappe.msgprint("No vaccinations found for the selected filters.");
                            return;
                        }

                        // Now loop through each vaccination
                        vaccinations.forEach(vaccination => {
                            frappe.call({
                                method: "gis.vaccination_validation.get_vaccination_validation_questions",
                                args: {
                                    vaccination_name: vaccination.name
                                },

                                callback: function (res) {
                                    const answers = res.message;
                                    let prettifiedMessage = "";

                                    Object.entries(answers).forEach(([sectionKey, sectionValue], index) => {
                                        // Convert key to uppercase and replace underscores with spaces
                                        const header = sectionKey.replace(/_/g, " ").toUpperCase();

                                        // Add double paragraph break before each section
                                        if (index > 0) prettifiedMessage += `<br><br>`;

                                        prettifiedMessage += `<strong>${header}</strong><br>`;

                                        Object.entries(sectionValue).forEach(([fieldKey, fieldValue]) => {
                                            if (fieldKey === "type" || fieldKey === "options") return;
                                            prettifiedMessage += `• ${fieldKey}: ${fieldValue}<br>`;
                                        });
                                    });

                                    const row = frm.add_child("vaccinations_under_validation", {
                                        vaccination: vaccination.name,
                                        vaccinator: vaccination.owner,
                                        validation_answers: prettifiedMessage.trim(),
                                        full_name: vaccination.full_name,
                                        gender: vaccination.gender,
                                        date_of_birth: vaccination.date_of_birth,
                                        last_name: vaccination.last_name,
                                        first_name: vaccination.first_name,
                                        vaccination_date: vaccination.vaccination_date,
                                        vaccines_administered: vaccination.vaccines_taken,
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
    }
});


frappe.ui.form.on("Vaccination Validation Summary", {
    vaccinations_under_validation: function (frm) {
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
    }
});