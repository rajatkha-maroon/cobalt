'''Tests for the cluster system component.

'''

from nose import *
import os
import Cobalt
import TestCobalt

#set and override config file prior to importing cluster_system
#the "init on import" behavior is probably a "broken" thing to be doing.
#perhaps this should all be moved to a mandatory configure method called
#by the component init? --PMR

STD_COBALT_CONFIG_FILE_NAME = 'cobalt-cluster-test.conf'
STD_COBALT_CONFIG_FILE = '''
[cluster_system]
hostfile = cobalt.hostfile
simulation_mode = True
run_remote = false

[system]
size = 4

[logging]
to_syslog = True
syslog_level = DEBUG

'''
STD_COBALT_HOSTFILE_NAME = 'cobalt.hostfile'
STD_COBALT_HOSTFILE = '''vs1.test
vs2.test
vs3.test
vs4.test
'''

def gen_std_config_files():
    '''Generate a standard Cobalt conf and hostfile for testing.

    '''
    f = open(STD_COBALT_CONFIG_FILE_NAME, 'w')
    f.write(STD_COBALT_CONFIG_FILE)
    f.close()

    f = open(STD_COBALT_HOSTFILE_NAME, 'w')
    f.write(STD_COBALT_HOSTFILE)
    f.close()

    Cobalt.CONFIG_FILES[0] = STD_COBALT_CONFIG_FILE_NAME
gen_std_config_files()

import Cobalt.Components.cluster_base_system
import Cobalt.Components.cluster_system
import time


def teardown_module():
    '''remove standard conf files.'''
    os.remove(STD_COBALT_CONFIG_FILE_NAME)
    os.remove(STD_COBALT_HOSTFILE_NAME)


def get_basic_job_dict():
    return {'jobid': 1,
            'nodes': 1,
            'queue': 'default',
            'walltime': 10,
            'user': 'testuser'
            }

