import frappe
from frappe import _
from frappe.model.document import Document


class Trip(Document):
	def validate(self):
		self._compute_distance()
		self._check_vehicle_available()
		self._check_driver_active()

	def before_submit(self):
		if not self.end_datetime or self.end_odo is None:
			frappe.throw(_("Trip cannot be submitted until end time and end odometer are filled."))
		if (self.distance_km or 0) <= 0:
			frappe.throw(_("Distance must be greater than zero to submit a trip."))
		self.status = "Completed"

	def on_submit(self):
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		vehicle.odometer_km = max(vehicle.odometer_km or 0, self.end_odo or 0)
		vehicle.current_driver = self.driver
		if vehicle.status == "In-Use":
			vehicle.status = "Active"
		vehicle.save(ignore_permissions=True)

	def on_cancel(self):
		self.status = "Cancelled"
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		new_max = frappe.db.sql(
			"""SELECT MAX(end_odo) FROM `tabTrip`
			   WHERE vehicle=%s AND docstatus=1 AND name != %s""",
			(self.vehicle, self.name),
		)[0][0] or 0
		vehicle.odometer_km = max(vehicle.odometer_km or 0, new_max)
		vehicle.save(ignore_permissions=True)

	def _compute_distance(self):
		if self.start_odo is not None and self.end_odo is not None:
			if self.end_odo < self.start_odo:
				frappe.throw(_("End odometer ({0}) cannot be less than start odometer ({1}).").format(self.end_odo, self.start_odo))
			self.distance_km = self.end_odo - self.start_odo
		else:
			self.distance_km = 0

	def _check_vehicle_available(self):
		if not self.vehicle:
			return
		vstatus = frappe.db.get_value("Vehicle", self.vehicle, "status")
		if vstatus in ("Retired", "Maintenance") and self.docstatus == 0:
			frappe.throw(_("Vehicle {0} is currently {1} and cannot be assigned to a trip.").format(self.vehicle, vstatus))

	def _check_driver_active(self):
		if not self.driver:
			return
		dstatus = frappe.db.get_value("Driver", self.driver, "status")
		if dstatus == "Inactive":
			frappe.throw(_("Driver {0} is inactive.").format(self.driver))
