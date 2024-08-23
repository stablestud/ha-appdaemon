import hassapi as ha

class HAPowerOffNotifier(ha.Hass):

    def initialize(self):
        self.set_namespace("homeassistant")
        self.switch = self.get_entity(self.args["entity_power"])
        self.notify_targets = self.args["notify_targets"]
        self.switch.listen_state(self.trigger_poweroff, new="off")

    def trigger_poweroff(self, entity, attribute, old, new, cb_args):
        for target in self.notify_targets:
            self.call_service("notify/" + target, title="HomeAssistant", message="Smarthome power is OFFLINE, running now on UPS")
