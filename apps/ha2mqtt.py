import hassapi as ha
import mqttapi as mqtt

import json

'''
Expose Home Assistant entity states to MQTT (readonly)
This allows using Home Assistant internal sensors also in MQTT enabled applications.
The app does not listen on the MQTT topcis, therefore its a one-way communication and can only be used to read internal HA sensors

Configuration:
- `entities`: list of HA entities to expose on MQTT
  - `id`: HA entity to expose on MQTT
    `topic`: MQTT topic to write to
    `retain`: whether the topic should be retained on the MQTT broker; default False
'''
class Ha2MQTT(ha.Hass, mqtt.Mqtt):
    def initialize(self):
        self.set_namespace("homeassistant")
        for entity_args in self.args["entities"]:
            assert entity_args and entity_args["id"] and entity_args["topic"]
            entity = self.get_entity(entity_args["id"])
            entity.listen_state(callback=self.update, topic=entity_args["topic"], retain=entity_args["retain"] == True)

    def update(self, entity, attribute, old, new, kwargs):
        topic = kwargs.get("topic")
        assert topic is not None
        retain = kwargs.get("retain")
        payload = { attribute: new }
        self.set_namespace("mqtt")
        self.log(f"Updating {topic} to {payload}")
        self.mqtt_publish(topic, payload = json.dumps(payload), retain = retain)
