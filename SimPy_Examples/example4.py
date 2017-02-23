# coding=utf-8
__author__ = 'shahargino'

import simpy

# This example demonstrates a shared resource modelling, using request() API.

# Example model:  an electric car can be charged when parking, and may drive only when charging is completed
#                 The car will now drive to a battery charging station (BCS) and request one of its two charging spots.
#                 If both of these spots are currently in use, it waits until one of them becomes available again.
#                 It then starts charging its battery and leaves the station afterwards.

# Note that the first two cars can start charging immediately after they arrive at the BCS, while cars 2 an 3 have to wait.

# Additional information for SimPy is available at:
# (-) http://simpy.readthedocs.org/en/latest/simpy_intro/shared_resources.html


def car(env, name, bcs, driving_time, charge_duration):
    # Simulate driving to the BCS
    yield env.timeout(driving_time)

    # Request one of its charging spots
    print('%s arriving at %d' % (name, env.now))
    with bcs.request() as req:
        yield req

        # Charge the battery
        print('%s starting to charge at %s' % (name, env.now))
        yield env.timeout(charge_duration)
        print('%s leaving the bcs at %s' % (name, env.now))


simEnv = simpy.Environment()

simBCS = simpy.Resource(simEnv, capacity=2)

for i in range(4):
    simEnv.process(car(simEnv, 'Car %d' % i, simBCS, i*2, 5))

simEnv.run(until=15)
