"""Demo seed data for screenshots / smoke tests.

Run via: bench --site fleet.localhost execute fleet_management.demo_seed.seed
"""

from datetime import date, datetime, timedelta

import frappe


DRIVERS = [
	{"full_name": "Ramesh Kumar", "license_no": "DL-AP-2024-001", "license_expiry": date.today() + timedelta(days=14), "phone": "+91 98765 11111"},
	{"full_name": "Sunita Sharma", "license_no": "DL-KA-2023-042", "license_expiry": date.today() + timedelta(days=120), "phone": "+91 98765 22222"},
	{"full_name": "Mohammed Akhtar", "license_no": "DL-DL-2022-987", "license_expiry": date.today() + timedelta(days=400), "phone": "+91 98765 33333"},
]


VEHICLES = [
	{"registration_no": "KA-01-AB-1234", "make": "Tata", "model": "Nexon", "year": 2022, "vehicle_type": "SUV", "odometer_km": 18450},
	{"registration_no": "KA-05-MN-9876", "make": "Maruti", "model": "Dzire", "year": 2021, "vehicle_type": "Sedan", "odometer_km": 32100},
	{"registration_no": "DL-08-CA-5544", "make": "Ashok Leyland", "model": "Dost", "year": 2020, "vehicle_type": "Truck", "odometer_km": 71200},
	{"registration_no": "MH-12-DE-7788", "make": "Force", "model": "Traveller", "year": 2023, "vehicle_type": "Van", "odometer_km": 8900},
	{"registration_no": "AP-09-BG-2211", "make": "Hero", "model": "Splendor", "year": 2024, "vehicle_type": "Motorbike", "odometer_km": 3200},
]


def seed():
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


def _driver_names():
	return frappe.get_all("Driver", pluck="name", order_by="creation asc")


def _vehicle_names():
	return frappe.get_all("Vehicle", pluck="name", order_by="creation asc")


def _assign_current_drivers():
	d_names = _driver_names()
	v_names = _vehicle_names()
	for i, v in enumerate(v_names):
		if i < len(d_names):
			frappe.db.set_value("Vehicle", v, "current_driver", d_names[i % len(d_names)])


def _seed_trips():
	d_names = _driver_names()
	v_names = _vehicle_names()
	if not d_names or not v_names:
		return

	now = datetime.now().replace(microsecond=0)

	def add_submitted_trip(vehicle_idx, driver_idx, days_ago, duration_hr, distance, purpose):
		v = v_names[vehicle_idx]
		veh = frappe.get_doc("Vehicle", v)
		start = now - timedelta(days=days_ago)
		end = start + timedelta(hours=duration_hr)
		start_odo = veh.odometer_km or 0
		end_odo = start_odo + distance
		doc = frappe.get_doc({
			"doctype": "Trip",
			"vehicle": v,
			"driver": d_names[driver_idx % len(d_names)],
			"start_datetime": start.isoformat(),
			"end_datetime": end.isoformat(),
			"start_odo": start_odo,
			"end_odo": end_odo,
			"purpose": purpose,
			"status": "Completed",
		})
		doc.insert(ignore_permissions=True)
		doc.submit()

	add_submitted_trip(0, 0, 3, 2, 45, "Client visit — Whitefield")
	add_submitted_trip(0, 1, 1, 4, 120, "Site survey — Tumkur")
	add_submitted_trip(1, 2, 2, 6, 220, "Airport drop")
	add_submitted_trip(2, 1, 5, 8, 380, "Cargo delivery — Hyderabad")

	# one open / planned trip
	v = v_names[3]
	frappe.get_doc({
		"doctype": "Trip",
		"vehicle": v,
		"driver": d_names[0],
		"start_datetime": (now + timedelta(days=1, hours=9)).isoformat(),
		"start_odo": frappe.db.get_value("Vehicle", v, "odometer_km") or 0,
		"purpose": "Team transport — corporate offsite",
		"status": "Planned",
	}).insert(ignore_permissions=True)


def _seed_maintenance():
	v_names = _vehicle_names()
	if not v_names:
		return
	logs = [
		{"vehicle": v_names[1], "service_date": date.today() - timedelta(days=10), "service_type": "Oil Change", "odometer_at_service": 32050, "cost": 2400, "vendor": "QuickFix Motors"},
		{"vehicle": v_names[2], "service_date": date.today() - timedelta(days=20), "service_type": "Tyre Change", "odometer_at_service": 70950, "cost": 18500, "vendor": "Apollo Tyres Authorized"},
		{"vehicle": v_names[0], "service_date": date.today() - timedelta(days=2), "service_type": "Routine", "odometer_at_service": 18300, "cost": 4200, "vendor": "Tata Motors Service"},
	]
	for log in logs:
		doc = frappe.get_doc({"doctype": "Maintenance Log", **log})
		doc.insert(ignore_permissions=True)
		doc.submit()


def _seed_fuel():
	v_names = _vehicle_names()
	d_names = _driver_names()
	if not v_names or not d_names:
		return
	entries = [
		{"vehicle": v_names[0], "driver": d_names[0], "date": date.today() - timedelta(days=3), "litres": 35, "cost_per_litre": 102.50, "odometer": 18450, "notes": "HP, Whitefield"},
		{"vehicle": v_names[1], "driver": d_names[1], "date": date.today() - timedelta(days=1), "litres": 28, "cost_per_litre": 101.80, "odometer": 32100, "notes": "Indian Oil"},
		{"vehicle": v_names[2], "driver": d_names[2], "date": date.today() - timedelta(days=5), "litres": 60, "cost_per_litre": 92.40, "odometer": 71200, "notes": "BPCL Highway"},
	]
	for e in entries:
		frappe.get_doc({"doctype": "Fuel Entry", **e}).insert(ignore_permissions=True)
