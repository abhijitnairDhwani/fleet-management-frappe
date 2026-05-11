"""Scheduled tasks for Fleet Management."""

from datetime import timedelta

import frappe


def check_license_expiries(window_days: int = 30) -> None:
	"""Daily job: log a warning entry for licenses expiring within window_days."""
	cutoff = frappe.utils.getdate() + timedelta(days=window_days)
	expiring = frappe.get_all(
		"Driver",
		filters={"status": "Active", "license_expiry": ["<=", cutoff]},
		fields=["name", "full_name", "license_expiry"],
	)
	for d in expiring:
		days_left = (d["license_expiry"] - frappe.utils.getdate()).days
		frappe.logger("fleet").warning(
			f"Driver {d['name']} ({d['full_name']}) license expires in {days_left}d on {d['license_expiry']}"
		)
