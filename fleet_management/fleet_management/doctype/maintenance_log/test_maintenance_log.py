"""Maintenance Log lifecycle tests."""

from __future__ import annotations

from datetime import date

import frappe
from frappe.tests import IntegrationTestCase


class TestMaintenanceLog(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Vehicle", "TEST-ML-001"):
			frappe.get_doc(
				{
					"doctype": "Vehicle",
					"registration_no": "TEST-ML-001",
					"make": "M",
					"model": "L",
					"status": "Active",
					"odometer_km": 20000,
				}
			).insert(ignore_permissions=True)
		cls.vehicle = "TEST-ML-001"

	def setUp(self):
		super().setUp()
		_purge_maintenance(self.vehicle)
		frappe.db.set_value("Vehicle", self.vehicle, {"status": "Active", "odometer_km": 20000})

	def test_breakdown_flips_vehicle_to_maintenance(self):
		log = _new_log(self.vehicle, "Breakdown", 25000)
		log.insert()
		log.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "status"), "Maintenance")

	def test_routine_service_returns_vehicle_to_active_when_in_maintenance(self):
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Maintenance")
		log = _new_log(self.vehicle, "Routine", 25500)
		log.insert()
		log.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "status"), "Active")

	def test_odometer_rolls_forward_when_service_odo_higher(self):
		log = _new_log(self.vehicle, "Oil Change", 25500)
		log.insert()
		log.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 25500)

	def test_odometer_does_not_roll_back_on_lower_service_odo(self):
		log = _new_log(self.vehicle, "Oil Change", 15000)  # lower than current 20000
		log.insert()
		log.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 20000)

	def test_negative_cost_rejected(self):
		log = _new_log(self.vehicle, "Routine", 22000, cost=-1)
		with self.assertRaises(frappe.ValidationError):
			log.insert()

	def test_cancelling_solo_breakdown_returns_vehicle_to_active(self):
		log = _new_log(self.vehicle, "Breakdown", 25000)
		log.insert()
		log.submit()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "status"), "Maintenance")
		log.cancel()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "status"), "Active")

	def test_cancelling_one_breakdown_with_another_still_open_keeps_maintenance(self):
		log_a = _new_log(self.vehicle, "Breakdown", 25000)
		log_a.insert()
		log_a.submit()
		log_b = _new_log(self.vehicle, "Breakdown", 25500)
		log_b.insert()
		log_b.submit()
		log_a.cancel()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "status"), "Maintenance")


def _purge_maintenance(vehicle: str) -> None:
	for name in frappe.get_all("Maintenance Log", filters={"vehicle": vehicle}, pluck="name"):
		doc = frappe.get_doc("Maintenance Log", name)
		if doc.docstatus == 1:
			try:
				doc.cancel()
			except Exception:
				pass
		frappe.delete_doc("Maintenance Log", name, force=True, ignore_permissions=True)


def _new_log(vehicle: str, service_type: str, odo: int, *, cost: float = 1000):
	return frappe.get_doc(
		{
			"doctype": "Maintenance Log",
			"vehicle": vehicle,
			"service_date": date.today(),
			"service_type": service_type,
			"odometer_at_service": odo,
			"cost": cost,
			"vendor": "Test Vendor",
		}
	)
