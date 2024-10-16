import hassapi as ha


'''
Notify on state changes
This notifies different notify targets (Pushover, etc) with custom messages if state has changed

Configuration:
- name: "Smarthome Power"
  msg_on: "RECOVERY: Smarthome power is now back ONLINE ({new})"
  msg_off: "WARNING: Smarthome power went OFFLINE ({new}), running now on UPS"
  listen_entity: "switch.0x70b3d52b6008ac57"
  notify_targets:
    - "pushover"
    - "persistent_notification"
  states_on:
    - "on"
  states_off:
    - "off"
    - "unknown"
    - "unavailable"
'''
class StateOffNotifier(ha.Hass):

    DEFAULT_OFF_STATES = ["off", "unavailable", "unknown"]
    REQUIRED_FIELDS = ["name", "msg_on", "msg_off", "listen_entity", "notify_targets"]

    def initialize(self):
        self.set_namespace("homeassistant")
        for service in self.args["states"]:
            self.initialize_each(service)

    def initialize_each(self, service):
        self.verify_state_def(service)
        entity = self.get_entity(service["listen_entity"])
        entity.listen_state(self.send_notifications,
                            new=self.get_off_lambda(service),
                            name=service["name"],
                            msg=service["msg_off"],
                            notify_targets=service["notify_targets"])
        entity.listen_state(self.send_notifications,
                            new=self.get_on_lambda(service),
                            name=service["name"],
                            msg=service["msg_on"],
                            notify_targets=service["notify_targets"])

    def verify_state_def(self, service):
        missing_keys = [key for key in self.REQUIRED_FIELDS if key not in service]
        if missing_keys:
            raise KeyError(f"Missing state obj fields: {', '.join(missing_keys)}")

    def get_off_lambda(self, service):
        if "states_off" in service:
            return lambda s: s in service["states_off"]
        elif "states_on" in service:
            return lambda s: s not in service["states_on"]
        else:
            return lambda s: s in self.DEFAULT_OFF_STATES

    def get_on_lambda(self, service):
        if "states_on" in service:
            return lambda s: s in service["states_on"]
        elif "states_off" in service:
            return lambda s: s not in service["states_off"]
        else:
            return lambda s: s not in self.DEFAULT_OFF_STATES

    def send_notifications(self, entity, attribute, old, new, kwargs):
        msg = kwargs.get("msg").format(new=new, old=old)
        self.log("[{name}]: {msg}".format(name=kwargs.get("name"), msg=msg))
        for target in kwargs.get("notify_targets"):
            self.call_service("notify/" + target, title="HomeAssistant", message=msg)
