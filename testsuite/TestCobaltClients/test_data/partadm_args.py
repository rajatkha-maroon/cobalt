"""
This module defines the test argument information list for partadm.py and will 
dynamically be imported by testutils.py to generate the tests for partadm.py.

Refer to the TESTUTILS_README.txt for more information about the usage of this module and testutils.py

test_argslist - is a list of dictionaries, each dictionary has all the necessary info for a test.

"""

test_argslist = [
    { "tc_name" : "version_option", "args" : """--version""", },
    { "tc_name" : "help_option_1", "args" : """-h""", },
    { "tc_name" : "help_option_2", "args" : """--help""", },
    { "tc_name" : "no_arg_1", "args" : "", "new_only" : False,},
    { "tc_name" : "no_arg_2", "args" : """-a""", "new_only" : False,},
    { "tc_name" : "debug", "args" : """--debug""", "new_only" : False,},
    { "tc_name" : "combo_options_1", "args" : """-a -d PART""", "new_only" : False,},
    { "tc_name" : "combo_options_2", "args" : """-a --enable PART""", "new_only" : False,},
    { "tc_name" : "combo_options_3", "args" : """-d --enable PART""", "new_only" : False,},
    { "tc_name" : "combo_options_4", "args" : """--enable --disable PART""", "new_only" : False,},
    { "tc_name" : "combo_options_5", "args" : """--deactivate --activate PART""", "new_only" : False,},
    { "tc_name" : "combo_options_6", "args" : """-a --deactivate PART""", "new_only" : False,},
    { "tc_name" : "combo_options_7", "args" : """--fail --unfail PART""", "new_only" : False,},
    { "tc_name" : "combo_options_8", "args" : """--savestate /tmp/savestate -a""", "new_only" : False,},
    { "tc_name" : "combo_options_9", "args" : """-l --xml""", "new_only" : False,},
    { "tc_name" : "combo_options_10", "args" : """-l --xml""", "new_only" : False,},
    { "tc_name" : "combo_options_11", "args" : """-a --queue q1 PART""", "new_only" : False,},
    { "tc_name" : "combo_options_12", "args" : """--dump --queue q1 PART""", "new_only" : False,},
    { "tc_name" : "combo_options_13", "args" : """--savestate /tmp/s --xml""", "new_only" : False,},
    { "tc_name" : "combo_options_14", "args" : """-a -c -b PART""", "new_only" : False,},
    { "tc_name" : "add_option_1", "args" : """-a -r PART""", },
    { "tc_name" : "add_option_2", "args" : """-a --recursive PART""", },
    { "tc_name" : "add_option_3", "args" : """-a PART1 PART2 PART3""", },
    { "tc_name" : "add_option_4", "args" : """-a -b PART1 PART2""", },
    { "tc_name" : "add_option_5", "args" : """-a -c PART1 PART2""", },
    { "tc_name" : "delete_option_1", "args" : """-d -r PART""", },
    { "tc_name" : "delete_option_2", "args" : """-d --recursive PART""", },
    { "tc_name" : "delete_option_3", "args" : """-d PART1 PART2 PART3""", },
    { "tc_name" : "delete_option_4", "args" : """-d -b PART1 PART2""", },
    { "tc_name" : "delete_option_5", "args" : """-d -c PART1 PART2""", },
    { "tc_name" : "enable_option_1", "args" : """--enable -r PART""", },
    { "tc_name" : "enable_option_2", "args" : """--enable --recursive PART""", },
    { "tc_name" : "enable_option_3", "args" : """--enable PART1 PART2 PART3""", },
    { "tc_name" : "enable_option_4", "args" : """--enable -b PART1 PART2""", },
    { "tc_name" : "enable_option_5", "args" : """--enable -c PART1 PART2""", },
    { "tc_name" : "disable_option_1", "args" : """--disable -r PART""", },
    { "tc_name" : "disable_option_2", "args" : """--disable --recursive PART""", },
    { "tc_name" : "disable_option_3", "args" : """--disable PART1 PART2 PART3""", },
    { "tc_name" : "disable_option_4", "args" : """--disable -b PART1 PART2""", },
    { "tc_name" : "disable_option_5", "args" : """--disable -c PART1 PART2""", },
    { "tc_name" : "activate_option_1", "args" : """--activate -r PART""", },
    { "tc_name" : "activate_option_2", "args" : """--activate --recursive PART""", },
    { "tc_name" : "activate_option_3", "args" : """--activate PART1 PART2 PART3""", },
    { "tc_name" : "activate_option_4", "args" : """--activate -b PART1 PART2""", },
    { "tc_name" : "activate_option_5", "args" : """--activate -c PART1 PART2""", },
    { "tc_name" : "deactivate_option_1", "args" : """--deactivate -r PART""", },
    { "tc_name" : "deactivate_option_2", "args" : """--deactivate --recursive PART""", },
    { "tc_name" : "deactivate_option_3", "args" : """--deactivate PART1 PART2 PART3""", },
    { "tc_name" : "deactivate_option_4", "args" : """--deactivate -b PART1 PART2""", },
    { "tc_name" : "deactivate_option_5", "args" : """--deactivate -c PART1 PART2""", },
    { "tc_name" : "fail_option_1", "args" : """--fail -r PART""", },
    { "tc_name" : "fail_option_2", "args" : """--fail --recursive PART""", },
    { "tc_name" : "fail_option_3", "args" : """--fail PART1 PART2 PART3""", },
    { "tc_name" : "fail_option_4", "args" : """--fail -b PART1 PART2""", },
    { "tc_name" : "fail_option_5", "args" : """--fail -c PART1 PART2""", },
    { "tc_name" : "unfail_option_1", "args" : """--unfail -r PART""", },
    { "tc_name" : "unfail_option_2", "args" : """--unfail --recursive PART""", },
    { "tc_name" : "unfail_option_3", "args" : """--unfail PART1 PART2 PART3""", },
    { "tc_name" : "unfail_option_4", "args" : """--unfail -b PART1 PART2""", },
    { "tc_name" : "unfail_option_5", "args" : """--unfail -c PART1 PART2""", },
    { "tc_name" : "savestate_option_1", "args" : """--savestate /bad/save""", },
    { "tc_name" : "savestate_option_2", "args" : """--savestate /tmp/save p1""", },
    { "tc_name" : "savestate_option_3", "args" : """--savestate""", },
    { "tc_name" : "savestate_option_4", "args" : """--savestate /tmp/save -c p1""", },
    { "tc_name" : "savestate_option_5", "args" : """--savestate /tmp/save -b p1""", },
    { "tc_name" : "xml_option_1", "args" : """--xml""", },
    { "tc_name" : "xml_option_2", "args" : """--xml p1""", },
    { "tc_name" : "xml_option_3", "args" : """--xml --recursive p1""", },
    { "tc_name" : "xml_option_4", "args" : """--xml --blockinfo""", },
    { "tc_name" : "xml_option_5", "args" : """--xml --clean_block""", },
    { "tc_name" : "xml_option_6", "args" : """--xml --recursive --blockinfo""", },
    { "tc_name" : "xml_option_7", "args" : """--xml --recursive --clean_block""", },
    { "tc_name" : "queue_option_1", "args" : """--queue""", },
    { "tc_name" : "queue_option_2", "args" : """--queue q1:q2 p1 p2 p3""", },
    { "tc_name" : "queue_option_3", "args" : """--queue kebra:bbb:myq p1""", },
    { "tc_name" : "queue_option_4", "args" : """--queue kebra:bbb:myq -c p1""", },
    { "tc_name" : "queue_option_5", "args" : """--queue kebra:bbb:myq -b p1""", },
    { "tc_name" : "queue_option_6", "args" : """--queue kebra:bbb -r -b p1""", },
    { "tc_name" : "queue_option_7", "args" : """--queue kebra:bbb -r -c p1""", },
    { "tc_name" : "dump_option_1", "args" : """--dump""", },
    { "tc_name" : "dump_option_2", "args" : """--dump p1""", },
    { "tc_name" : "dump_option_3", "args" : """--dump --recursive p1""", },
    { "tc_name" : "dump_option_4", "args" : """--dump --blockinfo""", },
    { "tc_name" : "dump_option_5", "args" : """--dump --clean_block""", },
    { "tc_name" : "dump_option_6", "args" : """--dump --recursive --blockinfo""", },
    { "tc_name" : "dump_option_7", "args" : """--dump --recursive --clean_block""", },
    { "tc_name" : "boot_stop_option_1", "args" : """--boot-stop""", },
    { "tc_name" : "boot_stop_option_2", "args" : """--boot-stop p1""", },
    { "tc_name" : "boot_stop_option_3", "args" : """--boot-stop --recursive p1""", },
    { "tc_name" : "boot_stop_option_4", "args" : """--boot-stop --blockinfo""", },
    { "tc_name" : "boot_stop_option_5", "args" : """--boot-stop --clean_block""", },
    { "tc_name" : "boot_stop_option_6", "args" : """--boot-stop --recursive --blockinfo""", },
    { "tc_name" : "boot_stop_option_7", "args" : """--boot-stop --recursive --clean_block""", },
    { "tc_name" : "boot_start_option_1", "args" : """--boot-start""", },
    { "tc_name" : "boot_start_option_2", "args" : """--boot-start p1""", },
    { "tc_name" : "boot_start_option_3", "args" : """--boot-start --recursive p1""", },
    { "tc_name" : "boot_start_option_4", "args" : """--boot-start --blockinfo""", },
    { "tc_name" : "boot_start_option_5", "args" : """--boot-start --clean_block""", },
    { "tc_name" : "boot_start_option_6", "args" : """--boot-start --recursive --blockinfo""", },
    { "tc_name" : "boot_start_option_7", "args" : """--boot-start --recursive --clean_block""", },
    { "tc_name" : "boot_status_option_1", "args" : """--boot-status""", },
    { "tc_name" : "boot_status_option_2", "args" : """--boot-status p1""", },
    { "tc_name" : "boot_status_option_3", "args" : """--boot-status --recursive p1""", },
    { "tc_name" : "boot_status_option_4", "args" : """--boot-status --blockinfo""", },
    { "tc_name" : "boot_status_option_5", "args" : """--boot-status --clean_block""", },
    { "tc_name" : "boot_status_option_6", "args" : """--boot-status --recursive --blockinfo""", },
    { "tc_name" : "boot_status_option_7", "args" : """--boot-status --recursive --clean_block""", },
    ]
