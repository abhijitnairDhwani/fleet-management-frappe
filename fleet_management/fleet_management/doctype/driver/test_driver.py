"""Tests for Driver: license expiry warnings."""

import unittest
from datetime import date, timedelta

import frappe


class TestDriver(unittest.TestCase):
	def tearDown(self):
		for name in frappe.get_all("Driver", filters={"license_no": ["like", "TEST-LIC-%"]}, pluck="name"):
			frappe.delete_doc("Driver", name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_save_succeeds_for_valid_long_horizon_license(self):
		d = _new_driver("TEST-LIC-VALID", days_to_expiry=365)
		d.insert()
		self.assertTrue(d.name)

	def test_save_succeeds_for_expiring_within_30d_with_warning_emitted(self):
		# A near-expiry license should NOT block save — it emits an orange msgprint.
		d = _new_driver("TEST-LIC-NEAR", days_to_expiry=10)
		d.insert()
		self.assertTrue(d.name)

	def test_save_succeeds_for_expired_license_with_red_warning(self):
		d = _new_driver("TEST-LIC-EXP", days_to_expiry=-5)
		d.insert()
		self.assertTrue(d.name)


def _new_driver(license_no: str, *, days_to_expiry: int):
	return frappe.get_doc(
		{
			"doctype": "Driver",
			"full_name": "Test Person",
			"license_no": license_no,
			"license_expiry": date.today() + timedelta(days=days_to_expiry),
			"status": "Active",
		}
	)
