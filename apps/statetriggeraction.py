import json
import time

import hassapi as ha

'''
Call HA services on HA/MQTT state changes
* trigger: initial ha/mqtt trigger that starts the action
* action: action that is run, name must be a function name defined in the class

HA entity configuration (for trigger:)
  type: "ha"
  entity: HA entity id
  states:
    - list of accepted states

MQTT entity configuration (for trigger:)
  type: "mqtt"
  topic: full MQTT topic URL
  states:
    - list of accepted states, does not work with JSON payload

Configuration (actions):

workflows:
  - name: "Fountain"
    trigger:
      type: "mqtt"
      topic: "zigbee2mqtt/Bedroom Desk Button/action"
      states:
        - "on"
        - "single"
    action: "turn_on_fountain"
  - name: "Fountain2"
    trigger:
      type: "ha"
      entity: "button.foutain"
      states:
        - "on"
    action: "turn_on_fountain"
actions:
  - name: "turn_on_fountain"
    action_args:
      fountain_entity: "switch.power_fountain"
'''
class StateTriggerAction(ha.Hass):
    def initialize(self):
        self.set_namespace("homeassistant")
        action = None
        for workflow in self.args["workflows"]:
            if isinstance(workflow["action"], str):
                action = workflow["action"]
            elif isinstance(workflow["action"], dict):
                action = workflow["action"]["name"]
            assert action is not None, f"failed to read action name for workflow '{workflow["name"]}'"
            assert action in StateTriggerAction.__dict__, f"action/function '{action}' not implemented in StateTriggerAction"
            assert "trigger" in workflow, f"failed to read trigger for workflow '{workflow["name"]}'"
            if "mqtt" == workflow["trigger"]["type"]:
                self.setup_mqtt_trigger(workflow=workflow, action=action)
            elif "ha" == workflow["trigger"]["type"]:
                self.setup_ha_trigger(workflow=workflow, action=action)
            else:
                raise ValueError(f"unknown trigger type: {workflow["trigger"]["type"]}")

    def setup_mqtt_trigger(self, workflow, action):
        topic = workflow["trigger"]["topic"]
        assert topic is not None, f"failed to read MQTT trigger topic for workflow '{workflow["name"]}'"
        self.call_service("mqtt/subscribe", namespace="mqtt", topic=topic)
        self.listen_event(callback=self.get_action_callback(action), namespace="mqtt", event="MQTT_MESSAGE", topic=topic, workflow=workflow)

    def setup_ha_trigger(self, workflow, action):
        pass

    def get_action_args(self, workflow):
        if "action_args" in workflow["action"]:
            return workflow["action"]["action_args"]
        for action in self.args["actions"]:
            if action["name"] == workflow["action"]:
                return action["action_args"] if "action_args" in action else []
        return []

    def get_action_callback(self, action):
        callback = getattr(self, action)
        assert callable(callback), f"Callback '{action}' is not callable"
        return callback

    def wake_computer(self, event_name, event_data, **kwargs):
        data = None;
        workflow = kwargs.get("workflow")
        action_args = self.get_action_args(workflow)
        if isinstance(workflow["action"], dict):
            data = json.loads(event_data["payload"])
        else:
            data = event_data["payload"]
        if data not in workflow["trigger"]["states"]:
            return
        self.log(f"[{workflow["name"]}]: triggered WOL")
        self.set_namespace("homeassistant")
        power_plug = self.get_entity(action_args["power_entity"])
        wol_device = self.get_entity(action_args["wol_entity"])
        if power_plug.get_state() != "on":
            self.log("is NOT on")
            power_plug.turn_on()
            time.sleep(3)
        wol_device.call_service(service="press")
