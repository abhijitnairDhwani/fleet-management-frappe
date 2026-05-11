"""Driver controller.

Validation rules:
* ``user`` (link to Frappe User) is 1:1 with Driver. Enforced at the
  controller level rather than via a DB unique constraint, because adding a
  unique column to an existing SQLite table is not supported.

License-expiry surfacing is split across three layers, each authoritative
for its own use:

* **Client (``driver.js``)** — live indicator pill on the form. UX feedback.
* **Server (``fleet_management.scheduled.check_license_expiries``)** —
  daily job that logs warnings (and in production would email a digest).
* **Controller** — silent. Validation runs from every code path (REST PUT,
  background jobs, fixtures); flashing a toast there is wrong-shaped and
  was previously duplicating the other two layers.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class Driver(Document):
	def validate(self):
		self._enforce_unique_user()

	def _enforce_unique_user(self):
		if not self.user:
			return
		other = frappe.db.get_value(
			"Driver",
			{"user": self.user, "name": ["!=", self.name or ""]},
			"name",
		)
		if other:
			frappe.throw(_("User {0} is already linked to Driver {1}.").format(self.user, other))
