import json
import logging
from abc import ABCMeta
from typing import Any, List

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SWING_OFF,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SWING_BOTH,
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_DIFFUSE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    CONF_API_KEY,
    CONF_DEVICE_ID,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from custom_components.smartthings_ac_windfree.api import SmartthingsApi

_LOGGER = logging.getLogger(__name__)

SWING_MODES_HASS_TO_SAMSUNG = {
    SWING_OFF: "fixed",
    SWING_VERTICAL: "vertical",
    SWING_HORIZONTAL: "horizontal",
    SWING_BOTH: "all",
}

SWING_MODES_SAMSUNG_TO_HASS = {
    "fixed": SWING_OFF,
    "vertical": SWING_VERTICAL,
    "horizontal": SWING_HORIZONTAL,
    "all": SWING_BOTH,
}

HVAC_MODES_HASS_TO_SAMSUNG = {
    HVAC_MODE_OFF: "off",
    HVAC_MODE_HEAT: "heat",
    HVAC_MODE_COOL: "cool",
    HVAC_MODE_AUTO: "auto",
    HVAC_MODE_HEAT_COOL: "aIComfort",
    HVAC_MODE_DRY: "dry",
}

HVAC_MODES_SAMSUNG_TO_HASS = {
    "off": HVAC_MODE_OFF,
    "heat": HVAC_MODE_HEAT,
    "cool": HVAC_MODE_COOL,
    "aIComfort": HVAC_MODE_HEAT_COOL,
    "auto": HVAC_MODE_AUTO,
    "dry": HVAC_MODE_DRY,
    "wind": HVAC_MODE_FAN_ONLY,
}

FAN_MODES_HASS_TO_SAMSUNG = {
    FAN_AUTO: "auto",
    FAN_LOW: "low",
    FAN_MEDIUM: "medium",
    FAN_HIGH: "high",
    "turbo": "turbo",
    FAN_DIFFUSE: "windFree",
}

FAN_MODES_SAMSUNG_TO_HASS = {
    "auto": FAN_AUTO,
    "low": FAN_LOW,
    "medium": FAN_MEDIUM,
    "high": FAN_HIGH,
    "turbo": "turbo",
    "windFree": FAN_DIFFUSE,
}

SAMSUNGAC_HVAC_MODE = "airConditionerMode"
SAMSUNGAC_FAN_MODE = "fanMode"
SAMSUNGAC_SWING_MODE = "fanOscillationMode"
SAMSUNGAC_TARGET_TEMP = "coolingSetpoint"
SAMSUNGAC_CURRENT_TEMP = "temperature"
SAMSUNGAC_HUMIDITY = "humidity"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the climate devices config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None
) -> None:
    """Set up platform."""
    api_key = config.get(CONF_API_KEY)
    device_id = config.get(CONF_DEVICE_ID)
    websession = async_get_clientsession(hass)
    # Fetch latest states
    states = await SmartthingsApi.async_update_states(websession, api_key, device_id)
    name = await SmartthingsApi.async_get_name(websession, api_key, device_id)

    async_add_entities([SamsungAc(
        api_key=api_key,
        device_id=device_id,
        name=name,
        states=states,
        websession=websession
    )])
    # TODO: implement sensor for power consumption


def process_json_states(data):
    states = {}
    for key, obj in data['main'].items():
        try:
            states[key] = json.loads(obj['value'])
        except ValueError:
            states[key] = obj['value']
        except TypeError:
            states[key] = obj['value']
    return states


