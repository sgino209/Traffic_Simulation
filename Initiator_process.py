__author__ = 'shahargino'

import simpy
from Initiator_procedure import Initiator_procedure
from Initiator_queue import Initiator_queue


class Initiator_process(object):
    """
        This class implements an Initiator process entity, such as CPU, GPU, etc., to be used in simulation

         Notes:
         ~~~~~~
         (1) Procedures examples:  - Write channel and Read channel
                                   - Multiple cores
                                   - etc.

         (2) Queue sharing is supported, i.e. different procedures may share same queues
    """

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.clk_ns = 1000.0 / self.params['FREQUENCY_MHZ']

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.procedures = {}
        for procedure_name, procedure_params in self.params['PROCEDURES'].items():
            self.procedures[procedure_name] = Initiator_procedure(name + "_" + procedure_name, procedure_params, self.clk_ns, tb)

        self.queues = {}
        for queue_name, queue_params in self.params['QUEUES'].items():
            self.queues[queue_name] = Initiator_queue(name + "_" + queue_name, queue_params, self.clk_ns, tb)

        for procedure_name, procedure in self.procedures.items():
            queue = self.queues[procedure.get_queue_name()]
            procedure.bind_queue(queue)
            queue.bind_procedure(procedure_name, procedure)

        self.action = self.env.process(self.run())

        for key, value in self.params.items():
            self.debug(self.name, 'Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def get_queues(self):

        return self.queues

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            try:

                yield self.env.timeout(self.clk_ns)

                for queue_name, queue in self.queues.items():
                    self.debug(self.name, 'Queue "%s" fullness: %d / %d' % (queue_name, queue.get_fullness(), queue.get_quota()))

            except simpy.Interrupt as interrupt:

                int_cause = interrupt.cause

                if int_cause[0] == 'ACK_FROM_TARGET':
                    self.debug(self.name, 'ACK received from %s' % int_cause[1])

                else:
                    self.error(self.name, 'Invalid interrupt "%s"' % int_cause[0])