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
    SWING_BOTH, SUPPORT_TARGET_TEMPERATURE,
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
    """Representation of a heater."""

    _attr_supported_features = SUPPORT_FAN_MODE | SUPPORT_SWING_MODE | SUPPORT_TARGET_TEMPERATURE
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

    def __init__(self, api_key, device_id, name, states, websession) -> None:
        """Initialize the climate."""
        self._state = STATE_OFF
        self._attr_name = "samsungwindfree_" + name
        self.api_key = api_key
        self.device_id = device_id
        self.states = process_json_states(states)
        self.websession = websession

    @property
    def swing_mode(self) -> str:
        """Return swing mode ie. fixed, vertical."""
        return SWING_MODES_SAMSUNG_TO_HASS[self.states["fanOscillationMode"]]

    @property
    def swing_modes(self) -> List[str]:
        """Return the list of available swing modes.

        Requires SUPPORT_SWING_MODE.
        """
        # TODO: remove workaround once windfree & optional modes become separate property
        # SWING_MODES["windFree"] = "windFree"
        return list(SWING_MODES_HASS_TO_SAMSUNG.keys())

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        if self._state == STATE_OFF:
            return "off"
        return self.states["airConditionerMode"]

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        # TODO: test if extra modes are passing
        # self._states["supportedAcModes"].remove("aIComfort")
        # self._states["supportedAcModes"].remove("wind")
        self.states["supportedAcModes"].append("off")
        return self.states["supportedAcModes"]

    @property
    def icon(self) -> str:
        #     """Return nice icon for heater."""
        #     # TODO: icons for each HVAC mode
        #     # if self.hvac_mode == HVAC_MODE_HEAT:
        #     #     return "mdi:fire"
        #     # if self.hvac_mode == HVAC_MODE_OFF:
        #     #     return "mdi:fire"
        return "mdi:radiator-off"

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.states["temperature"])

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return float(self.states["coolingSetpoint"])

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self.states["fanMode"]

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        # TODO: test if extra mode is passing
        self.states["supportedAcFanModes"].remove("turbo")
        return self.states["supportedAcFanModes"]

    @property
    def current_humidity(self) -> int:
        """Return the current humidity."""
        return int(self.states["humidity"])

    async def async_update(self) -> None:
        """Get the latest data."""
        states = await SmartthingsApi.async_update_states(self.websession, self.api_key, self.device_id)
        self.states = process_json_states(states)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        self._attr_hvac_mode = hvac_mode
        # TODO: implement hvac command
        if hvac_mode == "off":
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_SWITCH_OFF
            )
        elif self.state == "off":
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_SWITCH_ON
            )
        else:
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_AC_MODE,
                arguments=[hvac_mode]
            )
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._attr_target_temperature = temperature
        await SmartthingsApi.async_send_command(
            session=self.websession,
            api_key=self.api_key,
            device_id=self.device_id,
            command=SmartthingsApi.COMMAND_TARGET_TEMPERATURE,
            arguments=[temperature]
        )
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new swing mode."""
        self._attr_swing_mode = swing_mode

        # TODO: remove workaround once windfree & optional modes become separate property
        if swing_mode == "windFree":
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_OPTIONAL_MODE,
                arguments=[swing_mode]
            )
        else:
            await SmartthingsApi.async_send_command(
                session=self.websession,
                api_key=self.api_key,
                device_id=self.device_id,
                command=SmartthingsApi.COMMAND_FAN_OSCILLATION_MODE,
                arguments=[swing_mode]
            )
        await self.async_update()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        self._attr_fan_mode = fan_mode
        await SmartthingsApi.async_send_command(
            session=self.websession,
            api_key=self.api_key,
            device_id=self.device_id,
            command=SmartthingsApi.COMMAND_FAN_MODE,
            arguments=[fan_mode]
        )
        await self.async_update()
        self.async_write_ha_state()
