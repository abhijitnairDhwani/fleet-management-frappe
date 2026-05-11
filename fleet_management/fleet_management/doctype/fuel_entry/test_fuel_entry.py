"""Tests for Fuel Entry: total_cost computation and rejection rules."""

import unittest
from datetime import date

import frappe


class TestFuelEntry(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
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

	@classmethod
	def tearDownClass(cls):
		for name in frappe.get_all("Fuel Entry", filters={"vehicle": cls.vehicle}, pluck="name"):
			frappe.delete_doc("Fuel Entry", name, force=True, ignore_permissions=True)
		frappe.db.delete("Vehicle", {"name": cls.vehicle})
		frappe.db.commit()

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
