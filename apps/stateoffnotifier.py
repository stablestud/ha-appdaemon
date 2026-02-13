import threading

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
  delay_time: 180
  delay_on:
    - "unknown"
    - "unavailable"
'''
class StateOffNotifier(ha.Hass):

    DEFAULT_DELAY_TIME = 300
    DEFAULT_DELAY_STATES = [ "unavailable", "unknown" ]
    DEFAULT_OFF_STATES = ["off", "unavailable", "unknown"]
    REQUIRED_FIELDS = ["name", "msg_on", "msg_off", "listen_entity", "notify_targets"]

    def initialize(self):
        self.set_namespace("homeassistant")
        self.lock = threading.Lock()
        self.timer_handles = {}
        for service in self.args["states"]:
            self.initialize_each(service)

    def initialize_each(self, service):
        self.verify_state_def(service)
        entity = self.get_entity(service["listen_entity"])
        entity.listen_state(self.handle_change,
                            new=self.get_off_lambda(service),
                            name=service["name"],
                            msg=service["msg_off"],
                            notify_targets=service["notify_targets"],
                            delay_on=self.get_delay_on(service),
                            delay_time=self.get_delay_time(service))
        entity.listen_state(self.handle_change,
                            new=self.get_on_lambda(service),
                            name=service["name"],
                            msg=service["msg_on"],
                            notify_targets=service["notify_targets"],
                            delay_on=self.get_delay_on(service),
                            delay_time=self.get_delay_time(service))

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

    def get_delay_on(self, service):
        if "delay_on" in service:
            return service["delay_on"]
        else:
            return self.DEFAULT_DELAY_STATES

    def get_delay_time(self, service):
        if "delay_time" in service:
            return service["delay_time"]
        else:
            return self.DEFAULT_DELAY_TIME

    def handle_change(self, entity, attribute, old, new, **kwargs):
        with self.lock:
            if entity in self.timer_handles:
                delay_data = self.timer_handles.pop(entity)
                self.log("[{name}]: Cancelling notification timer due to state change".format(name=kwargs.get("name")))
                self.cancel_timer(delay_data["handle"])
                if delay_data["old"] == new:
                    self.log("[{name}]: Returned back to '{new}' before delay timeout, suppressing notification".format(name=kwargs.get("name"), new=new))
                    return
        ntfy_kwargs = kwargs.copy()
        ntfy_kwargs.update({
            "entity": entity,
            "attribute": attribute,
            "old": old,
            "new": new
        })
        if kwargs.get("delay_on") and new in kwargs.get("delay_on"):
            with self.lock:
                self.timer_handles[entity] = { "handle": self.run_in(self.send_notifications, kwargs.get("delay_time"), **ntfy_kwargs), "old": old }
            self.log("[{name}]: Delaying notification for {time}s due to '{new}' in 'delay_on'".format(name=kwargs.get("name"), new=new, time=kwargs.get("delay_time")))
        else:
            self.send_notifications(**ntfy_kwargs)

    def send_notifications(self, **kwargs):
        msg = kwargs.get("msg").format(new=kwargs["new"], old=kwargs["old"])
        self.log("[{name}]: {msg}".format(name=kwargs.get("name"), msg=msg))
        for target in kwargs.get("notify_targets"):
            self.call_service("notify/" + target, title="HomeAssistant", message=msg)
