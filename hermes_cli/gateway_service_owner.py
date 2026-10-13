"""Compatibility facade for gateway service-definition ownership."""

from gateway.service_owner import (
    definition_belongs_to_home,
    pinned_home,
    systemd_service_home_for_unit as service_home_for_unit,
    systemd_unit_belongs_to_caller as unit_belongs_to_caller,
)
from gateway.service_definition import (
    refuse_temp_home_write as refuse_temp_home_service_write,
    temp_home_in_definition as temp_home_in_service_definition,
)

__all__ = [
    "definition_belongs_to_home",
    "pinned_home",
    "service_home_for_unit",
    "unit_belongs_to_caller",
    "refuse_temp_home_service_write",
    "temp_home_in_service_definition",
]
