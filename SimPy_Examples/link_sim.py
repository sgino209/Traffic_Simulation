#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Created by Shahar Gino at April 2019, sgino209@gmail.com
# Link simulation for an early uarch exploration.
# Based on Python SimPy framework.
#
#    -------------------     ------------------------------------------------------     ------------------
#    |   Producer      |     |  Link (DUT)                                        |     |   Consumer     |
#    |                 |     |                  -------------------------------   |     |                |
#    | ( bitstream     |     |   -----------    | Pop Process                 |   |     | ( parametrized |
#    |   distribution, |--1----->| Buffer  |--->| ( depends on "pack state" ) |-----1-->|   latency )    |
#    |   parameterized |     |   | (Store) |    |                             |   |     |                |
#    |   rate )        |     |   ----^------    |   ---------------------     |   |     |                |
#    |                 |     |       |          |   | pack FSM          |     |   |     ------------------
#    -------------------     |       ---------------| ( depends on      |     |   |
#                            |                  |   |   buffer fullness |     |   |
#                            |                  |   |   and pop rate )  |     |   |
#                            |                  |   ---------------------     |   |
#                            |                  -------------------------------   |
#                            ------------------------------------------------------
#
# ------------------------------------------------------------------------------------------------------------------

import sys
import simpy
import getopt
from time import time
from pandas import Series
from numpy import arange, mean
import matplotlib.pyplot as plt
from random import normalvariate

global debug_en

# ------------------------------------------------------------------------------------------------------------------

class Struct:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

run_mode_t = Struct(
    Both = 0,
    Bypass = 1,
    NonBypass = 2
)

# ------------------------------------------------------------------------------------------------------------------

def usage():
    print('link_sim.py [-s <simulation_time_ns>]\n')
    print('')
    print('Optional flags:')
    print('  --debug_en')
    print('  --plots_en')
    print('  --run_mode')
    print('')
    print('  --producer_idle_ps=<value_mean;value_std>')
    print('  --producer_burst=<value_window;value_utilization>')
    print('')
    print('  --freq_ghz=<value>')
    print('  --buffer_size=<value>')
    print('  --avg_bw_1_gbps=<value>')
    print('  --avg_bw_2_gbps=<value>')
    print('  --avg_bw_4_gbps=<value>')
    print('  --avg_bw_trns_short=<value1;value2;value4>')
    print('  --avg_bw_trns_long="<value1;value2;value4>"')
    print('  --avg_bw_cyc_short="<value1;value2;value4>"')
    print('  --avg_bw_cyc_long=<value1;value2;value4>')
    print('  --data_avl_1_trns_num=<value>')
    print('  --data_avl_2_trns_num=<value>')
    print('  --data_avl_1_cyc=<value>')
    print('  --data_avl_2_cyc=<value>')
    print('  --fsm_delay_cyc=<value>')
    print('  --fsm_highperf_mode=<value>')

# ------------------------------------------------------------------------------------------------------------------

def debug(msg):
    if debug_en:
        print("[DEBUG] " + msg)

def info(msg):
    print("[INFO] " + msg)

# ------------------------------------------------------------------------------------------------------------------

