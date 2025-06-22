import hassapi as ha
import enum as enum

class StoreroomMotion(ha.Hass):
    class TriggerMode(enum.Enum):
        MANUAL  = 1,
        MOTION  = 2,
        SERVICE = 3 # Manually turned ON via appdaemon service call
                    # In this case the lights stays ON until its turned off manually

    def initialize(self):
        self.set_namespace("homeassistant")
        self.ignore_action = False
        self.state = None
        self.initialize_args()
        self.initialize_listen_states()
        self.initialize_service()

    def initialize_args(self):
        self.timer = self.get_entity(self.args["entity_timer"])
        self.sensor = self.get_entity(self.args["entity_sensor"])
        self.switch = self.get_entity(self.args["entity_switch"])
        self.motion_timeout = self.args["motion_timeout"]
        self.manual_timeout = self.args["manual_timeout"]

    def initialize_listen_states(self):
        self.sensor.listen_state(self.sensor_detected, new="on")
        self.sensor.listen_state(self.sensor_cleared, new="off")
        self.switch.listen_state(self.switch_on, new="on")
        self.switch.listen_state(self.switch_off, new="off")
        self.listen_event(self.timer_finished, "timer.finished", entity_id = self.args["entity_timer"])

    def initialize_service(self):
        self.register_service("storeroom/light", cb=self.service_handler, namespace="default")

    def service_handler(self, namespace, domain, service, kwargs):
        assert "state" in kwargs.get("service_args")
        self.ignore_action = False
        state = kwargs.get("service_args")["state"]
        if self.str2bool(state):
            self.switch_on_service()
        else:
            self.switch_off(None, None, None, None, None)

    def switch_on_service(self):
        self.log("Switch via service call ON")
        self.state = self.TriggerMode.SERVICE
        if self.is_timer_active():
            self.timer.call_service("cancel")
        self.turn_on_light()

    def switch_on(self, entity, attribute, old, new, cb_args):
        if self.is_ignore_action():
            return
        self.log("Switch manually ON")
        if self.is_occupied():
            self.log("Motion sensor already active, switching to motion based trigger")
            self.state = self.TriggerMode.MOTION
        else:
            self.state = self.TriggerMode.MANUAL
            self.start_timer(self.manual_timeout)
    
    def switch_off(self, entity, attribute, old, new, cb_args):
        self.state = None
        if self.is_ignore_action():
            return
        self.log("Switch manually OFF")
        if self.is_timer_active():
            self.timer.call_service("cancel")

    def sensor_detected(self, entity, attribute, old, new, cb_args):
        self.log("Motion detected")
        # If manually actived light
        if self.state == self.TriggerMode.MANUAL:
            self.log("Switching to motion based turn off")
            self.state == self.TriggerMode.MOTION
            self.timer.call_service("cancel")
        elif self.state == self.TriggerMode.SERVICE:
            return
        else:
            self.state = self.TriggerMode.MOTION
            self.turn_on_light()

    def sensor_cleared(self, entity, attribute, old, new, cb_args):
        # If not manually triggered
        if self.state == self.TriggerMode.MOTION and self.is_light_on():
            self.log("Motion cleared")
            self.start_timer(self.motion_timeout)

    def timer_finished(self, event_name, data, cb_args):
        self.log("Timer 'light_timeout' finished")
        if self.is_light_on():
            self.turn_off_light()

    def is_light_on(self):
        return self.switch.get_state("state") == "on"

    def is_timer_active(self):
        return self.timer.get_state("state") == "active"

    def is_occupied(self):
        return self.sensor.get_state("state") == "on"

    def is_ignore_action(self):
        if self.ignore_action == True:
            self.ignore_action = False
            return True
        else:
            return False

    def turn_on_light(self):
        self.log("Turning ON storeroom light")
        self.ignore_action = True
        self.switch.call_service("turn_on")

    def turn_off_light(self):
        self.log("Turning OFF storeroom light")
        self.ignore_action = True
        self.switch.call_service("turn_off")

    def start_timer(self, duration):
        if self.is_timer_active():
            self.log(f"Restarting timer 'light timeout': duration: {duration}s")
        else:
            self.log(f"Starting timer 'light timeout': duration: {duration}s")
        self.timer.call_service("start", duration = duration)

    def str2bool(self, value):
        if isinstance(value, str) or sys.version_info[0] < 3 and isinstance(value, basestring):
            value = value.lower()
            if value in {'yes', 'true', 'on', 't', 'y', '1'}:
                return True
            if value in {'no', 'false', 'off', 'f', 'n', '0'}:
                return False
        return None
