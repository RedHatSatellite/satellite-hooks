# HP-UEFI

Hook scripts for Foreman/Red Hat Satellite to provision hosts using the foreman bootdisk host image.

When DHCP servers are not available in a subnet the foreman bootdisk ISO imaga can be used to bootstrap a systems and start a kickstart installation.

To make the process of provisioning systems automatic this hooks will automate the following tasks:

When a host is created, or placed in build mode the hook will:

    Download the bootdisk ISO from satellite
    Copy it to /var/www/html/pub/bootdisk_hook/
    Optionally add UEFI support to it.
    Connect the bootdisk ISO image to the host.
    Configure the host to boot from CD-Rom.

When the kicstart reports to foreman that the host is built:

    Remove/Disconnect/Unmount the ISO image from the host.
    Reconfigure the host to boot from hard drive.
    Start the host.

There is validation before any of the above runs:
 - Hosts model name must contains 'HP' string
 - Hosts comment must contain the iLO address


## Requirements

### yum 

- `yum install python-requests -y`


### Install

1. `mkdir -p /usr/share/foreman/config/hp-uefi`
1. `cd /usr/share/foreman/config/`
1. `git clone https://github.com/RedHatSatellite/satellite-hooks.git`
1. `cp -r satellite-hooks/hp-uefi hp-uefi`
1. `rm -rf satellite-hooks`
1. `cd hp-uefi`
1. `chmod +x hp_hook.py`
1. `mkdir -p /usr/share/foreman/config/hooks/host/managed/create/`
1. `mkdir -p /usr/share/foreman/config/hooks/host/managed/after_build/`
1. `mkdir -p /usr/share/foreman/config/hooks/host/managed/before_provision/`
1. `ln -s /usr/share/foreman/config/hp-uefi/hp_hook.py /usr/share/foreman/config/hooks/host/managed/create/hp_hook.py` # Run when host is created
1. `ln -s /usr/share/foreman/config/hp-uefi/hp_hook.py /usr/share/foreman/config/hooks/host/managed/after_build/hp_hook.py` # Run when put into Build mode
1. `ln -s /usr/share/foreman/config/hp-uefi/hp_hook.py /usr/share/foreman/config/hooks/host/managed/before_provision/hp_hook.py` # Run when a host completes the OS install
1. `restorecon -RvF /usr/share/foreman/config`
1. `chown -R foreman. /usr/share/foreman/config/hooks/
1. `cp /usr/share/foreman/config/hp-uefi/example-confrc /usr/share/foreman/.bootdisk_hookrc`
1. `chown foreman. /usr/share/foreman/.bootdisk_hookrc`
1. `systemctl reload  httpd`


NOTE: if selinux is in enforcing mode, you will get denials: use `audit2why` & `audit2allow` to reolve these. 

### UEFI Support

[Foreman_bootdisk](https://github.com/theforeman/foreman_bootdisk) currently doesn't support UEFI, this hook can use a workaround that will regenerate the full-host ISO with UEFI support. This as a few extra requirements..

#### UEFI Requirements

In order to recreate a ISO with UEFI support we need the following files stored in 'write path'/UEFI/. e.g `/var/www/html/pub/bootdisk_hook/UEFI/
- copy all of the /EFI/ directory from the RHEL7 install ISO
- During the ISO regeneration process we use the isolinux.cfg on the old ISO as /EFI/BOOT/grub.cfg, this means there is no support of legacy BIOS. It also means we need to modify the PXELinux template as follows:
```ruby
<% if @host.params['UEFI_bootdisk'] %>
set timeout=3
set default=0
insmod gzio
insmod part_gpt
insmod ext2
menuentry '<%= @host %> Installation' {
  linuxefi /boot/vmlinuz ks=<%= foreman_url('provision')%> ksdevice=<%= @host.mac %> network kssendmac <%= dhcp ? '' : "ip=#{@host.ip} netmask=#{subnet.mask} gateway=#{subnet.gateway} dns=#{subnet.dns_primary}" %>
  initrdefi /boot/initrd
}
<% else %>
.... default template content ...
<% end -%>

```

### Troubleshooting
Foreman will run this script as the `foreman` user, we can use `sudo -u foreman /usr/share/foreman/config/satellite-hook/hp_hook.py create test1.example.com` to test it. It also logs to syslog, so /var/log/messages in most configurations. Also see the [foreman_hooks documentation](https://github.com/theforeman/foreman_hooks) for information regarding foreman_hooks

