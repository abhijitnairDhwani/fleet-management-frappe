import frappe
from frappe import _
from frappe.model.document import Document


class FuelEntry(Document):
	def validate(self):
		if self.litres is not None and self.litres <= 0:
			frappe.throw(_("Litres must be positive."))
		if self.cost_per_litre is not None and self.cost_per_litre < 0:
			frappe.throw(_("Cost per litre cannot be negative."))
		self.total_cost = (self.litres or 0) * (self.cost_per_litre or 0)

	def on_update(self):
		if not self.odometer:
			return
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		if self.odometer > (vehicle.odometer_km or 0):
			vehicle.odometer_km = self.odometer
			vehicle.save(ignore_permissions=True)
