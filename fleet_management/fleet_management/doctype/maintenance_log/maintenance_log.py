"""Maintenance Log controller.

Side effects on the Vehicle live in
``fleet_management.services.vehicle_state.on_maintenance_submit`` /
``on_maintenance_cancel`` and are wired via ``doc_events`` in ``hooks.py``.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class MaintenanceLog(Document):
	def validate(self):
		if self.cost is not None and self.cost < 0:
			frappe.throw(_("Cost cannot be negative."))
