import requests
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
    COMMAND_TARGET_TEMPERATURE = {"commands": [
        {"component": "main", "capability": "thermostatCoolingSetpoint", "command": "setCoolingSetpoint "}]}

    @staticmethod
    def build_request_base(api_key: str, device_id: str, command: str):
        request_headers = {"Authorization": "Bearer " + api_key}
        url = "https://api.smartthings.com/v1/devices/" + device_id + command

        return url, request_headers

    @staticmethod
    def send_command(api_key: str, device_id: str, command: json, arguments=None):
        # TODO: handling wrong/missing command

        if arguments:
            command["commands"][0]["arguments"] = arguments
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/commands")
        resp = requests.post(
            url=url,
            json=command,
            headers=request_headers
        )

        if resp.status_code != 200:
            # TODO: throw error
            pass
        if resp.json()["results"][0]["status"] != "ACCEPTED":
            # TODO: throw error
            pass

    @staticmethod
    async def async_send_command(session: ClientSession, api_key: str, device_id: str, command: json, arguments=None):
        # TODO: handling wrong/missing command
        if arguments:
            command["commands"][0]["arguments"] = arguments
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/commands")
        async with session.post(url, json=command, headers=request_headers) as response:
            data = await response.json()
            if response.status != 200:
                # TODO: throw error
                pass
            if data["results"][0]["status"] != "ACCEPTED":
                # TODO: throw error
                pass

    @staticmethod
    def get_name(api_key: str, device_id: str):
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "")
        resp = requests.get(
            url=url,
            headers=request_headers
        )

        if resp.status_code != 200:
            # TODO: throw error
            pass
        return resp.json()["label"]

    @staticmethod
    async def async_get_name(session: ClientSession, api_key: str, device_id: str):
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "")
        async with session.get(url, headers=request_headers) as response:
            data = await response.json()
            if response.status != 200:
                # TODO: throw error
                pass
            return data["label"]

    @staticmethod
    def update_states(api_key: str, device_id: str):
        # SmartthingsApi.send_command(api_key, device_id, SmartthingsApi.COMMAND_REFRESH)  -> 409 'invalid device state'
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/states")
        resp = requests.get(
            url=url,
            headers=request_headers
        )
        # TODO: error handling

        return resp.json()

    @staticmethod
    async def async_update_states(session: ClientSession, api_key: str, device_id: str):
        # await SmartthingsApi.async_send_command(  -> 409 'invalid device state'
        #     session=session,
        #     api_key=api_key,
        #     device_id=device_id,
        #     command=SmartthingsApi.COMMAND_REFRESH
        # )
        url, request_headers = SmartthingsApi.build_request_base(api_key, device_id, "/states")
        async with session.get(url, headers=request_headers) as response:
            # TODO: error handling
            return await response.json()
