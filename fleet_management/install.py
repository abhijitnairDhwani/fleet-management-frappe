"""Post-install: create the three Fleet roles and seed standard Vehicle Types.

Roles are created here rather than as fixtures because they are required by
the DocType permission tables that ``bench migrate`` builds *before* fixture
sync would run. ``after_install`` is the authoritative source — no
``fixtures`` declaration in ``hooks.py``.
"""

from __future__ import annotations

import frappe

ROLES = [
	("Fleet Manager", "Full access to fleet operations"),
	("Mechanic", "Maintenance access only"),
	("Driver Role", "Read access scoped to the linked Driver's own records"),
]

SEED_VEHICLE_TYPES = [
	("Sedan", "Standard passenger sedan"),
	("SUV", "Sport Utility Vehicle"),
	("Truck", "Light or heavy goods truck"),
	("Van", "Cargo or passenger van"),
	("Motorbike", "Two-wheeler"),
]


def after_install() -> None:
	_create_roles()
	_seed_vehicle_types()
	frappe.db.commit()


def _create_roles() -> None:
	# Frappe's Role DocType doesn't carry a "description" column in v16 — the
	# tuple stores the human-readable intent only for code readers here.
	for role_name, _desc in ROLES:
		desk_access = frappe.db.get_value("Role", role_name, "desk_access")
		if desk_access is None:
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": 1,
				}
			).insert(ignore_permissions=True)
		elif not desk_access:
			frappe.db.set_value("Role", role_name, "desk_access", 1)


def _seed_vehicle_types() -> None:
	for type_name, desc in SEED_VEHICLE_TYPES:
		if frappe.db.exists("Vehicle Type", type_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Vehicle Type",
				"type_name": type_name,
				"description": desc,
			}
		).insert(ignore_permissions=True)
