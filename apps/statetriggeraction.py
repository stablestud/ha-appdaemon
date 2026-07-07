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
      entity: "button.fountain"
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
        assert workflow["trigger"]["topic"] is not None, f"failed to read MQTT trigger topic for workflow '{workflow["name"]}'"
        topic = workflow["trigger"]["topic"]
        self.call_service("mqtt/subscribe", namespace="mqtt", topic=topic)
        self.listen_event(callback=self.get_action_callback(action), namespace="mqtt", event="MQTT_MESSAGE", topic=topic, workflow=workflow)

    def setup_ha_trigger(self, workflow, action):
        assert workflow["trigger"]["entity"] is not None, f"failed to read MQTT trigger topic for workflow '{workflow["name"]}'"
        entity = workflow["trigger"]["entity"]
        self.listen_event(callback=self.get_action_callback(action), namespace="homeassistant", event="state_changed", entity_id=entity, workflow=workflow)

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

    def trigger_matches(self, workflow, event_data):
        trigger_states = workflow["trigger"]["states"]
        if "payload" in event_data:
            if isinstance(trigger_states, dict):
                json.loads(event_data["payload"])
                raise ValueError("JSON payload not yet implemented")
            return event_data["payload"] in trigger_states
        elif "new_state" in event_data:
            if isinstance(trigger_states, dict):
                json.loads(event_data["new_state"]["state"])
                raise ValueError("JSON state not yet implemented")
            return event_data["new_state"]["state"] in trigger_states
        else:
            raise ValueError("cannot extract state from event_data")


    def prepare_workflow(self, event_data, **kwargs):
        workflow = kwargs["workflow"]
        if not self.trigger_matches(workflow, event_data):
            return None, None
        return workflow, self.get_action_args(workflow)

    # Action functions below

    def wake_computer(self, event_name, event_data, **kwargs):
        workflow, action_args = self.prepare_workflow(event_data, **kwargs)
        if workflow is None:
            return False
        self.log(f"[{workflow['name']}]: triggered WOL")
        self.set_namespace("homeassistant")
        power_plug = self.get_entity(action_args["power_switch"])
        wol_device = self.get_entity(action_args["wol_device"])
        if power_plug.get_state() != "on":
            power_plug.turn_on()
            time.sleep(3)
        wol_device.turn_on()
        return True

    def shutdown_computer(self, event_name, event_data, **kwargs):
        workflow, action_args = self.prepare_workflow(event_data, **kwargs)
        if workflow is None:
            return False
        self.log(f"[{workflow['name']}]: triggered shutdown")
        self.set_namespace("homeassistant")
        computer = self.get_entity(action_args["device"])
        computer.turn_off()
        return True

    def shutdown_tv(self, event_name, event_data, **kwargs):
        workflow, action_args = self.prepare_workflow(event_data, **kwargs)
        if workflow is None:
            return False
        device_status = self.get_entity(action_args["device_status"])
        power_plug = self.get_entity(action_args["power_switch"])
        if device_status.get_state() not in ( "unavailable", "unknown", "disconnected", "off",):
            if self.shutdown_computer(event_name, event_data, **kwargs):
                time.sleep(45)
        self.log(f"[{workflow['name']}]: turning power off")
        self.set_namespace("homeassistant")
        power_plug.turn_off()
        return True
