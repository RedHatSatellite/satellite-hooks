import requests
import json
import syslog
import time

class RedfishAPIUtils:
   # Init
   def __init__(self, hostname, username, password):
      self.post_headers = {'content-type': 'application/json'}
      self.put_headers = {'content-type': 'application/json'}
      self.patch_headers = {'content-type': 'application/json'}
      self.https = False
      self.protocol = 'https'
      self.hostname = hostname
      self.username = username
      self.password = password

   # Wrappers:
   # getRequest Wrapper
   def patchRequest(self,url,data=False,**kwargs):
      self.url = url
      self.data = data
      # Generate the URL
      self.fullurl = "%s://%s/%s" % (self.protocol, self.hostname, self.url)
      r = requests.patch(self.fullurl, auth=(self.username, self.password), verify=self.https, data=json.dumps(self.data), headers=self.put_headers)
      if not r.status_code == 200:
         syslog.syslog("Error, patch: API call failed! (url: '"+self.fullurl+"', params: '"+str(data)+"', response: '"+str(r.content)+"')")
         return 1,json.loads(r.content)
      return 0,r.content
   def postRequest(self,url,data=False,**kwargs):
      self.url = url
      self.data = data
      # Generate the URL
      self.fullurl = "%s://%s/%s" % (self.protocol, self.hostname, self.url)
      r = requests.post(self.fullurl, auth=(self.username, self.password), verify=self.https, data=json.dumps(self.data), headers=self.put_headers)
      if not r.status_code == 200:
         syslog.syslog("Error, post: API call failed! (url: '"+self.fullurl+"', params: '"+str(data)+"', response: '"+str(r.content)+"')")
         return 1
      return r.content

   def eject_virtual_media(self):
      url = 'redfish/v1/Managers/1/VirtualMedia/2/'
      data = {}
      syslog.syslog('Sending API request to eject Virtual CD on {}'.format(self.hostname))
      retstat = self.postRequest(url, data)
      return retstat
      
   def mount_virtual_media_iso(self, iso_path, BootOnNextServerReset):
      url = 'redfish/v1/Managers/1/VirtualMedia/2/'
      data = {"Image": iso_path, 
              "Oem": {"Hp": {"BootOnNextServerReset": BootOnNextServerReset}}}
      syslog.syslog('Sending API request to {} to mount {}, BootOnNextServerReset set to {}'.format(self.hostname, iso_path, BootOnNextServerReset))
      wait = 40
      i = 0
      while True:
         i += 1
         retstat,content = self.patchRequest(url, data)
         if retstat == 1 and content["error"]["@Message.ExtendedInfo"][0]['MessageID']:
           syslog.syslog('Mount API failed, waiting {} seconds and trying again'.format(wait))
           time.sleep(wait)
           if content["error"]["@Message.ExtendedInfo"][0]['MessageID'] == "iLO.0.10.MaxVirtualMediaConnectionEstablished":
             #self.eject_virtual_media()
             pass
         if retstat == 0 or i == 6:
            break
      return retstat
   def reset_server(self):
      url = 'redfish/v1/Systems/1/'
      data = {"Action": "Reset", "ResetType": "ForceRestart"}
      syslog.syslog('Sending API request to reboot {}'.format(self.hostname))
      retstat = self.postRequest(url, data)
      return retstat
