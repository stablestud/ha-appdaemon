import hassapi as ha
from datetime import datetime

class WashingMachineTimer(ha.Hass):

    def initialize(self):
        self.set_namespace("homeassistant")
        self.timer = None
        self.initialize_args()
        self.initialize_listen_states()


    def initialize_args(self):
        self.time = self.get_entity(self.args["entity_time"])
        self.switch = self.get_entity(self.args["entity_switch"])


    def initialize_listen_states(self):
        self.switch.listen_state(self.switch_on, new="on")
        self.time.listen_state(self.time_updated, attribute="timestamp")


    def switch_on(self, entity, attribute, old, new, cb_args):
        if self.timer != None and self.timer_running(self.timer):
            self.log("Switch manually triggered, cancelling timer")
            self.cancel_timer(self.timer)
            self.timer = None


    def time_updated(self, entity, attribute, old, new, cb_args):
        if self.timer != None and self.timer_running(self.timer):
            self.cancel_timer(self.timer)
            self.timer = None
        now  = datetime.now().replace(microsecond=0)
        new_time = datetime.fromtimestamp(new).replace(microsecond=0)
        diff = new_time - now
        if 0 > diff.total_seconds():
            self.log(f"Error: time updated, but its behind current time by: {now - new_time} hours, aborting")
            self.switch.turn_on()
            return
        self.log(f"Time updated, washing machine will run in {diff} hours at: {new_time}")
        self.timer = self.run_at(self.time_reached, new_time)
        self.switch.turn_off()


    def time_reached(self, cb_args):
        self.log("Time reached, turning on washing machine")
        self.timer = None
        self.switch.turn_on()
