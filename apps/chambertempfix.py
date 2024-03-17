import numbers
import json

import mqttapi as mqtt

'''
This class fixes the Octoprint Plugin MQTT Chamber Temperature
that it cannot read directly from the zigbee2MQTT published topics,
instead we update a topic which the plugin can read from
'''
class ChamberTempFix3DPrinter(mqtt.Mqtt):

    def initialize(self):
        self.set_namespace("mqtt")
        self.mqtt_subscribe(self.args["entity_temp_source"])
        self.listen_event(self.mqtt_message_received_event, "MQTT_MESSAGE", topic = self.args["entity_temp_source"])

    def mqtt_message_received_event(self, event_name, data, cb_args):
        values = json.loads(data["payload"])
        temp = values["temperature"]
        if isinstance(temp, numbers.Number):
            self.log(f"Updating Chamber Temp to {temp}")
            self.mqtt_publish(self.args["entity_temp_target"], payload = temp)

