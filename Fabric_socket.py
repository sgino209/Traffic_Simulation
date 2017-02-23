__author__ = 'shahargino'


import simpy


class Fabric_socket:
    """This class implements the socket core of the Fabric"""

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, parent, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.parent = parent
        self.clk_ns = parent.clk_ns
        self.granted = True

        if self.params['INIT_TGT'] == 'initiator':
            self.granted = False

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.action = self.env.process(self.run())

        for key, value in self.params.iteritems():
            self.debug(self.name, 'Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def is_initiator(self):

        return self.params['INIT_TGT'] == 'initiator'

    # ----------------------------------------------------------------------------------------
    def set_grant(self, val):

        if not self.granted and val:
            self.debug(self.name, '"%s" has been granted by Fabric Arbiter' % self.name)
        self.granted = val

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            try:
                yield self.env.timeout(self.clk_ns)

                if self.params['INIT_TGT'] == 'initiator' and self.granted:
                    self.parent.action.interrupt(
                        ["SOCKET_GRANTED", self.name[len(self.__class__.__name__ + "_"):]]
                    )

            except simpy.Interrupt as interrupt:

                int_cause = interrupt.cause

                if int_cause[0] == 'MESSAGE_FOR_TARGET':

                    if self.is_initiator():
                        self.error(self.name, 'An Initiator socket cannot receive Target messages')

                    else:
                        self.parent.action.interrupt(int_cause)
