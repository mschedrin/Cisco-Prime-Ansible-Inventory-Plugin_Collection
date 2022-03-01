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

## Known issues
Due to Cisco Prime API limitations the script will fail if device group names contain comma. 