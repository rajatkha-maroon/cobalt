"""Hardware abstraction layer for the system on which process groups are run.

Classes:
Partition -- atomic set of nodes
PartitionDict -- default container for partitions
ProcessGroup -- virtual process group running on the system
ProcessGroupDict -- default container for process groups
Simulator -- simulated system component

Exceptions:
ProcessGroupCreationError -- error when creating a process group
"""

import pwd
from sets import Set as set
import logging
import sys
import os
import operator
import random
import time
import thread
from datetime import datetime
from ConfigParser import ConfigParser

try:
    from elementtree import ElementTree
except ImportError:
    from xml.etree import ElementTree

import Cobalt
import Cobalt.Data
from Cobalt.Data import Data, DataDict, IncrID
from Cobalt.Components.base import Component, exposed, automatic, query

__all__ = [
    "ProcessGroupCreationError",
    "Partition", "PartitionDict",
    "ProcessGroup", "ProcessGroupDict",
    "Simulator",
]

logger = logging.getLogger(__name__)


class ProcessGroupCreationError (Exception):
    """An error occured when creation a process group."""

class Partition (Data):
    
    """An atomic set of nodes.
    
    Partitions can be reserved to run process groups on.
    
    Attributes:
    tag -- partition
    scheduled -- ? (default False)
    name -- canonical name
    functional -- the partition is available for reservations
    queue -- ?
    parents -- super(containing)-partitions
    children -- sub-partitions
    size -- number of nodes in the partition
    
    Properties:
    state -- "idle", "busy", or "blocked"
    """
    
    fields = Data.fields + [
        "tag", "scheduled", "name", "functional",
        "queue", "size", "parents", "children", "state",
    ]
    
    def __init__ (self, spec):
        """Initialize a new partition."""
        Data.__init__(self, spec)
        spec = spec.copy()
        self.scheduled = spec.pop("scheduled", False)
        self.name = spec.pop("name", None)
        self.functional = spec.pop("functional", False)
        self.queue = spec.pop("queue", "default")
        self.size = spec.pop("size", None)
        self._parents = set()
        self.parents = list()
        self._children = set()
        self.children = list()
        self._busy = False
        self.state = spec.pop("state", "idle")
        self.tag = spec.get("tag", "partition")
    
    def __str__ (self):
        return self.name
    
    def __repr__ (self):
        return "<%s name=%r>" % (self.__class__.__name__, self.name)
    
    def _get_state (self):
        for partition in self._parents | self._children:
            if partition._busy:
                return "blocked"
        if self._busy:
            return "busy"
        return "idle"
    
    def _set_state (self, value):
        if self.state == "blocked":
            raise ValueError("blocked")
        if value == "idle":
            self._busy = False
        elif value == "busy":
            self._busy = True
        else:
            raise ValueError(value)
    
    state = property(_get_state, _set_state)
    

class PartitionDict (DataDict):
    
    """Default container for partitions.
    
    Keyed by partition name.
    """
    
    item_cls = Partition
    key = "name"


