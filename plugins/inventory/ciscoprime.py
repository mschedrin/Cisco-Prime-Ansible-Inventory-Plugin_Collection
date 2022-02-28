import urllib3, requests, re, sys
# from pprint import pprint
from ansible.module_utils.six.moves.urllib.parse import urljoin
from ansible.errors import AnsibleError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable, to_safe_group_name

DOCUMENTATION = """
    name: ciscoprime
    plugin_type: inventory
    author:
        - Mikhail Shchedrin mschedrin@gmail.com 
    short_description: Cisco Prime inventory plugin
    description:
        - Ansible dynamic inventory plugin for Cisco Prime Infrastructure
    extends_documentation_fragment:
        - constructed
        - inventory_cache
    options:
        plugin:
            description: token that ensures this is a source file for the 'ciscorpime' plugin.
            required: True
            choices: ['ciscoprime']
            type: str
        api_endpoint:
            description: "Endpoint of the Cisco Prime API, for example: https://<prime ip address>/webacs/api/v4"
            required: True
            env:
                - name: CISCOPRIME_API_URL
            type: str
        api_user:
            required: True
            description: Cisco Prime username
            env:
                - name: CISCOPRIME_USER
            type: str
        api_password:
            required: True
            description: Cisco Prime password
            env:
                - name: CISCOPRIME_PASSWORD
            type: str
        api_max_results: 
            description: Cisco Prime pagination parameter, default value is 1000 and it matches Prime default value
            default: 1000
            type: integer
        validate_certs:
            description: Allows connection when SSL certificates are not valid.
            default: True
            type: boolean
        cache_plugin: 
            desciprtion: Cache plugin to use for caching. To get list of supported plugins use command `ansible-doc -t cache -l`
            default: jsonfile
            type: str
        cache_connection:
            default: /tmp
            type: str
        cache_force_update:
            description: Force inventory cache update regardless cache timeouts
            type: bool
            default: False
        timeout:
            description: Timeout for CPI requests in seconds
            type: int
            default: 60
        exclude_unmanaged:
            description: Exclude from inventory hosts which are marked "unmanaged" in Cisco Prime
            type: bool
            default: True

"""
EXAMPLES = """
# ciscoprime_inventory.yml file in YAML format
# Example command line: ansible-inventory -v --list -i ciscoprime_inventory.yml

plugin: ciscoprime
api_endpoint: https://prime.local/webacs/api/v4
api_user: ansible # you can fill your token here, but you should rather use environment variable CISCOPRIME_USER
api_password: ansible_password # you can fill your password here, but you should rather use environment variable CISCOPRIME_PASSWORD
api_max_results: 1000 # Cisco Prime pagination parameter, default value is 1000 and it matches Prime default value
validate_certs: True 
cache: True # use ansible cache for inventory
cache_plugin: jsonfile 
cache_connection: /tmp/ # where to put cache files
cache_timeout: 86400 #seconds
timeout: 15 # api timeout
exclude_unmanaged: True # Exclude from inventory hosts which are marked "unmanaged" in Cisco Prime
"""




