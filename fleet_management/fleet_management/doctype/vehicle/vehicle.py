import frappe
from frappe import _
from frappe.model.document import Document


class Vehicle(Document):
	def validate(self):
		if self.year and (self.year < 1900 or self.year > frappe.utils.now_datetime().year + 1):
			frappe.throw(_("Year {0} is not realistic.").format(self.year))
		if self.odometer_km is not None and self.odometer_km < 0:
			frappe.throw(_("Odometer cannot be negative."))
