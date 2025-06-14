import enum
import datetime
import numbers

import hassapi as ha


class AirFilter3DPrinter(ha.Hass):

    class FanUsage(enum.Enum):
        DOOR_OPENED = 1,
        PRINTING    = 2,
        ENCLOSURE_PM25 = 3,
        STOREROOM_PM25 = 4
    
    class FanSpeed(enum.IntEnum):
        OFF    = 0,
        SLOW   = 1,
        NORMAL = 2,
        FAST   = 3

    class PM25Thresholds(enum.IntEnum):
        OFF    = -1,
        LOW    = 5,
        HIGH   = 25

    def initialize(self):
        self.set_namespace("homeassistant")
        self.fan_usage = {}
        self.initialize_args()
        self.initialize_listen_states()
        enclosure_pm25 = self.enclosure_air_pm25.get_state("state")
        storeroom_pm25 = self.storeroom_air_pm25.get_state("state")
        self.set_enclosure_pm25_fan_speed(self.get_pollution_level(enclosure_pm25), enclosure_pm25)
        self.set_storeroom_pm25_fan_speed(self.get_pollution_level(storeroom_pm25), storeroom_pm25)

    def initialize_args(self):
        self.fan = self.get_entity(self.args["entity_fan"])
        self.printer = self.get_entity(self.args["entity_printer"])
        self.enclosure_door = self.get_entity(self.args["entity_enclosure_door"])
        self.enclosure_air_pm25 = self.get_entity(self.args["entity_enclosure_air_pm25"])
        self.enclosure_air_dirty = self.get_entity(self.args["entity_enclosure_air_dirty"])
        self.storeroom_air_pm25 = self.get_entity(self.args["entity_storeroom_air_pm25"])
        self.timer_enclosure_door_opened = self.get_entity(self.args["entity_timer_enclosure_door_opened"])
        self.timer_print_ended = self.get_entity(self.args["entity_timer_print_ended"])
        self.timestamp_print_started = self.get_entity(self.args["entity_timestamp_print_started"])
        self.timestamp_print_ended = self.get_entity(self.args["entity_timestamp_print_ended"])

    def initialize_listen_states(self):
        self.enclosure_door.listen_state(self.enclosure_door_opened, new="on")
        self.enclosure_door.listen_state(self.enclosure_door_closed, new="off")
        self.enclosure_air_pm25.listen_state(self.enclosure_air_pm25_changed)
        self.storeroom_air_pm25.listen_state(self.storeroom_air_pm25_changed)
        self.listen_event(self.timer_enclosure_door_opened_finished, "timer.finished", entity_id = self.args["entity_timer_enclosure_door_opened"])
        self.listen_event(self.timer_print_ended_finished, "timer.finished", entity_id = self.args["entity_timer_print_ended"])
        self.printer.listen_state(self.print_started, new="printing")
        self.printer.listen_state(self.print_ended, old="printing")

    def print_started(self, entity, attribute, old, new, cb_args):
        self.log("Print started")
        self.set_print_started_timestamp()
        if self.is_timer_print_ended_active():
            self.cancel_timer_print_ended()
        self.set_fan_usage(self.FanUsage.PRINTING, self.FanSpeed.SLOW)
        if self.is_enclosure_door_open():
            self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.FAST)

    def print_ended(self, entity, attribute, old, new, cb_args):
        self.log("Print ended")
        print_duration = self.get_current_print_duration()
        self.log(f"Print duration {self.secs_to_str(print_duration)}")
        self.set_print_ended_timestamp()
        self.start_timer_print_ended(10*60)
        self.set_fan_usage(self.FanUsage.PRINTING, self.FanSpeed.SLOW)
        if self.is_enclosure_door_open():
            self.start_timer_enclosure_door_opened(15*60)
            self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.NORMAL)
            self.clear_enclosure_air_dirty()
        else:
            self.set_enclosure_air_dirty()

    def get_pollution_level(self, pm25):
        try:
            pm25 = int(pm25)
        except ValueError:
            pass
        if isinstance(pm25, numbers.Number) and pm25 >= self.PM25Thresholds.HIGH:
            return self.PM25Thresholds.HIGH
        elif isinstance(pm25, numbers.Number) and pm25 >= self.PM25Thresholds.LOW:
            return self.PM25Thresholds.LOW
        else:
            return self.PM25Thresholds.OFF

    def set_enclosure_pm25_fan_speed(self, level, pm25):
        switch = { self.PM25Thresholds.OFF: self.FanSpeed.OFF }
        if self.is_enclosure_door_open():
            switch[self.PM25Thresholds.LOW] = self.FanSpeed.NORMAL
            switch[self.PM25Thresholds.HIGH] = self.FanSpeed.FAST
        else:
            switch[self.PM25Thresholds.LOW] = self.FanSpeed.SLOW
            switch[self.PM25Thresholds.HIGH] = self.FanSpeed.SLOW
        fan_speed = switch.get(level)
        already_applied = self.FanUsage.ENCLOSURE_PM25 in self.fan_usage
        if (not already_applied and fan_speed != self.FanSpeed.OFF) or (already_applied and self.fan_usage[self.FanUsage.ENCLOSURE_PM25] != fan_speed):
            self.log(f"Detected enclosure pollution level: {self.pollution_to_str(level)} (PM2.5: {pm25} MG/m3)")
            self.set_fan_usage(self.FanUsage.ENCLOSURE_PM25, switch.get(level))

    def set_storeroom_pm25_fan_speed(self, level, pm25):
        switch = { self.PM25Thresholds.OFF:  self.FanSpeed.OFF,
                   self.PM25Thresholds.LOW:    self.FanSpeed.NORMAL,
                   self.PM25Thresholds.HIGH:   self.FanSpeed.FAST }
        fan_speed = switch.get(level)
        already_applied = self.FanUsage.STOREROOM_PM25 in self.fan_usage
        if (not already_applied and fan_speed != self.FanSpeed.OFF) or (already_applied and self.fan_usage[self.FanUsage.STOREROOM_PM25] != fan_speed):
            self.log(f"Detected storeroom pollution level: {self.pollution_to_str(level)} (PM2.5: {pm25} MG/m3)")
            self.set_fan_usage(self.FanUsage.STOREROOM_PM25, switch.get(level))

    def enclosure_air_pm25_changed(self, entity, attribute, old, new, cb_args):
        old_level = self.get_pollution_level(old)
        new_level = self.get_pollution_level(new)
        if old_level != new_level:
            self.set_enclosure_pm25_fan_speed(new_level, new)

    def storeroom_air_pm25_changed(self, entity, attribute, old, new, cb_args):
        old_level = self.get_pollution_level(old)
        new_level = self.get_pollution_level(new)
        if old_level != new_level:
            self.set_storeroom_pm25_fan_speed(new_level, new)

    def enclosure_door_opened(self, entity, attribute, old, new, cb_args):
        self.log("Enclosure door opened")
        pm25 = self.enclosure_air_pm25.get_state("state")
        self.set_enclosure_pm25_fan_speed(self.get_pollution_level(pm25), pm25)
        if self.is_printing():
            if self.is_timer_enclosure_door_opened_active():
                self.cancel_timer_enclosure_door_opened()
            self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.FAST)
        elif self.is_enclosure_air_dirty():
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
            self.start_timer_enclosure_door_opened(fan_time)
            self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.NORMAL)
            self.clear_enclosure_air_dirty()

    def enclosure_door_closed(self, entity, attribute, old, new, cb_args):
        self.log("Enclosure door closed")
        pm25 = self.enclosure_air_pm25.get_state("state")
        self.set_enclosure_pm25_fan_speed(self.get_pollution_level(pm25), pm25)
        if self.is_printing():
            if self.get_current_print_duration() > 30*60:
                self.start_timer_enclosure_door_opened(15*60)
            else:
                self.start_timer_enclosure_door_opened(5*60)
            self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.NORMAL)

    def timer_enclosure_door_opened_finished(self, event_name, data, cb_args):
        self.log("Timer 'Enclosure Door Opened' finished")
        self.set_fan_usage(self.FanUsage.DOOR_OPENED, self.FanSpeed.OFF)

    def timer_print_ended_finished(self, event_name, data, cb_args):
        self.log("Timer 'Print Ended' finished")
        self.set_fan_usage(self.FanUsage.PRINTING, self.FanSpeed.OFF)

    def is_printing(self):
        return self.printer.get_state("state") == "printing"

    def is_enclosure_door_open(self):
        return self.enclosure_door.get_state("state") == "on"

    def is_enclosure_air_dirty(self):
        return self.enclosure_air_dirty.get_state("state") == "on"
    
    def set_enclosure_air_dirty(self):
        self.enclosure_air_dirty.turn_on()

    def clear_enclosure_air_dirty(self):
        self.enclosure_air_dirty.turn_off()

    def set_print_started_timestamp(self):
        self.timestamp_print_started.call_service("set_datetime", timestamp = datetime.datetime.now().timestamp())

    def set_print_ended_timestamp(self):
        self.timestamp_print_ended.call_service("set_datetime", timestamp = datetime.datetime.now().timestamp())

    def is_timer_enclosure_door_opened_active(self):
        return self.timer_enclosure_door_opened.get_state("state") == "active"

    def is_timer_print_ended_active(self):
        return self.timer_print_ended.get_state("state") == "active"

    def cancel_timer_enclosure_door_opened(self):
        self.log("Cancelling timer 'Enclosure Door opened'")
        self.timer_enclosure_door_opened.call_service("cancel")

    def cancel_timer_print_ended(self):
        self.log("Cancelling timer 'Print ended'")
        self.timer_print_ended.call_service("cancel")

    def start_timer_enclosure_door_opened(self, duration):
        self.log(f"Starting timer 'Enclosure Door opened' for {self.secs_to_str(duration)}")
        self.timer_enclosure_door_opened.call_service("start", duration = duration)

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

    def set_fan_usage(self, fan_usage, fan_speed):
        if not fan_usage in self.fan_usage or self.fan_usage[fan_usage] != fan_speed:
            if fan_speed == self.FanSpeed.OFF:
                self.rm_fan_usage(fan_usage)
            else:
                self.fan_usage[fan_usage] = fan_speed
            self.apply_fan_usage()

    def rm_fan_usage(self, fan_usage):
        if fan_usage in self.fan_usage:
            del(self.fan_usage[fan_usage])

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

    def pollution_to_str(self, level):
        switch = {
                self.PM25Thresholds.OFF    : "OFF",
                self.PM25Thresholds.LOW    : "LOW",
                self.PM25Thresholds.HIGH   : "HIGH"
        }
        return switch.get(level)

    def secs_to_str(self, seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02}"