class ProcessGroup (Cobalt.Data.Data):
    required_fields = ['user', 'executable', 'args', 'location', 'size', 'cwd']
    fields = Cobalt.Data.Data.fields + [
        "id", "user", "size", "cwd", "executable", "env", "args", "location",
        "head_pid", "stdin", "stdout", "stderr", "exit_status", "state",
        "mode", "kerneloptions", "true_mpi_args",
    ]
    
    def __init__(self, spec):
        Data.__init__(self, spec)
        self.id = spec.get("id")
        self.head_pid = None
        self.stdin = spec.get('stdin')
        self.stdout = spec.get('stdout')
        self.stderr = spec.get('stderr')
        self.exit_status = None
        self.location = spec.get('location') or []
        self.user = spec.get('user', "")
        self.executable = spec.get('executable')
        self.cwd = spec.get('cwd')
        self.size = spec.get('size')
        self.mode = spec.get('mode', 'co')
        self.args = " ".join(spec.get('args') or [])
        self.kerneloptions = spec.get('kerneloptions')
        self.env = spec.get('env') or {}
        self.true_mpi_args = spec.get('true_mpi_args')
        self.signals = []
    
    def _get_state (self):
        if self.exit_status is None:
            return "running"
        else:
            return "terminated"
    
    state = property(_get_state)
    
    def _get_argv (self, config_files=None):
        """Get a command string for a process group for a process group."""
        if config_files is None:
            config_files = Cobalt.CONFIG_FILES
        config = ConfigParser()
        config.read(config_files)
        
        argv = [
            config.get("bgpm", "mpirun"),
            os.path.basename(config.get("bgpm", "mpirun")),
        ]
        
        if self.true_mpi_args is not None:
            # arguments have been passed along in a special attribute.  These arguments have
            # already been modified to include the partition that cobalt has selected
            # for the process group.
            argv.extend(self.true_mpi_args)
            return argv
    
        argv.extend([
            "-np", str(self.size),
            "-mode", self.mode,
            "-cwd", self.cwd,
            "-exe", self.executable,
        ])
        
        try:
            partition = self.location[0]
        except (KeyError, IndexError):
            raise ProcessGroupCreationError("location")
        argv.extend(["-partition", partition])
        
        if self.kerneloptions:
            argv.extend(['-kernel_options', self.kerneloptions])
        
        if self.args:
            argv.extend(["-args", " ".join(self.args)])
        
        if self.env:
            env_kvstring = " ".join(["%s=%s" % (key, value) for key, value in self.env.iteritems()])
            argv.extend(["-env",  env_kvstring])
        
        return argv


class ProcessGroupDict (DataDict):
    
    """Default container for process groups.
    
    Keyed by process group id.
    """
    
    item_cls = ProcessGroup
    key = "id"
    
    def __init__ (self):
        self.id_gen = IncrID()
 
    def q_add (self, specs, callback=None, cargs={}):
        for spec in specs:
            if spec.get("id", "*") != "*":
                raise Cobalt.Data.DataCreationError("cannot specify an id")
            spec['id'] = self.id_gen.next()
        return DataDict.q_add(self, specs)


