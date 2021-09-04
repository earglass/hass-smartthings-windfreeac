import json

from aiohttp import ClientSession


class SmartthingsApi:
    COMMAND_SWITCH_ON = {"commands": [{"component": "main", "capability": "switch", "command": "on"}]}
    COMMAND_SWITCH_OFF = {"commands": [{"component": "main", "capability": "switch", "command": "off"}]}
    COMMAND_REFRESH = {"commands": [{"component": "main", "capability": "refresh", "command": "refresh"}]}
    COMMAND_FAN_OSCILLATION_MODE = {
        "commands": [{"component": "main", "capability": "fanOscillationMode", "command": "setFanOscillationMode"}]}
    COMMAND_OPTIONAL_MODE = {"commands": [
        {"component": "main", "capability": "custom.airConditionerOptionalMode", "command": "setAcOptionalMode"}]}
    COMMAND_FAN_MODE = {"commands": [{"component": "main", "capability": "fanMode", "command": "setFanMode"}]}
    COMMAND_AC_MODE = {"commands": [{"component": "main", "capability": "airConditionerMode", "command": "setAirConditionerMode"}]}
    COMMAND_TARGET_TEMPERATURE = {"commands": [
        {"component": "main", "capability": "thermostatCoolingSetpoint", "command": "setCoolingSetpoint"}]}

    @staticmethod
    def build_request_base(api_key: str, device_id: str, command: str):
        request_headers = {"Authorization": "Bearer " + api_key}
        url = "https://api.smartthings.com/v1/devices/" + device_id + command
        return url, request_headers

    @staticmethod
    async def async_send_command(session: ClientSession, api_key: str, device_id: str, command: json, arguments=None):
        # TODO: handling wrong/missing command
        if arguments:
            command["commands"][0]["arguments"] = arguments
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/commands")
        async with session.post(url, json=command, headers=request_headers) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception("Error from API: " + json.dumps(data))
            if data["results"][0]["status"] != "ACCEPTED":
                raise Exception("Error from API: " + json.dumps(data))

    @staticmethod
    async def async_get_name(session: ClientSession, api_key: str, device_id: str):
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "")
        async with session.get(url, headers=request_headers) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception("Error from API: " + json.dumps(data))
            return data["label"]

    @staticmethod
    async def async_update_states(session: ClientSession, api_key: str, device_id: str):
        await SmartthingsApi.async_send_command(
            session=session,
            api_key=api_key,
            device_id=device_id,
            command=SmartthingsApi.COMMAND_REFRESH
        )
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/states")
        async with session.get(url, headers=request_headers) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception("Error from API: " + json.dumps(data))
            return data
