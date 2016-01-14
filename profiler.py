import time


class Profiler:
    def __init__(self, name="_"):
        self.name = name

    # Thanks to:
    # http://preshing.com/20110924/timing-your-code-using-pythons-with-statement/
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
        print "profiled {}: {:.0f} (ms)".format(self.name, self.interval * 1000)
