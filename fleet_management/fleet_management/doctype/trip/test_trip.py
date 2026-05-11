"""Trip lifecycle tests.

Uses ``IntegrationTestCase`` so every test rolls back at the class level and
each ``setUp`` resets shared state — no manual ``frappe.db.commit()`` and no
``tearDownClass`` cleanup is required.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import frappe
from frappe.tests import IntegrationTestCase


class TestTrip(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.vehicle = _ensure_vehicle("TEST-V-001", "Active", 10000)
		cls.driver = _ensure_driver("TEST-DR-001", "Test Driver", days_to_expiry=365)

	def setUp(self):
		super().setUp()
		_purge_trips(self.vehicle)
		frappe.db.set_value("Vehicle", self.vehicle, {"odometer_km": 10000, "status": "Active"})

	# --------------------------------------------------------- validate
	def test_distance_computed_on_validate(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10125)
		t.save()
		self.assertEqual(t.distance_km, 125)

	def test_end_odo_less_than_start_rejected(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=9990)
		with self.assertRaises(frappe.ValidationError):
			t.save()

	def test_cannot_assign_to_vehicle_in_maintenance(self):
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Maintenance")
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10100)
		with self.assertRaises(frappe.ValidationError):
			t.save()

	# ----------------------------------------------------------- submit
	def test_on_submit_rolls_vehicle_odometer_forward(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10300)
		t.insert()
		t.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 10300)

	def test_on_submit_sets_current_driver_for_recent_trip(self):
		# Trip starts ~10 minutes ago -> recent -> should set current_driver.
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10080)
		t.start_datetime = (datetime.now() - timedelta(minutes=10)).isoformat()
		t.end_datetime = datetime.now().isoformat()
		t.insert()
		t.submit()
		self.assertEqual(
			frappe.db.get_value("Vehicle", self.vehicle, "current_driver"),
			self.driver,
		)

	def test_on_submit_does_not_set_current_driver_for_backdated_trip(self):
		# Trip from 60 days ago should NOT silently rewrite current_driver.
		other_driver = _ensure_driver("TEST-DR-OTHER", "Other Driver", days_to_expiry=365)
		frappe.db.set_value("Vehicle", self.vehicle, "current_driver", other_driver)
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10080)
		t.start_datetime = (datetime.now() - timedelta(days=60)).isoformat()
		t.end_datetime = (datetime.now() - timedelta(days=60, hours=-1)).isoformat()
		t.insert()
		t.submit()
		self.assertEqual(
			frappe.db.get_value("Vehicle", self.vehicle, "current_driver"),
			other_driver,
		)

	def test_submit_requires_end_fields(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=None)
		t.end_datetime = None
		t.insert()
		with self.assertRaises(frappe.ValidationError):
			t.submit()

	# ---------------------------------------------------------- cancel
	def test_on_cancel_recomputes_odometer_from_remaining_trips(self):
		t1 = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10200)
		t1.insert()
		t1.submit()
		t2 = _new_trip(self.vehicle, self.driver, start_odo=10200, end_odo=10500)
		t2.insert()
		t2.submit()

		t2.cancel()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 10200)

	def test_on_cancel_resets_to_zero_when_no_remaining_trips(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10250)
		t.insert()
		t.submit()
		t.cancel()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 0)


# --------------------------------------------------------- helpers (module-level)
def _ensure_vehicle(reg_no: str, status: str, odo: int) -> str:
	if not frappe.db.exists("Vehicle", reg_no):
		frappe.get_doc(
			{
				"doctype": "Vehicle",
				"registration_no": reg_no,
				"make": "TestMake",
				"model": "TestModel",
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


def _new_trip(vehicle: str, driver: str, *, start_odo: int, end_odo: int | None):
	start = datetime.now().replace(microsecond=0)
	end = start + timedelta(hours=2)
	return frappe.get_doc(
		{
			"doctype": "Trip",
			"vehicle": vehicle,
			"driver": driver,
			"start_datetime": start.isoformat(),
			"end_datetime": end.isoformat() if end_odo is not None else None,
			"start_odo": start_odo,
			"end_odo": end_odo,
			"purpose": "Test",
			"status": "Planned",
		}
	)


def _purge_trips(vehicle: str):
	for name in frappe.get_all("Trip", filters={"vehicle": vehicle}, pluck="name"):
		doc = frappe.get_doc("Trip", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Trip", name, force=True, ignore_permissions=True)
