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
    COMMAND_FAN_MODE = {
        "commands": [{"component": "main", "capability": "airConditionerFanMode", "command": "setFanMode"}]}
    COMMAND_AC_MODE = {
        "commands": [{"component": "main", "capability": "airConditionerMode", "command": "setAirConditionerMode"}]}
    COMMAND_TARGET_TEMPERATURE = {"commands": [
        {"component": "main", "capability": "thermostatCoolingSetpoint", "command": "setCoolingSetpoint"}]}

    @staticmethod
    def build_request_base(api_key: str, device_id: str, command: str):
        request_headers = {"Authorization": "Bearer " + api_key}
        url = "https://api.smartthings.com/v1/devices/" + device_id + command
        return url, request_headers

    @staticmethod
    async def async_send_command(session: ClientSession, api_key: str, device_id: str, request_payload: json,
                                 arguments=None):
        # TODO: handling wrong/missing command
        if arguments:
            request_payload["commands"][0]["arguments"] = arguments
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/commands")
        async with session.post(url, json=request_payload, headers=request_headers) as response:
            response_payload = await response.json()
            if response.status != 200:
                raise ApiError("API call failed", response.status, request_payload, response_payload)
            if response_payload["results"][0]["status"] != "ACCEPTED":
                raise ApiError("Device didn't accept change", response.status, request_payload, response_payload)

    @staticmethod
    async def async_get_name(session: ClientSession, api_key: str, device_id: str):
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "")
        async with session.get(url, headers=request_headers) as response:
            response_payload = await response.json()
            if response.status != 200:
                raise ApiError("API call failed", response.status, response_payload=response_payload)
            return response_payload["label"]

    @staticmethod
    async def async_update_states(session: ClientSession, api_key: str, device_id: str):
        request_payload = SmartthingsApi.COMMAND_REFRESH
        await SmartthingsApi.async_send_command(
            session=session,
            api_key=api_key,
            device_id=device_id,
            request_payload=request_payload
        )
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/states")
        async with session.get(url, headers=request_headers) as response:
            response_payload = await response.json()
            if response.status != 200:
                raise ApiError("API call failed", response.status, request_payload, response_payload)
            return response_payload


class ApiError(Exception):

    def __init__(self, message, status_code=None, request_payload=None, response_payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.requestPayload = request_payload
        self.responsePayload = response_payload
