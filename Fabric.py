__author__ = 'shahargino'

import simpy
from Fabric_socket import Fabric_socket
from Fabric_arbiter import Fabric_arbiter


class Fabric(object):
    """This class implements the Fabric entity (e.g. AF, AXI, etc.), to be used in simulation"""

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.clk_ns = 1000.0 / self.params['FREQUENCY_MHZ']

        self.initiators = {}
        self.queues = {}
        for initiator_name, initiator in tb['INITIATORS'].items():
            self.initiators[initiator_name] = initiator
            self.queues[initiator_name] = initiator.get_queues()

        self.targets = {}
        for target_name, target in tb['TARGETS'].items():
            self.targets[target_name] = target

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.sockets = {}
        for socket_name, socket_params in self.params['SOCKETS'].items():
            self.sockets[socket_name] = Fabric_socket(socket_name, socket_params, self, tb)

        self.arbiter = Fabric_arbiter(self.params['ARBITER'], tb)

        self.action = self.env.process(self.run())

        for key, value in self.params.items():
            self.debug(self.name, 'Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            try:
                yield self.env.timeout(self.clk_ns)

                # Manage "Grants" for initiator sockets:
                granted = self.arbiter.get_granted()

                for socket_name, socket in self.sockets.items():
                    if socket.is_initiator():
                        socket.set_grant(socket_name == granted)

            # Pass requests to their corresponding targets:
            except simpy.Interrupt as interrupt:

                int_cause = interrupt.cause

                if int_cause[0] == 'INITIATOR_DEQUEUE':
                    self.debug(self.name, 'Messaged received in Fabric: "%s"' % int_cause[1])
                    self.sockets[int_cause[1]['dst']].action.interrupt(
                        ['MESSAGE_FOR_TARGET', int_cause[1]]
                    )

                elif int_cause[0] == 'SOCKET_GRANTED':
                    for queue_name, queue in self.queues[int_cause[1]].items():
                        self.debug(self.name, "Dequeue from %s" % queue_name)
                        self.env.process( queue.dequeue(self) )

                elif int_cause[0] == 'MESSAGE_FOR_TARGET':
                    self.debug(self.name, 'Passing the message to Target socket')
                    _tmp = [int_cause[0], int_cause[1], self]
                    self.targets[int_cause[1]['dst']].action.interrupt(_tmp)

                elif int_cause[0] == 'ACK_FROM_TARGET':
                    self.debug(self.name, 'ACK received from Target "%s"' % int_cause[1])
                    self.initiators[int_cause[2]].action.interrupt(
                        ['ACK_FROM_TARGET', int_cause[1]]
                    )

                else:
                    self.error(self.name, 'Invalid interrupt "%s"' % int_cause[0])
