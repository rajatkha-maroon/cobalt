"""Resource management for Cray ALPS based systems"""



from Cobalt.Components.base import Component, exposed, automatic
from Cobalt.Components.system.base_system import BaseSystem
import Cobalt.Components.system.AlpsBridge as AlpsBridge
from Cobalt.Components.system.CrayNode import CrayNode
from Cobalt.Components.system.base_pg_manager import ProcessGroupManager
import Cobalt.Util

import logging
import threading
import thread
import copy
import time

_logger = logging.getLogger(__name__)

#TODO: these need to be config options
UPDATE_THREAD_TIMEOUT = 10 #TODO: Time in seconds, make setable
TEMP_RESERVATION_TIME = 300 #Time in seconds to set a temp resource res for startup


class CraySystem(BaseSystem):

    name = "system"
    implementation = "alps_system"
    logger = _logger

    def __init__(self, *args, **kwargs):
        '''Initialize system.  Read initial states from bridge.
        Get current state

        '''
        super(CraySystem, self).__init__(*args, **kwargs)
        #process manager setup
        self.process_manager = ProcessGroupManager()
        self.process_manager.forkers.append('user_script_forker')
        _logger.info('PROCESS MANAGER INTIALIZED')
        #resource management setup
        self.nodes = {} #cray node_id: CrayNode
        self.node_name_to_id = {} #cray node name to node_id map.
        self.alps_reservations = {}
        self._init_nodes_and_reservations()
        #state update thread and lock
        self._node_lock = threading.RLock()
        self.node_update_thread = thread.start_new_thread(self._run_update_state,
                tuple())
        self.alps_reservations = {} #cobalt jobid : AlpsReservation object
        self.current_equivalence_classes = []
        _logger.info('ALPS SYSTEM COMPONENT READY TO RUN.')

    def _init_nodes_and_reservations(self):
        '''Initialize nodes from ALPS bridge data'''

        retnodes = {}
        inventory = AlpsBridge.fetch_inventory(resinfo=True)
        for nodespec in inventory['nodes']:
            node = CrayNode(nodespec)
            node.managed = True
            retnodes[node.node_id] = node
        self.nodes = retnodes
        #Reversing the node name to id lookup is going to save a lot of cycles.
        for node in self.nodes.values():
            self.node_name_to_id[node.name] = self.node.node_id
        _logger.info('NODE INFORMATION INITIALIZED')
        _logger.info('ALPS REPORTS %s NODES', len(self.nodes))
        print [str(node) for node in self.nodes.values()]
        for resspec in inventory['reservations']:
            self.alps_reservations[resspec['reservation_id']] = ALPSReservation(resspec)

    @exposed
    def get_nodes(self, as_dict=False, node_ids=None):
        '''fetch the node dictionary.

            node_ids - a list of node names to return, if None, return all nodes
                       (default None)

            returns the node dictionary.  Can reutrn underlying node data as
            dictionary for XMLRPC purposes

        '''
        if node_ids is None:
            if as_dict:
                retdict = {}
                for node in self.nodes.values():
                    raw_node = node.to_dict()
                    cooked_node = {}
                    for key, val in raw_node.items():
                        if key.startswith('_'):
                            cooked_node[key[1:]] = val
                        else:
                            cooked_node[key] = val
                    retdict[node.name] = cooked_node
                return retdict
            else:
                return self.nodes
        else:
            raise NotImplementedError

    def _run_update_state(self):
        '''automated node update functions on the update timer go here.'''
        while True:
            self.update_node_state()
            Cobalt.Util.sleep(UPDATE_THREAD_TIMEOUT)

    @exposed
    def update_node_state(self):
        '''update the state of cray nodes. Check reservation status and system
        stateus as reported by ALPS

        '''
        with self._node_lock:
            original_nodes = copy.deepcopy(self.nodes)
        updates = {} #node_id and node to update
        inventory = AlpsBridge.fetch_inventory(resinfo=True) #This is a full-refresh,
                                                 #summary should be used otherwise
        inven_nodes  = inventory['nodes']
        inven_reservations = inventory['reservations']
        #find hardware status
        with self._node_lock:
            for inven_node in inven_nodes:
                if self.nodes.has_key(inven_node['name']):
                    self.nodes[inven_node['name']].status = inven_node['state'].upper()
                else:
                    # Cannot add nodes on the fly.  Or at lesat we shouldn't be
                    # able to.
                    _logger.error('UNS: ALPS reports node %s but not in our node list.',
                            inven_node['name'])
        #check/update reservation information and currently running locations?
        #fetch info from process group manager for currently running jobs.
        #should down win over running in terms of display?

        return

    @exposed
    def find_queue_equivalence_classes(self, reservation_dict,
            active_queue_names, passthrough_blocking_res_list=[]):
        '''Aggregate queues together that can impact eachother in the same
        general pass (both drain and backfill pass) in find_job_location.
        Equivalence classes will then be used in find_job_location to consider
        placement of jobs and resources, in separate passes.  If multiple
        equivalence classes are returned, then they must contain orthogonal sets
        of resources.

        Inputs:
        reservation_dict -- a mapping of active reservations to resrouces.
                            These will block any job in a normal queue.
        active_queue_names -- A list of queues that are currently enabled.
                              Queues that are not in the 'running' state
                              are ignored.
        passthrough_partitions -- Not used on Cray systems currently.  This is
                                  for handling hardware that supports
                                  partitioned interconnect networks.

        Output:
        A list of dictionaries of queues that may impact eachother while
        scheduling resources.

        Side effects:
        None

        Internal Data:
        queue_assignments: a mapping of queues to schedulable locations.

        '''
        equiv = []
        #reverse mapping of queues to nodes
        for node in self.nodes.values():
            if node.managed and node.schedulable:
                #only condiser nodes that we are scheduling.
                node_active_queues = []
                for queue in node.queues:
                    if queue in active_queue_names:
                        node_active_queues.append(queue)
                if node_active_queues == []:
                    #this node has nothing active.  The next check can get
                    #expensive, so skip it.
                    continue
            #determine the queues that overlap.  Hardware has to be included so
            #that reservations can be mapped into the equiv classes.
            found_a_match = False
            for e in equiv:
                for queue in node_active_queues:
                    if queue in e['queues']:
                        e['data'].add(node.name)
                        e['queues'] = e['queues'] | set(node_active_queues)
                        found_a_match = True
                        break
                if found_a_match:
                    break
            if not found_a_match:
                equiv.append({'queues': set([node_active_queues]),
                              'data': set([node.name]),
                             'reservations': set()})
        #second pass to merge queue lists based on hardware
        real_equiv = []
        for eq_class in equiv:
            found_a_match = False
            for e in real_equiv:
                if e['data'].intersection(eq_class['data']):
                    e['queues'].update(eq_class['queues'])
                    e['data'].update(eq_class['data'])
                    found_a_match = True
                    break
            if not found_a_match:
                real_equiv.append(eq_class)
        equiv = real_equiv
        #add in reservations:
        for eq_class in equiv:
            for res_name in reservation_dict:
                for node_name in reservation_dict[res_name].split(":"):
                    if node_name in eq_class['data']:
                        eq_class['reservations'].add(res_name)
                        break
            #don't send what could be a large block list back in the return
            for key in eq_class:
                eq_class[key] = list(eq_class[key])
            del eq_class['data']
        self.current_equivalence_classes = eq_class
        return equiv

    @exposed
    def find_job_location(self, arg_list, end_times, pt_blocking_locations=[]):
        '''Given a list of jobs, and when jobs are ending, return a set of
        locations mapped to a jobid that can be run.  Also, set up draining
        as-needed to run top-scored jobs and backfill when possible.

        Called once per equivalence class.

        Input:
        arg_list - A list of dictionaries containning information on jobs to
                   cosnider.
        end_times - list containing a mapping of locations and the times jobs
                    runninng on those locations are scheduled to end.  End times
                    are in seconds from Epoch UTC.
        pt_blocking_locations - Not used for this system.  Used in partitioned
                                interconnect schemes. A list of locations that
                                should not be used to prevent passthrough issues
                                with other scheduler reservations.

        Output:
        A mapping of jobids to locations to run a job to run immediately.

        Side Effects:
        May set draining flags and backfill windows on nodes.
        If nodes are being returned to run, set ALPS reservations on them.

        Notes:
        The reservation set on ALPS resources is uncomfirmed at this point.
        This reservation may timeout.  The forker when it confirms will detect
        this and will re-reserve as needed.  The alps reservation id may change
        in this case post job startup.

        '''
        #TODO: make not first-fit
        now = time.time()
        resource_until_time = now + TEMP_RESERVATION_TIME
        with self._blocks_lock:
            idle_nodecount = len([node for node in self.nodes.values() if
                node.managed and node.state is 'idle'])
            self._clear_draining_for_queues(arg_list[0]['queue'])
            #check if we can run immedaitely, if not drain.  Keep going until all
            #nodes are marked for draining or have a pending run.
            best_match = {} #jobid: list(locations)
            current_idle_nodecount = idle_nodecount
            for job in arglist:
                if job['nodecount'] >= idle_nodecount:
                    label = '%s/%s' % (job['jobid'], job['user'])
                    #this can be run immediately
                    job_locs = self._ALPS_reserve_resources
                    if job_locs is not None and len(job_locs) == job['nodecount']:
                        #temporary reservation until job actually starts
                        self.reserve_resources_until(job_locs,
                                resource_until_time, job['jobid'])
                        #set resource reservation, adjust idle count
                        idle_nodecount -= int(job['nodecount'])
                        best_match[job['jobid']] = job_locs
                        _logger.info("%s: Job selected for running on nodes  %s",
                                label, " ".join(job_locs))
                else:
                    #TODO: draining goes here
                    pass
            #TODO: backfill pass goes here
            return best_match

    def _ALPS_reserve_resources(self, job, new_time):
        '''Call ALPS to reserve resrources.  Use their allocator.  We can change
        this later to substitute our own allocator if-needed.

        Input:
        Nodecount - number of nodes to reserve for  a job.

        Returns: a list of locations that ALPS has reserved.

        Side effects:
        Places an ALPS reservation on resources.  Calls reserve resources until
        on the set of nodes, and will mark nodes as allocated.

        '''
        #TODO: passthrough from attrs for cray-specific options
        reserved_nodes = []
        res_info = ALPSBridge.reserve(job['user'], job['jobid'],
                job['nodecount'])
        new_alps_res = None
        if res_info is not None:
            new_alps_res = ALPSReservation(res_info)
            self.alps_reservation.add(ALPSReservation(res_info))
            reserved_nodes = new_alps_res.node_ids
        #place a resource_reservation
        if new_alps_res is not None:
            self.reserve_resources_until(new_alps_res.node_names, new_time,
                    job['jobid'])
        return self.new_alps_res.node_names

    def _clear_draining_for_queues(self, queue):
        '''Given a list of queues, remove the draining flags on nodes.

        queues - a queue in an equivalence class to consider.  This will clear
        the entire equiv class

        return - none

        Note: does not acquire block lock.  Must be locked externally.

        '''
        current_queues = []
        for equiv_class in self.current_equivalence_classes:
            if queue in equiv_class['queues']:
                current_queues = equiv_class['queues']
        if current_queues:
            for node in self.nodes:
                if node.queue in current_queues:
                    node.clear_drain

    @exposed
    def reserve_resources_until(self, location, new_time, jobid):
        '''Place, adjust and release resource reservations.

        Input:
            location: the location to reserve [list of nodes]
            new_time: the new end time of a resource reservation
            jobid: the Cobalt jobid that this reservation is for

        Output:
            True if resource reservation is successfully placed.
            Otherwise False.

        Side Effects:
            * Sets/releases reservation on specified node list
            * Sets/releases ALPS reservation.  If set reservation is unconfirmed
              Confirmation must occur a cray_script_forker

        Notes:
            This holds the node data lock while it's running.
        '''
        rc = False
        with self._node_lock:
            if new_time is not None:
                #reserve the location. Unconfirmed reservations will have to
                #be lengthened.  Maintain a list of what we have reserved, so we
                #extend on the fly, and so that we don't accidentally get an
                #overallocation/user
                for location in reserved_locations:
                    node = self.nodes[self.node_name_to_id[location]]
                    try:
                        node.reserve(new_time, jobid=jobid)
                    except Cobalt.Exceptions.ResourceReservationFailure as exc:
                        self.logger.error(exc)
                    self.logger.info("job %s: block '%s' now reserved until %s",
                        jobid, location, time.asctime(time.gmtime(new_time)))
                rc = True
            else:
                #release the reservation and the underlying ALPS reservation
                #and the reserration on blocks.
                for location in reserved_locations:
                    node = self.nodes[self.node_name_to_id[location]]
                    try:
                        node.release(user=None, jobid=jobid)
                    except Cobalt.Exceptions.ResourceReservationFailure as exc:
                        self.logger.error(exc)
                    #cleanup pending has to be dealt with.  Do this in UNS for
                    #now
                    self.logger.info("job %s:  node '%s' released. Cleanup pending.",
                        jobid, location)
                rc = True
        return rc

    def add_jobs(self, specs):
        raise NotImplementedError


