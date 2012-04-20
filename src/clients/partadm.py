#!/usr/bin/env python

'''Partadm sets partition attributes in the scheduler'''
__revision__ = '$Revision: 1981 $'
__version__ = '$Version$'

import sys
import xmlrpclib
import os
import optparse
import pwd

import Cobalt.Util
from Cobalt.Proxy import ComponentProxy
from Cobalt.Exceptions import ComponentLookupError


helpmsg = '''Usage: partadm.py [-a] [-d] part1 part2 (add or del)
Usage: partadm.py -l
Usage: partadm.py [--activate|--deactivate] part1 part2 (functional or not)
Usage: partadm.py [--enable|--disable] part1 part2 (scheduleable or not)
Usage: partadm.py --queue=queue1:queue2 part1 part2
Usage: partadm.py --diag=diag_name partition
Usage: partadm.py --fail part1 part2
Usage: partadm.py --unfail part1 part2
Usage: partadm.py --dump
Usage: partadm.py --xml
Usage: partadm.py --version
Usage: partadm.py --savestate filename

Must supply one of -a or -d or -l or -start or -stop or --queue
Adding "-r" or "--recursive" will add the children of the blocks passed in.

'''

opt_parser = optparse.OptionParser(usage=helpmsg, version=("Cobalt Version: %s" % __version__))

opt_parser.add_option("-a", action="store_true", dest="add")
opt_parser.add_option("-d", action="store_true", dest="delete")
opt_parser.add_option("-l", action="store_true", dest="list_blocks")
opt_parser.add_option("-r", "--recursive", action="store_true", dest="recursive")
opt_parser.add_option("--queue", action="store", type="string", dest="queue")
opt_parser.add_option("--activate", action="store_true", dest="activate")
opt_parser.add_option("--deactivate", action="store_true", dest="deactivate")
opt_parser.add_option("--enable", action="store_true", dest="enable")
opt_parser.add_option("--disable", action="store_true", dest="disable")
opt_parser.add_option("--fail", action="store_true", dest="fail")
opt_parser.add_option("--unfail", action="store_true", dest="unfail")
opt_parser.add_option("--dump", action="store_true", dest="dump")
opt_parser.add_option("--xml", action="store_true", dest="xml")
opt_parser.add_option("--savestate", action="store", type="string", dest="savestate")
opt_parser.add_option("--boot_stop", action="store_true", dest="boot_stop")
opt_parser.add_option("--boot_start", action="store_true", dest="boot_start")
opt_parser.add_option("--boot_status", action="store_true", dest="boot_status")
opt_parser.add_option("-b", "--blockinfo", action="store_true", dest="blockinfo")



conflicting_args = {'add':['delete','fail','unfail','boot_stop','boot_start'],
                    'delete':['add','fail','unfail','boot_stop','boot_start'],
                    'list_blocks':['blockinfo'],
                    }

def component_call(func, args):
    try:
        parts = apply(func, args)
    except xmlrpclib.Fault, fault:
        print "Command failure", fault
    except:
        print "strange failure"
    return parts


def print_block(block_dicts):

    for block in block_dicts:
        #print block['name']
    
        #print ' '.join([nodecard['name'] for nodecard in block['node_cards']])
        header_list = []
        value_list = []

        for key,value in block.iteritems():

            if key in ['node_cards','nodes']:
                if block['size'] > 32 and key == 'nodes':
                    continue
                else:
                    header_list.append(key)
                    value_list.append(' '.join([v['name'] for v in value]))
            else:
                header_list.append(key)
                value_list.append(value)

        Cobalt.Util.print_vertical([header_list,value_list])

