import frappe
from frappe import _
from frappe.model.document import Document


class MaintenanceLog(Document):
	def validate(self):
		if self.cost is not None and self.cost < 0:
			frappe.throw(_("Cost cannot be negative."))

	def on_submit(self):
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		if self.service_type == "Breakdown":
			vehicle.status = "Maintenance"
		else:
			if vehicle.status == "Maintenance":
				vehicle.status = "Active"
		if self.odometer_at_service and self.odometer_at_service > (vehicle.odometer_km or 0):
			vehicle.odometer_km = self.odometer_at_service
		vehicle.save(ignore_permissions=True)

	def on_cancel(self):
		pass