class Link(object):
    """This class represents the propagation through the Link"""

    def __init__(self, env, args, dummy=False):
        self.env = env
        self.args = args
        self.dummy = dummy
        self.cyc_step_ps = int(1e3/args.freq_ghz)
        self.consumer_quota = 0
        self.consumer_bw = []
        self.enqueue_while_idle = False
        self.last_mark_cyc = 0
        self.last_dequeue_cyc = -1
        self.fsm_update_stack = []
        self.link_state = []
        self.buffer_fullness = []
        
        self.cyc_curr = 0
        self.data_avl_cnt = {}
        self.data_avl_cond = {}
        for data_avl_type in ('avl1', 'avl2'):
            self.data_avl_cnt[data_avl_type] = 0
            self.data_avl_cond[data_avl_type] = False
        
        self.avg_bw_long_cond = False
        self.avg_bw_cond = {}
        self.avg_bw_list = {}
        self.avg_bw_win_start_cyc = {}
        for avg_bw_type in ('short', 'long'):
            self.avg_bw_cond[avg_bw_type] = False
            self.avg_bw_list[avg_bw_type] = [1] * args.avg_bw_cyc[avg_bw_type]['4PACK']
            self.avg_bw_win_start_cyc[avg_bw_type] = 0
            self.init_avg_bw(avg_bw_type)
        
        self.state = "IDLE"
        self.store = simpy.Store(env, capacity=args.buffer_size)  # exceeding the Store capacity causes a backpressure
        self.cycle_process = self.env.process(self.cycle())

    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def cycle(self):
                
        fsm_busy = False
        
        while True:
            yield self.env.timeout(self.cyc_step_ps)
        
            # UpScale:
            for data_avl_type in ('avl1', 'avl2'):
                self.data_avl_cond[data_avl_type] = False
                if self.state != "4PACK":
                    if len(self.store.items) >= self.args.data_avl_trns_num[data_avl_type]:
                        self.data_avl_cnt[data_avl_type] += 1
                    else:
                        self.data_avl_cnt[data_avl_type] = 0

                    if self.data_avl_cnt[data_avl_type] >= self.args.data_avl_cyc[data_avl_type]:
                        self.data_avl_cond[data_avl_type] = True
                        self.data_avl_cnt[data_avl_type] = 0

            # DownGrade:
            for avg_bw_type in ('short', 'long'):
                self.avg_bw_cond[avg_bw_type] = False
                avg_bw_win_cyc = self.cyc_curr - self.avg_bw_win_start_cyc[avg_bw_type]
                if avg_bw_win_cyc < len(self.avg_bw_list[avg_bw_type]):
                    self.avg_bw_list[avg_bw_type][avg_bw_win_cyc] = int(self.cyc_curr == self.last_dequeue_cyc)
                if self.state != "IDLE":
                    if avg_bw_win_cyc >= self.args.avg_bw_cyc[avg_bw_type][self.state]:
                        self.init_avg_bw(avg_bw_type)
                    elif (avg_bw_win_cyc > 0):
                        self.avg_bw_cond[avg_bw_type] = sum(self.avg_bw_list[avg_bw_type]) < self.args.avg_bw_trns[avg_bw_type][self.state]
           
            # FSM State Update:
            if len(self.fsm_update_stack) > 0:
            
                fsm_update_cyc = self.fsm_update_stack[0][0] 
            
                if fsm_update_cyc <= self.cyc_curr:
                    new_state = self.fsm_update_stack[0][1] 
                    old_state = self.state
                    self.state = new_state 
                    self.fsm_update_stack.pop()
                    for avg_bw_type in ('short', 'long'):
                        self.init_avg_bw(avg_bw_type )
                    fsm_busy = False
                    if transition:
                        self.link_state.append(transition)
                    debug("time=%dps - Link FSM Update:  %s --> %s" % (self.env.now, old_state, new_state))
            
            # FSM State Evaluation (+registeration):
            else:
                not_empty_cond = len(self.store.items) > 0 or self.enqueue_while_idle
                upscale_cond = self.data_avl_cond['avl1'] or self.data_avl_cond['avl2']
                downgrade_cond = self.avg_bw_cond['short'] and self.avg_bw_cond['long'] and not upscale_cond

                new_state = self.state
                    
                transition = None

                if self.state == "IDLE":
                    self.enqueue_while_idle = False
                    not_empty_cond = len(self.store.items) > 0
                    if not_empty_cond:
                        if self.args.fsm_highperf_mode:
                            new_state = "4PACK"
                            transition = "IDLE_to_4PACK"
                        else:
                            new_state = "1PACK"
                            transition = "IDLE_to_1PACK"

                elif self.state == "1PACK":
                    if upscale_cond:
                        if self.args.fsm_highperf_mode:
                            new_state = "4PACK"
                            transition = "1PACK_to_4PACK"
                        else:
                            new_state = "2PACK"
                            transition = "1PACK_to_2PACK"
                    elif downgrade_cond:
                        new_state = "IDLE"
                        transition = "1PACK_to_IDLE"

                elif self.state == "2PACK":
                    if upscale_cond:
                        new_state = "4PACK"
                        transition = "2PACK_to_4PACK"
                    elif downgrade_cond:
                        new_state = "1PACK"
                        transition = "2PACK_to_1PACK"

                elif self.state == "4PACK":
                  if downgrade_cond:
                      new_state = "2PACK"
                      transition = "4PACK_to_2PACK"
                
                if new_state != self.state:
                    self.fsm_update_stack.append((self.cyc_curr+self.args.fsm_delay_cyc, new_state))
            
            # Collecting Stats:
            if not self.dummy:
                if transition and not fsm_busy:
                    fsm_busy = True
                self.link_state.append(self.state)
                self.buffer_fullness.append(len(self.store.items))

            # Cycle Incrementation:
            self.cyc_curr += self.cyc_step_ps

    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def init_avg_bw(self, avg_bw_type):
        avg_bw_win_cyc = self.cyc_curr - self.avg_bw_win_start_cyc[avg_bw_type]
        if (avg_bw_win_cyc > 0):
            avg_bw_gbps = (1e3/8.0) * sum(self.avg_bw_list[avg_bw_type]) / (avg_bw_win_cyc * self.cyc_step_ps)
            self.avg_bw_win_start_cyc[avg_bw_type] = self.cyc_curr
            self.avg_bw_cond[avg_bw_type] = False
            self.last_dequeue_cyc = -1
            if self.state != "IDLE":
                self.avg_bw_list[avg_bw_type] = [1] * self.args.avg_bw_cyc[avg_bw_type][self.state]
            debug("time=%dps - Link AvgBW %s Reset, BW=%.2fGBps" % (self.env.now, avg_bw_type, avg_bw_gbps))

    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def enqueue(self, value):
        self.store.put(value)

        if self.state == "IDLE":
            self.enqueue_while_idle = True

        debug('time=%dps - Link enqueue: cyc=%d, data=%d, capacity=%d, data_avl_1=%s, data_avl_2=%s, avg_bw_long=%s, avg_bw_short=%s, state=%s' %
            (self.env.now, self.cyc_curr, value, len(self.store.items), self.data_avl_cond['avl1'], self.data_avl_cond['avl2'], self.avg_bw_cond['long'], self.avg_bw_cond['short'], self.state))

    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def can_dequeue(self):
        idle_ps = (1e3/8.0) / self.args.avg_bw_4_gbps
        if self.state == "1PACK":
            idle_ps = (1e3/8.0) / self.args.avg_bw_1_gbps
        elif self.state == "2PACK":
            idle_ps = (1e3/8.0) / self.args.avg_bw_2_gbps
        elif self.state == "4PACK":
            idle_ps = (1e3/8.0) / self.args.avg_bw_4_gbps

        return self.env.timeout(idle_ps)

    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def dequeue(self):
        self.last_dequeue_cyc = self.cyc_curr
        return self.store.get()
    
    # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    def mark_rate(self, rate):
        self.consumer_quota += 1
        for k in range(self.cyc_curr-self.last_mark_cyc):
            self.consumer_bw.append(rate)
        self.last_mark_cyc = self.cyc_curr
    
