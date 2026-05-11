"""Driver controller tests.

The controller is now silent — license-expiry surfacing lives in the client
script and the daily scheduler. These tests assert that the controller
*does not* reject any of the three license-state cases (valid / near /
expired).
"""

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.tests import IntegrationTestCase


class TestDriver(IntegrationTestCase):
	def test_save_succeeds_for_valid_long_horizon_license(self):
		d = _new_driver("TEST-LIC-VALID", days_to_expiry=365)
		d.insert()
		self.assertTrue(d.name)

	def test_save_succeeds_for_expiring_within_30d(self):
		d = _new_driver("TEST-LIC-NEAR", days_to_expiry=10)
		d.insert()
		self.assertTrue(d.name)

	def test_save_succeeds_for_expired_license(self):
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
