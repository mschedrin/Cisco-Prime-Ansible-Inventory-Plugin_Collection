# Ansible galaxy collection with dynamic inventory plugin for Cisco Prime Infrastructure

## Installation and usage in Ansible 
Create file `collections/requirements.yml` in your working directory:
```
collections:
   - name: https://github.com/mschedrin/Cisco-Prime-Ansible-Inventory-Plugin_Collection.git
     type: git
     version: master
```
Install necessary python modules `pip install urllib3 requests`

Install Cisco-Prime-Ansible-Inventory-Plugin_Collection `ansible-galaxy install -r collections/requirements.yml `

Make sure it has installed correctly: `ansible-doc -t inventory mschedrin.ciscoprime.ciscoprime`. You should see plugin documentation. 

Create inventory file `cpi-inventory.yaml`. Example:
```
---
plugin: mschedrin.ciscoprime.ciscoprime
validate_certs: False
cache: True # use ansible cache for inventory
cache_plugin: jsonfile
cache_connection: /tmp/ # where to put cache files
cache_timeout: 86400 #seconds
timeout: 15 # api timeout
exclude_unmanaged: True # Exclude from inventory hosts which are marked "unmanaged" in Cisco Prime
```

Declare environment variables
```
export CISCOPRIME_API_URL=https://<prime host>/webacs/api/v4/ \
    CISCOPRIME_USER=primeuser \
    CISCOPRIME_PASSWORD=primepassword
```

Enable API usage for prime user in Cisco Prime GUI. 

Run ansible inventory and verify results `ansible-inventory -i cpi-inventory.yml --graph`. If it fails or works unexpected try adding `-vvvvv` key to the command to increase output verbosity.

## Installation in AWX
### Cisco Prime
Enable API usage for prime user in Cisco Prime GUI. 

### Repository with inventory configuration
Create repository with inventory configuration. You will need to create two files in the repository: `cpi_inventory.yml` and `collections/requirements.yml`.
`collections/requirements.yml` contains reference to ansible galaxy collection and will be installed upon first inventory run:
```
collections:
   - name: https://github.com/mschedrin/Cisco-Prime-Ansible-Inventory-Plugin_Collection.git
     type: git
     version: master
```
`cpi_inventory.yml` is a configuration file for your inventory. You can check documentation by running `ansible-doc -t inventory mschedrin.ciscoprime.ciscoprime` on an ansible installation, check out [Installation and usage in Ansible](installation-and-usage-in-ansible).
Example file:
```
---
plugin: mschedrin.ciscoprime.ciscoprime
validate_certs: False
cache: True # use ansible cache for inventory
cache_plugin: jsonfile
cache_connection: /tmp/ # where to put cache files
cache_timeout: 86400 #seconds
timeout: 15 # api timeout
exclude_unmanaged: True # Exclude from inventory hosts which are marked "unmanaged" in Cisco Prime
```
### AWX configuration
Create Project that is linked to newly created repository with inventory configuration.

Create Credential Type. Input configuration(YAML):
```
fields:
  - id: username
    type: string
    label: CPI Username
    secret: false
  - id: password
    type: string
    label: CPI Password
    secret: true
  - id: api_endpoint
    type: string
    label: CPI API Endpoint
    secret: false
required:
  - username
  - password
  - api_endpoint
```
Injector configuration(YAML):
```
env:
  CISCOPRIME_USER: '{{ username }}'
  CISCOPRIME_API_URL: '{{ api_endpoint }}'
  CISCOPRIME_PASSWORD: '{{ password }}'
```

Create Credential of newly created Credential Type. Populate CPI API Endpoint, username and password of user that has API access. CPI API Endpoint format: `https://<hostname>/webacs/api/v4`

Create Inventory. Create Inventory Source. Use Credential and Project that you created in previous steps. Inventory file: / (project root). 

Run inventory sync.

If it dows not work as expected, increase Inventory Source verbosity to debugging level and check inventory sync job output. 

## Known issues
Due to Cisco Prime API limitations the script will fail if device group names contain comma. 