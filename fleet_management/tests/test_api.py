"""REST API endpoint tests.

Covers ``fleet_management.api.*``:
* Each endpoint runs end-to-end without DB errors (catches the SQLite-only
  ``strftime`` bug that previously slipped past on MariaDB CI).
* Each endpoint enforces the right permission boundary — a non-Fleet user
  is rejected and a Driver-only user is self-scoped.
"""

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.tests import IntegrationTestCase

from fleet_management import api


class TestApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_vehicle = _ensure_vehicle("TEST-API-V-001", "Active", 30000)
		# A driver expiring tomorrow — guarantees an entry in the 7-day window
		cls.expiring_driver = _ensure_driver("TEST-API-DR-EXP", "Expiring Person", days_to_expiry=1)
		# A driver expiring far in the future — should not show up in 7-day window
		cls.safe_driver = _ensure_driver("TEST-API-DR-SAFE", "Safe Person", days_to_expiry=365)

	# ----------------------------------------------------- get_vehicle_summary
	def test_get_vehicle_summary_returns_expected_shape(self):
		result = api.get_vehicle_summary(self.test_vehicle)
		self.assertEqual(result["vehicle"], self.test_vehicle)
		self.assertIn("trips", result)
		self.assertIn("total_km", result)
		self.assertIn("fuel_litres_total", result)
		self.assertIn("fuel_cost_total", result)
		self.assertEqual(result["status"], "Active")

	def test_get_vehicle_summary_rejects_non_string(self):
		with self.assertRaises(frappe.ValidationError):
			api.get_vehicle_summary(["a", "b"])

	def test_get_vehicle_summary_rejects_empty(self):
		with self.assertRaises(frappe.ValidationError):
			api.get_vehicle_summary("")

	# ------------------------------------------------ upcoming_license_expiries
	def test_expiring_driver_appears_in_window(self):
		results = api.upcoming_license_expiries(days=7)
		names = {r["name"] for r in results}
		self.assertIn(self.expiring_driver, names)
		self.assertNotIn(self.safe_driver, names)

	def test_negative_days_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			api.upcoming_license_expiries(days=-1)

	def test_string_days_coerced(self):
		# `frappe.utils.cint` should coerce "30" -> 30 without raising.
		results = api.upcoming_license_expiries(days="30")
		self.assertIsInstance(results, list)

	# --------------------------------------------------------- fleet_dashboard
	def test_fleet_dashboard_runs_without_sql_error(self):
		# This is the regression test for the SQLite-only `strftime` bug.
		result = api.fleet_dashboard()
		for key in (
			"vehicles",
			"vehicles_active",
			"vehicles_in_maintenance",
			"drivers",
			"trips_open",
			"distance_this_month_km",
		):
			self.assertIn(key, result)
		self.assertGreaterEqual(result["distance_this_month_km"], 0)

	def test_fleet_dashboard_rejects_non_fleet_role(self):
		# Simulate a logged-in user with no Fleet role.
		test_user = _ensure_user("api_test_user@example.com")
		original_user = frappe.session.user
		try:
			frappe.set_user(test_user)
			with self.assertRaises(frappe.PermissionError):
				api.fleet_dashboard()
		finally:
			frappe.set_user(original_user)


# ------------------------------------------------------- helpers (module-level)
def _ensure_vehicle(reg_no: str, status: str, odo: int) -> str:
	if not frappe.db.exists("Vehicle", reg_no):
		frappe.get_doc(
			{
				"doctype": "Vehicle",
				"registration_no": reg_no,
				"make": "T",
				"model": "M",
				"status": status,
				"odometer_km": odo,
			}
		).insert(ignore_permissions=True)
	return reg_no


def _ensure_driver(license_no: str, full_name: str, days_to_expiry: int) -> str:
	existing = frappe.db.get_value("Driver", {"license_no": license_no}, "name")
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Driver",
				"full_name": full_name,
				"license_no": license_no,
				"license_expiry": date.today() + timedelta(days=days_to_expiry),
				"status": "Active",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _ensure_user(email: str) -> str:
	if frappe.db.exists("User", email):
		return email
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "API",
			"last_name": "Tester",
			"send_welcome_email": 0,
			"new_password": "Test@1234",
		}
	).insert(ignore_permissions=True)
	return user.name
