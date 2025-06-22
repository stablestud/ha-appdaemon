import requests

import hassapi as ha


'''
Do predifined actions on NFC/tag scans
This allows custom actions to be taken on tag scans

Configuration:
- `tags`: list of tags that trigger actions
  - `tag_id`: home assistant tag id
  - `action`: function inside TagReader class that should be called
- `actions`: list of actions that are being triggered (optional; can be omitted if no additional data needs to be passed)
  - `name`: function name
  - `data`: list of objects that should be passed to the action
'''
class TagReader(ha.Hass):
    def initialize(self):
        self.set_namespace("homeassistant")
        for tag in self.args["tags"]:
            assert tag["action"] in TagReader.__dict__, f"action/function '{tag['action']}' not implemented in TagReader"
            self.listen_event(callback=self.get_action_callback(tag["action"]), event="tag_scanned", tag_id=tag["tag_id"], data=self.get_action_data(tag["action"]))

    def get_action_data(self, action_name):
        for action in self.args["actions"]:
            if action["name"] == action_name:
                return action["data"] if "data" in action else []
        return []

    def get_action_callback(self, action):
        callback = getattr(self, action)
        assert callable(callback), f"Callback '{action}' is not callable"
        return callback

    def select_spool(self, event_name, event_data, kwargs):
        data = kwargs.get("data")
        self.reload_spools(data["spoolman_device"], data["spoolman_integration"])
        self.log(f"Tag read for {event_data['name']}")
        spool_id = 0
        spool_friendly_name = None
        if event_data["tag_id"] != "null_spool":
            spool_entity = self.get_spool_entity(data["spoolman_device"], event_data["tag_id"])
            if spool_entity is None:
                self.log(f"Warning: no spool found for {event_data['name']}")
                return
            spool_id = spool_entity.get_state(attribute="id")
            spool_friendly_name = spool_entity.get_state(attribute='friendly_name')
        response = requests.post(data["moonraker_url"], json={"spool_id": spool_id})
        if response.status_code == 200:
            self.log(f"Successfully set '{spool_friendly_name}' as active spool")
        else:
            self.log(f"Error: Failed to set '{spool_friendly_name}' as active spool: {response.status_code} {response.text}")


    def get_spool_entity(self, spoolman_device, tag_id):
        for spool in self.device_entities(spoolman_device):
            spool_entity = self.get_entity(spool)
            if spool_entity.get_state(attribute="extra_tag_id") == tag_id:
                return spool_entity
        return None

    def reload_spools(self, spoolman_device, spoolman_integration):
        self.call_service(service="homeassistant/reload_config_entry", device_id=spoolman_device, entry_id=spoolman_integration)