class ALPSReservation(object):

    def __init__(self, spec):
        '''spec should be the information returned from the Reservation Response
        object.

        '''
        self.jobid = spec['batch_id']
        self.node_ids = [int(node_id) for node_id in spec['node_ids']]
        self.node_names = []
        for node_id in node_ids:
            self.node_names.append(self.nodes[node_id])
        self.pg_id = spec.get('pagg_id', None) #process group of executing script
        self.alps_res_id = spec['reservation_id']
        self.app_info = spec['ApplicationArray']
        self.user = spec['user_name']
        self.gid = spec['account_name'] #appears to be gid.
        self.dying = False
        self.dead = False #System no longer has this alps reservation

    @property
    def confirmed(self):
        '''Has this reservation been confirmed?  If not, it's got a 2 minute
        lifetime.

        '''
        return self.pg_id is not None

    def confirm(self, pagg_id):
        '''Mark a reservation as confirmed.  This must be passed back from the
        forker that confirmed the reservation and is the process group id of the
        child process forked for the job.

        '''
        self.pg_id = pagg_id

    def release(self):
        '''Release an underlying ALPS reservation.

        Note:
        A reservation may remain if there are still active claims.  When all
        claims are gone

        '''
        status = AlpsBridge.release(self.alps_res_id)
        if int(status['claims']) != 0:
            _logger.info('ALPS reservation: %s still has %s claims.',
                    self.alps_res_id, status['claims'])
        else:
            _logger.info('ALPS reservation: %s has no claims left.',
                self.alps_res_id)


#if __name__ == '__main__':
#
#    cs = CraySystem()
#    nodes = cs.get_nodes()
#
#    for node_name, node in nodes.iteritems():
#        print "Name: %s" % node_name
#        for key, val in node.to_dict().iteritems():
#            print "    %s: %s" % (key, val)
#
#    for res_id, reservation in cs.alps_reservations.items():
#        print "Resid: %s" % res_id
#        for key, val in reservation.__dict__.items():
#            print "    %s: %s" % (key, val)
#