if __name__ == '__main__':
   
    
    try:
        opts, args  = opt_parser.parse_args() 
    except optparse.OptParseError, msg:
        print msg
        print helpmsg
        raise SystemExit, 1
   
    try:
        system = ComponentProxy("system", defer=False)
    except ComponentLookupError:
        print "Failed to connect to system component"
        raise SystemExit, 1

    whoami = pwd.getpwuid(os.getuid())[0]

    if opts.recursive:
        partdata = system.get_partitions([{'tag':'partition', 'name':name, 'children':'*'} for name in args])
        parts = args
        
        for part in partdata:
            for child in part['children']:
                if child not in parts:
                    parts.append(child)
    else:
        parts = args

    if opts.add:
        args = ([{'tag':'partition', 'name':partname, 'size':"*", 'functional':False,
                  'scheduled':False, 'queue':'default', 'deps':[]} for partname in parts], whoami)
        parts = component_call(system.add_partitions, args)
    elif opts.delete:
        args = ([{'tag':'partition', 'name':partname} for partname in parts], whoami)
        parts = component_call(system.del_partitions, args)
    elif opts.enable:
        args = ([{'tag':'partition', 'name':partname} for partname in parts],
                {'scheduled':True}, whoami)
        parts = component_call(system.set_partitions, args)
    elif opts.disable:
        args = ([{'tag':'partition', 'name':partname} for partname in parts],
                {'scheduled':False}, whoami)
        parts = component_call(system.set_partitions, args)
    elif opts.activate:
        args = ([{'tag':'partition', 'name':partname} for partname in parts],
                {'functional':True}, whoami)
        parts = component_call(system.set_partitions, args)
    elif opts.deactivate:
        args = ([{'tag':'partition', 'name':partname} for partname in parts],
                {'functional':False}, whoami)
        parts = component_call(system.set_partitions, args)
    elif opts.fail:
        args = ([{'tag':'partition', 'name':partname} for partname in parts], whoami)
        parts = component_call(system.fail_partitions, args)
    elif opts.unfail:
        args = ([{'tag':'partition', 'name':partname} for partname in parts], whoami)
        parts = component_call(system.unfail_partitions, args)
    elif opts.xml:
        args = tuple()
        parts = component_call(system.generate_xml, args)
    elif opts.savestate:
        directory = os.path.dirname(savestate)
        if not os.path.exists(directory):
            print "directory %s does not exist" % directory
            sys.exit(1)
        func = system.save
        args = (savestate,)
        parts = component_call(system.save, args)

    elif opts.list_blocks:
        func = system.get_partitions
        args = ([{'name':'*', 'size':'*', 'state':'*', 'scheduled':'*', 'functional':'*',
                  'queue':'*', 'relatives':'*'}], )
        parts = component_call(system.get_partitions, args)
    elif opts.queue:
        try:
            cqm = ComponentProxy("queue-manager", defer=False)
            existing_queues = [q.get('name') for q in cqm.get_queues([ \
                {'tag':'queue', 'name':'*'}])]
        except:
            print "Error getting queues from queue_manager"
            raise SystemExit, 1
        error_messages = []
        for q in opts.queue.split(':'):
            if not q in existing_queues:
                error_messages.append('\'' + q + '\' is not an existing queue')
        if error_messages:
            for e in error_messages:
                print e
            raise SystemExit, 1
        args = ([{'tag':'partition', 'name':partname} for partname in parts],
                {'queue':opts.queue}, whoami)
        parts = component_call(system.set_partitions, args)
    elif opts.dump:
        args = ([{'tag':'partition', 'name':'*', 'size':'*', 'state':'*', 'functional':'*',
                  'scheduled':'*', 'queue':'*', 'deps':'*'}], )
        parts = component_call(system.get_partitions, args)
    elif opts.boot_stop:
        args = (whoami,)
        parts = component_call(halt_booting, args)
        print "Halting booting: halting scheduling is advised"
    elif opts.boot_start:
        args = (whoami,)
        parts = component_call(resume_booting, args)
        print "Enabling booting"
    elif opts.boot_status:
        boot_status = system.booting_status()
        if not boot_status:
            print "Block Booting: ENABLED"
        else:
            print "Block Booting: SUSPENDED."
        sys.exit(0)


    if opts.blockinfo:
        for part in parts:
            print_block(system.get_blocks([{'name':part,'node_cards':'*',
                'subblock_parent':'*','nodes':'*', 'scheduled':'*', 'funcitonal':'*',
                'queue':'*','parents':'*','children':'*','reserved_until':'*',
                'reserved_by':'*','used_by':'*','freeing':'*','block_type':'*',
                'corner_node':'*', 'extents':'*', 'cleanup_pending':'*', 'state':'*',
                'size':'*','draining':'*','backfill_time':'*'}]))
        sys.exit(0)
 
    if opts.list_blocks:
        # need to cascade up busy and non-functional flags
#        print "buildRackTopology sees : " + repr(parts)
#
#        partinfo = Cobalt.Util.buildRackTopology(parts)

        try:
            scheduler = ComponentProxy("scheduler", defer=False)
            reservations = scheduler.get_reservations([{'queue':"*", 'partitions':"*", 'active':True}])
        except ComponentLookupError:
            print "Failed to connect to scheduler; no reservation data available"
            reservations = []
    
        expanded_parts = {}
        for res in reservations:
            for res_part in res['partitions'].split(":"):
                for p in parts:
                    if p['name'] == res_part:
                        if expanded_parts.has_key(res['queue']):
                            expanded_parts[res['queue']].update(p['relatives'])
                        else:
                            expanded_parts[res['queue']] = set( p['relatives'] )
                        expanded_parts[res['queue']].add(p['name'])
            
        
        for res in reservations:
            for p in parts:
                if p['name'] in expanded_parts[res['queue']]:
                    p['queue'] += ":%s" % res['queue']
    
        def my_cmp(left, right):
            val = -cmp(int(left['size']), int(right['size']))
            if val == 0:
                return cmp(left['name'], right['name'])
            else:
                return val
        
        parts.sort(my_cmp)
    
        offline = [part['name'] for part in parts if not part['functional']]
        forced = [part for part in parts \
                  if [down for down in offline \
                      if down in part['relatives']]]
        [part.__setitem__('functional', '-') for part in forced]
        data = [['Name', 'Queue', 'Size', 'Functional', 'Scheduled', 'State', 'Dependencies']]
        # FIXME find something useful to output in the 'deps' column, since the deps have vanished
        data += [[part['name'], part['queue'], part['size'], part['functional'], part['scheduled'],
                  part['state'], ','.join([])] for part in parts]
        Cobalt.Util.printTabular(data, centered=[3, 4])

    elif opts.boot_start or opts.boot_stop: 
        pass
    else:
        print parts
            
        
