// Copyright (c) 2024, Sydani Technologies and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Grid Creator", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Grid Creator", {
    refresh(frm) {
        frm.set_query("location_type", function () {
            return {
                filters: {
                    name: ["in", ["Ward"]]
                }
            };
        });
    },

    create_grids(frm) {
        frappe.call({
            // method: "gis.grid_creator.create_grids",
            method: "gis.square_grid_creator.create_grids",
            args: {
                ward_name: frm.doc.location,
                // hex_size: frm.doc.hex_size
                square_size: frm.doc.hex_size / 10000
            },
            callback: function (r) {
                if (r.message) {
                    frappe.msgprint(r.message);

                }
            }
        });
    },
    preview_grids(frm) {
        frappe.call({
            // method: "gis.grid_creator.preview_grids",
            method: "gis.square_grid_creator.preview_grids",

            args: {
                ward_name: frm.doc.location,
                // hex_size: frm.doc.hex_size
                square_size: frm.doc.hex_size / 10000
            },
            callback: function (r) {
                if (r.message) {
                    frappe.msgprint("Number of grids generated: " + r.message.number_of_grids);
                    frappe.msgprint('Click on the link to download preview file: <a href="' + r.message.file_url + '" target="_blank">Download</a>');
                    // console.log(r.message.number_of_grids);
                }
            }
        });
    },
});
