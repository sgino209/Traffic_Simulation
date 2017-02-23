__author__ = 'shahargino'


from random import randint, choice
import simpy


class Initiator_procedure(object):
    """
        This class implements a procedure entity. Each initiator process comprises one or more such procedures

        Procedure Model (BW Generator):
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Assumptions:
         (1) BW has a repetitive pattern which consists of finite amount of transactions ("beats") per burst
         (2) Separate channels for address and data, in both directions (R/W) --> full out-of-order freedom
         (3) Bursts are randomly sparsed to fit the required average throughput
         (4) Throughput corresponds to Data only (negligible for Address) - "paid" upon Request and released upon Grant

        Burst waveform (schematic):

            Address:   O: ----< Req #0 >---< Req #1 >----------< Req #2 > ... -------< Req #N >------- | ----< Req #0 >-
                       I: -------------------------------< Gnt #0 >------< Gnt #1 >---------- ... ---------< Gnt #N >---

            Data:     I/O ----------------------------------<    D a t a   #0    >-------------<    D a t a   #1    >--

            Outstanding #: - 0 - 1 ---------- 2 ----------- 1 --- 2 ------- 1 ----- . . .

        Technical notes:
        (1) Procedure sends a Request to its corresponding Queue directly through calling queue.enqueue()
        (2) Procedure gets a Grant from its corresponding Queue through Interrupt (dequeue ringbell)
        (3) Procedure is blocked when it reaches is outstanding quota
    """

    # ----------------------------------------------------------------------------------------
    def __init__(self, name, params, clk_ns, tb):

        self.name = self.__class__.__name__ + "_" + name
        self.env = tb['ENV']
        self.params = params
        self.clk_ns = clk_ns
        self.queue = None
        self.outstanding = 0

        self.message = tb['AUX'].message
        self.debug = tb['AUX'].debug
        self.error = tb['AUX'].error

        self.action = self.env.process(self.run())

        self.debug(self.name, 'Created with params: %s' % params)

    # ----------------------------------------------------------------------------------------
    def bind_queue(self, queue):

        self.queue = queue

    # ----------------------------------------------------------------------------------------
    def get_queue_name(self):

        return self.params['QUEUE']

    # ----------------------------------------------------------------------------------------
    def send_request(self, destination, size_in_bytes, addr_gen):

        self.debug(self.name, 'Request sent (outstanding: %d out of %d)' % (self.outstanding+1, self.params['OUTSTANDING']))

        res = self.queue.enqueue(
            {'operation':  self.params['DIRECTION'],
             'src':        [self.name[len(self.__class__.__name__ + "_"):].split('_')[0], self.params['QUEUE']],
             'dst':        destination,
             'size':       size_in_bytes,
             'addr_gen':   addr_gen,
             'timestamp':  self.env.now}
        )

        if res == 'OK':
            self.outstanding += 1

    # ----------------------------------------------------------------------------------------
    def run(self):

        payload_bytes = 0

        while True:

            try:
                average_bw = 0
                payload_bytes = 0
                burst_start_time_ns = self.env.now

                for beat in range(self.params['BURST_LENGTH']):

                    yield self.env.timeout(self.clk_ns)

                    if self.outstanding < self.params['OUTSTANDING']:

                        if average_bw < self.params['THR_IN_MBPS']:

                            self.send_request(choice(['SRAM','ROM']), self.params['BURST_SIZE'], self.params['ADDRESS_GEN'])

                            elapsed_time_ns = self.env.now - burst_start_time_ns
                            average_bw = 1000.0 * payload_bytes / elapsed_time_ns

                        else:
                            self.debug(self.name, 'Stalled: reached maximum BW allocation (%.02fMBPS)' % average_bw)

                    else:
                        self.debug(self.name, 'Stalled: reached maximum outstanding allocation (%d)' % self.outstanding)

                yield self.env.timeout(randint(0, self.params['INTER_BURSTS']))

            except simpy.Interrupt as interrupt:

                int_cause = interrupt.cause

                if int_cause == 'Grant':
                    self.outstanding -= 1
                    payload_bytes += self.params['BURST_SIZE']
                    self.debug(self.name, 'Grant received (outstanding: %d out of %d)' % (self.outstanding, self.params['OUTSTANDING']))

                else:
                    self.error(self.name, 'Unknown interrupt: %s' % int_cause)
