import enum
import datetime

import hassapi as ha


class AirFilter3DPrinter(ha.Hass):

    class FanUsage(enum.Enum):
        DOOR_OPENED = 1,
        PRINTING = 2

    
    class FanSpeed(enum.IntEnum):
        SLOW = 1,
        NORMAL = 2,
        FAST = 3


    def initialize(self):
        self.set_namespace("homeassistant")
        self.fan_usage = {}
        self.initialize_args()
        self.initialize_listen_states()


    def initialize_args(self):
        self.enclosure_door = self.get_entity(self.args["entity_door"])
        self.fan = self.get_entity(self.args["entity_fan"])
        self.air_dirty = self.get_entity(self.args["entity_air_dirty"])
        self.printer = self.get_entity(self.args["entity_printer"])
        self.timer_door_opened = self.get_entity(self.args["entity_timer_door_opened"])
        self.timer_print_ended = self.get_entity(self.args["entity_timer_print_ended"])
        self.timestamp_print_started = self.get_entity(self.args["entity_timestamp_print_started"])
        self.timestamp_print_ended = self.get_entity(self.args["entity_timestamp_print_ended"])


    def initialize_listen_states(self):
        self.enclosure_door.listen_state(self.enclosure_door_opened, new="on")
        self.enclosure_door.listen_state(self.enclosure_door_closed, new="off")
    
        self.listen_event(self.timer_door_opened_finished, "timer.finished", entity_id = self.args["entity_timer_door_opened"])
        self.listen_event(self.timer_print_ended_finished, "timer.finished", entity_id = self.args["entity_timer_print_ended"])
        self.printer.listen_state(self.print_started, new="on")
        self.printer.listen_state(self.print_ended, old="on")


    def print_started(self, entity, attribute, old, new, cb_args):
        self.log("Print started")
        self.set_print_started_timestamp()
        if self.is_timer_print_ended_active():
            self.cancel_timer_print_ended()
        self.add_fan_usage_printing(self.FanSpeed.SLOW)
        if self.is_door_open():
            self.add_fan_usage_door_opened(self.FanSpeed.FAST)


    def print_ended(self, entity, attribute, old, new, cb_args):
        self.log("Print ended")
        print_duration = self.get_current_print_duration()
        self.log(f"Print duration {self.secs_to_str(print_duration)}")
        self.set_print_ended_timestamp()
        self.start_timer_print_ended(10*60)
        self.add_fan_usage_printing(self.FanSpeed.SLOW)
        if self.is_door_open():
            self.start_timer_door_opened(15*60)
            self.add_fan_usage_door_opened(self.FanSpeed.NORMAL)
            self.clear_air_dirty()
        else:
            self.set_air_dirty()


    def enclosure_door_opened(self, entity, attribute, old, new, cb_args):
        self.log("Enclosure door opened")
        if self.is_printing():
            if self.is_timer_door_opened_active():
                self.cancel_timer_door_opened()
            self.add_fan_usage_door_opened(self.FanSpeed.FAST)
        elif self.is_air_dirty():
            print_duration = self.get_previous_print_duration()
            # Calculated fan time after print by 1/6 of print duration
            fan_time = int(print_duration)/6
            # Check if malformed print duration
            if fan_time > 0:
                self.log(f"Previous print duration {self.secs_to_str(print_duration)}")
                # If less than 5m calculated fan time enforce 5m
                if fan_time < 5*60:
                    fan_time = 5*60
                # If more than 45m calculated fan time enforce 45m
                elif fan_time > 45*60:
                    fan_time = 45*60
            # Use fallback fan time of 10m
            else:
                fan_time = 10*60
            self.start_timer_door_opened(fan_time)
            self.add_fan_usage_door_opened(self.FanSpeed.NORMAL)
            self.clear_air_dirty()


    def enclosure_door_closed(self, entity, attribute, old, new, cb_args):
        self.log("Enclosure door closed")
        if self.is_printing():
            if self.get_current_print_duration() > 30*60:
                self.start_timer_door_opened(15*60)
            else:
                self.start_timer_door_opened(5*60)
            self.add_fan_usage_door_opened(self.FanSpeed.NORMAL)


    def timer_door_opened_finished(self, event_name, data, cb_args):
        self.log("Timer 'Door Opened' finished")
        self.rm_fan_usage_door_opened()


    def timer_print_ended_finished(self, event_name, data, cb_args):
        self.log("Timer 'Print Ended' finished")
        self.rm_fan_usage_printing()


    def is_printing(self):
        return self.printer.get_state("state") == "on"


    def is_door_open(self):
        return self.enclosure_door.get_state("state") == "on"


    def is_air_dirty(self):
        return self.air_dirty.get_state("state") == "on"

    
    def set_air_dirty(self):
        self.air_dirty.turn_on()


    def clear_air_dirty(self):
        self.air_dirty.turn_off()


    def set_print_started_timestamp(self):
        self.timestamp_print_started.call_service("set_datetime", timestamp = datetime.datetime.now().timestamp())


    def set_print_ended_timestamp(self):
        self.timestamp_print_ended.call_service("set_datetime", timestamp = datetime.datetime.now().timestamp())


    def is_timer_door_opened_active(self):
        return self.timer_door_opened.get_state("state") == "active"


    def is_timer_print_ended_active(self):
        return self.timer_print_ended.get_state("state") == "active"


    def cancel_timer_door_opened(self):
        self.log("Cancelling timer 'Door opened'")
        self.timer_door_opened.call_service("cancel")


    def cancel_timer_print_ended(self):
        self.log("Cancelling timer 'Print ended'")
        self.timer_print_ended.call_service("cancel")


    def start_timer_door_opened(self, duration):
        self.log(f"Starting timer 'Door opened' for {self.secs_to_str(duration)}")
        self.timer_door_opened.call_service("start", duration = duration)


    def start_timer_print_ended(self, duration):
        self.log(f"Starting timer 'Print ended' for {self.secs_to_str(duration)}")
        self.timer_print_ended.call_service("start", duration = duration)


    def get_previous_print_duration(self):
        print_started = self.timestamp_print_started.get_state("timestamp")
        print_ended = self.timestamp_print_ended.get_state("timestamp")
        return int(print_ended) - int(print_started)


    def get_current_print_duration(self):
        print_started = self.timestamp_print_started.get_state("timestamp")
        print_current = datetime.datetime.now().timestamp()
        return int(print_current) - int(print_started)


    def add_fan_usage_door_opened(self, fan_speed):
        self.add_fan_usage(self.FanUsage.DOOR_OPENED, fan_speed)


    def add_fan_usage_printing(self, fan_speed):
        self.add_fan_usage(self.FanUsage.PRINTING, fan_speed)

    
    def rm_fan_usage_printing(self):
        self.rm_fan_usage(self.FanUsage.PRINTING)

    
    def rm_fan_usage_door_opened(self):
        self.rm_fan_usage(self.FanUsage.DOOR_OPENED)


    def add_fan_usage(self, fan_usage, fan_speed):
        self.fan_usage[fan_usage] = fan_speed
        self.apply_fan_usage()


    def rm_fan_usage(self, fan_usage):
        if fan_usage in self.fan_usage:
            del(self.fan_usage[fan_usage])
        self.apply_fan_usage()


    def apply_fan_usage(self):
        if len(self.fan_usage) < 1:
            self.fan.call_service("turn_off")
            self.log("No fan usage, turning off")
            return
        max_speed = max(self.fan_usage.values())
        max_speed_usage = max(self.fan_usage, key=self.fan_usage.get)
        self.log(f"Setting fan level due to {max_speed_usage} to '{self.fan_speed_to_str(max_speed)}'")
        self.fan.call_service("turn_on")
        self.fan.call_service("set_preset_mode", preset_mode = self.fan_speed_to_str(max_speed))


    def fan_speed_to_str(self, fan_speed):
        switch = {
            self.FanSpeed.SLOW   : "sleep",
            self.FanSpeed.NORMAL : "auto",
            self.FanSpeed.FAST   : "manual",
        }
        return switch.get(fan_speed)


    def secs_to_str(self, seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02}"
