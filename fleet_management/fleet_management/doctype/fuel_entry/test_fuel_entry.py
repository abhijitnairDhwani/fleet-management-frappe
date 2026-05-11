"""Fuel Entry tests: total_cost computation, rejections, and odometer roll-forward."""

from __future__ import annotations

from datetime import date

import frappe
from frappe.tests import IntegrationTestCase


class TestFuelEntry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Vehicle", "TEST-FE-001"):
			frappe.get_doc(
				{
					"doctype": "Vehicle",
					"registration_no": "TEST-FE-001",
					"make": "T",
					"model": "M",
					"status": "Active",
					"odometer_km": 5000,
				}
			).insert(ignore_permissions=True)
		cls.vehicle = "TEST-FE-001"

	def setUp(self):
		super().setUp()
		frappe.db.set_value("Vehicle", self.vehicle, "odometer_km", 5000)

	def test_total_cost_computed(self):
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 40,
				"cost_per_litre": 100.5,
			}
		)
		fe.insert()
		self.assertAlmostEqual(fe.total_cost, 4020.0, places=2)

	def test_zero_litres_rejected(self):
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 0,
				"cost_per_litre": 100,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			fe.insert()

	def test_negative_cost_per_litre_rejected(self):
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 20,
				"cost_per_litre": -5,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			fe.insert()

	def test_after_insert_rolls_vehicle_odometer_forward(self):
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 30,
				"cost_per_litre": 100,
				"odometer": 5500,
			}
		)
		fe.insert()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 5500)

	def test_after_insert_does_not_lower_odometer(self):
		frappe.db.set_value("Vehicle", self.vehicle, "odometer_km", 6000)
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 30,
				"cost_per_litre": 100,
				"odometer": 5500,
			}
		)
		fe.insert()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 6000)

	def test_save_does_not_re_propagate_after_initial_insert(self):
		fe = frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": self.vehicle,
				"date": date.today(),
				"litres": 30,
				"cost_per_litre": 100,
				"odometer": 5500,
			}
		)
		fe.insert()
		# Manually lower the vehicle's odometer to verify a subsequent fuel-entry
		# save does NOT push it back up — propagation lives in after_insert only.
		frappe.db.set_value("Vehicle", self.vehicle, "odometer_km", 5000)
		fe.notes = "edit"
		fe.save()
		self.assertEqual(frappe.db.get_value("Vehicle", self.vehicle, "odometer_km"), 5000)
