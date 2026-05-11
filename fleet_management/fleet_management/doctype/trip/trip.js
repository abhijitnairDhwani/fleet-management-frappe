frappe.ui.form.on("Trip", {
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		frappe.db.get_doc("Vehicle", frm.doc.vehicle).then((veh) => {
			if (veh.current_driver && !frm.doc.driver) {
				frm.set_value("driver", veh.current_driver);
			}
			if (veh.odometer_km && !frm.doc.start_odo) {
				frm.set_value("start_odo", veh.odometer_km);
			}
			if (["Retired", "Maintenance"].includes(veh.status)) {
				frappe.show_alert(
					{ message: __("Vehicle is {0}", [veh.status]), indicator: "orange" },
					6
				);
			}
		});
	},
	start_odo: recompute_distance,
	end_odo: recompute_distance,
});

function recompute_distance(frm) {
	const s = parseFloat(frm.doc.start_odo);
	const e = parseFloat(frm.doc.end_odo);
	if (!isNaN(s) && !isNaN(e) && e >= s) {
		frm.set_value("distance_km", e - s);
	}
}
