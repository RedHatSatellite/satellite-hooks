#!/usr/bin/env python

import sys, getopt
import Sat6APIUtils
import RedfishAPIUtils
import os
import ConfigParser
import syslog
import socket
import re
import shutil
import tempfile
import subprocess

class Config():
   pass

def validate_create(sat6conn, hostname):
   """
   This validates if we should run, we check is the host Hardare Model contains 'HP', the host is 'managed'
   by foreman, the commetn of the host contains a IP or DNS name. 
   """
   host_info = sat6conn.getHostInfo(hostname)
   if not host_info['managed']:
      syslog.syslog('{} validation failed: Host isn\'t managed'.format(hostname))
      exit(0)
   if host_info['model_id']:
      model_info = sat6conn.getModelInfo(host_info['model_id'])
      if not 'HP' in model_info['name'] or not model_info['name']:
         syslog.syslog('{} validation failed: Host model_info doesnt contain \'HP\''.format(hostname))
         exit(0)
   else:
      syslog.syslog('{} validation failed: Host model_info isn\'t set'.format(hostname))
      exit(0)
   try:
      if not socket.gethostbyname(host_info['comment']):
         syslog.syslog('{} validation failed: The Comment ({}) isn\'t a IP or resolvable'.format(hostname, host_info['comment']))
         exit(0)
   except:
      if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",host_info['comment']) is None:
         syslog.syslog('{} validation failed: The Comment ({}) isn\'t a IP or resolvable'.format(hostname, host_info['comment']))
         exit(0)
   return True 

def write_file(data, config, filename): 
   """
   This writes a file in the 'write path' when passed a filename & data. We use this to write the ISO before the iLO is told to mount and reboot.
   'write path' is specified in the config file
   """
   if not os.path.exists(config.write_path):
      os.makedirs(config.write_path)
   fq_path = '{}{}'.format(config.write_path,filename)
   f = open(fq_path, 'a')
   f.write(data)
   f.close
   syslog.syslog('ISO file written to {}'.format(fq_path))
   accessible_path = fq_path.replace('/var/www/html/pub','http://{}/pub'.format(config.sathostname))
   return accessible_path

def remove_file(config, filename):
   """
   This removes a file in the 'write path' when passed a filename. We use this to delete the ISO after install.
   'write path' is specified in the config file
   """
   fq_path = '{}{}'.format(config.write_path,filename)
   if os.path.isfile(fq_path):
      os.remove(fq_path)
   syslog.syslog('Deleted {}'.format(fq_path))
   return True

def enable_UEFI(BIOSisoPath, UEFIisoPath, UEFIfilesPath):
   """
   This takes the path of the old ISO and the path of a ISO to save the UEFI compatible version
   """
   syslog.syslog("Converting ISO to UEFI")
   try:
      dirpath = "/usr/share/foreman/tmp/bootdisk_hook"
      if not os.path.exists(dirpath):
         os.mkdir(dirpath)
      UEFIisoCreatePath = dirpath + '/new_iso'
      os.mkdir(UEFIisoCreatePath)
      os.mkdir(UEFIisoCreatePath + '/boot')
      os.system("isoinfo -i {} -x /BOOT/$(isoinfo -i {} -l | grep -i vmlinuz | awk \'{{print $12}}\') > {}/boot/vmlinuz".format(BIOSisoPath, BIOSisoPath, UEFIisoCreatePath))
      os.system("isoinfo -i {} -x /BOOT/$(isoinfo -i {} -l | grep -i initrd | awk \'{{print $12}}\') > {}/boot/initrd".format(BIOSisoPath, BIOSisoPath, UEFIisoCreatePath))
      os.chmod(UEFIisoCreatePath, 755)
      shutil.copytree(UEFIfilesPath + '/EFI', UEFIisoCreatePath + '/EFI')
      os.system("isoinfo -i {} -x /ISOLINUX.CFG\;1 > {}/EFI/BOOT/grub.cfg".format(BIOSisoPath, UEFIisoCreatePath))
      os.system("isoinfo -i {} -x /ISOLINUX.BIN\;1 > {}/isolinux.bin".format(BIOSisoPath, UEFIisoCreatePath))
      os.system("chmod -R 755 {} > /dev/null 2>&1".format(dirpath))
      os.system("genisoimage -U -r -v -T -J -joliet-long -V \"EFI Boot Image\" -volset \"REFI Boot Image\" "
                "-A \"EFI Boot Image\" -b isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table "
                "-eltorito-alt-boot -e EFI/images/efiboot.img -no-emul-boot -o {} {} > /dev/null 2>&1".format(UEFIisoPath, UEFIisoCreatePath))
   finally:
      shutil.rmtree(dirpath)
      pass
   syslog.syslog("Converted ISO to UEFI")
   return True

# Main
def main():
   HOOK_EVENT = sys.argv[1]
   HOOK_OBJECT = sys.argv[2]

   # Load config
   homedir = os.environ.get("HOME")
   if not os.path.isfile(homedir + '/.bootdisk_hookrc'):
      syslog.syslog("Error, ~/.bootdisk_hookrc does not exist!")
      exit(1)
 
   hookconfig = ConfigParser.ConfigParser()
   hookconfig.readfp(open(homedir+'/.bootdisk_hookrc','r'))
   config = Config()
   config.write_path = hookconfig.get('hook', 'write path')
   config.uefi_iso = hookconfig.getboolean('hook', 'uefi iso')

   config.sathostname = hookconfig.get('satellite', 'hostname')
   config.satusername = hookconfig.get('satellite', 'username')
   config.satpassword = hookconfig.get('satellite', 'password')

   config.ilousername = hookconfig.get('HP API', 'username')
   config.ilopassword = hookconfig.get('HP API', 'password')

   if HOOK_EVENT == 'after_commit' or  HOOK_EVENT == 'after_build':
      remove_file(config, '{}.iso'.format(HOOK_OBJECT))
      # Establish API Connection to Satellite
      sat6conn = Sat6APIUtils.Sat6APIUtils(config.sathostname, config.satusername, config.satpassword)
      validate_create(sat6conn, HOOK_OBJECT)
      ilo_address = sat6conn.getHostInfo(HOOK_OBJECT)['comment']
      bootdisk_iso = sat6conn.getHostBootDisk(HOOK_OBJECT, full=True)
      # Write bootdisk
      accessible_path = write_file(bootdisk_iso, config, '{}.iso'.format(HOOK_OBJECT))
      if config.uefi_iso:
         old_iso = config.write_path + '{}.iso'.format(HOOK_OBJECT)
         new_EFI_iso = config.write_path + '{}.iso'.format(HOOK_OBJECT)
         enable_UEFI(old_iso, new_EFI_iso, "{}UEFI".format(config.write_path))

      # Now we have ilo_address, accessible_path (ISO) for the host and the username/password from the config lets do the exciting stuff
      iLO_https_host = 'https://{}'.format(ilo_address)
      # Establish API Connection to HP API
      redfish = RedfishAPIUtils.RedfishAPIUtils(ilo_address, config.ilousername, config.ilopassword)
      if redfish.mount_virtual_media_iso(accessible_path, True) == 1:
         exit(1)
      if redfish.reset_server() == 1:
         exit(1)
      exit(0)

   if HOOK_EVENT == 'before_provision':
      remove_file(config, '{}.iso'.format(HOOK_OBJECT))
      exit(0)

# call main
if __name__ == "__main__":
   main()