class SamsungAc(ClimateEntity, metaclass=ABCMeta):
    """Representation of a climate entity."""

    # [x] "humidity",
    # [x] "airConditionerMode",
    # [ ] "doNotDisturb",
    # [x] "fanOscillationMode",
    # [x] "fanMode",
    # [ ] "volume",
    # [x] "coolingSetpoint",
    # [x] "switch",
    # [x] "temperature",
    # [ ] "powerConsumption",
    # [ ] "disabledCapabilities",
    # [?] "acOptionalMode",  # "[\"auto\",\"low\",\"medium\",\"high\",\"turbo\"]"
    # [x] "supportedAcModes",  # "[\"aIComfort\",\"cool\",\"dry\",\"wind\",\"auto\",\"heat\"]"
    # [x] "supportedAcFanModes",  # "[\"auto\",\"low\",\"medium\",\"high\",\"turbo\"]"
    # [x] "supportedFanOscillationModes", - currently returns null, but works ["fixed", "vertical", "horizontal", "all"]
    # [?] "supportedAcOptionalMode",  # "[\"off\",\"sleep\",\"quiet\",\"smart\",\"speed\",\"windFree\",
    #                                       \"windFreeSleep\"]"\

    _attr_supported_features = SUPPORT_FAN_MODE | SUPPORT_SWING_MODE | SUPPORT_TARGET_TEMPERATURE
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, api_key, device_id, name, states, websession) -> None:
        """Initialize the climate."""
        self.api_key = api_key
        self.device_id = device_id
        self.websession = websession
        self.states = process_json_states(states)

        self._attr_name = "samsungwindfree_" + name
        self._attr_min_temp = self.states["minimumSetpoint"]
        self._attr_max_temp = self.states["maximumSetpoint"]

    @property
    def state(self) -> str:
        """Return the current state."""
        if self.states["switch"] == "on":
            return STATE_ON
        return STATE_OFF

    @property
    def swing_mode(self) -> str:
        """Return swing mode ie. fixed, vertical."""
        return SWING_MODES_SAMSUNG_TO_HASS[self.states[SAMSUNGAC_SWING_MODE]]

    @property
    def swing_modes(self) -> List[str]:
        """Return the list of available swing modes.

        Requires SUPPORT_SWING_MODE.
        """
        return list(SWING_MODES_HASS_TO_SAMSUNG.keys())

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        if self.state == STATE_OFF:
            return "off"
        if self.states[SAMSUNGAC_HVAC_MODE] in HVAC_MODES_SAMSUNG_TO_HASS:
            return HVAC_MODES_SAMSUNG_TO_HASS[self.states[SAMSUNGAC_HVAC_MODE]]
        return HVAC_MODE_AUTO

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return list(HVAC_MODES_HASS_TO_SAMSUNG.keys())

    @property
    def hvac_action(self) -> str:
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        return self.hvac_mode

    @property
    def icon(self) -> str:
        # TODO: icons for each HVAC mode
        if self.hvac_mode == HVAC_MODE_HEAT:
            return "mdi:radiator"
        return "mdi:radiator-off"

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.states[SAMSUNGAC_CURRENT_TEMP])

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return float(self.states[SAMSUNGAC_TARGET_TEMP])

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if self.states["fanMode"] in FAN_MODES_SAMSUNG_TO_HASS:
            return FAN_MODES_SAMSUNG_TO_HASS[self.states[SAMSUNGAC_FAN_MODE]]
        return FAN_AUTO

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return list(FAN_MODES_HASS_TO_SAMSUNG.keys())

    @property
    def current_humidity(self) -> int:
        """Return the current humidity."""
        return int(self.states[SAMSUNGAC_HUMIDITY])

    async def async_update(self) -> None:
        """Get the latest data."""
        states = await SmartthingsApi.async_update_states(self.websession, self.api_key, self.device_id)
        self.states = process_json_states(states)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        samsung_hvac_mode = HVAC_MODES_HASS_TO_SAMSUNG[hvac_mode]
        if hvac_mode == "off":
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_SWITCH_OFF
            )
            self.schedule_update_ha_state(True)
            return
        if self.state == STATE_OFF:
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_SWITCH_ON
            )
        await SmartthingsApi.async_send_command(
            session=self.websession,
            api_key=self.api_key,
            device_id=self.device_id,
            command=SmartthingsApi.COMMAND_AC_MODE,
            arguments=[samsung_hvac_mode]
        )
        self.schedule_update_ha_state(True)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await SmartthingsApi.async_send_command(
            session=self.websession,
            api_key=self.api_key,
            device_id=self.device_id,
            command=SmartthingsApi.COMMAND_TARGET_TEMPERATURE,
            arguments=[temperature]
        )
        self.schedule_update_ha_state(True)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        samsung_swing_mode = SWING_MODES_HASS_TO_SAMSUNG[swing_mode]
        await SmartthingsApi.async_send_command(
            session=self.websession,
            api_key=self.api_key,
            device_id=self.device_id,
            command=SmartthingsApi.COMMAND_FAN_OSCILLATION_MODE,
            arguments=[samsung_swing_mode]
        )
        self.schedule_update_ha_state(True)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        samsung_fan_mode = FAN_MODES_HASS_TO_SAMSUNG[fan_mode]
        if samsung_fan_mode == "windFree":
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_OPTIONAL_MODE,
                arguments=[samsung_fan_mode]
            )
        else:
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_FAN_MODE,
                arguments=[samsung_fan_mode]
            )
        self.schedule_update_ha_state(True)
