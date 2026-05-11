"""Vehicle state-mutation service.

All cross-doctype writes that touch a Vehicle row live here. Trip,
Maintenance Log, and Fuel Entry controllers stay thin and call into these
functions via `doc_events` in `hooks.py`. This keeps cross-doctype
concurrency in one place and removes the gratuitous ``ignore_permissions``
flags that were scattered across submit/cancel handlers.

Concurrency model
-----------------
The Vehicle row is mutated by several writers (Trip submit/cancel,
Maintenance submit/cancel, Fuel after-insert). Each function below
acquires a row lock on the Vehicle via ``frappe.db.get_value(..., for_update=True)``
before reading the current state, then issues atomic writes with
``frappe.db.set_value``. This eliminates the read-then-write race that the
audit flagged on ``Vehicle.odometer_km``.
"""

from __future__ import annotations

from datetime import timedelta

import frappe

_BREAKDOWN = "Breakdown"


# --------------------------------------------------------------------- Trip
def on_trip_submit(doc, method=None):
	"""Roll vehicle odometer forward (high-water-mark) and refresh current_driver.

	Only refresh ``current_driver`` if this trip is recent (started within
	the last 24h) — submitting a backdated trip should not silently rewrite
	the driver assignment.
	"""
	_lock_vehicle(doc.vehicle)

	current_odo = frappe.db.get_value("Vehicle", doc.vehicle, "odometer_km") or 0
	new_odo = max(current_odo, doc.end_odo or 0)

	updates = {"odometer_km": new_odo}
	if _is_recent(doc.start_datetime):
		updates["current_driver"] = doc.driver

	status = frappe.db.get_value("Vehicle", doc.vehicle, "status")
	if status == "In-Use":
		updates["status"] = "Active"

	frappe.db.set_value("Vehicle", doc.vehicle, updates)


def on_trip_cancel(doc, method=None):
	"""Roll the odometer back to the highest end_odo of any remaining submitted trip.

	The vehicle's last unsubmitted-trip odometer acts as the floor (0 when no
	trips remain). Status is intentionally NOT changed here — vehicle status
	transitions are owned by maintenance flows.
	"""
	_lock_vehicle(doc.vehicle)

	new_max = (
		frappe.db.sql(
			"""SELECT MAX(end_odo) FROM `tabTrip`
			   WHERE vehicle = %s AND docstatus = 1 AND name != %s""",
			(doc.vehicle, doc.name),
		)[0][0]
		or 0
	)
	frappe.db.set_value("Vehicle", doc.vehicle, "odometer_km", new_max)
	# Pull cancellation back through to the doc itself for the form view.
	doc.db_set("status", "Cancelled", update_modified=False)


# --------------------------------------------------------- Maintenance Log
def on_maintenance_submit(doc, method=None):
	"""Flip Vehicle.status based on service type, advance odometer if higher.

	A Breakdown moves the vehicle to Maintenance. Any non-Breakdown service
	performed while the vehicle is in Maintenance moves it back to Active.
	"""
	_lock_vehicle(doc.vehicle)

	current_status = frappe.db.get_value("Vehicle", doc.vehicle, "status")
	current_odo = frappe.db.get_value("Vehicle", doc.vehicle, "odometer_km") or 0

	updates: dict = {}
	if doc.service_type == _BREAKDOWN:
		updates["status"] = "Maintenance"
	elif current_status == "Maintenance":
		updates["status"] = "Active"

	if doc.odometer_at_service and doc.odometer_at_service > current_odo:
		updates["odometer_km"] = doc.odometer_at_service

	if updates:
		frappe.db.set_value("Vehicle", doc.vehicle, updates)


def on_maintenance_cancel(doc, method=None):
	"""Reverse the status flip from on_submit.

	If a Breakdown maintenance is cancelled, the vehicle was likely flipped to
	Maintenance. Recompute status from the set of remaining submitted
	maintenance logs: if any other Breakdown is still submitted, keep status
	as Maintenance; otherwise restore to Active. Odometer is monotonic and
	intentionally not rolled back.
	"""
	_lock_vehicle(doc.vehicle)

	current_status = frappe.db.get_value("Vehicle", doc.vehicle, "status")
	if current_status != "Maintenance":
		return  # Nothing to reverse; on_submit didn't put us here.

	remaining_breakdown = frappe.db.exists(
		"Maintenance Log",
		{
			"vehicle": doc.vehicle,
			"docstatus": 1,
			"service_type": _BREAKDOWN,
			"name": ["!=", doc.name],
		},
	)
	if not remaining_breakdown:
		frappe.db.set_value("Vehicle", doc.vehicle, "status", "Active")


# --------------------------------------------------------------- Fuel Entry
def on_fuel_entry_after_insert(doc, method=None):
	"""One-shot odometer roll-forward when a fuel entry is first created.

	Lives in ``after_insert`` instead of ``on_update`` so the propagation
	does not re-fire on every typo correction. Repeated saves of the same
	entry are intentionally idempotent: the row lock + high-water-mark check
	mean a no-op when ``doc.odometer`` is below the current vehicle value.
	"""
	if not doc.odometer or not doc.vehicle:
		return
	_lock_vehicle(doc.vehicle)
	current_odo = frappe.db.get_value("Vehicle", doc.vehicle, "odometer_km") or 0
	if doc.odometer > current_odo:
		frappe.db.set_value("Vehicle", doc.vehicle, "odometer_km", doc.odometer)


# ------------------------------------------------------------------- helpers
def _lock_vehicle(vehicle: str) -> None:
	"""Acquire a row lock on the Vehicle for the rest of this transaction."""
	if not vehicle:
		return
	frappe.db.get_value("Vehicle", vehicle, "name", for_update=True)


def _is_recent(start_datetime) -> bool:
	"""True if a start datetime is within the last 24 hours."""
	if not start_datetime:
		return False
	now = frappe.utils.now_datetime()
	dt = frappe.utils.get_datetime(start_datetime)
	return (now - dt) <= timedelta(hours=24)
