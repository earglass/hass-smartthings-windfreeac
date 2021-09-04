import json
import logging
from typing import Any, List

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SWING_OFF,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SWING_BOTH,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_HALVES,
    TEMP_CELSIUS,
    CONF_API_KEY,
    CONF_DEVICE_ID,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType, ConfigType

from custom_components.smartthings_ac_windfree.api import SmartthingsApi

_LOGGER = logging.getLogger(__name__)

SWING_MODES = {
    SWING_OFF: "fixed",
    SWING_VERTICAL: "vertical",
    SWING_HORIZONTAL: "horizontal",
    SWING_BOTH: "all",
}

SUPPORTED_AC_OPTIONAL_MODES = [
    "off",
    "sleep",
    "quiet",
    "smart",
    "speed",
    "windFree",
    "windFreeSleep",
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the climate devices config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up platform."""
    api_key = config.get(CONF_API_KEY)
    device_id = config.get(CONF_DEVICE_ID)
    # Fetch latest states
    states = await hass.async_add_executor_job(SmartthingsApi.update_states, api_key, device_id)

    async_add_entities([SamsungAc(api_key, device_id, states)])
    # TODO: implement sensor for power consumption


class SamsungAc(ClimateEntity):
    """Representation of a heater."""

    _attr_supported_features = SUPPORT_FAN_MODE | SUPPORT_SWING_MODE
    _attr_target_temperature_step = PRECISION_HALVES
    _attr_temperature_unit = TEMP_CELSIUS

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
    # [ ] "acOptionalMode",  # "[\"auto\",\"low\",\"medium\",\"high\",\"turbo\"]"
    # [x] "supportedAcModes",  # "[\"aIComfort\",\"cool\",\"dry\",\"wind\",\"auto\",\"heat\"]"
    # [x] "supportedAcFanModes",  # "[\"auto\",\"low\",\"medium\",\"high\",\"turbo\"]"
    # [ ] "supportedFanOscillationModes", - currently returns null, but works ["fixed", "vertical", "horizontal", "all"]
    # [ ] "supportedAcOptionalMode",  # "[\"off\",\"sleep\",\"quiet\",\"smart\",\"speed\",\"windFree\",
    #                                       \"windFreeSleep\"]"

    def __init__(self, api_key, device_id, states) -> None:
        """Initialize the climate."""
        # TODO: implement -> SmartthingsApi.get_name()
        self._name = "Samsung AC"
        self._api_key = api_key
        self._device_id = device_id
        self._state = STATE_OFF
        self._states = {}
        for key, obj in states['main'].items():
            if self._states[key] is str:
                self._states[key] = json.loads(obj['value'])
        _LOGGER.warning(self._states)

    # @property
    # def name(self) -> str:
    #     """Return the name of the device, if any."""
    #     return self._name

    @property
    def state(self) -> str:
        """Return the current state."""
        return self._states["switch"]

    @property
    def swing_mode(self) -> str:
        """Return swing mode ie. fixed, vertical."""
        return SWING_MODES[self._states["fanOscillationMode"]]

    @property
    def swing_modes(self) -> List[str]:
        """Return the list of available swing modes.

        Need to be a subset of HVAC_MODES.
        """
        # TODO: remove workaround once windfree & optional modes become separate property
        SWING_MODES["windFree"] = "windFree"
        return list(SWING_MODES.keys())

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        return self._states["airConditionerMode"]

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        # TODO: test if extra modes are passing
        # self._states["supportedAcModes"].remove("aIComfort")
        # self._states["supportedAcModes"].remove("wind")
        return self._states["supportedAcModes"]

    # @property
    # def icon(self) -> str:
    #     """Return nice icon for heater."""
    #     # TODO: icons for each HVAC mode
    #     # if self.hvac_mode == HVAC_MODE_HEAT:
    #     #     return "mdi:fire"
    #     # if self.hvac_mode == HVAC_MODE_OFF:
    #     #     return "mdi:fire"
    #     return "mdi:radiator-off"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._states["temperature"]

    @property
    def target_temperature(self) -> int | None:
        """Return the temperature we try to reach."""
        return self._states["coolingSetpoint"]

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._states["fanMode"]

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        # TODO: test if extra mode is passing
        # self._states["supportedAcFanModes"].remove("turbo")
        return self._states["supportedAcFanModes"]

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._states["humidity"]

    async def async_update(self) -> None:
        """Get the latest data."""
        data = SmartthingsApi.update_states(api_key=self._api_key, device_id=self._device_id)
        for key, obj in data['main'].items():
            if self._states[key] is str:
                self._states[key] = json.loads(obj['value'])

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        # TODO: implement hvac command
        # SmartthingsApi.send_command()
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._attr_current_temperature = self._states["coolingSetpoint"]
        SmartthingsApi.send_command(
            api_key=self._api_key,
            device_id=self._device_id,
            command=SmartthingsApi.COMMAND_TARGET_TEMPERATURE,
            arguments=[temperature]
        )

        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        self._attr_swing_mode = swing_mode

        # TODO: remove workaround once windfree & optional modes become separate property
        if swing_mode == "windFree":
            SmartthingsApi.send_command(
                api_key=self._api_key,
                device_id=self._device_id,
                command=SmartthingsApi.COMMAND_OPTIONAL_MODE,
                arguments=[swing_mode]
            )
        else:
            SmartthingsApi.send_command(
                api_key=self._api_key,
                device_id=self._device_id,
                command=SmartthingsApi.COMMAND_FAN_OSCILLATION_MODE,
                arguments=[swing_mode]
            )
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        self._attr_fan_mode = fan_mode
        SmartthingsApi.send_command(
            api_key=self._api_key,
            device_id=self._device_id,
            command=SmartthingsApi.COMMAND_FAN_MODE,
            arguments=[fan_mode]
        )
        self.async_write_ha_state()

    @property
    def states(self):
        return self._states
