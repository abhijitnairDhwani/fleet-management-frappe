"""Permission scoping for Driver Role users.

A user with *only* ``Driver Role`` (no Fleet Manager / Mechanic / System
Manager) sees just their own data:

* ``Trip`` rows where ``driver`` is their linked Driver record
* ``Vehicle`` rows where ``current_driver`` is their linked Driver record
* ``Fuel Entry`` rows where ``driver`` is their linked Driver record

Wiring lives in ``hooks.py`` under ``permission_query_conditions`` (for
list-view filtering) and ``has_permission`` (for individual document
access). Privileged roles bypass the scope entirely.
"""

from __future__ import annotations

import frappe

_PRIVILEGED_ROLES = ("System Manager", "Fleet Manager", "Mechanic")


# ------------------------------------------------------------- query scopes
def driver_scope_trip(user: str | None = None) -> str:
	return _doctype_scope("Trip", "driver", user)


def driver_scope_vehicle(user: str | None = None) -> str:
	return _doctype_scope("Vehicle", "current_driver", user)


def driver_scope_fuel_entry(user: str | None = None) -> str:
	return _doctype_scope("Fuel Entry", "driver", user)


# ------------------------------------------------------- individual-doc check
def driver_can_read_trip(doc, user: str | None = None) -> bool:
	return _doc_check(doc, "driver", user)


def driver_can_read_vehicle(doc, user: str | None = None) -> bool:
	return _doc_check(doc, "current_driver", user)


def driver_can_read_fuel_entry(doc, user: str | None = None) -> bool:
	return _doc_check(doc, "driver", user)


# -------------------------------------------------------------------- helpers
def _doctype_scope(doctype: str, driver_field: str, user: str | None) -> str:
	"""Return a SQL WHERE clause (table-qualified) for list-view filtering."""
	driver = _driver_for_session(user)
	if driver is _UNRESTRICTED:
		return ""
	if not driver:
		# Driver-only user with no linked Driver record — see nothing.
		return f"`tab{doctype}`.name = 'no-such-record'"
	return f"`tab{doctype}`.`{driver_field}` = {frappe.db.escape(driver)}"


def _doc_check(doc, driver_field: str, user: str | None) -> bool:
	"""Allow / deny on an individual document load."""
	driver = _driver_for_session(user)
	if driver is _UNRESTRICTED:
		return True
	if not driver:
		return False
	return getattr(doc, driver_field, None) == driver


# `_UNRESTRICTED` is a sentinel distinct from any string/None; identity-comparable.
_UNRESTRICTED = object()


def _driver_for_session(user: str | None) -> object:
	"""Resolve the active user's linked Driver, or ``_UNRESTRICTED`` for privileged roles."""
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return _UNRESTRICTED
	roles = set(frappe.get_roles(user))
	if roles & set(_PRIVILEGED_ROLES):
		return _UNRESTRICTED
	if "Driver Role" not in roles:
		return _UNRESTRICTED
	return frappe.db.get_value("Driver", {"user": user, "status": "Active"}, "name")
