import hassapi as ha
from datetime import datetime

class WashingMachineTimer(ha.Hass):

    def initialize(self):
        self.set_namespace("homeassistant")
        self.timer = None
        self.initialize_args()
        self.initialize_listen_states()
        self.initialize_timer()

    def initialize_args(self):
        self.time = self.get_entity(self.args["entity_time"])
        self.switch = self.get_entity(self.args["entity_switch"])

    def initialize_listen_states(self):
        self.time.listen_state(self.time_updated, attribute="timestamp")

    def initialize_timer(self):
        new = self.time.get_state(attribute="timestamp")
        new_time = datetime.fromtimestamp(new).replace(microsecond=0)
        if new_time > self.now():
            self.setup_timer(new_time)

    def now(self):
        return datetime.now().replace(microsecond=0)

    def setup_timer(self, new_time):
        now = self.now()
        diff = new_time - now
        if 0 > diff.total_seconds():
            self.log(f"Warning: time updated, but its behind current time by: {now - new_time}, aborting")
            self.switch.turn_on()
        else:
            self.log(f"Time updated, washing machine will run in {diff} hours at: {new_time}")
            self.timer = self.run_at(self.time_reached, new_time)
            self.switch.turn_off()

    def time_updated(self, entity, attribute, old, new, cb_args):
        if self.timer != None and self.timer_running(self.timer):
            self.cancel_timer(self.timer)
            self.timer = None
        new_time = datetime.fromtimestamp(new).replace(microsecond=0)
        self.setup_timer(new_time)

    def time_reached(self, cb_args):
        self.log("Time reached, turning on washing machine")
        self.timer = None
        self.switch.turn_on()
