__author__ = 'shahargino'


import simpy


class Target_process(object):
    """This class implements a Target entity, such as SRAM, ROM, etc., to be used in simulation"""

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.clk_ns = 1000.0 / self.params['FREQUENCY_MHZ']

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.action = self.env.process(self.run())

        for key, value in self.params.items():
            self.debug(self.name, 'Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            try:
                yield self.env.timeout(self.clk_ns)

            except simpy.Interrupt as interrupt:

                int_cause = interrupt.cause

                if int_cause[0] == 'MESSAGE_FOR_TARGET':
                    self.debug(self.name, 'Message Received: "%s"' % int_cause[1])

                    # ACK:
                    int_cause[2].action.interrupt(
                        ['ACK_FROM_TARGET', self.name, int_cause[1]['src'][0]]
                    )
