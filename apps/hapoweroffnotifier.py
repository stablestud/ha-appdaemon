import hassapi as ha

class HAPowerOffNotifier(ha.Hass):

    def initialize(self):
        off_states = ["off", "unavailable", "unknown"]
        self.set_namespace("homeassistant")
        self.switch = self.get_entity(self.args["entity_power"])
        self.notify_targets = self.args["notify_targets"]
        self.switch.listen_state(self.trigger_poweroff, new=lambda s: s in off_states)
        self.switch.listen_state(self.trigger_poweron, new=lambda s: s not in off_states)


    def trigger_poweron(self, entity, attribute, old, new, cb_args):
        for target in self.notify_targets:
            self.call_service("notify/" + target, title="HomeAssistant", message=f"RECOVERY: Smarthome power is now back ONLINE ({new})")


    def trigger_poweroff(self, entity, attribute, old, new, cb_args):
        for target in self.notify_targets:
            self.call_service("notify/" + target, title="HomeAssistant", message=f"WARNING: Smarthome power went OFFLINE ({new}), running now on UPS" )
