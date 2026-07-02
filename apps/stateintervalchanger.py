from itertools import cycle

import hassapi as ha

'''
Toggle between states based on given interval
Toggles entity state between given states.
Multiple states are possible with different state duration.
* State is used as state, if service is set its only used as log description what is being done
* Duration is given in seconds, is optional
* Service is optional, if set then it will call the given HA service instead of updating the state attribute of the entity


Configuration:
- name: "Cat Fountain"
  entity: "switch.cat_fountain"
  states:
    - state: "on"
      duration: 60
      service: "turn_on"
    - state: "off"
      duration: 60
      service: "turn_off"
'''
class StateIntervalChanger(ha.Hass):
    DEFAULT_DURATION = 600
    REQUIRED_FIELDS = ["name", "entity", "states"]

    def initialize(self):
        self.set_namespace("homeassistant")
        self.jobs = {}
        for job in self.args["jobs"]:
            self.initialize_each(job)

    def initialize_each(self, job):
        self.verify_state_def(job)
        entity = self.get_entity(job["entity"])
        self.jobs[job["name"]] = job
        self.jobs[job["name"]]["iterator_"] = cycle(job["states"])
        self.schedule_next(job=job["name"], old_state={"duration": 0})

    def verify_state_def(self, service):
        missing_keys = [key for key in self.REQUIRED_FIELDS if key not in service]
        if missing_keys:
            raise KeyError(f"Missing state obj fields: {', '.join(missing_keys)}")

    def handle_interval(self, **kwargs):
        job = kwargs.get("job")
        new_state = kwargs.get("new_state")
        old_state = kwargs.get("old_state")
        self.log(f"[{job}]: Switching {self.jobs[job]["entity"]} to next state '{new_state["state"]}' for {new_state.get("duration", self.DEFAULT_DURATION)}s")
        if "service" in new_state:
            self.call_service(new_state["service"], target={"entity_id": self.jobs[job]["entity"]})
        else:
            self.set_state(entity_id=self.jobs[job]["entity"], state=new_state["state"])
        self.schedule_next(job, new_state)

    def schedule_next(self, job, old_state):
        duration = self.DEFAULT_DURATION;
        if "duration" in old_state:
            duration = old_state["duration"]
        self.run_in(self.handle_interval, delay=duration, job=job, new_state=next(self.jobs[job]["iterator_"]), old_state=old_state)
