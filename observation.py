class DOMObservation:
    def __init__(self, htmlCapture):
        self.raw_obs = htmlCapture
        self._set_times()

    def _set_times(self):
        self.timestamp = self.raw_obs["timestamp"]
        self.video_timestamp = self.raw_obs["video_timestamp"]

    @property
    def observation(self):
        return self.raw_obs["html"][:500] # for demo / testing

        # return self.raw_obs["html"]
    