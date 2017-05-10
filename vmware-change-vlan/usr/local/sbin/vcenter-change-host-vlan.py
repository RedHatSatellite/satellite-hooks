#!/usr/bin/env python
"""
This script is a rework of the following pyvmomi community sample:
https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/change_vm_vif.py

The wait_for_tasks() function is copied from here:
https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/tasks.py

The function is put directly in this script to remove dependencies from the tools directory.

"""

import atexit
from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl
import argparse
import sys
import syslog
import json

parser = argparse.ArgumentParser(description='vcenter-change-host-vlan.py')
parser.add_argument('--hostname', required=True, help='The name of the host you want to modify')
parser.add_argument('--target_vlan', required=True, help='The name VLAN you want to move the host to')
parser.add_argument('--is_VDS', action="store_true", default=False, help='Use this flag if the network have a VDS (Virtual Distributed Switch)')

args = parser.parse_args()

hostname = args.hostname
target_vlan = args.target_vlan

# Insert address and credentials for the vCenter your VM exist in
vcenter = "<vcenter url>"
username = "<vcenter user>"
password = "<vcenter password>"
port = 443

# You can remove these if you don't want to clutter syslog
syslog.syslog("DEBUG: vcenter-change-host-vlan.py")
syslog.syslog("DEBUG: hostname: " + hostname)
syslog.syslog("DEBUG: target VLAN: " + target_vlan)
syslog.syslog("DEBUG: vCenter: " + vcenter)

def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype, True)
    for view in container.view:
        if view.name == name:
            obj = view
            break
    return obj

def wait_for_tasks(service_instance, tasks):
    """Given the service instance si and tasks, it returns after all the
   tasks are complete
   """
    property_collector = service_instance.content.propertyCollector
    task_list = [str(task) for task in tasks]
    # Create filter
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                 for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                               pathSet=[],
                                                               all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        # Loop looking for updates till the state moves to a completed state.
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()

def change_device():
    """
    Function for changing a virtual machines NIC.
    """
    service_instance = connect.SmartConnect(host=vcenter, user=username, pwd=password, port=port)
    atexit.register(connect.Disconnect, service_instance)
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], hostname)

    # This code is for changing only one Interface. For multiple Interface
    # Iterate through a loop of network names.
    device_change = []
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualEthernetCard):
            nicspec = vim.vm.device.VirtualDeviceSpec()
            nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            nicspec.device = device
            nicspec.device.wakeOnLanEnabled = True

            if args.is_VDS:
                syslog.syslog("vcenter-change-host-vlan.py: VDS flag is used")
                network = get_obj(content, [vim.dvs.DistributedVirtualPortgroup], args.target_vlan)
                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = network.key
                dvs_port_connection.switchUuid = network.config.distributedVirtualSwitch.uuid
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nicspec.device.backing.port = dvs_port_connection
            else:
                syslog.syslog("vcenter-change-host-vlan.py: VDS flag is not used")
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicspec.device.backing.network = get_obj(content, [vim.Network], target_vlan)
                nicspec.device.backing.deviceName = target_vlan

            nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nicspec.device.connectable.startConnected = True
            nicspec.device.connectable.connected = True
            nicspec.device.connectable.allowGuestControl = True
            device_change.append(nicspec)
            break

    config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
    task = vm.ReconfigVM_Task(config_spec)
    wait_for_tasks(service_instance, [task])
    syslog.syslog("vcenter-change-host-vlan.py: Successfully changed nic device for " + hostname + " to " + target_vlan)

    return 0

def print_device():
    """
    Function for printing a virtual machines NIC.
    """
    try:
        service_instance = connect.SmartConnect(host=vcenter, user=username, pwd=password, port=port)
        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], hostname)

        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                if args.is_VDS:
                   syslog.syslog("vcenter-change-host-vlan.py: " + hostname + " has VirtualEthernetCard device with switchUuid: " + str(device.backing.port.switchUuid))
                else:
                   syslog.syslog("vcenter-change-host-vlan.py: " + hostname + " has VirtualEthernetCard device with deviceName: " + str(device.backing.deviceName))

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

# Start program
if __name__ == "__main__":
    print_device()
    change_device()
    print_device()

