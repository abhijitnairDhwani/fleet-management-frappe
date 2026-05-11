"""Fuel Entry controller.

Validation only — the one-shot odometer roll-forward on insert lives in
``fleet_management.services.vehicle_state.on_fuel_entry_after_insert`` and
is wired via ``doc_events`` in ``hooks.py``. That avoids the previous
``on_update`` side-effect that fired on every typo correction.
"""

from __future__ import annotations

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
