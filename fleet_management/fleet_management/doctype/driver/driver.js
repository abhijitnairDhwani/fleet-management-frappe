frappe.ui.form.on("Driver", {
	refresh(frm) {
		render_license_warning(frm);
	},
	license_expiry(frm) {
		render_license_warning(frm);
	},
});

function render_license_warning(frm) {
	const wrap = frm.fields_dict.license_warning?.$wrapper;
	if (!wrap) return;
	wrap.empty();
	if (!frm.doc.license_expiry) return;
	const today = frappe.datetime.now_date();
	const days_left = frappe.datetime.get_diff(frm.doc.license_expiry, today);
	let color, msg;
	if (days_left < 0) {
		color = "red";
		msg = __("License expired {0} day(s) ago.", [Math.abs(days_left)]);
	} else if (days_left <= 30) {
		color = "orange";
		msg = __("License expires in {0} day(s).", [days_left]);
	} else {
		color = "green";
		msg = __("License valid for {0} more day(s).", [days_left]);
	}
	wrap.html(
		`<div class="indicator-pill ${color}" style="padding:6px 10px;">${msg}</div>`
	);
}