class Simulator (Component):
    
    """Generic system simulator.
    
    Methods:
    configure -- load partitions from an xml file
    get_state -- db2-like description of partition state (exposed)
    get_partitions -- retrieve partitions in the simulator (exposed, query)
    reserve_partition -- lock a partition for use by a process_group (exposed)
    release_partition -- release a locked (busy) partition (exposed)
    add_process_groups -- add (start) a process group on the system (exposed, query)
    get_process_groups -- retrieve process groups (exposed, query)
    wait_process_groups -- get process groups that have exited, and remove them from the system (exposed, query)
    signal_process_groups -- send a signal to the head process of the specified process groups (exposed, query)
    """
    
    name = "system"
    implementation = "simulator"
    
    logger = logger

    def __init__ (self, *args, **kwargs):
        """Initialize a system simulator."""
        Component.__init__(self, *args, **kwargs)
        self._partitions = PartitionDict()
        self._managed_partitions = set()
        self.process_groups = ProcessGroupDict()
        self.config_file = kwargs.get("config_file", None)
        if self.config_file is not None:
            self.configure(self.config_file)
    
    def _get_partitions (self):
        return PartitionDict([
            (partition.name, partition) for partition in self._partitions.itervalues()
            if partition.name in self._managed_partitions
        ])
    
    partitions = property(_get_partitions)
    
    def __getstate__(self):
        return {'managed_partitions':self._managed_partitions, 'version':1, 'config_file':self.config_file}
    
    def __setstate__(self, state):
        self._managed_partitions = state['managed_partitions']
        self.config_file = state['config_file']
        self._partitions = PartitionDict()
        self.process_groups = ProcessGroupDict()
        if self.config_file is not None:
            self.configure(self.config_file)

        self.update_relatives()
        
    def save_me(self):
        Component.save(self)
    save_me = automatic(save_me)
        
    
    def configure (self, config_file):
        
        """Configure simulated partitions.
        
        Arguments:
        config_file -- xml configuration file
        """
        
        self.logger.info("configure()")
        system_doc = ElementTree.parse(config_file)
        system_def = system_doc.getroot()
        
        # initialize a new partition dict with all partitions
        partitions = PartitionDict()
        partitions.q_add([
            dict(
                name = partition_def.get("name"),
                queue = "default",
                scheduled = True,
                functional = True,
                size = partition_def.get("size"),
            )
            for partition_def in system_def.getiterator("Partition")
        ])
        
        # parent/child relationships
        for partition_def in system_def.getiterator("Partition"):
            partition = partitions[partition_def.get("name")]
            partition._children.update([
                partitions[child_def.get("name")]
                for child_def in partition_def.getiterator("Partition")
                if child_def.get("name") != partition.name
            ])
            for child in partition._children:
                child._parents.add(partition)
        
        # update object state
        self._partitions.clear()
        self._partitions.update(partitions)
    
    def add_partitions (self, specs):
        self.logger.info("add_partitions(%r)" % (specs))
        specs = [{'name':spec.get("name")} for spec in specs]
        partitions = [
            partition for partition in self._partitions.q_get(specs)
            if partition.name not in self._managed_partitions
        ]
        self._managed_partitions.update([
            partition.name for partition in partitions
        ])
        self.update_relatives()
        return partitions
    add_partition = exposed(query(add_partitions))
    
    def get_partitions (self, specs):
        """Query partitions on simulator."""
        self.logger.info("get_partitions(%r)" % (specs))
        return self.partitions.q_get(specs)
    get_partitions = exposed(query(get_partitions))
    
    def del_partitions (self, specs):
        self.logger.info("del_partitions(%r)" % (specs))
        partitions = [
            partition for partition in self._partitions.q_get(specs)
            if partition.name in self._managed_partitions
        ]
        self._managed_partitions -= set( [partition.name for partition in partitions] )
        self.update_relatives()
        return partitions
    del_partitions = exposed(query(del_partitions))
    
    def set_partitions (self, specs, updates):
        def _set_partitions(part, newattr):
            part.update(newattr)
        return self._partitions.q_get(specs, _set_partitions, updates)
    set_partitions = exposed(query(set_partitions))
    
    def reserve_partition (self, name, size=None):
        """Reserve a partition and block all related partitions.
        
        Arguments:
        name -- name of the partition to reserve
        size -- size of the process group reserving the partition (optional)
        """
        try:
            partition = self.partitions[name]
        except KeyError:
            self.logger.error("reserve_partition(%r, %r) [does not exist]" % (name, size))
            return False
        if partition.state != "idle":
            self.logger.error("reserve_partition(%r, %r) [%s]" % (name, size, partition.state))
            return False
        if not partition.functional:
            self.logger.error("reserve_partition(%r, %r) [not functional]" % (name, size))
        if size is not None and size > partition.size:
            self.logger.error("reserve_partition(%r, %r) [size mismatch]" % (name, size))
            return False
        partition.state = "busy"
        self.logger.info("reserve_partition(%r, %r)" % (name, size))
        return True
    reserve_partition = exposed(reserve_partition)
    
    def release_partition (self, name):
        """Release a reserved partition.
        
        Arguments:
        name -- name of the partition to release
        """
        try:
            partition = self.partitions[name]
        except KeyError:
            self.logger.error("release_partition(%r) [already free]" % (name))
            return False
        if not partition.state == "busy":
            self.logger.info("release_partition(%r) [not busy]" % (name))
            return False
        partition.state = "idle"
        self.logger.info("release_partition(%r)" % (name))
        return True
    release_partition = exposed(release_partition)
    
    def add_process_groups (self, specs):
        
        """Create a simulated process group.
        
        Arguments:
        spec -- dictionary hash specifying a process group to start
        """
        
        self.logger.info("add_process_groups(%r)" % (specs))
        process_groups = self.process_groups.q_add(specs)
        for process_group in process_groups:
            self.start(process_group)
        return  process_groups
    add_process_groups = exposed(query(all_fields=True)(add_process_groups))
    
    def get_process_groups (self, specs):
        """Query process_groups from the simulator."""
        self.logger.info("get_process_groups(%r)" % (specs))
        return self.process_groups.q_get(specs)
    get_process_groups = exposed(query(get_process_groups))
    
    def wait_process_groups (self, specs):
        """get process groups that have finished running."""
        self.logger.info("wait_process_groups(%r)" % (specs))
        process_groups = [pg for pg in self.process_groups.q_get(specs) if pg.exit_status is not None]
        for process_group in process_groups:
            del self.process_groups[process_group.id]
        return process_groups
    wait_process_groups = exposed(query(wait_process_groups))
    
    def signal_process_groups (self, specs, signame="SIGINT"):
        """Simulate the signaling of a process_group."""
        self.logger.info("signal_process_groups(%r, %r)" % (specs, signame))
        process_groups = self.process_groups.q_get(specs)
        for process_group in process_groups:
            process_group.signals.append(signame)
        return process_groups
    signal_process_groups = exposed(query(signal_process_groups))
    
    def start (self, process_group):
        thread.start_new_thread(self._mpirun, (process_group, ))
    
    def _mpirun (self, process_group):
        argv = process_group._get_argv()
        stdout = open(process_group.stdout or "/dev/null", "a")
        stderr = open(process_group.stderr or "/dev/null", "a")
        try:
            partition = argv[argv.index("-partition") + 1]
        except ValueError:
            print >> stderr, "ERROR: '-partition' is a required flag"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        except IndexError:
            print >> stderr, "ERROR: '-partition' requires a value"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        
        try:
            mode = argv[argv.index("-mode") + 1]
        except ValueError:
            print >> stderr, "ERROR: '-mode' is a required flag"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        except IndexError:
            print >> stderr, "ERROR: '-mode' requires a value"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        
        try:
            size = argv[argv.index("-np") + 1]
        except ValueError:
            print >> stderr, "ERROR: '-np' is a required flag"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        except IndexError:
            print >> stderr, "ERROR: '-np' requires a value"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        try:
            size = int(size)
        except ValueError:
            print >> stderr, "ERROR: '-np' got invalid value %r" % (size)
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
        
        print >> stdout, "ENVIRONMENT"
        print >> stdout, "-----------"
        for key, value in process_group.env.iteritems():
            print >> stdout, "%s=%s" % (key, value)
        print >> stdout
        
        print >> stderr, "FE_MPI (Info) : Initializing MPIRUN"
        reserved = self.reserve_partition(partition, size)
        if not reserved:
            print >> stderr, "BE_MPI (ERROR): Failed to run process on partition"
            print >> stderr, "BE_MPI (Info) : BE completed"
            print >> stderr, "FE_MPI (ERROR): Failure list:"
            print >> stderr, "FE_MPI (ERROR): - 1. ProcessGroup execution failed - unable to reserve partition", partition
            print >> stderr, "FE_MPI (Info) : FE completed"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        print >> stderr, "FE_MPI (Info) : process group with id", process_group.id
        print >> stderr, "FE_MPI (Info) : Waiting for process_group to terminate"
        
        print >> stdout, "Running process_group: %s" % " ".join(argv)
        
        start_time = time.time()
        run_time = random.randint(60, 180)
        print "running for about %f seconds" % run_time
        while time.time() < (start_time + run_time):
            if "SIGKILL" in process_group.signals:
                process_group.exit_status = 1
                return
            elif "SIGTERM" in process_group.signals:
                print >> stderr, "FE_MPI (Info) : ProcessGroup got signal SIGTERM"
                break
            else:
                time.sleep(1) # tumblers better than pumpers
        
        print >> stderr, "FE_MPI (Info) : ProcessGroup", process_group.id, "switched to state TERMINATED ('T')"
        print >> stderr, "FE_MPI (Info) : ProcessGroup sucessfully terminated"
        print >> stderr, "BE_MPI (Info) : Releasing partition", partition
        released = self.release_partition(partition)
        if not released:
            print >> stderr, "BE_MPI (ERROR): Partition", partition, "could not switch to state FREE ('F')"
            print >> stderr, "BE_MPI (Info) : BE completed"
            print >> stderr, "FE_MPI (Info) : FE completed"
            print >> stderr, "FE_MPI (Info) : Exit status: 1"
            process_group.exit_status = 1
            return
        print >> stderr, "BE_MPI (Info) : Partition", partition, "switched to state FREE ('F')"
        print >> stderr, "BE_MPI (Info) : BE completed"
        print >> stderr, "FE_MPI (Info) : FE completed"
        print >> stderr, "FE_MPI (Info) : Exit status: 0"
        
        process_group.exit_status = 0
    
    def update_relatives(self):
        """Call this method after changing the contents of self._managed_partitions"""
        for p_name in self._managed_partitions:
            p = self._partitions[p_name]
            p.parents = [parent.name for parent in p._parents if parent.name in self._managed_partitions]
            p.children = [child.name for child in p._children if child.name in self._managed_partitions]
