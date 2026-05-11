frappe.ui.form.on("Fuel Entry", {
	vehicle(frm) {
		if (!frm.doc.vehicle) return;
		frappe.db.get_value("Vehicle", frm.doc.vehicle, ["current_driver", "odometer_km"]).then((r) => {
			if (r.message?.current_driver && !frm.doc.driver) {
				frm.set_value("driver", r.message.current_driver);
			}
			if (r.message?.odometer_km && !frm.doc.odometer) {
				frm.set_value("odometer", r.message.odometer_km);
			}
		});
	},
	litres: recalc,
	cost_per_litre: recalc,
});

function recalc(frm) {
	const l = parseFloat(frm.doc.litres) || 0;
	const c = parseFloat(frm.doc.cost_per_litre) || 0;
	frm.set_value("total_cost", l * c);
}
