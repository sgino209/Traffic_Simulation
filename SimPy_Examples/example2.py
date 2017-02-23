__author__ = 'shahargino'

import simpy

# This example demonstrates process interaction scheme.

# Example model:  an electric car can be charged when parking, and may drive only when charging is completed

# Additional information for SimPy is available at:
# (-) http://simpy.readthedocs.org/en/latest/simpy_intro/process_interaction.html


class Car(object):
    def __init__(self, env):
        self.env = env
        # Start the run process everytime an instance is created.
        self.action = self.env.process(self.run())

    def run(self):
        while True:
            print('Start parking and charging at %d' % self.env.now)
            charge_duration = 5
            # We yield the process that process() returns to wait for it to finish
            yield self.env.process(self.charge(charge_duration))

            # The charge process has finished and we can start driving again.
            print('Start driving at %d' % self.env.now)
            trip_duration = 2
            yield self.env.timeout(trip_duration)

    def charge(self, duration):
        yield self.env.timeout(duration)


simEnv = simpy.Environment()

simCar = Car(simEnv)

simEnv.run(until=15)
