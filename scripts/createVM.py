import subprocess, traceback, platform, json, time, os

from haikunator import Haikunator
from datetime import datetime
from msrestazure.azure_exceptions import CloudError

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule, SecurityRuleAccess, SecurityRuleDirection, SecurityRuleProtocol, PublicIPAddress, PublicIPAddressDnsSettings
from azure.mgmt.network import NetworkManagementClient, models

haikunator = Haikunator()

def get_json_data(url):
    with open(url, 'r') as f:
        contenu = f.read()        
        donnees = json.loads(contenu)
        return donnees

def set_json_data(url, data):
    with open(url, 'w') as f:
        # Écrire les nouvelles données dans le fichier
        json.dump(data, f)

        
def get_credentials():
    subscription_id = subscription
    credentials = ServicePrincipalCredentials(
        client_id=client,
        secret=secret,
        tenant=tenant
    )
    return credentials, subscription_id

def createVM():
    """Virtual Machine management example."""
    #
    # Create all clients with an Application (service principal) token provider
    #
    credentials, subscription_id = get_credentials()
    resource_client = ResourceManagementClient(credentials, subscription_id)
    compute_client = ComputeManagementClient(credentials, subscription_id)
    network_client = NetworkManagementClient(credentials, subscription_id)

    ###########
    # Prepare #
    ###########

    # Create Resource group
    print('{} > Create Resource Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    resource_client.resource_groups.create_or_update(
        GROUP_NAME, 
        {
            "location": LOCATION
        }
    )

    try:
        # Create a NIC
        nic = create_nic(network_client)

        #############
        # VM Sample #
        #############

        # Create VM
        print('{} > Creating {} Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name_os))
        vm_parameters = create_vm_parameters(nic.id, VM_RESOURCES)
        async_vm_creation = compute_client.virtual_machines.create_or_update(
            GROUP_NAME, 
            VM_NAME, 
            vm_parameters
        )
        async_vm_creation.wait()

        # Tag the VM
        print('{} > Adding Tag Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        async_vm_update = compute_client.virtual_machines.create_or_update(
            GROUP_NAME,
            VM_NAME,
            {
                "location": LOCATION,
                "tags": {
                    "created-with": "python",
                    "where": "on azure",
                    "i_leik": "mudkipz"
                }
            }
        )
        async_vm_update.wait()

        # Create managed data disk
        print('{} > Create empty managed Data Disk'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        async_disk_creation = compute_client.disks.create_or_update(
            GROUP_NAME,
            "mydatadisk1",
            {
                "location": LOCATION,
                "disk_size_gb": 10,
                "creation_data": {
                    "create_option": DiskCreateOption.empty
                }
            }
        )
        data_disk = async_disk_creation.result()

        # Get the virtual machine by name
        print('{} > Get Virtual Machine by Name'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        virtual_machine = compute_client.virtual_machines.get(
            GROUP_NAME,
            VM_NAME
        )

        # Attach data disk
        print('{} > Attach Data Disk'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        virtual_machine.storage_profile.data_disks.append(
        {
            "lun": 12,
            "name": "mydatadisk1",
            "create_option": DiskCreateOption.attach,
            "managed_disk": 
            {
                "id": data_disk.id
            }
        })
        async_disk_attach = compute_client.virtual_machines.create_or_update(
            GROUP_NAME,
            virtual_machine.name,
            virtual_machine
        )
        async_disk_attach.wait()
        
        # Create public ip
        print('{} > Create Public IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ip_address = create_public_ip(network_client, compute_client)
        # here
        try:
            print("{} > Public ip address : {} is {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), VM_NAME, ip_address))
        except:
             print("{} > No public IP address was found for this machine".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))    
        
        print('{} > Create Port 22 conn'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Enable connection on port 22 :
        create_security_rule(network_client, compute_client)
        
        # if is linux, else if windows
        if check_os(name_os) != 'w':
            linux_configuration = virtual_machine.os_profile.linux_configuration
            linux_configuration.disable_password_authentication = False
        elif check_os(name_os) == 'w':
            windows_configuration = virtual_machine.os_profile.windows_configuration
            if windows_configuration is not None:
                windows_configuration.provision_vmagent = True
                if windows_configuration.win_rm is not None:
                    windows_configuration.win_rm.protocol = "http"
                    windows_configuration.win_rm.certificate_url = None
                    windows_configuration.win_rm.listeners = None
                    windows_configuration.win_rm.max_shell_minutes = 60
                windows_configuration.disable_password_authentication = False
        
        # Start the VM
        print('{} > Start VM {} Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name_os))
        async_vm_start = compute_client.virtual_machines.start(
            GROUP_NAME, 
            VM_NAME
        )
        async_vm_start.wait()
        
        print('{} > Start terminal on OS : {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform.system()))
       
        output = "Voici la commande à rentrer dans ce terminal : "
        if check_os(name_os) != 'w':
        # L'OS de la VM est un Linux :
            output += "ssh " + username + "@" + ip_address + " -p 22"
        else:
        # L'OS de la VM est un Windows :
            output += "Voici la commande à rentrer dans ce terminal : \ rdesktop -u " + username + " -p " + password + " " + ip_address + ":3389"
        
        if platform.system().lower().startswith('w'):
        # L'OS physique est un Windows :
            os.system("start cmd /k echo " + output)
        else:
        # L'OS physique est un Linux :
            os.system('xterm -hold -e "echo ' + output + '; exec $SHELL" &')
            
        # timer defined by user
        print('{} > Waiting {} minutes before deleting'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(timer_duration/60)))
        time.sleep(timer_duration)
        
        # Stop the VM
        print('{} > Stop VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        async_vm_stop = compute_client.virtual_machines.power_off(
            GROUP_NAME, VM_NAME)
        async_vm_stop.wait()

        # Delete VM
        print('{} > Delete VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        async_vm_delete = compute_client.virtual_machines.delete(
            GROUP_NAME, VM_NAME)
        async_vm_delete.wait()

    except CloudError:
        print('A VM operation failed:\n{}'.format(traceback.format_exc()))
    else:
        print('All example operations completed successfully!')
    finally:
        # Delete Resource group and everything in it
        print('{} > Delete Resource Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_async_operation = resource_client.resource_groups.delete(
            GROUP_NAME)
        delete_async_operation.wait()
        print("{} > Deleted: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), GROUP_NAME))

def create_nic(network_client):
    """Create a Network Interface for a VM.
    """
    # Create VNet
    print('{} > Create Vnet'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    async_vnet_creation = network_client.virtual_networks.create_or_update(     
        resource_group_name=GROUP_NAME,
        virtual_network_name=VNET_NAME,
        parameters=
        {
            "location": LOCATION,
            "address_space": {
                "address_prefixes": ["10.0.0.0/16"]
            }
        }
    )
    result = async_vnet_creation.result()
    
    # Create Subnet
    print('{} > Create Subnet'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    async_subnet_creation = network_client.subnets.create_or_update(
        GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        {
            "address_prefix": "10.0.0.0/24"
        }
    )
    subnet_info = async_subnet_creation.result()
    
    # Create NIC
    print('{} > Create NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    async_nic_creation = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        {
            "location": LOCATION,
            "ip_configurations": [
                {
                    "name": IP_CONFIG_NAME,
                    "subnet": 
                    {
                        "id": subnet_info.id
                    }
                }
            ]
        }
    )
    return async_nic_creation.result()

def get_network_interface(network_client, compute_client):
    virtual_machine = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
    nic_id = virtual_machine.network_profile.network_interfaces[0].id
    nic_info = network_client.network_interfaces.get(GROUP_NAME, nic_id.split('/')[-1])
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)

    return network_client.network_interfaces.get(GROUP_NAME, nic_info.name)

def create_public_ip(network_client, compute_client):
    ip_name = 'ip-' + VM_NAME + '-' + LOCATION
    dns_name = VM_NAME.lower() + '-' + LOCATION
    # Get the network interface of the VM
    # Récupérez l'interface réseau associée à la machine virtuelle
    virtual_machine = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
    nic_id = virtual_machine.network_profile.network_interfaces[0].id
    nic_info = network_client.network_interfaces.get(GROUP_NAME, nic_id.split('/')[-1])
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    network_interface = get_network_interface(
        network_client=network_client, 
        compute_client=compute_client)
    # Create a public IP address
    public_ip_parameters = PublicIPAddress(
            location=LOCATION,
            public_ip_allocation_method='Static',
            idle_timeout_in_minutes=10,
            sku={
                "name": "Standard"
            },
            dns_settings=PublicIPAddressDnsSettings(
                domain_name_label=dns_name
            )
        )
    async_public_ip_creation = network_client.public_ip_addresses.create_or_update(
        GROUP_NAME,
        ip_name,
        public_ip_parameters
    )
    print('{} > Create IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
 
    public_ip_info = async_public_ip_creation.result()
    local_ip_address = public_ip_info.ip_address
    ip_config = nic.ip_configurations[0]
    ip_config.public_ip_address = public_ip_info
    async_nic_update = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        nic
    )
    print('{} > Update IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    # Wait for the update operation to complete
    nic_info = async_nic_update.result()
    
    return local_ip_address

def create_security_rule(network_client, compute_client):

    # Define the name of the new network security group
    nsg_name = LOCATION + "-webpython-" + VM_NAME

    # Empty the NSG
    network_client.network_security_groups.create_or_update(
        GROUP_NAME, 
        nsg_name, 
        parameters= {
            'location': LOCATION,
            'security_rules': []
        }
    )


    if check_os(name_os) != 'w':
        security_rule = SecurityRule(
            name='SSH',
            protocol=SecurityRuleProtocol.tcp,
            access=SecurityRuleAccess.allow,
            direction=SecurityRuleDirection.inbound,
            priority=100,
            source_address_prefix='*',
            source_port_range='*',
            destination_address_prefix='*',
            destination_port_range='22'
        )
    else:
        security_rule = SecurityRule(
            name='AllowAllInboundRDP',
            protocol=SecurityRuleProtocol.tcp,
            access=SecurityRuleAccess.allow,
            direction=SecurityRuleDirection.inbound,
            priority=1100,
            source_address_prefix='*',
            source_port_range='*',
            destination_address_prefix='*',
            destination_port_range='3389',
        )

    # Create the new network security group using a dictionary of parameters
    
    nsg = network_client.network_security_groups.create_or_update(
        GROUP_NAME,
        nsg_name,
        parameters= {
            'location': LOCATION,
            'security_rules': [security_rule]
        }
    )
    nsg.wait()
    
    
    # Add the security rule to the network security group of the VM
    res = network_client.security_rules.create_or_update(
        resource_group_name=GROUP_NAME, 
        network_security_group_name=nsg_name, 
        security_rule_name=security_rule.name, 
        security_rule_parameters=security_rule
    )
    res.wait()
    network_interface = network_client.network_interfaces.get(
        GROUP_NAME, 
        NIC_NAME
    )
    network_interface = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        {
            "location": LOCATION,
            "ip_configurations": [
                network_interface.ip_configurations[0].as_dict()
            ]
        }
    )

    network_interface.wait()
    result = network_interface.result()
    
    # Add the network security group to the network interface
    result.ip_configurations[0].network_security_group = {
        'id': nsg.result().id
    }

    result = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        result
    )
    result.wait()
    
    network_interface = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)

    # Attach the network security group to the network interface
    network_interface.network_security_group = {
        'id': nsg.result().id
    }

    network_interface = network_client.network_interfaces.create_or_update(
        GROUP_NAME,
        NIC_NAME,
        network_interface
    )
    network_interface.wait()
    json_data = get_json_data('../data/config.json')
    json_data['ip_address'] = 'adresse_ip'
    set_json_data('../data/config.json', json_data)


def create_vm_parameters(nic_id, vm_resources):
    """Create the VM parameters structure.
    """
    return {
        "location": LOCATION,
        "os_profile": 
        {
            "computer_name": VM_NAME,
            "admin_username": USERNAME,
            "admin_password": PASSWORD
        },
        "hardware_profile": 
        {
            "vm_size": "Standard_DS1_v2"
        },
        "storage_profile": 
        {
            "image_reference": 
            {
                "publisher": vm_resources['publisher'],
                "offer": vm_resources['offer'],
                "sku": vm_resources['sku'],
                "version": vm_resources['version']
            },
        },
        "network_profile": 
        {
            "network_interfaces": 
            [
                {
                    "id": nic_id
                }
            ]
        }
    }

def check_os(input_str, arr=["windows", "windowsDesktop", "windowsServer", "debian", "ubuntu"]):
    if input_str in arr:
        return input_str[0]
    else:
        return -1


data_conn = get_json_data('../data/azure.json')
data_config = get_json_data('../data/config.json')
timer_duration = int(data_config['TimerDuration'])*60
name_virtual_machine = data_config['name_virtual_machine']
name_os = data_config['defaultOS']
region = data_config['defaultRegion']
username = data_config['username']
password = data_config['password']
ip_address = data_config['ip_address']
tenant = data_conn['TENANT']
client = data_conn['CLIENT']
secret = data_conn['SECRET']
subscription = data_conn['SUBSCRIPTION']

VM_NAME = name_virtual_machine

# Azure Datacenter
LOCATION = region

# Resource Group
GROUP_NAME = VM_NAME + '-azure-sample-group-virtual-machines'

# Network
VNET_NAME = VM_NAME + '-azure-sample-vnet'
SUBNET_NAME = VM_NAME + '-azure-sample-subnet'

# VM
OS_DISK_NAME = VM_NAME + '-azure-sample-osdisk'
STORAGE_ACCOUNT_NAME = haikunator.haikunate(delimiter='')
IP_CONFIG_NAME = VM_NAME + '-azure-sample-ip-config'
NIC_NAME = VM_NAME + "-nic"

USERNAME = username
PASSWORD = password

VM_REFERENCE = {
    "debian": {
        "publisher": "debian",
        "offer": "debian-10",
        "sku": "10",
        "version": "latest"
    },
    "ubuntu" : {
    "publisher": "Canonical",
    "offer": "UbuntuServer",
    "sku": "18.04-LTS",
    "version": "latest"
    },
    "windowsServer": {
        "publisher": "MicrosoftWindowsServer",
        "offer": "WindowsServer",
        "sku": "2019-Datacenter",
        "version": "latest"
    },
    "windowsDesktop" : {
        "publisher": "MicrosoftWindowsDesktop",
        "offer": "Windows-10",
        "sku": "20h2-pro",
        "version": "latest"
    }
}

VM_RESOURCES = VM_REFERENCE[name_os]

if __name__ == "__main__":
    print('{} > Starting Application'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    createVM()
    
