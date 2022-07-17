#!/usr/bin/env python
#  __  __      _        ___         _      _
# |  \/  |__ _(_)_ _   / __| __ _ _(_)_ __| |_
# | |\/| / _` | | ' \  \__ \/ _| '_| | '_ \  _|
# |_|  |_\__,_|_|_||_| |___/\__|_| |_| .__/\__|
#                                    |_|

import simpy
import include as inc
from Fabric import Fabric
from Auxiliary import Auxiliary
from Target_process import Target_process as Target
from Initiator_process import Initiator_process as Initiator


def main():
    """
      -----------------------------------------------------------------
    --|-------------------------------------------------------------- |     -----------------------------
    |  Initiator Process                                            | |     | Fabric                    |
    |                                                               | |     |                           |
    |  -------------------                ----------                | |     |---------         ---------|    -----------
    |  | Init. Procedure |---enqueue()--->| Queue  |<---dequeue()------------ Socket |-----    | Socket ---->| Target  |
    |  | (BW Generator)  |                | (FIFO) |    (implicit)  | |     |---------    |    ---------|    | Process |
    |  -------------------                ----------                | |     |             |      |      |    -----------
    |                                                               | |     |            ------------   |
    |  -------------------                ----------                | |     |---------   | ARBITER  |   |
    |  | Init. Procedure |---enqueue()--->| Queue  |<---dequeue()------------ Socket |---|          |   |
    |  | (BW Generator)  |                | (FIFO) |    (implicit)  | |     |---------   |          |   |
    |  -------------------                ----------                | |     |    .       |          |   |
    |          .                              .                     | |     |    .       |          |   |
    |          .                              .                     | |     |    .       ------------   |
    |          .                              .                     | |     |    .        |      |      |
    |  -------------------                ----------                | |     |---------    |    ---------|    -----------
    |  | Init. Procedure |---enqueue()--->| Queue  |<---dequeue()------------ Socket |-----    | Socket ---->| Target  |
    |  | (BW Generator)  |                | (FIFO) |    (implicit)  | |     |---------         ---------|    | Process |
    |  -------------------                ----------                |--     |                           |    -----------
    -----------------------------------------------------------------       -----------------------------
    """

    env = simpy.Environment()

    aux = Auxiliary(env, inc.global_params['DEBUG_LEVEL'])

    tb = {
        'ENV': env,
        'AUX': aux
    }

    # ========================================================================================
    aux.timestamp(__name__, "Initialization Phase started")

    # Create Initiators:
    tb['INITIATORS'] = {
        'CPU':  Initiator('CPU', inc.initiators_params['CPU'], tb),
        'PCIE': Initiator('PCIE', inc.initiators_params['PCIE'], tb)
    }

    # ------------------------------------------------------
    # Create Targets:
    tb['TARGETS'] = {
        'SRAM': Target('SRAM', inc.targets_params['SRAM'], tb),
        'ROM':  Target('ROM', inc.targets_params['ROM'], tb)
    }

    # ------------------------------------------------------
    # Create Fabric:
    tb['FABRIC'] = Fabric('DATA', inc.fabric_params, tb)

    aux.timestamp(__name__, "Initialization Phase completed")

    # ========================================================================================
    aux.timestamp(__name__, "Run Phase started")

    tb['ENV'].run(until=inc.global_params['SIMULATION_TIME_IN_CYCLES'])

    aux.timestamp(__name__, "Run Phase completed")


if __name__ == "__main__":

    main()