# ------------------------------------------------------------------------------------------------------------------

def producer(env, link, args):
    """A process which randomly generates bitstream"""
    msg = 0
    window_pos = 0

    if args.utilization > 0:

        while True:
          
            idle_ps = -1 
            if args.window > 0:
                window_pos = env.now % args.window
                if window_pos >= int(args.utilization * args.window):
                    idle_ps = int((1-args.utilization) * args.window)
    
            if idle_ps < 0:
                idle_ps = normalvariate(args.idle_ps_mean, args.idle_ps_std)
            
            # Wait for next transmission, then enqueue:
            idle_ps = max(1,idle_ps)
            rate_gbps = (1e3/8.0) / idle_ps
            debug('time=%dps - Producer sent: data=%d, idle=%.2fps (=%.2fGB/s)' % (env.now, msg, idle_ps, rate_gbps))
            yield env.timeout(idle_ps)
            link.enqueue(msg)
            msg += 1

# ------------------------------------------------------------------------------------------------------------------

def consumer(env, link, args):
    """A process which consumes bitstream"""
    t = 0
    while True:
        # Receive bitstream from link:
        if not link.dummy:
            yield link.can_dequeue()
        if link.dummy or link.state != 'IDLE':
            msg = yield link.dequeue()
            delta_ps = (env.now - t)
            rate_gbps = (1e3/8.0) / delta_ps
            link.mark_rate(rate_gbps)
            t = env.now
            debug('time=%dps - Consumer %d received: data=%d, delta=%.2fps (=%.2fGB/s)' % (env.now, link.dummy, msg, delta_ps, rate_gbps))

