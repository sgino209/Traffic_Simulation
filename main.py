__author__ = 'shahargino'

# '||\   /||`                          .|'''|                              ||
#  ||\\.//||           ''              ||                    ''            ||
#  ||     ||   '''|.   ||  `||''|,     `|'''|, .|'', '||''|  ||  '||''|, ''||''
#  ||     ||  .|''||   ||   ||  ||      .   || ||     ||     ||   ||  ||   ||
# .||     ||. `|..||. .||. .||  ||.     |...|' `|..' .||.   .||.  ||..|'   `|..'
#                                                                 ||
#                                                                .||

import include as inc
from Auxiliary import Auxiliary
from Fabric import Fabric
from Initiator_process import Initiator_process as Initiator
from Target_process import Target_process as Target
import simpy


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

    #------------------------------------------------------
    # Create Targets:
    tb['TARGETS'] = {
        'SRAM': Target('SRAM', inc.targets_params['SRAM'], tb),
        'ROM':  Target('ROM', inc.targets_params['ROM'], tb)
    }

    #------------------------------------------------------
    # Create Fabric:
    tb['FABRIC'] = Fabric('DATA', inc.fabric_params, tb)

    aux.timestamp(__name__, "Initialization Phase completed")

    # ========================================================================================
    aux.timestamp(__name__, "Run Phase started")

    tb['ENV'].run(until=inc.global_params['SIMULATION_TIME_IN_CYCLES'])

    aux.timestamp(__name__, "Run Phase completed")

main()