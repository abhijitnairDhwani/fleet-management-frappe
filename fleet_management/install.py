"""Post-install hook: create Fleet roles and seed vehicle types."""

import frappe


ROLES = [
	("Fleet Manager", "Full access to fleet operations"),
	("Mechanic", "Maintenance access only"),
	("Driver Role", "Read access for assigned drivers"),
]


SEED_VEHICLE_TYPES = [
	("Sedan", "Standard passenger sedan"),
	("SUV", "Sport Utility Vehicle"),
	("Truck", "Light or heavy goods truck"),
	("Van", "Cargo or passenger van"),
	("Motorbike", "Two-wheeler"),
]


def after_install():
	_create_roles()
	_seed_vehicle_types()
	frappe.db.commit()


def _create_roles():
	for role_name, desc in ROLES:
		if frappe.db.exists("Role", role_name):
			continue
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role_name,
			"desk_access": 1,
			"description": desc,
		}).insert(ignore_permissions=True)


def _seed_vehicle_types():
	for type_name, desc in SEED_VEHICLE_TYPES:
		if frappe.db.exists("Vehicle Type", type_name):
			continue
		frappe.get_doc({
			"doctype": "Vehicle Type",
			"type_name": type_name,
			"description": desc,
		}).insert(ignore_permissions=True)
