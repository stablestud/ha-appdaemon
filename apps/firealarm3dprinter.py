import mqttapi as mqtt

import json

'''
This class turns of the 3D printer power socket
on fire detection from the smoke sensor
The sensor is mounted directly above the 3D printer
'''
class Firealarm3DPrinter(mqtt.Mqtt):

    def initialize(self):
        self.set_namespace("mqtt")
        self.mqtt_subscribe(self.args["entity_alarm_source"])
        self.listen_event(self.mqtt_msg, "MQTT_MESSAGE", topic = self.args["entity_alarm_source"])


    def mqtt_msg(self, event_name, data, cb_args):
        values = json.loads(data["payload"])
        if ("smoke" in values and values["smoke"] == True) or ("test" in values and values["test"] == True):
            self.log("Smoke detected, turning 3D printer power off")
            self.mqtt_publish(self.args["entity_alarm_target"] + "/set", payload = json.dumps({ "state": "off" }))
