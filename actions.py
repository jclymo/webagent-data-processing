def get_target_type(target_html):
    def is_dropdown():
        dropdown_terms = [
            '<select', '<option', 'dropdown', 'role="listbox"', 'role="menu"']
        return any(s in target_html for s in dropdown_terms)

        
    def is_combobox():
        combobox_terms = [
            'combobox', 'combo-box', 'role="combobox"',
            'aria-autocomplete', 'aria-haspopup="listbox"',
            'autocomplete']
        return any(s in target_html for s in combobox_terms)
        
    def is_aria():
        return "aria" in target_html
    
    if not is_dropdown():
        return False
    if not is_combobox():
        return "dropdown"
    if not is_aria():
        return "combobox"
    return "aria combobox"

def event_to_action(event):
    if event["target"]["tag"] == "SELECT":
        return SelectOption(event)
    elif event["target"]["tag"] == "INPUT":
        return Fill(event)
    else:
        return Click(event)
    # if event["type"] == "click":
    #     target_html = event["target"]["outerHTMLSnippet"].lower()
    #     target_type = get_target_type(target_html)
    #     if target_type == "dropdown":
    #         return SelectOption(event)
    #     if target_type == "aria combobox":
    #         return [Press(event), Click(event)]
    #     return Click(event)
        
    # if event["type"] == "submit":
    #     return Click(event)
    # if event["type"] == "input":
    #     return Fill(event)

class Action:
    def __init__(self, event):
        self.event = event
        self.from_url = event["url"]
        self._set_times()
        self._set_target()

    def _set_times(self):
        self.timestamp = self.event["timestamp"]
        self.video_timestamp = self.event["video_timestamp"]

    def _set_target(self):
        self.data_bid = self.event["target"]["bid"]

class Fill(Action):
    def __init__(self, event):
        super().__init__(event)
        self._set_value()
    
    def _set_value(self):
        self.value = self.event["target"]["value"]

    def _set_time(self):
        super()._set_time()
        self.end_timestamp = self.timestamp
        self.timestamp = self.event["start_timestamp"]
        
    @property
    def bg_action(self):
        return {
            "action": "fill",
            "data_bid": self.data_bid,
            "value": self.value
        }
        # return f"fill(data_bid='{self.data_bid}', text='{self.text}')"

class Click(Action):
    def __init__(self, event):
        super().__init__(event)

    @property
    def bg_action(self):
        return {
            "action": "click",
            "data_bid": self.data_bid,
        }
        # return f"click(data_bid='{self.data_bid}')"
    
class Press(Action):
    def __init__(self, event):
        super().__init__(event)
   
    @property
    def bg_action(self):
        return {
            "action": "press",
            "data_bid": self.data_bid,
        }
        # return f"press(data_bid='{self.data_bid}', '')"
    
class SelectOption(Action):
    def __init__(self, event):
        super().__init__(event)
        self._set_option()

    def _set_option(self):
        self.option = self.event['target']['value']
   
    @property
    def bg_action(self):
        return {
            "action": "select_option",
            "data_bid": self.data_bid,
            "option": self.option
        }
        # return f"select_option(data_bid='{self.data_bid}', option='{self.option}')"