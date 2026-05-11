"""Tests for the Trip lifecycle: validate, submit, cancel."""

import unittest
from datetime import datetime, timedelta

import frappe


class TestTrip(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.vehicle = _ensure_vehicle("TEST-V-001", "Active", 10000)
		cls.driver = _ensure_driver("TEST-DR-001", "Test Driver", days_to_expiry=365)

	@classmethod
	def tearDownClass(cls):
		_purge_trips(cls.vehicle)
		frappe.db.delete("Vehicle", {"name": cls.vehicle})
		frappe.db.delete("Driver", {"license_no": "TEST-DR-001"})
		frappe.db.commit()

	def setUp(self):
		_purge_trips(self.vehicle)
		frappe.db.set_value("Vehicle", self.vehicle, {"odometer_km": 10000, "status": "Active"})
		frappe.db.commit()

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
		frappe.db.commit()
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10100)
		with self.assertRaises(frappe.ValidationError):
			t.save()
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Active")
		frappe.db.commit()

	# ----------------------------------------------------------- submit
	def test_on_submit_rolls_vehicle_odometer_forward(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10300)
		t.insert()
		t.submit()
		odo = frappe.db.get_value("Vehicle", self.vehicle, "odometer_km")
		self.assertEqual(odo, 10300)

	def test_on_submit_sets_current_driver(self):
		t = _new_trip(self.vehicle, self.driver, start_odo=10000, end_odo=10080)
		t.insert()
		t.submit()
		self.assertEqual(
			frappe.db.get_value("Vehicle", self.vehicle, "current_driver"),
			self.driver,
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

		# Cancel the LAST trip; odometer should fall back to the previous high water mark.
		t2.cancel()
		odo = frappe.db.get_value("Vehicle", self.vehicle, "odometer_km")
		self.assertEqual(odo, 10200)


# --------------------------------------------------- helpers (module-level)
def _ensure_vehicle(reg_no: str, status: str, odo: int) -> str:
	if not frappe.db.exists("Vehicle", reg_no):
		# minimum viable vehicle (vehicle_type required? no — link is optional)
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
	from datetime import date
	from datetime import timedelta as _td

	doc = frappe.get_doc(
		{
			"doctype": "Driver",
			"full_name": full_name,
			"license_no": license_no,
			"license_expiry": date.today() + _td(days=days_to_expiry),
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	return doc.name


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
