// Copyright (c) 2025, Sydani Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vaccination Validation Summary", {
    refresh(frm) {
        frm.add_custom_button(__("Fetch Vaccinations"), function () {
            if (!frm.doc.health_facility || !frm.doc.start_time || !frm.doc.end_time) {
                return;
            }
            // frm.set_value("vaccinations_under_validation", []);
            frm.clear_table("vaccinations_under_validation");
            frappe.call({
                method: "gis.vaccination_validation.get_vaccinations",
                args: {
                    health_facility: frm.doc.health_facility,
                    start_time: frm.doc.start_time,
                    end_time: frm.doc.end_time
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
});
