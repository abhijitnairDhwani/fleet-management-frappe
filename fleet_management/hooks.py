"""Fleet Management — app hooks.

Keep this file as configuration only; cross-cutting logic belongs in
``services/`` modules referenced from here.
"""

app_name = "fleet_management"
app_title = "Fleet Management"
app_publisher = "Abhijit Nair"
app_description = "Mini fleet management system: vehicles, drivers, trips, maintenance, fuel"
app_email = "abhijit.nair@dhwaniris.com"
app_license = "mit"

# ----------------------------------------------------------------------------
# Install / fixtures
# ----------------------------------------------------------------------------

after_install = "fleet_management.install.after_install"

# ----------------------------------------------------------------------------
# Document events — cross-doctype writes routed to the vehicle_state service
# ----------------------------------------------------------------------------

doc_events = {
	"Trip": {
		"on_submit": "fleet_management.services.vehicle_state.on_trip_submit",
		"on_cancel": "fleet_management.services.vehicle_state.on_trip_cancel",
	},
	"Maintenance Log": {
		"on_submit": "fleet_management.services.vehicle_state.on_maintenance_submit",
		"on_cancel": "fleet_management.services.vehicle_state.on_maintenance_cancel",
	},
	"Fuel Entry": {
		"after_insert": "fleet_management.services.vehicle_state.on_fuel_entry_after_insert",
	},
}

# ----------------------------------------------------------------------------
# Permission scoping — Driver Role sees only their own linked records
# ----------------------------------------------------------------------------

permission_query_conditions = {
	"Trip": "fleet_management.permissions.driver_scope_trip",
	"Vehicle": "fleet_management.permissions.driver_scope_vehicle",
	"Fuel Entry": "fleet_management.permissions.driver_scope_fuel_entry",
}

has_permission = {
	"Trip": "fleet_management.permissions.driver_can_read_trip",
	"Vehicle": "fleet_management.permissions.driver_can_read_vehicle",
	"Fuel Entry": "fleet_management.permissions.driver_can_read_fuel_entry",
}

# ----------------------------------------------------------------------------
# Scheduler
# ----------------------------------------------------------------------------

scheduler_events = {
	"daily": [
		"fleet_management.scheduled.check_license_expiries",
	],
}
