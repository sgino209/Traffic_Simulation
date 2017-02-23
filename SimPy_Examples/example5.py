# coding=utf-8
__author__ = 'shahargino'

import simpy

# This example demonstrates how 2 processes may send messages one to each other through a native queue ("store()")

# Additional information for SimPy is available at:
# (-) http://simpy.readthedocs.org/en/latest/examples/latency.html


SIM_DURATION = 100


class Cable(object):
    """This class represents the propagation through a cable."""
    def __init__(self, env, delay):
        self.env = env
        self.delay = delay
        self.store = simpy.Store(env)

    def latency(self, value):
        yield self.env.timeout(self.delay)
        self.store.put(value)

    def put(self, value):
        self.env.process(self.latency(value))

    def get(self):
        return self.store.get()


def sender(env, cable):
    """A process which randomly generates messages."""
    while True:
        # wait for next transmission
        yield env.timeout(5)
        cable.put('Sender sent this at %d' % env.now)


def receiver(env, cable):
    """A process which consumes messages."""
    while True:
        # Get event for message pipe
        msg = yield cable.get()
        print('Received this at %d while %s' % (env.now, msg))


# Setup and start the simulation
print('Event Latency')
simEnv = simpy.Environment()

simCable = Cable(simEnv, 10)
simEnv.process(sender(simEnv, simCable))
simEnv.process(receiver(simEnv, simCable))

simEnv.run(until=SIM_DURATION)
