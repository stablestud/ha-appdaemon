import requests

import hassapi as ha


'''
Do predifined actions on NFC/tag scans
This allows custom actions to be taken on tag scans

Configuration:
- `tags`: list of tags that trigger actions
  - `tag_id`: home assistant tag id
  - `action`: function name inside TagReader class that should be called
    - `name`: function name (optional)
    - `action_args`: list of objects that should be passed to the action (optional)
- `actions`: list of actions that are being triggered (optional; can be omitted if no additional action_args needs to be passed)
  - `name`: function name
  - `action_args`: list of objects that should be passed to the action
'''
class TagReader(ha.Hass):
    def initialize(self):
        self.set_namespace("homeassistant")
        action = None
        for tag in self.args["tags"]:
            if isinstance(tag["action"], str):
                action = tag["action"]
            elif isinstance(tag["action"], dict):
                action = tag["action"]["name"]
            assert action is not None, f"failed to read action name for tag '{tag['tag_id']}'"
            assert action in TagReader.__dict__, f"action/function '{action}' not implemented in TagReader"
            self.listen_event(callback=self.get_action_callback(action), event="tag_scanned", tag_id=tag["tag_id"], action_args=self.get_action_args(tag))

    def get_action_args(self, tag):
        if "action_args" in tag["action"]:
            return tag["action"]["action_args"]
        for action in self.args["actions"]:
            if action["name"] == tag["action"]:
                return action["action_args"] if "action_args" in action else []
        return []

    def get_action_callback(self, action):
        callback = getattr(self, action)
        assert callable(callback), f"Callback '{action}' is not callable"
        return callback

    def execute_service(self, event_name, event_data, kwargs):
        action_args = kwargs.get("action_args")
        self.log(f"Tag read for {event_data['name']}")
        service_args = {}
        namespace = "default"
        assert "service" in action_args
        if "namespace" in action_args:
            namespace = action_args["namespace"]
        if "service_args" in action_args:
            service_args = action_args["service_args"]
        self.call_service(service=action_args["service"], namespace=action_args["namespace"], service_args=service_args)


    ## Spoolman actions

    def select_spool(self, event_name, event_data, kwargs):
        action_args = kwargs.get("action_args")
        self.log(f"Tag read for {event_data['name']}")
        spool_id = 0
        spool_friendly_name = None
        if event_data["tag_id"] != "null_spool":
            spool_entity = self.get_spool_entity(self.get_spools(action_args["spoolman_url"]), event_data["tag_id"])
            if spool_entity is None:
                self.log(f"Warning: no spool found for {event_data['name']}")
                return
            spool_id = spool_entity["id"]
            spool_friendly_name = spool_entity["filament"]["vendor"]["name"] + " " + spool_entity["filament"]["name"]
        response = requests.post(action_args["moonraker_url"], json={"spool_id": spool_id})
        if response.status_code == 200:
            self.log(f"Successfully set '{spool_friendly_name}' as active spool")
        else:
            self.log(f"Error: Failed to set '{spool_friendly_name}' as active spool: {response.status_code} {response.text}")

    def get_spools(self, spoolman_url):
        response = requests.get(spoolman_url, timeout=5, headers={"Accept": "application/json"})
        response.raise_for_status()
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise ValueError("Response is not JSON")
        self.log(response.json())
        return response.json()

    def get_spool_entity(self, spools, tag_id):
        return next((item for item in spools if item.get("extra", {}).get("tag_id", "").lower().strip().replace('"', '') == tag_id.lower()), None)
