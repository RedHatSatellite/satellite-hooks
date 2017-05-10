#!/bin/bash

# Description: This script is used as a Foreman hook to change change the VLAN of newly provisioned VMs in vCenter 
# It should be placed in /usr/share/foreman/config/hooks/host/managed/before_provision/ in order to be executed as soon as a host leave build mode
#
# Foreman hooks get the object that triggers the hook on stdin and is executed in the following manner:
# echo '{"host":{"name":"foo.example.com"}}' | ~foreman/config/hooks/host/managed/before_provision/01-before-provision.sh before_provision foo.example.com
# This command can be used to debug the script by adding arbitrary data in the json on stdin
#
# Prerequisites: This scripts requires the script "vcenter-change-host-vlan.py" to be in the path for the foreman user, e.g. here:
# /usr/local/sbin/vcenter-change-host-vlan.py

# Remove the logger lines if you don't want to clutter syslog
logger "01-change-host-vlan.sh $2"

# Get host object from stdin
host_object=$(cat -)

# Extract parameters from host object
hostname=$(echo $host_object | jq '.host.name')
target_vlan=$(echo $host_object | jq '.host.all_parameters[] | select(.name=="target_vlan") | .value')

# Remove "" from paramters
hostname=${hostname//\"}
target_vlan=${target_vlan//\"}

logger "01-change-host-vlan.sh $hostname: Target VLAN: $target_vlan"

# Check that parameters are set
if [ -z "$hostname" ] || [ -z "$target_vlan"]  
then
    logger "01-change-host-vlan.sh $hostname: ERROR: hostname or target_vlan not set correctly"
    logger "01-change-host-vlan.sh $hostname: Exiting..."
    exit 1
fi


# If you are using virtual distributed switches, add the --is_VDS flag

logger "01-change-host-vlan.sh: executing vcenter-change-host-vlan.py --hostname $hostname --target_vlan $target_vlan"
vcenter-change-host-vlan.py --hostname $hostname --target_vlan $target_vlan

