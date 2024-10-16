import json
import numbers

import mqttapi as mqtt


class External3DPrinterSensors(mqtt.Mqtt):

    REQUIRED_FIELDS = ["source", "target", "values"]

    def initialize(self):
        self.set_namespace("mqtt")
        for sensor in self.args["entities"]:
            self.initialize_each(sensor)

    def initialize_each(self, sensor):
        self.verify_state_def(sensor)
        self.mqtt_subscribe(sensor["source"])
        self.listen_event(self.mqtt_message_received_event, "MQTT_MESSAGE", topic = sensor["source"], sensor = sensor)

    def verify_state_def(self, sensor):
        missing_keys = [key for key in self.REQUIRED_FIELDS if key not in sensor]
        if missing_keys:
            raise KeyError(f"Missing state obj fields: {', '.join(missing_keys)}")

    def mqtt_message_received_event(self, event_name, data, kwargs):
        data = json.loads(data["payload"])
        sensor = kwargs.get("sensor")
        payload = {}
        for value in sensor["values"]:
            payload[value] = data[value]
        self.log(f"Updating {sensor['target']} to {payload}")
        self.mqtt_publish(sensor["target"], payload = json.dumps(payload), retain = True)
