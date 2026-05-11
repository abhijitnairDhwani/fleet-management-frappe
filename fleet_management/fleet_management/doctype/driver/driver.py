from datetime import date, timedelta

import frappe
from frappe import _
from frappe.model.document import Document


class Driver(Document):
	def validate(self):
		self._warn_license_expiry()

	def _warn_license_expiry(self):
		if not self.license_expiry:
			return
		exp = frappe.utils.getdate(self.license_expiry)
		today = frappe.utils.getdate()
		if exp < today:
			frappe.msgprint(
				_("License for {0} expired on {1}.").format(self.full_name, exp),
				title=_("License Expired"),
				indicator="red",
			)
		elif exp <= today + timedelta(days=30):
			days_left = (exp - today).days
			frappe.msgprint(
				_("License for {0} expires in {1} day(s) on {2}.").format(self.full_name, days_left, exp),
				title=_("License Expiring Soon"),
				indicator="orange",
			)
