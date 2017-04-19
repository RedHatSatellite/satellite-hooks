import requests
import json
import ConfigParser
import os
class Sat6APIUtils:
   # Init
   def __init__(self, hostname, username, password):
      self.post_headers = {'content-type': 'application/json'}
      self.put_headers = {'content-type': 'application/json'}
      self.https = False
      self.protocol = 'https'
      self.hostname = hostname
      self.username = username
      self.password = password
   # Wrappers:
   # getRequest Wrapper
   def getRequest(self,url,data=False,**kwargs):
      self.url = url
      # Generate the URL
      self.fullurl = "%s://%s/%s" % (self.protocol, self.hostname, self.url)
      r = requests.get(self.fullurl, auth=(self.username, self.password), verify=self.https, params=kwargs)
      if not str(r).find("[200]"):
         print "Error, get: API call failed! (url: '"+self.fullurl+"', params: '"+str(kwargs)+"', response: '"+str(r)+"')"
         return 1
      if data:
         return r.content
      return r.json()
   # putRequest Wrapper
   def putRequest(self,url,data):
      self.url = url
      self.data = data
      # Generate the URL
      self.fullurl = "%s://%s/%s" % (self.protocol, self.hostname, self.url)
      r = requests.put(self.fullurl, auth=(self.username, self.password), verify=self.https, data=json.dumps(self.data), headers=self.put_headers)
      # Success response is: Response [200]
      if str(r).find("[200]"):
         return 0
      else:
         print "Error, put: API call failed! (url: '"+self.fullurl+"', data: '"+str(self.data)+"', response: '"+str(r)+"')"
         return 1
      return 1
   # GET:
   def getOrganizationByName(self,organization_label):
      return self.getRequest('katello/api/v2/organizations', search=organization_label, full_results='yes')['results'][0]
   def getOrganizationIDByName(self,organization_label):
      return self.getOrganizationByName(organization_label)[u'id']
   def getContentViews(self,organization_id):
      return self.getRequest('katello/api/v2/content_views', organization_id=organization_id)
   def getLVEnvIDbyName(self,organization_id,environment):
      env_results = self.getRequest('katello/api/v2/environments', organization_id=organization_id, search=environment, full_results='yes')
      return env_results['results'][0]['id']
   def getCVIDbyName(self,organization_id,content_view):
      cv_results = self.getRequest('katello/api/v2/content_views', organization_id=organization_id, search=content_view, full_results='yes')
      return cv_results['results'][0]['id']
   def getHostCollectionID(self,org_id,host_collection):
      url = 'katello/api/v2/organizations/%s/host_collections' % (org_id)
      host_collection_info = self.getRequest(url, organization_id=org_id, name=host_collection,)['results'][0]
      returndict = {}
      returndict['host_collection_id'] = host_collection_info['id']
      returndict['host_collection_hostcount'] = host_collection_info['total_content_hosts']
      return returndict
   def getHostsFromHostCollection(self,org_id,host_collection):
      hc_info = self.getHostCollectionID(org_id, host_collection)
      hc_id = hc_info['host_collection_id']
      hc_hostcount = hc_info['host_collection_hostcount']
      url = 'katello/api/v2/host_collections/%s/systems' % (hc_id)
      content_hosts = self.getRequest(url,id=hc_id)['results']
      return content_hosts
   def getHostIDsFromHostCollection(self,org_id,host_collection):
      content_hosts = self.getHostsFromHostCollection(org_id,host_collection)
      hc_host_ids = []
      for host in range (len(content_hosts)):
         host_id = content_hosts[host]['id']
         hc_host_ids.append(host_id)
      return hc_host_ids
   def getHostInfo(self,host_id):
      url = 'api/v2/hosts/%s' % (host_id)
      retstat = self.getRequest(url)
      return retstat
   def getModelInfo(self,model_id):
      url = 'api/v2/models/%s' % (model_id)
      retstat = self.getRequest(url)
      return retstat
   def getHostBootDisk(self,host_id,full=False):
      if full:
         url = 'bootdisk/api/v2/hosts/%s?full=true' % (host_id)
      else:
         url = 'bootdisk/api/v2/hosts/%s' % (host_id)
      retstat = self.getRequest(url,data=True)
      return retstat
   # SET:
   def setHostCollectionContentView(self,org_id,content_view_id,environment_id,host_collection):
      # First get the list of host ids in the HC
      hc_host_ids = self.getHostIDsFromHostCollection(org_id,host_collection)
      url = "katello/api/v2/systems/bulk/environment_content_view"
      # works with: 'included': {'ids': [1,2]},
      data = {'organization_id': org_id,
              'included': {'ids': hc_host_ids},
              'content_view_id': content_view_id,
              'environment_id': environment_id}
      print "   setHostCollectionContentView: called with data: '" + str(data) + "'"
      retstat = self.putRequest(url, data)
      return retstat
