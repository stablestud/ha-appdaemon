import mqttapi as mqtt

import json

'''
This class turns of the 3D printer power socket
on fire detection from the smoke sensor
The sensor is mounted directly above the 3D printer
Additionally we notify via Pushover
'''
class Firealarm3DPrinter(mqtt.Mqtt):

    def initialize(self):
        self.set_namespace("mqtt")
        self.smoke_detected = False
        self.notify_targets = self.args["notify_targets"]
        self.mqtt_subscribe(self.args["entity_alarm_source"])
        self.listen_event(self.trigger_fire, "MQTT_MESSAGE", topic = self.args["entity_alarm_source"])

    
    def trigger_fire(self, event_name, data, cb_args):
        values = json.loads(data["payload"])
        if ("smoke" in values and values["smoke"] == True) or ("test" in values and values["test"] == True):
            if (not self.smoke_detected):
                self.smoke_detected = True
                self.log("Smoke detected, turning 3D printer power off")
                self.mqtt_publish(self.args["entity_alarm_target"] + "/set", payload = json.dumps({ "state": "off" }))
                self.notify()
        else:
            self.smoke_detected = False


    def notify(self):
        self.set_namespace("homeassistant")
        for target in self.notify_targets:
            self.call_service("notify/" + target, title="HomeAssistant", message="WARNING: Smoke alarm triggered in 3D printer enclosure!")
        self.set_namespace("mqtt")
