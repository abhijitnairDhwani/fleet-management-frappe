"""Public API endpoints for Fleet Management.

All methods are exposed under ``/api/method/fleet_management.api.<method>``.
Each one explicitly checks Frappe permissions — ``@frappe.whitelist()``
alone only requires *some* session, not a Fleet-relevant role.
"""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _

_FLEET_OPS_ROLES = ("System Manager", "Fleet Manager", "Mechanic")


# --------------------------------------------------------------------- guards
def _require_fleet_role() -> None:
	roles = set(frappe.get_roles())
	if not roles & set(_FLEET_OPS_ROLES):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _coerce_str(value, name: str) -> str:
	if not isinstance(value, str) or not value:
		frappe.throw(_("{0} is required and must be a string").format(name))
	return value


# ---------------------------------------------------------- get_vehicle_summary
@frappe.whitelist()
def get_vehicle_summary(vehicle: str) -> dict:
	"""Return aggregate stats for a vehicle.

	Requires read permission on the specified Vehicle. Aggregate sub-queries
	are executed with ``ignore_permissions`` deliberately (we've already
	gated the parent access) so they don't double-filter against the
	caller's row scope.
	"""
	vehicle = _coerce_str(vehicle, "vehicle")
	if not frappe.has_permission("Vehicle", "read", vehicle):
		frappe.throw(_("Not permitted to read Vehicle {0}").format(vehicle), frappe.PermissionError)

	veh = frappe.get_doc("Vehicle", vehicle)

	trip_stats = frappe.db.sql(
		"""SELECT COUNT(*) AS trips, COALESCE(SUM(distance_km), 0) AS total_km
		   FROM `tabTrip`
		   WHERE vehicle = %s AND docstatus = 1""",
		(vehicle,),
		as_dict=True,
	)[0]

	last_service = frappe.db.get_value(
		"Maintenance Log",
		{"vehicle": vehicle, "docstatus": 1},
		["service_date", "service_type"],
		order_by="service_date desc",
		as_dict=True,
	)

	fuel_stats = frappe.db.sql(
		"""SELECT COALESCE(SUM(litres), 0) AS litres, COALESCE(SUM(total_cost), 0) AS cost
		   FROM `tabFuel Entry`
		   WHERE vehicle = %s""",
		(vehicle,),
		as_dict=True,
	)[0]

	return {
		"vehicle": veh.name,
		"make": veh.make,
		"model": veh.model,
		"status": veh.status,
		"odometer_km": veh.odometer_km,
		"current_driver": veh.current_driver,
		"trips": int(trip_stats["trips"]),
		"total_km": float(trip_stats["total_km"]),
		"last_service": last_service,
		"fuel_litres_total": float(fuel_stats["litres"]),
		"fuel_cost_total": float(fuel_stats["cost"]),
	}


# -------------------------------------------------- upcoming_license_expiries
@frappe.whitelist()
def upcoming_license_expiries(days: int = 30) -> list[dict]:
	"""List drivers whose licenses expire within the given window.

	A privileged user (Fleet Manager / System Manager / Mechanic) sees all
	drivers. A user with only Driver Role sees only their own linked record
	(if any) — the public phone numbers of other drivers stay private.
	"""
	days = frappe.utils.cint(days)
	if days < 0:
		frappe.throw(_("days must be a non-negative integer"))

	today = frappe.utils.getdate()
	cutoff = today + timedelta(days=days)

	filters: dict = {
		"status": "Active",
		"license_expiry": ["<=", cutoff],
	}

	# Driver-only users: self-filter so we don't leak other drivers' PII.
	if not (set(frappe.get_roles()) & set(_FLEET_OPS_ROLES)):
		own_driver = frappe.db.get_value("Driver", {"user": frappe.session.user, "status": "Active"}, "name")
		if not own_driver:
			return []
		filters["name"] = own_driver

	return frappe.get_all(
		"Driver",
		filters=filters,
		fields=["name", "full_name", "license_no", "license_expiry", "phone"],
		order_by="license_expiry asc",
	)


# ---------------------------------------------------------- fleet_dashboard
@frappe.whitelist()
def fleet_dashboard() -> dict:
	"""High-level KPIs for a fleet operations dashboard.

	Restricted to Fleet operations roles — this endpoint surfaces counts
	across all vehicles and drivers regardless of row scope.
	"""
	_require_fleet_role()

	totals = {
		"vehicles": frappe.db.count("Vehicle"),
		"vehicles_active": frappe.db.count("Vehicle", {"status": "Active"}),
		"vehicles_in_maintenance": frappe.db.count("Vehicle", {"status": "Maintenance"}),
		"drivers": frappe.db.count("Driver", {"status": "Active"}),
		"trips_open": frappe.db.count(
			"Trip",
			{"status": ["in", ["Planned", "In-Progress"]], "docstatus": 0},
		),
	}

	# Portable across MariaDB / Postgres / SQLite — date computed in Python.
	first_of_month = frappe.utils.get_first_day(frappe.utils.nowdate())
	month_distance = frappe.db.sql(
		"""SELECT COALESCE(SUM(distance_km), 0)
		   FROM `tabTrip`
		   WHERE docstatus = 1 AND start_datetime >= %s""",
		(first_of_month,),
	)[0][0]

	totals["distance_this_month_km"] = float(month_distance or 0)
	return totals