class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = 'ciscoprime'  # used internally by Ansible, it should match to field in inventory .yml file: plugin:ciscoprime
    #NAME = 'mschedrin.ciscoprime.ciscoprime' # it must include namespace for ansible 2.9 and older
    re_flags = 0
    prime_to_ansible_variable_mapping = { #map certain variable names to ansible names
        'deviceName': 'ansible_host',
        'softwareType': 'ansible_network_os',
    } 
    prime_to_ansible_os_mapping = {
        'asa': 'asa',
        'IOS':'ios',
        'IOS-XE':'ios',
        'IOS XR':'iosxr',
        'NX OS': 'nxos' }

    def _http_request(self, url):
        # if cache is disabled or request is not cached
        if not self._use_cache or url not in self._cache.get(self.cache_key, {}): 
            self.display.vvvvv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Cache miss or it's disabled(use_cache={self._use_cache})")
            if self.cache_key not in self._cache:
                self.display.vvvvv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Cache does not exist, create new")
                self._cache[self.cache_key] = {url: ''}
            self.display.vvvvv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Sending get request {url}")
            r = requests.get(url, auth=(self.api_user, self.api_password), verify=self.validate_certs)
            if r.status_code not in range(200,300):
                raise AnsibleError(f'Got unexpected HTTP code {r.status_code} when sending GET request {url}')
            self._cache[self.cache_key][url] = r.json()
        else: 
            self.display.vvvvv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Cache hit")
        return self._cache[self.cache_key][url]

    def _filter_device_groups(self, device_groups, filters):
        result = list()
        for f in filters:
            result += [ grp for grp in device_groups['groups'] if re.match(f, grp['name'], self.re_flags)  ]
        return result
    
    def _filter_device_hostnames(self, devices, filters):
        result = list()
        for f in filters:
            result += [ dev for dev in devices if re.match(f, dev['sysName'], self.re_flags) ]
        return result

    def _check_device_match_filters(self, device, filters):
        for f in filters:
            if re.match(f, device['sysName'], self.re_flags):
                return device
        return False

    def _get_devices(self):
        index = 0
        url = f"{self.api_endpoint}/data/Devices.json?.full=true&.maxResults={self.api_max_results}&.firstResult={index}"
        self.display.vv("Getting devices from CPI")
        r = self._http_request(url)['queryResponse']
        raw_hosts = r['entity']
        self.display.vv(f"Got {len(raw_hosts)} out of {r['@count']} hosts")
        while r['@last']+1 < r['@count']: #if there are more hosts
            index = r['@last']+1
            url = f"{self.api_endpoint}/data/Devices.json?.full=true&.maxResults={self.api_max_results}&.firstResult={index}"
            self.display.vv(f"Requesting more hosts from CPI")
            r = self._http_request(url)['queryResponse']
            raw_hosts+=r['entity']
            self.display.vv(f"Got {len(r['entity'])} more hosts")
        return raw_hosts

    def _get_groups(self):
        index = 0
        url = f"{self.api_endpoint}/data/GroupSpecification.json?.full=true&.maxResults={self.api_max_results}&.firstResult={index}"
        self.display.vv("Getting device groups from CPI")
        r = self._http_request(url)['queryResponse']
        raw_groups = r['entity']
        self.display.vv(f"Got {len(raw_groups)} out of {r['@count']} groups")
        while r['@last']+1 < r['@count']: #if there are more groups        
            index = r['@last']+1
            url = f"{self.api_endpoint}/data/GroupSpecification.json?.full=true&.maxResults={self.api_max_results}&.firstResult={index}"
            self.display.vv(f"Requesting more groups from CPI")
            r = self._http_request(url)['queryResponse']
            raw_groups+=r['entity']
            self.display.vv(f"Got {len(r['entity'])} more groups")        
        #make group id to index in dictinary
        groups = {}
        for raw_group in raw_groups:
            groups[raw_group['groupSpecificationDTO']['@id']] = raw_group['groupSpecificationDTO']
        return groups
    
    def _get_devices_by_group_path(self, group_path):
        #url = f"{self.api_endpoint}/data/InventoryDetails.json?.group=/{group_path}&.full=true" # much more details
        url = f"{self.api_endpoint}/data/Devices.json?.group=/{group_path}&.full=true"
        r = self._http_request(url)['queryResponse']
        if r['@count'] > 0:
            return r['entity']
        else:
            return []

    def _set_host_variables(self, hostname, variables_list):
        for variable_name, value in variables_list.items():
            variable_name = self.prime_to_ansible_variable_mapping.get(variable_name, variable_name)
            self.inventory.set_variable(hostname, variable_name, value)
            if variable_name == 'ansible_network_os':
                value = self.prime_to_ansible_os_mapping.get(value, value)
                self.inventory.set_variable(hostname, variable_name, value)

    def _add_device(self, device, group_name=None):
        hostname = device['deviceName']
        self.display.vvvv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Adding host: {hostname}")
        if group_name:
            self.inventory.add_host(group=group_name, host=hostname)
        else:
            self.inventory.add_host(host=hostname)
        self._set_host_variables(hostname, device)

    def _add_group(self, group_name):
        self.inventory.add_group(group_name)

    def _add_child(self, parent_group_name, child_entity_name):
        return self.inventory.add_child(parent_group_name, child_entity_name)
    
    def _populate_ansible_inventory(self,):
        self.display.vvvv(f"In {sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno}")
        raw_hosts = self._get_devices()
        groups = self._get_groups()
        # add all groups
        for grp_id, group in groups.items():
            self._add_group(to_safe_group_name(group['groupName']))
        # establish group hierarchy
        for grp_id, group in groups.items():
            if group.get('parentId') > 0:
                child_group_name = to_safe_group_name(group.get('groupName'))
                parent_group_name = to_safe_group_name(groups[group['parentId']]['groupName'])
                self.display.vvvv(f"In {sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Adding {parent_group_name}/{child_group_name}")
                try:
                    self._add_child(parent_group_name, child_group_name)
                except Exception as e:
                    self.display.warning(str(e))
                    continue
        # add all hosts
        for raw_host in raw_hosts:
            host = raw_host['devicesDTO']
            if not ( host['adminStatus'] == "UNMANAGED" and self.exclude_unmanaged ): 
                self._add_device(host)
        # assign hosts to groups
        for grp_id, group in groups.items():
            self.display.vvvv(f"Processing {group.get('groupPath')}")
            raw_hosts = self._get_devices_by_group_path(group.get('groupPath'))
            for raw_host in raw_hosts:
                host = raw_host['devicesDTO']
                self.display.vvvv(f"\tadding {host['deviceName']}")
                self._add_child(to_safe_group_name(group['groupName']), host['deviceName'])
            
    def parse(self, inventory, loader, path, cache=True):
        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache=cache)
        self.config = self._read_config_data(path=path)
        self.api_endpoint = self.get_option("api_endpoint")
        self.api_user = self.get_option("api_user")
        self.api_password = self.get_option("api_password")
        self.api_max_results = self.get_option("api_max_results")
        self.validate_certs = self.get_option("validate_certs")
        self.exclude_unmanaged = self.get_option("exclude_unmanaged")
        self.cache_force_update = self.get_option("cache_force_update")
        self.cache_key = self.get_cache_key(path)

        if not self.validate_certs:
            urllib3.disable_warnings()
        self.timeout = self.get_option("timeout")
        self.display.vvvv(f"Plugin configuration: {self.config}")

        self.display.vvvv("Cache location: {}{}".format(self.get_option("cache_connection"),self.cache_key))
        self.display.vvvv("Plugin path: "+path)

        if cache: #if caching enabled globally
            self._use_cache = self.get_option('cache') #read cache parameter from plugin config
        else:
            self._use_cache = False

        if self.cache_force_update:
            self._cache[self.cache_key] = {} 
                
        self.display.vv(f"{sys._getframe(  ).f_code.co_name}:{sys._getframe(  ).f_lineno} Populate ansible inventory")
        self._populate_ansible_inventory()
