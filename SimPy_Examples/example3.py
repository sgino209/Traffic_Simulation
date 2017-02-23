# coding=utf-8
__author__ = 'shahargino'

import simpy

# This example demonstrates process interaction scheme with interrupts.

# Example model:  an electric car can be charged when parking, and may drive only when charging is completed
#                 This time (comparing to example2) we don’t want to wait until the electric vehicle is fully charged,
#                 but want to interrupt the charging process and just start driving instead.

# Additional information for SimPy is available at:
# (-) http://simpy.readthedocs.org/en/latest/simpy_intro/process_interaction.html


def driver(env, car):
    yield env.timeout(3)
    car.action.interrupt('spam')


class Car(object):
    def __init__(self, env):
        self.env = env
        self.action = self.env.process(self.run())

    def run(self):
        while True:
            print('Start parking and charging at %d' % self.env.now)
            charge_duration = 5
            # We may get interrupted while charging the battery
            try:
                yield self.env.process(self.charge(charge_duration))
            except simpy.Interrupt as interrupt:
                # When we received an interrupt, we stop charging and switch to the "driving" state
                cause = interrupt.cause
                print('Was interrupted due to "%s". Hope, the battery is full enough ...' % cause)

            print('Start driving at %d' % self.env.now)
            trip_duration = 2
            yield self.env.timeout(trip_duration)

    def charge(self, duration):
        yield self.env.timeout(duration)


simEnv = simpy.Environment()

simCar = Car(simEnv)
simEnv.process(driver(simEnv, simCar))

simEnv.run(until=15)