class TestClusterSystem(object):
    '''Test core cluster system functionality'''

    def __init__(self):
        self.cluster_system = None
        self.full_node_set = set(['vs1.test', 'vs2.test', 'vs3.test', 'vs4.test'])

    def setup(self):
        '''Ensure cluster system exists for all tests.  Refresh the setup between tests'''
        self.cluster_system = Cobalt.Components.cluster_system.ClusterSystem()

    def teardown(self):
        '''Free cluster system base class between tests.  Forces reinitialization.'''
        del self.cluster_system

    def test_init_drain_time_no_jobs(self):
        #Test initilaization of drain times with no currently running jobs.
        end_times = []
        self.cluster_system.node_end_time_dict = {-1:['foo']}
        self.cluster_system.init_drain_times(end_times)
        assert -1 not in self.cluster_system.node_end_time_dict.keys(), "ERROR: node_end_time_dict not reset!"
        assert set(self.cluster_system.node_end_time_dict[0]) ^ self.full_node_set == set([]), \
                "ERROR: Mismatch between node_end_time_dict and full node set for no jobs test! Generated: %s\nExpected %s\n" % \
                (set(self.cluster_system.node_end_time_dict[0]), self.full_node_set)

    def test_init_drain_time_single_node_job(self):
        #Check drain time initialization with single running job
        end_time = int(time.time()) + 300
        end_times = [[['vs2.test'], end_time]]
        self.cluster_system.node_end_time_dict = {-1:['foo']}
        self.cluster_system.init_drain_times(end_times)
        assert -1 not in self.cluster_system.node_end_time_dict.keys(), "ERROR: node_end_time_dict not reset!"
        assert set(self.cluster_system.node_end_time_dict[0]) ^ self.full_node_set == set(['vs2.test']), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time 0!\nGenerated %s\nExpected %s\n" % \
                (set(self.cluster_system.node_end_time_dict[0]) ^ self.full_node_set, set(['vs2.test']))
        assert set(self.cluster_system.node_end_time_dict[end_time]) ^ self.full_node_set == \
                set(['vs1.test', 'vs3.test', 'vs4.test']), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time %s!\nGenerated %s\nExpected %s\n" % \
                (end_time, set(self.cluster_system.node_end_time_dict[0]),set(['vs2.test']))

    def test_init_drain_time_multiple_jobs(self):
        #Check drain time initialization for multiple running jobs.
        now = int(time.time())
        end_time_list = [now + 300, now + 400, now + 600]
        end_times = [[['vs2.test'], end_time_list[0]], [['vs1.test', 'vs3.test'], end_time_list[1]],
                [['vs4.test'], end_time_list[2]]]
        self.cluster_system.node_end_time_dict = {-1:['foo']}
        self.cluster_system.init_drain_times(end_times)
        assert -1 not in self.cluster_system.node_end_time_dict.keys(), "ERROR: node_end_time_dict not reset!"
        assert set(self.cluster_system.node_end_time_dict[0]) == set([]), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time 0!\nGenerated %s\nExpected %s\n" % \
                (set(self.cluster_system.node_end_time_dict[0]), set([]))
        assert set(self.cluster_system.node_end_time_dict[end_time_list[0]]) == set(['vs2.test']), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time %s!\nGenerated %s\nExpected %s\n" % \
                (end_time_list[0], set(self.cluster_system.node_end_time_dict[end_time_list[0]]), set(['vs2.test']))
        assert set(self.cluster_system.node_end_time_dict[end_time_list[1]]) == set(['vs1.test', 'vs3.test']), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time %s!\nGenerated %s\nExpected %s\n" % \
                (end_time_list[1], set(self.cluster_system.node_end_time_dict[end_time_list[1]]), set(['vs1.test', 'vs3.test']))
        assert set(self.cluster_system.node_end_time_dict[end_time_list[2]]) == set(['vs4.test']), \
                "ERROR: Mismatch between node_end_time_dict and full_node set for time %s!\nGenerated %s\nExpected %s\n" % \
                (end_time_list[2], set(self.cluster_system.node_end_time_dict[end_time_list[2]]), set(['vs4.test']))

    def test__find_job_location_basic_job_no_drain(self):
        #Check that find job locations works with a basic job, clean resources, and sets job to run.
        now = int(time.time())
        job = get_basic_job_dict()
        job['nodes'] = 4

        self.cluster_system.init_drain_times([]) #All resources are clear
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)

        assert ready_to_run, "ERROR: Job not ready to run on empty system"
        assert new_drain_time == 0, "Job ready to run, drain time must be 0"
        assert best_location != {}, "ERROR: Ready to run, but we have no best location."
        assert best_location == {'1':['vs2.test', 'vs4.test', 'vs1.test', 'vs3.test']}, "ERROR: Missing nodes from best location," \
            " got: %s" % best_location

    def test__find_job_location_job_all_down_locs(self):
        #ensure no attempt to run if all nodes are down.
        now = int(time.time())
        job = get_basic_job_dict()
        self.cluster_system.nodes_down(list(self.full_node_set))
        assert self.cluster_system.down_nodes ^ self.full_node_set == set([]), "all nodes were not marked down."
        self.cluster_system.init_drain_times([])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)

        assert not ready_to_run, "ERROR: marked ready to run when running impossible."
        assert new_drain_time == 0, "ERROR: No draining possible for all down hardware."
        assert best_location == {}, "ERROR: Best locaion found when no best loc possible! Tried %s" % best_location

    def test__find_job_location_job_too_few_locs(self):
        #ensure we dont' try to schedule a job when we have too few locations available.
        now = int(time.time())
        job = get_basic_job_dict()
        job['nodes'] = 4
        self.cluster_system.nodes_down(['vs1.test'])
        self.cluster_system.init_drain_times([])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)

        assert not ready_to_run, "ERROR: marked ready to run when running impossible."
        assert new_drain_time == 0, "ERROR: No draining possible for this set of down hardware."
        assert best_location == {}, "ERROR: Best locaion found when no best loc possible! Tried %s" % best_location

    def test__find_job_location_drain_for_job(self):
        now = int(time.time())
        end_time = now + 600
        job = get_basic_job_dict()
        job['nodes'] = 4
        self.cluster_system.running_nodes.update(['vs1.test'])
        self.cluster_system.init_drain_times([[['vs1.test'], end_time]])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)
        assert not ready_to_run, "ERROR: marked ready to run when running impossible."
        assert new_drain_time == end_time, "ERROR: Expected new drain time of %d but got %d." % (end_time, new_drain_time)
        assert best_location == {'1':['vs2.test', 'vs4.test', 'vs1.test', 'vs3.test']}, \
                "ERROR: Unexpected best location selection.  Generated %s." % best_location

    def test__find_job_location_drain_soonest(self):
        now = int(time.time())
        end_time_list = [ now + 600, now + 700]
        job = get_basic_job_dict()
        job['nodes'] = 2
        self.cluster_system.running_nodes.update(['vs2.test', 'vs3.test', 'vs4.test'])
        self.cluster_system.init_drain_times([[['vs2.test'], end_time_list[0]], [['vs3.test', 'vs4.test'], end_time_list[1]]])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)
        assert not ready_to_run, "ERROR: job selected to run with insufficient resources."
        assert new_drain_time == end_time_list[0], "ERROR: Expected drain time %d, got %d instead" % (end_time_list[0],
                new_drain_time)
        assert best_location == {'1':['vs2.test', 'vs1.test']}, "ERROR: Expected best location: %s\nGot:%s" % \
                ({'1':['vs2.test', 'vs1.test']}, best_location)

    def test__find_job_location_drain_sufficient(self):
        now = int(time.time())
        end_time_list = [ now + 600, now + 700]
        job = get_basic_job_dict()
        job['nodes'] = 3
        self.cluster_system.running_nodes.update(['vs2.test', 'vs3.test', 'vs4.test'])
        self.cluster_system.init_drain_times([[['vs2.test'], end_time_list[0]], [['vs3.test', 'vs4.test'], end_time_list[1]]])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now)
        assert not ready_to_run, "ERROR: job selected to run with insufficient resources."
        assert new_drain_time == end_time_list[1], "ERROR: Expected drain time %d, got %d instead" % (end_time_list[1],
                new_drain_time)
        assert best_location == {'1':['vs2.test', 'vs1.test', 'vs3.test']}, "ERROR: Expected best location: %s\nGot:%s" % \
                ({'1':['vs2.test', 'vs1.test', 'vs3.test']}, best_location)

    def test__find_job_location_select_backfill_job(self):
        now = int(time.time())
        end_time_list = [ now + 600, now + 700]
        job = get_basic_job_dict()
        job['walltime'] = 5
        self.cluster_system.running_nodes.update(['vs2.test', 'vs3.test', 'vs4.test'])
        self.cluster_system.init_drain_times([[['vs2.test'], end_time_list[0]], [['vs3.test', 'vs4.test'], end_time_list[1]]])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now, end_time_list[0])
        assert ready_to_run, "ERROR: job not backfilled."
        assert new_drain_time == 0, "ERROR: Expected drain time %d, got %d instead" % (0,
                new_drain_time)
        assert best_location == {'1':['vs1.test']}, "ERROR: Expected best location: %s\nGot:%s" % \
                ({'1':['vs1.test']}, best_location)

    def test__find_job_location_backfill_too_few_locs(self):
        #Jobs that are longer than the backfill window should not be selected.
        now = int(time.time())
        end_time_list = [ now + 600, now + 700]
        job = get_basic_job_dict()
        job['walltime'] = 15
        self.cluster_system.running_nodes.update(['vs2.test', 'vs3.test', 'vs4.test'])
        self.cluster_system.init_drain_times([[['vs2.test'], end_time_list[0]], [['vs3.test', 'vs4.test'], end_time_list[1]]])
        best_location, new_drain_time, ready_to_run = self.cluster_system._find_job_location(job, now, end_time_list[0])
        assert not ready_to_run, "ERROR: No jobs should be backfilled."
        assert new_drain_time == 0, "ERROR: Expected drain time %d, got %d instead" % (0,
                new_drain_time)
        assert best_location == {}, "ERROR: Expected best location: %s\nGot:%s" % \
                ({}, best_location)

    #Test find_job_location.  Take list of jobs and end times, and find a valid location.
    def test_find_job_locaiton_single_valid_job(self):
        jobs = [get_basic_job_dict()]
        best_location = self.cluster_system.find_job_location(jobs, [])
        assert best_location == {'1':['vs2.test']}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({'1':['vs2.test']}, best_location)

    def test_find_job_locaiton_no_valid_job(self):
        jobs = [get_basic_job_dict()]
        jobs[0]['walltime'] = 300
        self.cluster_system.running_nodes = self.full_node_set
        end_times = [[list(self.full_node_set), int(time.time()) + 600]]
        best_location = self.cluster_system.find_job_location(jobs, end_times)
        assert best_location == {}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({}, best_location)

    def test_find_job_location_too_many_down_locs(self):
        jobs = [get_basic_job_dict()]
        self.cluster_system.nodes_down(list(self.full_node_set))
        best_location = self.cluster_system.find_job_location(jobs, [])
        assert best_location == {}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({}, best_location)

    def test_find_job_locaiton_permit_short_job(self):
        #Backfill a single elligible job
        jobs = [get_basic_job_dict(), get_basic_job_dict()]
        jobs[0]['walltime'] = 720
        jobs[0]['score'] = 50000
        jobs[0]['nodes'] = 2
        jobs[1]['jobid'] = 2
        jobs[1]['walltime'] = 5
        jobs[1]['score'] = 10
        self.cluster_system.running_nodes = set(['vs1.test', 'vs2.test', 'vs3.test'])
        end_times = [[['vs1.test', 'vs2.test', 'vs3.test'], int(time.time()) + 400]]
        best_location = self.cluster_system.find_job_location(jobs, end_times)
        assert best_location == {'2':['vs4.test']}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({'2':['vs4.test']}, best_location)

    def test_find_job_location_backfill_only_eligible(self):
        jobs = [get_basic_job_dict() for _ in range(3)]
        jobs[0]['walltime'] = 720
        jobs[0]['score'] = 50000
        jobs[0]['nodes'] = 2
        jobs[1]['jobid'] = 2
        jobs[1]['walltime'] = 10
        jobs[1]['score'] = 100
        jobs[2]['jobid'] = 3
        jobs[2]['walltime'] = 5
        jobs[2]['score'] = 10
        self.cluster_system.running_nodes = set(['vs1.test', 'vs2.test', 'vs3.test'])
        end_times = [[['vs1.test', 'vs2.test', 'vs3.test'], int(time.time()) + 400]]
        best_location = self.cluster_system.find_job_location(jobs, end_times)
        assert best_location == {'3':['vs4.test']}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({'3':['vs4.test']}, best_location)

    def test_find_job_location_backfill_best_score(self):
        #This is first.  It is assumed that jobs come in in priority order.
        jobs = [get_basic_job_dict() for _ in range(3)]
        jobs[0]['walltime'] = 720
        jobs[0]['score'] = 50000
        jobs[0]['nodes'] = 2
        jobs[1]['jobid'] = 2
        jobs[1]['walltime'] = 5
        jobs[1]['score'] = 101
        jobs[2]['jobid'] = 3
        jobs[2]['walltime'] = 5
        jobs[2]['score'] = 100
        self.cluster_system.running_nodes = set(['vs1.test', 'vs2.test', 'vs3.test'])
        end_times = [[['vs1.test', 'vs2.test', 'vs3.test'], int(time.time()) + 400]]
        best_location = self.cluster_system.find_job_location(jobs, end_times)
        assert best_location == {'2':['vs4.test']}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({'2':['vs4.test']}, best_location)

    def test_find_job_location_hold_for_cleanup(self):
        #ensure that a job that is in a "cleanup" state doesn't get ignored for backfill scheduling
        jobs = [get_basic_job_dict(), get_basic_job_dict()]
        jobs[0]['walltime'] = 720
        jobs[0]['nodes'] = 2
        jobs[1]['jobid'] = 2
        jobs[1]['walltime'] = 60
        self.cluster_system.running_nodes = set(['vs1.test', 'vs2.test', 'vs3.test'])
        self.cluster_system.locations_by_jobid = {100:['vs1.test', 'vs2.test', 'vs3.test']}
        end_times = []
        best_location = self.cluster_system.find_job_location(jobs, end_times)
        assert best_location == {}, "ERROR: Unexpected best_location.\nExpected %s\nGot %s" % \
                ({}, best_location)

