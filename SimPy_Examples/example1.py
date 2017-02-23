# coding=utf-8
__author__ = 'shahargino'

import simpy

# SimPy is a process-based discrete-event simulation framework based on standard Python.
# Its event dispatcher is based on Python’s generators and can also be used for implementing multi-agent systems.
# The components involved in SimPy are: Environment, Events and the Process functions.

# Additional information for SimPy is available at:
# (-) http://simpy.readthedocs.org/en/latest/index.html
# (-) http://stefan.sofa-rockers.org/2013/12/03/how-simpy-works


def timer(env, name, tick):
    value = yield env.timeout(tick, value=42)
    print(name, env.now, value)


def clock(env, name, tick):
    while True:
        print(name, env.now)
        yield env.timeout(tick)


simEnv = simpy.Environment()

simEnv.process(timer(simEnv, 'timer', 1))
simEnv.process(clock(simEnv, 'fast', 0.5))
simEnv.process(clock(simEnv, 'slow', 1))

simEnv.run(until=4)
