from gtt.gtt_display import GttDisplay


class Gtt43a(GttDisplay):
    def __init__(self, port: str):
        super().__init__(port, width=480, height=272)