# ------------------------------------------------------------------------------------------------------------------

def print_params(link_params, producer_params, consumer_params):

    info('')
    info('Link Parameters:')
    for k,v in link_params.__dict__.items():
        info('  %s = %s' % (k,str(v)))

    info('')
    info('Producer Parameters:')
    for k,v in producer_params.__dict__.items():
        info('  %s = %s' % (k,str(v)))
    
    info('')
    info('Consumer Parameters:')
    for k,v in consumer_params.__dict__.items():
        info('  %s = %s' % (k,str(v)))

# ------------------------------------------------------------------------------------------------------------------

def main(argv):

    t0 = time()
    
    info('Link Unit-Level Simulation')
    
    # Default parameters:
    sys_params = Struct(
        sim_duration_ns = 2.5,
        run_mode = run_mode_t.Both,
        debug_en = False,
        plots_en = False
    )
    
    producer_params = Struct(
        idle_ps_mean = 4,   # BW ~ (1e3/8)/2
        idle_ps_std = 0.05,
        window = 1200,
        utilization = 0.7,
    )
    
    consumer_params = Struct(
        plots_en = False
    )
    
    link_params = Struct(
        freq_ghz = 1000,
        buffer_size = 50,
        avg_bw_1_gbps = 64/4.0,
        avg_bw_2_gbps = 64/2.0,
        avg_bw_4_gbps = 64/1.0,
        avg_bw_trns = { 'short': { '1PACK':4,  '2PACK':4,   '4PACK':4 },
                        'long':  { '1PACK':10, '2PACK':10, '4PACK':10 } },
        avg_bw_cyc = { 'short': { '1PACK':4,  '2PACK':15,  '4PACK':25 },
                       'long':  { '1PACK':60, '2PACK':60, '4PACK':60 } },
        data_avl_trns_num = { 'avl1':5, 'avl2':20 },
        data_avl_cyc = { 'avl1':15, 'avl2':2 },
        fsm_delay_cyc = 35,
        fsm_highperf_mode = True,
        plots_en = False
    )

    global debug_en
    debug_en = False
    
    # -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- ..

    # User-Arguments parameters (overrides Defaults):
    try:
        opts, user_args = getopt.getopt(argv, "hs:",
                                        ["debug_en", "plots_en",
                                         "producer_idle_ps=", "producer_burst=",
                                         "run_mode=",
                                         "freq_ghz=", "buffer_size=", "avg_bw_1_gbps=", "avg_bw_2_gbps=", "avg_bw_4_gbps=",
                                         "avg_bw_trns_short=", "avg_bw_trns_long=", "avg_bw_cyc_short=", "avg_bw_cyc_long=", "data_avl_1_trns_num=", 
                                         "data_avl_2_trns_num=", "data_avl_1_cyc=", "data_avl_2_cyc=", "fsm_delay_cyc=", "fsm_highperf_mode="
                                        ])
        for opt, user_arg in opts:
            
            if opt == '-h':
                usage()
                sys.exit()

            elif opt in "-s":
                sys_params.sim_duration_ns = float(user_arg)
            elif opt in "--debug_en":
                sys_params.debug_en = True
            elif opt in "--plots_en":
                sys_params.plots_en = True

            elif opt in "--producer_idle_ps":
                producer_params.idle_ps_mean = float(user_arg.split(';')[0])
                producer_params.idle_ps_std = float(user_arg.split(';')[1])
            elif opt in "--producer_burst":
                producer_params.window = int(user_arg.split(';')[0])
                producer_params.utilization = float(user_arg.split(';')[1])
            
            elif opt in "--run_mode":
                sys_params.run_mode = int(user_arg)
            
            elif opt in "--freq_ghz":
                link_params.freq_ghz = float(user_arg)
            elif opt in "--buffer_size":
                link_params.buffer_size = float(user_arg)
            elif opt in "--avg_bw_1_gbps":
                link_params.avg_bw_1_gbps = float(user_arg)
            elif opt in "--avg_bw_2_gbps":
                link_params.avg_bw_2_gbps = float(user_arg)
            elif opt in "--avg_bw_4_gbps":
                link_params.avg_bw_4_gbps = float(user_arg)
            elif opt in "--avg_bw_trns_short":
                link_params.avg_bw_trns['short']['1PACK'] = int(user_arg.split(';')[0])
                link_params.avg_bw_trns['short']['2PACK'] = int(user_arg.split(';')[1])
                link_params.avg_bw_trns['short']['4PACK'] = int(user_arg.split(';')[2])
            elif opt in "--avg_bw_trns_long":
                link_params.avg_bw_trns['long']['1PACK'] = int(user_arg.split(';')[0])
                link_params.avg_bw_trns['long']['2PACK'] = int(user_arg.split(';')[1])
                link_params.avg_bw_trns['long']['4PACK'] = int(user_arg.split(';')[2])
            elif opt in "--avg_bw_cyc_short":
                link_params.avg_bw_cyc['short']['1PACK'] = int(user_arg.split(';')[0])
                link_params.avg_bw_cyc['short']['2PACK'] = int(user_arg.split(';')[1])
                link_params.avg_bw_cyc['short']['4PACK'] = int(user_arg.split(';')[2])
            elif opt in "--avg_bw_cyc_long":
                link_params.avg_bw_cyc['long']['1PACK'] = int(user_arg.split(';')[0])
                link_params.avg_bw_cyc['long']['2PACK'] = int(user_arg.split(';')[1])
                link_params.avg_bw_cyc['long']['4PACK'] = int(user_arg.split(';')[2])
            elif opt in "--data_avl_1_trns_num":
                link_params.data_avl_trns_num['avl1'] = int(user_arg)
            elif opt in "--data_avl_2_trns_num":
                link_params.data_avl_trns_num['avl2'] = int(user_arg)
            elif opt in "--data_avl_1_cyc":
                link_params.data_avl_cyc['avl1'] = int(user_arg)
            elif opt in "--data_avl_2_cyc":
                link_params.data_avl_cyc['avl2'] = int(user_arg)
            elif opt in "--fsm_delay_cyc":
                link_params.fsm_delay_cyc = int(user_arg)
            elif opt in "--fsm_highperf_mode":
                link_params.fsm_highperf_mode = bool(int(user_arg))

    except getopt.GetoptError:
        usage()
        sys.exit(2)
                
    debug_en = sys_params.debug_en
    consumer_params.plots_en = sys_params.plots_en
    link_params.plots_en = sys_params.plots_en

    # -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- ..
    
    # Setup and start the simulation
    info('')
    info('Run for %s ns' % sys_params.sim_duration_ns)
    print_params(link_params, producer_params, consumer_params)
    
    simEnv = simpy.Environment()
       
    dual_mode  = (sys_params.run_mode == run_mode_t.Both)
    dummy_mode = (sys_params.run_mode == run_mode_t.Bypass)
    func_mode  = (sys_params.run_mode == run_mode_t.NonBypass) 

    simLink = Link(simEnv, link_params, dummy_mode)
    simEnv.process(producer(simEnv, simLink, producer_params))
    simEnv.process(consumer(simEnv, simLink, consumer_params))
    
    if dual_mode:
        
        simLink_dummy = Link(simEnv, link_params, 1)
        simEnv.process(producer(simEnv, simLink_dummy, producer_params))
        simEnv.process(consumer(simEnv, simLink_dummy, consumer_params))

    simEnv.run(until=sys_params.sim_duration_ns*1e3)
   
    # -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- ..

    # Plottings:
    if sys_params.plots_en:

         info('')
         info('Plotting...')

         fig = plt.figure()
         plt.rcParams.update({'font.size': 8})

         ax = plt.subplot(421) if dual_mode else plt.subplot(321)
         plt.title('Link State over Time')
         plt.ylabel('State')
         link_state_reduced = []
         transitions = len([ state for state in simLink.link_state if "_to_" in state ])
         for state in simLink.link_state:
             if state == "IDLE":
                 link_state_reduced.append(0)
             elif state == "1PACK":
                 link_state_reduced.append(1)
             elif state == "2PACK":
                 link_state_reduced.append(2)
             elif state == "4PACK":
                 link_state_reduced.append(3)
         ax.step(arange(len(link_state_reduced)), link_state_reduced)
         plt.ylim([0,5.5])
         plt.yticks(arange(4), ('IDLE', '1PACK', '2PACK', '4PACK'))
         #ax.locator_params(numticks=4)
         
         ax = plt.subplot(423) if dual_mode else plt.subplot(323)
         plt.title('Buffer Fullness over Time')
         plt.ylabel('Fullness')
         if simLink.buffer_fullness:
             plt.ylim([0,max(simLink.buffer_fullness)+1])
         ax.step(arange(len(simLink.buffer_fullness)), simLink.buffer_fullness)

         ax = plt.subplot(425) if dual_mode else plt.subplot(325)#, sharex=ax)
         plt.title('Consumer BW over Time')
         plt.ylabel('BW [GB/s]')
         plt.ylim([0,max(simLink.consumer_bw)+1])
         plt.plot(arange(len(simLink.consumer_bw)), simLink.consumer_bw)
         if not dual_mode:
             plt.xlabel('Time [cyc]')
         
         if dual_mode:
             plt.subplot(427)
             plt.title('Consumer BW over Time (Bypass)')
             plt.ylabel('BW [GB/s]')
             plt.xlabel('Time [cyc]')
             plt.ylim([0,max(simLink_dummy.consumer_bw)+1])
             plt.plot(arange(len(simLink_dummy.consumer_bw)), simLink_dummy.consumer_bw)

         ax = plt.subplot(422) if dual_mode else plt.subplot(322)
         plt.title('Link State Histogram')
         plt.ylabel('State')
         if simLink.link_state:
             plt.hist(link_state_reduced+[4]*transitions, align="left", bins=5)
         plt.xticks(arange(5), ('IDLE', '1PACK', '2PACK', '4PACK', 'SWT'))
         plt.grid()
         
         ax = plt.subplot(424) if dual_mode else plt.subplot(324)
         plt.title('Buffer Fullness Histogram')
         plt.ylabel('Fullness')
         if simLink.buffer_fullness:
             plt.hist(simLink.buffer_fullness, align="left")
         ax.set_xlim(left=0)
         plt.grid()

         ax = plt.subplot(426) if dual_mode else plt.subplot(326)
         plt.title('Consumer BW Histogram')
         plt.ylabel('BW [GB/s]')
         plt.hist(simLink.consumer_bw, align="left")
         ax.set_xlim(left=0)
         plt.grid()
    
         if dual_mode:
             ax = plt.subplot(428)
             plt.title('Consumer BW Histogram (Bypass)')
             plt.ylabel('BW [GB/s]')
             plt.hist(simLink_dummy.consumer_bw, align="left")
             ax.set_xlim(left=0)
             plt.grid()

         plt.subplots_adjust(hspace=0.8, wspace=0.4)

         fig.savefig('link_result.png', dpi=600)

    # -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- .. -- ..
    
    t1 = time()
    t_elapsed_sec = t1 - t0

    info('')
    producer_mean_bw = (1e3/8.0)/producer_params.idle_ps_mean * producer_params.utilization
    info('Producer Demanded BW:')
    info('   Idle~N(%.2fps,%.2f) --> MeanBW=%.2fGB/s  ( = (1e3/8.0)/%.2f x %.2f )' % (producer_params.idle_ps_mean, producer_params.idle_ps_std, producer_mean_bw, producer_params.idle_ps_mean, producer_params.utilization))
    info('')
    info('Consumer Achieved BW:')
    sum_ = 0
    cnt_ = 0
    consumer_bw_hist = plt.hist(simLink.consumer_bw)
    for k in range(len(consumer_bw_hist[0])):
        bin_val = consumer_bw_hist[1][k]
        info('   %.2f GB/s --> x %d' % (bin_val, consumer_bw_hist[0][k]))
        sum_ += bin_val * consumer_bw_hist[0][k]
        cnt_ += consumer_bw_hist[0][k]
    info('   Mean = %.2f GB/s (=%d/%d)' % (float(sum_/cnt_), sum_, cnt_))
    info('   Quota = %d bits' % simLink.consumer_quota)
    info('')
    if dual_mode:
        info('Consumer (Bypass) Achieved BW:')
        sum_ = 0
        cnt_ = 0
        consumer_bw_hist = plt.hist(simLink_dummy.consumer_bw)
        bin_size = max(consumer_bw_hist[1]) / 10
        for k in range(len(consumer_bw_hist[0])):
            bin_val = consumer_bw_hist[1][k]
            info('   %.2f GB/s --> x %d' % (bin_val, consumer_bw_hist[0][k]))
            sum_ += bin_val * consumer_bw_hist[0][k]
            cnt_ += consumer_bw_hist[0][k]
        info('   Mean = %.2f GB/s (=%d/%d)' % (float(sum_/cnt_), sum_, cnt_))
        info('   Quota = %d bits' % simLink_dummy.consumer_quota)
        info('')
    if not dummy_mode:
        buffer_fullness_hist = plt.hist(simLink.buffer_fullness)
        info('Link State Historgam:')
        power_time = 0
        power_sum = 0.0
        link_state_hist = Series(simLink.link_state).value_counts()
        for state,freq in link_state_hist.items():
            info('   %s --> x %d' % (state,freq))
            power_wht = 0
            if state == "IDLE":
                power_time += freq
            if state == "1PACK":
                power_wht = 1
                power_time += freq
            elif state == "2PACK":
                power_wht = 2
                power_time += freq
            elif state == "4PACK":
                power_wht = 4
                power_time += freq
            elif state == "IDLE_to_4PACK":
                power_wht = simLink.args.fsm_delay_cyc * 4
            elif state == "IDLE_to_1PACK":
                power_wht = simLink.args.fsm_delay_cyc * 1
            elif state == "1PACK_to_2PACK":
                power_wht = simLink.args.fsm_delay_cyc * 2
            elif state == "2PACK_to_4PACK":
                power_wht = simLink.args.fsm_delay_cyc * 4
            power_sum += freq * power_wht
        power_normed = float(power_sum)/power_time
        info('')
        info('Normalized Power = %.2f (=%d/%d)' % (power_normed , power_sum, power_time))
        info('')
    
        sum_ = 0
        cnt_ = 0
        info('Link Buffer Fullness Historgam:')
        for k in range(len(buffer_fullness_hist[0])):
            info('   %d --> x %d' % (buffer_fullness_hist[1][k], buffer_fullness_hist[0][k]))
            sum_ += buffer_fullness_hist[1][k] * buffer_fullness_hist[0][k]
            cnt_ += buffer_fullness_hist[0][k]
        info('   Mean = %.2f GB/s' % float(sum_/cnt_))
        info('')
    
    info('Simulation Completed! (%.2f sec)' % t_elapsed_sec)
    info('')

# ==================================================================================================================

if __name__ == "__main__":

    main(sys.argv[1:])

