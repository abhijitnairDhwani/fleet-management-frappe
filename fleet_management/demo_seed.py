"""Demo seed data for screenshots / smoke tests.

Generates 8 vehicles, 5 drivers, ~70 trips, ~25 maintenance logs, ~50 fuel
entries spread over the last 180 days so dashboard charts have shape.

Run via: bench --site fleet.localhost execute fleet_management.demo_seed.seed
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import frappe

_RANDOM = random.Random(42)  # deterministic seed for repeatable demos


DRIVERS = [
	{
		"full_name": "Ramesh Kumar",
		"license_no": "DL-AP-2024-001",
		"license_expiry": date.today() + timedelta(days=14),
		"phone": "+91 98765 11111",
	},
	{
		"full_name": "Sunita Sharma",
		"license_no": "DL-KA-2023-042",
		"license_expiry": date.today() + timedelta(days=120),
		"phone": "+91 98765 22222",
	},
	{
		"full_name": "Mohammed Akhtar",
		"license_no": "DL-DL-2022-987",
		"license_expiry": date.today() + timedelta(days=400),
		"phone": "+91 98765 33333",
	},
	{
		"full_name": "Priya Iyer",
		"license_no": "DL-TN-2024-559",
		"license_expiry": date.today() + timedelta(days=240),
		"phone": "+91 98765 44444",
	},
	{
		"full_name": "Karan Singh",
		"license_no": "DL-HR-2025-117",
		"license_expiry": date.today() + timedelta(days=21),
		"phone": "+91 98765 55555",
	},
]


VEHICLES = [
	{
		"registration_no": "KA-01-AB-1234",
		"make": "Tata",
		"model": "Nexon",
		"year": 2022,
		"vehicle_type": "SUV",
		"odometer_km": 18450,
	},
	{
		"registration_no": "KA-05-MN-9876",
		"make": "Maruti",
		"model": "Dzire",
		"year": 2021,
		"vehicle_type": "Sedan",
		"odometer_km": 32100,
	},
	{
		"registration_no": "DL-08-CA-5544",
		"make": "Ashok Leyland",
		"model": "Dost",
		"year": 2020,
		"vehicle_type": "Truck",
		"odometer_km": 71200,
	},
	{
		"registration_no": "MH-12-DE-7788",
		"make": "Force",
		"model": "Traveller",
		"year": 2023,
		"vehicle_type": "Van",
		"odometer_km": 8900,
	},
	{
		"registration_no": "AP-09-BG-2211",
		"make": "Hero",
		"model": "Splendor",
		"year": 2024,
		"vehicle_type": "Motorbike",
		"odometer_km": 3200,
	},
	{
		"registration_no": "TN-22-XY-4501",
		"make": "Mahindra",
		"model": "Bolero",
		"year": 2022,
		"vehicle_type": "SUV",
		"odometer_km": 45200,
	},
	{
		"registration_no": "MH-04-PQ-6677",
		"make": "Tata",
		"model": "Ace",
		"year": 2021,
		"vehicle_type": "Truck",
		"odometer_km": 58400,
	},
	{
		"registration_no": "KA-09-RS-3344",
		"make": "Hyundai",
		"model": "Aura",
		"year": 2023,
		"vehicle_type": "Sedan",
		"odometer_km": 12100,
	},
]


TRIP_PURPOSES = [
	"Client visit",
	"Site survey",
	"Cargo delivery",
	"Airport drop",
	"Airport pickup",
	"Field inspection",
	"Document courier",
	"Stakeholder meeting",
	"Vendor visit",
	"Equipment transfer",
	"Team transport",
	"Inter-office shuttle",
	"Sample pickup",
	"Service call",
]

MAINTENANCE_TYPES = ["Routine", "Oil Change", "Tyre Change", "Repair", "Breakdown"]

VENDORS = [
	"Tata Motors Service",
	"Maruti Authorized Service",
	"Apollo Tyres Authorized",
	"QuickFix Motors",
	"Bosch Car Service",
	"Local Garage — MG Road",
	"Ashok Leyland Care",
	"HP Lubricants",
]

FUEL_STATIONS = [
	"HP — Whitefield",
	"Indian Oil — Hosur Road",
	"BPCL Highway",
	"Reliance Petroleum — Outer Ring",
	"Shell — Electronic City",
]


def seed():
	# Reset the random state at the entry point so re-running ``seed()`` after a
	# partial failure produces the same dataset rather than continuing from
	# wherever the previous run left off.
	_RANDOM.seed(42)

	# Top-level idempotency guard: if the dataset is already in place, do
	# nothing. Per-function guards below remain as a safety net.
	if (
		frappe.db.count("Driver") >= len(DRIVERS)
		and frappe.db.count("Vehicle") >= len(VEHICLES)
		and frappe.db.count("Trip", {"docstatus": 1}) >= 50
		and frappe.db.count("Fuel Entry") >= 30
		and frappe.db.count("Maintenance Log", {"docstatus": 1}) >= 15
	):
		print("Seed already present — nothing to do.")
		return

	_seed_drivers()
	_seed_vehicles()
	_assign_current_drivers()
	_seed_trips()
	_seed_maintenance()
	_seed_fuel()
	frappe.db.commit()
	print("Seed complete.")


def _seed_drivers():
	for d in DRIVERS:
		if frappe.db.exists("Driver", {"license_no": d["license_no"]}):
			continue
		frappe.get_doc({"doctype": "Driver", **d}).insert(ignore_permissions=True)


def _seed_vehicles():
	for v in VEHICLES:
		if frappe.db.exists("Vehicle", v["registration_no"]):
			continue
		frappe.get_doc({"doctype": "Vehicle", **v}).insert(ignore_permissions=True)


def _driver_names() -> list[str]:
	return frappe.get_all("Driver", pluck="name", order_by="creation asc")


def _vehicle_names() -> list[str]:
	return frappe.get_all("Vehicle", pluck="name", order_by="creation asc")


def _assign_current_drivers():
	d_names = _driver_names()
	v_names = _vehicle_names()
	for i, v in enumerate(v_names):
		if i >= len(d_names):
			continue
		# Don't stomp an existing assignment on re-run.
		if frappe.db.get_value("Vehicle", v, "current_driver"):
			continue
		frappe.db.set_value("Vehicle", v, "current_driver", d_names[i % len(d_names)])


def _seed_trips():
	"""~70 submitted trips spread across the last 180 days + a few open ones."""
	d_names = _driver_names()
	v_names = _vehicle_names()
	if not d_names or not v_names:
		return

	# Skip if we've already seeded a substantive history.
	if frappe.db.count("Trip", {"docstatus": 1}) >= 50:
		return

	now = datetime.now().replace(microsecond=0)

	for _ in range(70):
		v_idx = _RANDOM.randrange(len(v_names))
		d_idx = _RANDOM.randrange(len(d_names))
		days_ago = _RANDOM.randint(1, 180)
		duration_hr = _RANDOM.choice([1, 2, 3, 4, 6, 8, 10])
		# Distance correlates loosely with duration.
		distance = max(8, int(duration_hr * _RANDOM.uniform(25, 65)))

		_add_submitted_trip(
			v_names[v_idx],
			d_names[d_idx],
			days_ago=days_ago,
			duration_hr=duration_hr,
			distance=distance,
			purpose=_RANDOM.choice(TRIP_PURPOSES),
		)

	# A couple of trips planned for the next few days (open / draft).
	for offset in (1, 3, 5):
		v = v_names[_RANDOM.randrange(len(v_names))]
		frappe.get_doc(
			{
				"doctype": "Trip",
				"vehicle": v,
				"driver": d_names[_RANDOM.randrange(len(d_names))],
				"start_datetime": (now + timedelta(days=offset, hours=9)).isoformat(),
				"start_odo": frappe.db.get_value("Vehicle", v, "odometer_km") or 0,
				"purpose": _RANDOM.choice(TRIP_PURPOSES),
				"status": "Planned",
			}
		).insert(ignore_permissions=True)


def _add_submitted_trip(
	vehicle: str, driver: str, *, days_ago: int, duration_hr: int, distance: int, purpose: str
):
	veh = frappe.get_doc("Vehicle", vehicle)
	# Each new trip continues from the vehicle's current odometer (high-water-mark).
	start = (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0)
	end = start + timedelta(hours=duration_hr)
	start_odo = veh.odometer_km or 0
	end_odo = start_odo + distance
	doc = frappe.get_doc(
		{
			"doctype": "Trip",
			"vehicle": vehicle,
			"driver": driver,
			"start_datetime": start.isoformat(),
			"end_datetime": end.isoformat(),
			"start_odo": start_odo,
			"end_odo": end_odo,
			"purpose": purpose,
			"status": "Completed",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def _seed_maintenance():
	v_names = _vehicle_names()
	if not v_names:
		return
	if frappe.db.count("Maintenance Log", {"docstatus": 1}) >= 15:
		return

	for _ in range(22):
		v = v_names[_RANDOM.randrange(len(v_names))]
		days_ago = _RANDOM.randint(2, 180)
		stype = _RANDOM.choices(
			MAINTENANCE_TYPES,
			weights=[40, 25, 12, 18, 5],
			k=1,
		)[0]
		cost = {
			"Routine": _RANDOM.randint(1500, 5000),
			"Oil Change": _RANDOM.randint(1800, 3200),
			"Tyre Change": _RANDOM.randint(8000, 22000),
			"Repair": _RANDOM.randint(2500, 18000),
			"Breakdown": _RANDOM.randint(4500, 30000),
		}[stype]
		odo = frappe.db.get_value("Vehicle", v, "odometer_km") or 0
		doc = frappe.get_doc(
			{
				"doctype": "Maintenance Log",
				"vehicle": v,
				"service_date": (date.today() - timedelta(days=days_ago)).isoformat(),
				"service_type": stype,
				"odometer_at_service": max(0, odo - _RANDOM.randint(50, 800)),
				"cost": cost,
				"vendor": _RANDOM.choice(VENDORS),
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()


def _seed_fuel():
	v_names = _vehicle_names()
	d_names = _driver_names()
	if not v_names or not d_names:
		return
	if frappe.db.count("Fuel Entry") >= 30:
		return

	for _ in range(50):
		v = v_names[_RANDOM.randrange(len(v_names))]
		d = d_names[_RANDOM.randrange(len(d_names))]
		days_ago = _RANDOM.randint(1, 180)
		litres = _RANDOM.choice([15, 20, 25, 30, 35, 40, 45, 50, 55, 60])
		cpl = round(_RANDOM.uniform(90.0, 108.0), 2)
		odo = frappe.db.get_value("Vehicle", v, "odometer_km") or 0
		frappe.get_doc(
			{
				"doctype": "Fuel Entry",
				"vehicle": v,
				"driver": d,
				"date": (date.today() - timedelta(days=days_ago)).isoformat(),
				"litres": litres,
				"cost_per_litre": cpl,
				"odometer": max(0, odo - _RANDOM.randint(50, 1500)),
				"notes": _RANDOM.choice(FUEL_STATIONS),
			}
		).insert(ignore_permissions=True)


def reset_demo(confirm: str | None = None):
	"""Wipe ALL Fleet Management data from this site. Nuclear — read carefully.

	Guard rails:
	* Runs only when the site has ``developer_mode = 1``. Production sites
	  refuse the call.
	* Caller must pass ``confirm="WIPE-FLEET"`` so accidental invocations
	  (typos, scheduled jobs, copy-paste) are rejected.

	This deletes *every* Vehicle / Driver / Trip / Maintenance Log / Fuel
	Entry — not just rows created by :func:`seed`. If you need a "demo
	subset only" wipe, tag your seed rows with a custom field first.
	"""
	if not frappe.conf.developer_mode:
		frappe.throw("reset_demo refuses to run unless the site has developer_mode = 1.")
	if confirm != "WIPE-FLEET":
		frappe.throw('reset_demo requires confirm="WIPE-FLEET" (case-sensitive) to proceed.')

	for dt in ("Fuel Entry", "Trip", "Maintenance Log"):
		for name in frappe.get_all(dt, pluck="name"):
			doc = frappe.get_doc(dt, name)
			if getattr(doc, "docstatus", 0) == 1:
				try:
					doc.cancel()
				except Exception:
					pass
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	for dt in ("Vehicle", "Driver"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
	frappe.db.commit()
	print("Demo data wiped.")
