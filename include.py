__author__ = 'shahargino'

# ========================================================================================
global_params = {

    'DEBUG_LEVEL':  1,                      # 0 = no debug , 1 = debug prints enabled

    'SIMULATION_TIME_IN_CYCLES':  100       # Simulation time
}

# ========================================================================================
fabric_params = {

    # --------------------------
    'FREQUENCY_MHZ':  200,

    # --------------------------
    'ARBITER': {
        'POLICY':       'ROUND_ROBIN',  # ROUND_ROBIN
        'SLOT_LENGTH':  5,              # in fabric's cycles
        'START_AT':     'FIRST'         # FIRST / RANDOM
    },

    # --------------------------
    'SOCKETS': {

        'CPU': {
            'PROTOCOL':  'AXI',
            'RD_WR_CH':  {'both', 64},
            'INIT_TGT':  'initiator',
            'LATENCIES':  {
                'CPU':   0,
                'PCIE':  1,
                'SRAM':  1,
                'ROM':   1
            }
        },

        'PCIE': {
            'PROTOCOL':  'AXI',
            'RD_WR_CH':  {'both', 64},
            'INIT_TGT':  'initiator',
            'LATENCIES':  {
                'CPU':   0,
                'PCIE':  1,
                'SRAM':  1,
                'ROM':   1
            }
        },

        'SRAM': {
            'PROTOCOL':  'AXI',
            'RD_WR_CH':  {'both', 64},
            'INIT_TGT':  'target',
            'LATENCIES':  {}

        },


        'ROM': {
            'PROTOCOL':  'AXI',
            'RD_WR_CH':  {'both', 64},
            'INIT_TGT':  'target',
            'LATENCIES':  {}
        }
    }
}

# ========================================================================================
initiators_params = {

    # --------------------------
    'CPU': {
        'FREQUENCY_MHZ':  400,

        'BUS': {
            'PROTOCOL':       'AXI',
            'WR_EN':          1,
            'WR_LATENCY':     0,
            'RD_EN':          1,
            'RD_LATENCY':     0
        },

        'PROCEDURES': {

            'AXI_WR': {
                'DIRECTION':     'write',   # read / write
                'BURST_LENGTH':  8,         # Transfsers per burst, 1..16 (aka beats or cells)
                'BURST_SIZE':    64,        # Bytes in Transfer, 1..128
                'INTER_BURSTS':  10,        # Maximal latency between bursts, in clock cycles
                'THR_IN_MBPS':   100,       # in MBps, affects the beats sparsity
                'OUTSTANDING':   10,        # Maximal amount of outstanding transactions
                'ADDRESS_GEN':   'random',  # random / raster
                'BUS_WIDTH':     8,         # Bus width, in bytes
                'QUEUE':         'AXI_WR'
            },

            'AXI_RD': {
                'DIRECTION':     'read',    # read / write
                'BURST_LENGTH':  16,        # Transfsers per burst, 1..16 (aka beats or cells)
                'BURST_SIZE':    32,        # Bytes in Transfer, 1..128
                'INTER_BURSTS':  10,        # Maximal latency between bursts, in clock cycles
                'THR_IN_MBPS':   100,       # in MBps, affects the beats sparsity
                'OUTSTANDING':   10,        # Maximal amount of outstanding transactions
                'ADDRESS_GEN':   'raster',  # random / raster
                'BUS_WIDTH':     8,         # Bus width, in bytes
                'QUEUE':         'AXI_RD'
            }
        },

        'QUEUES': {

            'AXI_WR': {
                'DEPTH':  32,  # Number of entries
                'WIDTH':  4    # Bytes per entry
            },

            'AXI_RD': {
                'DEPTH':  32,  # Number of entries
                'WIDTH':  4    # Bytes per entry
            }
        }
    },

    # --------------------------
    'PCIE': {
        'FREQUENCY_MHZ':  200,

        'BUS': {
            'PROTOCOL':       'AXI',
            'WR_EN':          1,
            'WR_LATENCY':     0,
            'RD_EN':          1,
            'RD_LATENCY':     0
        },

        'PROCEDURES': {

            'AXI_WR': {
                'DIRECTION':     'write',   # read / write
                'BURST_LENGTH':  8,         # Transfsers per burst, 1..16 (aka beats or cells)
                'BURST_SIZE':    64,        # Bytes in Transfer, 1..128
                'INTER_BURSTS':  10,        # Maximal latency between bursts, in clock cycles
                'THR_IN_MBPS':   100,       # in MBps, affects the beats sparsity
                'OUTSTANDING':   10,        # Maximal amount of outstanding transactions
                'ADDRESS_GEN':   'random',  # random / raster
                'BUS_WIDTH':     8,         # Bus width, in bytes
                'QUEUE':         'AXI_WR'
            },

            'AXI_RD': {
                'DIRECTION':     'read',    # read / write
                'BURST_LENGTH':  16,        # Transfsers per burst, 1..16 (aka beats or cells)
                'BURST_SIZE':    32,        # Bytes in Transfer, 1..128
                'INTER_BURSTS':  10,        # Maximal latency between bursts, in clock cycles
                'THR_IN_MBPS':   100,       # in MBps, affects the beats sparsity
                'OUTSTANDING':   10,        # Maximal amount of outstanding transactions
                'ADDRESS_GEN':   'raster',  # random / raster
                'BUS_WIDTH':     8,         # Bus width, in bytes
                'QUEUE':         'AXI_RD'
            }
        },

        'QUEUES': {

            'AXI_WR': {
                'DEPTH':  32,  # Number of entries
                'WIDTH':  4    # Bytes per entry
            },

            'AXI_RD': {
                'DEPTH':  32,  # Number of entries
                'WIDTH':  4    # Bytes per entry
            }
        }
    }
}

# ========================================================================================
targets_params = {

    # --------------------------
    'SRAM': {
        'FREQUENCY_MHZ':  200,

        'BUS': {
            'PROTOCOL':    'AXI',
            'WR_EN':       1,
            'WR_LATENCY':  0,
            'RD_EN':       1,
            'RD_LATENCY':  0
        },

        'PENALTIES':      {}
    },

    # --------------------------
    'ROM': {
        'FREQUENCY_MHZ':  200,

        'BUS': {
            'PROTOCOL':    'AXI',
            'WR_EN':       0,
            'WR_LATENCY':  0,
            'RD_EN':       1,
            'RD_LATENCY':  0
        },

        'PENALTIES':      {}
    },
}
