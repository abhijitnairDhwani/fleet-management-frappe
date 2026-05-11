"""Public API endpoints for Fleet Management.

All methods are exposed under:
  /api/method/fleet_management.api.<method_name>
"""

from datetime import timedelta

import frappe
from frappe import _


@frappe.whitelist()
def get_vehicle_summary(vehicle: str) -> dict:
	"""Return aggregate stats for a vehicle.

	Args:
		vehicle: Vehicle name (registration_no).

	Returns:
		Dict with vehicle metadata + counts and totals.
	"""
	if not vehicle:
		frappe.throw(_("vehicle is required"))

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


@frappe.whitelist()
def upcoming_license_expiries(days: int = 30) -> list[dict]:
	"""List drivers whose licenses expire within the given window.

	Args:
		days: Look-ahead window in days (default 30).

	Returns:
		List of drivers sorted by license_expiry ascending.
	"""
	try:
		days = int(days)
	except (TypeError, ValueError):
		frappe.throw(_("days must be an integer"))

	today = frappe.utils.getdate()
	cutoff = today + timedelta(days=days)

	return frappe.get_all(
		"Driver",
		filters={
			"status": "Active",
			"license_expiry": ["<=", cutoff],
		},
		fields=["name", "full_name", "license_no", "license_expiry", "phone"],
		order_by="license_expiry asc",
	)


@frappe.whitelist()
def fleet_dashboard() -> dict:
	"""High-level KPIs for a fleet operations dashboard."""
	totals = {
		"vehicles": frappe.db.count("Vehicle"),
		"vehicles_active": frappe.db.count("Vehicle", {"status": "Active"}),
		"vehicles_in_maintenance": frappe.db.count("Vehicle", {"status": "Maintenance"}),
		"drivers": frappe.db.count("Driver", {"status": "Active"}),
		"trips_open": frappe.db.count(
			"Trip", {"status": ["in", ["Planned", "In-Progress"]], "docstatus": 0}
		),
	}

	month_distance = frappe.db.sql(
		"""SELECT COALESCE(SUM(distance_km), 0)
		   FROM `tabTrip`
		   WHERE docstatus = 1 AND start_datetime >= DATE(strftime('%%Y-%%m-01', 'now'))""",
	)[0][0]

	totals["distance_this_month_km"] = float(month_distance or 0)
	return totals
