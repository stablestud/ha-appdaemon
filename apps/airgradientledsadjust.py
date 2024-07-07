import hassapi as ha

class AirGradientLedsAdjust(ha.Hass):

    def initialize(self):
        self.set_namespace("homeassistant")
        self.timer = self.get_entity(self.args["entity_timer"])
        self.displays = []
        self.ledbars = []
        self.initialize_entities()
        self.initialize_state()
        self.initialize_listen_states()


    def initialize_listen_states(self):
        self.timer.listen_state(self.trigger_dimm, new="off")
        self.timer.listen_state(self.trigger_bright, new="on")


    def initialize_entities(self):
        for display in self.args["entities_display"]:
            self.displays.append(self.get_entity(display))
        for ledbar in self.args["entities_ledbar"]:
            self.ledbars.append(self.get_entity(ledbar))


    def initialize_state(self):
        if self.timer.get_state("state") == "off":
            self.make_dimm()
        else:
            self.make_bright()


    def trigger_bright(self, entity, attribute, old, new, cb_args):
        self.make_bright()


    def trigger_dimm(self, entity, attribute, old, new, cb_args):
        self.make_dimm()


    def make_dimm(self):
        self.log("Dimming AirGradient devices")
        for display in self.displays:
            display.call_service("set_value", value=0)
        for ledbar in self.ledbars:
            ledbar.call_service("set_value", value=5)


    def make_bright(self):
        self.log("Brighten AirGradient devices")
        for display in self.displays:
            display.call_service("set_value", value=100)
        for ledbar in self.ledbars:
            ledbar.call_service("set_value", value=100)
