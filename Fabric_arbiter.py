__author__ = 'shahargino'


from random import randint


class Fabric_arbiter:
    """This class implements the arbiter core of the Fabric"""

    # ----------------------------------------------------------------------------------------
    def __init__(self, params, tb):

        self.name = self.__class__.__name__
        self.env = tb['ENV']
        self.params = params

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.initiators = tb['INITIATORS'].keys()
        if self.params['START_AT'] == 'FIRST':
            self.granted = 0
        elif self.params['START_AT'] == 'RANDOM':
            self.granted = randint(0, len(self.initiators))
        else:
            self.error(self.name, 'Invalid START_AT value: "%s"' % self.params['START_AT'])

        self.action = self.env.process(self.run())

        for key, value in self.params.items():
            self.debug(self.name, ' Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def get_granted(self):

        return list(self.initiators)[self.granted]

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            yield self.env.timeout(self.params['SLOT_LENGTH'])

            self.debug(self.name, 'Slot #%s (%d out of %d) granted' %
                       (list(self.initiators)[self.granted], self.granted, len(self.initiators)))
            self.granted = (self.granted + 1) % len(self.initiators)
