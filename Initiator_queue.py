__author__ = 'shahargino'


import simpy


class Initiator_queue(object):
    """This class implements a queue entity, to be used in simulation"""

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, clk_ns, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.clk_ns = clk_ns
        self.store = simpy.Store(self.env)
        self.fullness = 0
        self.overflow = 0
        self.underflow = 0
        self.procedures = {}
        self.depth = params['DEPTH']
        self.width = params['WIDTH']

        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.action = self.env.process(self.run())

        for key, value in self.params.iteritems():
            self.debug(self.name, 'Created with %s = %s' % (key, value))

    # ----------------------------------------------------------------------------------------
    def enqueue(self, request):

        if self.fullness <= (self.depth * self.width) - request['size']:
            self.fullness += request['size']
            self.overflow = 0
            self.store.put(request)

            self.debug(self.name, 'Enqueue: %s ' % request)
            self.debug(self.name, 'Items currently in queue (%d):' % len(self.store.items))
            for item in self.store.items:
                self.debug(self.name, item)
            return 'OK'

        else:
            self.overflow = 1
            self.debug(self.name, "Overflow:  fullness=%d, request=%d" % (self.fullness, request['size']))

        return 'OVF'

    # ----------------------------------------------------------------------------------------
    def dequeue(self, caller=None):

        if len(self.store.items):

            self.debug(self.name, 'Dequeue started')

            request = yield self.store.get()

            self.debug(self.name, 'Dequeue completed: %s' % request)
            self.debug(self.name, 'Items currently in queue (%d):' % len(self.store.items))
            for item in self.store.items:
                self.debug(self.name, item)

            self.fullness -= request['size']
            self.underflow = 0

            self.debug(self.name, 'Sending "Grant" to procedure "%s"' % request['src'])
            self.procedures[request['src'][1]].action.interrupt('Grant')

            if caller is not None:
                caller.action.interrupt(
                    ['INITIATOR_DEQUEUE', request]
                )

        else:
            self.underflow = 1
            self.debug(self.name, "Underflow:  fullness=%d" % self.fullness)

    # ----------------------------------------------------------------------------------------
    def is_overflow(self):

        return self.overflow

    # ----------------------------------------------------------------------------------------
    def is_underflow(self):

        return self.underflow

    # ----------------------------------------------------------------------------------------
    def is_empty(self):

        return self.fullness == 0

    # ----------------------------------------------------------------------------------------
    def get_fullness(self):

        return self.fullness

    # ----------------------------------------------------------------------------------------
    def get_quota(self):

        return self.width * self.depth

    # ----------------------------------------------------------------------------------------
    def bind_procedure(self, procedure_name, procedure):

        self.procedures[procedure_name] = procedure

    # ----------------------------------------------------------------------------------------
    def run(self):

        while True:

            yield self.env.timeout(self.clk_ns)
