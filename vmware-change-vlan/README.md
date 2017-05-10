# vmware-change-vlan
This hook can be used to change VLAN of a VM in vCenter after the VM has been provisioned on e.g. a provisioning network.

It is fairly common that there are networks in your organization where you don't have DHCP. In this case, it is possible to set up a provisioning network, where Satellite (or a Capsule) is allowed to act as DHCP server in order to be able to PXE boot new VMs. After the VM has been provisioned on the provisioning network, it has to be moved to the correct target network and that is the purpose of this hook.

The idea is that when a host leaves build mode, the hook "before_provision" is executed (I know, the name does not make much sense). This hook then executes a script called "vcenter-change-host-vlan.py" that connects to the vCenter API and change the VLAN of a specified VM. vcenter-change-host-vlan.py supports both VDS (Virtual Distributed Switches) and Standard Switches, by either using the "--is_VDS" flag or not.

## Prerequisites
- python requests needs to be installed: http://docs.python-requests.org/en/master/
- jq needs to be installed, since it is used by 01-change-host-vlan.sh: https://stedolan.github.io/jq/download/ 
- the hook script, 01-change-host-vlan.sh, needs to be placed in /usr/share/foreman/config/hooks/host/managed/before_provision/ on the Satellite server
- the script that talks to the vCenter API, vcenter-change-host-vlan.py, needs to be placed somewhere in the foreman users path, e.g. /usr/local/sbin/
- vCenter URL and credentials for a service user that is allowed to edit the host objects in the vCenter needs to be added in the vcenter-change-host-vlan.py script (see row 32 of the script)
- when provisioning a new VM, the user needs to specify the name of the target VLAN (the VLAN that the VM should be moved to) as a Parameter, e.g. "target_vlan: vlan1234". That value is then extracted by 01-change-host-vlan.sh and provided to vcenter-change-host-vlan.py. 

In order to make the whole provisioning workflow automated, the kickstart files used also need to configure network settings correctly in the VM, but that is out of scope of this hook.

## Troubleshooting
see https://github.com/theforeman/foreman_hooks
