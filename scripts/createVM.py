import subprocess, traceback, platform, json, time, os, threading

from haikunator import Haikunator
from datetime import datetime
from msrestazure.azure_exceptions import CloudError
from azure.core.exceptions import HttpResponseError

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule, SecurityRuleAccess, SecurityRuleDirection, SecurityRuleProtocol, PublicIPAddress, PublicIPAddressDnsSettings, Subnet
from azure.mgmt.network import NetworkManagementClient, models
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.storage import StorageManagementClient

haikunator = Haikunator()


"""
    api version : 2023-03-01
    
"""

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
    credentials = ClientSecretCredential(
        client_id=client,
        client_secret=secret,
        tenant_id=tenant
    )
    return credentials, subscription_id

def get_api():
    credential, subscription_id = get_credentials()
    client = ResourceManagementClient(credential, subscription_id)
    providers = client.providers.get('Microsoft.Compute')
    return providers.resource_types[0].api_versions[0]
    

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

    # Check if the resource group exists
    rg_exists = resource_client.resource_groups.check_existence(GROUP_NAME)
    print('Groupe de ressource : ' +str(rg_exists))
    if rg_exists == False:
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
        async_vm_creation = compute_client.virtual_machines.begin_create_or_update(
            GROUP_NAME, 
            VM_NAME, 
            vm_parameters
        )
        async_vm_creation.wait()

        # Tag the VM
        print('{} > Adding Tag Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        async_vm_update = compute_client.virtual_machines.begin_create_or_update(
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

        async_disk_creation = compute_client.disks.begin_create_or_update(
            GROUP_NAME,
            DATA_DISK_NAME,
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
            "name": DATA_DISK_NAME,
            "create_option": DiskCreateOption.attach,
            "managed_disk": 
            {
                "id": data_disk.id
            }
        })
        async_disk_attach = compute_client.virtual_machines.begin_create_or_update(
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
        async_vm_start = compute_client.virtual_machines.begin_start(
            GROUP_NAME, 
            VM_NAME
        )
        async_vm_start.wait()
        
        print('{} > Start terminal on OS : {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform.system()))
       
        output = "Voici la commande à rentrer dans ce terminal : "
        if check_os(name_os) != 'w':
        # L'OS de la VM est un Linux :
            output += "ssh " + USERNAME + "@" + ip_address + " -p 22  password : " + PASSWORD
        else:
        # L'OS de la VM est un Windows :
            output += "Voici la commande à rentrer dans ce terminal : \ rdesktop -u " + USERNAME + " -p " + PASSWORD + " " + ip_address + ":3389"
        
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
        async_vm_stop = compute_client.virtual_machines.begin_power_off(
            GROUP_NAME, VM_NAME)
        async_vm_stop.wait()
        # Delete VM
        print('{} > List NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        list_ip_configurations()
        print('{} > Stopping every service'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        stop_everything_in_subnet()
        print('{} > Detach Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_network_security_group()
        print('{} > Detach Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_network_interface()
        print('{} > Detach Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_public_ip_address()
        print('{} > Delete Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_network_interface()
        print('{} > Delete VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_virtual_machine()
        print('{} > Delete Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_public_ip_address()
        print('{} > Detach Virtual Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_subnet()
        print('{} > Detach Virtual Network'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_vnet()

        print('{} > Delete Virtual Network and Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_vnet_subnet()

        print('{} > Delete Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_network_security_group()
        
    except CloudError:
        print('A VM operation failed:\n{}'.format(traceback.format_exc()))
    else:
        print('All example operations completed successfully!')
    finally:
        # Delete VM
        print('{} > List NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        list_ip_configurations()
        print('{} > Stopping every service'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        stop_everything_in_subnet()
        print('{} > Detach Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_network_security_group()
        print('{} > Detach Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_network_interface()
        print('{} > Detach Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_public_ip_address()
        print('{} > Delete Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_network_interface()
        print('{} > Delete VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_virtual_machine()
        print('{} > Delete Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_public_ip_address()
        print('{} > Detach Virtual Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_subnet()
        print('{} > Detach Virtual Network'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        detach_vnet()

        print('{} > Delete Virtual Network and Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_vnet_subnet()

        print('{} > Delete Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        delete_network_security_group()
def stop_everything_in_subnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
    # Stop all network interfaces in the subnet
    nics = network_client.network_interfaces.list(GROUP_NAME)
    for nic in nics:
        if nic.ip_configurations is not None:
            for config in nic.ip_configurations:
                if config.subnet is not None and config.subnet.id.split('/')[-3] == VNET_NAME and config.subnet.name == SUBNET_NAME:
                    network_client.network_interfaces.begin_stop(GROUP_NAME, nic.name).wait()

    # Stop all public IP addresses in the subnet
    public_ips = network_client.public_ip_addresses.list(GROUP_NAME)
    for ip in public_ips:
        if ip.ip_configuration is not None and ip.ip_configuration.subnet is not None and ip.ip_configuration.subnet.name == SUBNET_NAME:
            network_client.public_ip_addresses.begin_delete(GROUP_NAME, ip.name).wait()

    # Stop all network security groups in the subnet
    nsgs = network_client.network_security_groups.list(GROUP_NAME)
    for nsg in nsgs:
        if nsg.subnets is None:
            continue
        if SUBNET_NAME in nsg.subnets:
            network_client.network_security_groups.begin_delete(GROUP_NAME, nsg.name).wait()

    # Stop all load balancers in the subnet
    lbs = network_client.load_balancers.list(GROUP_NAME)
    for lb in lbs:
        if SUBNET_NAME in lb.backend_address_pools:
            network_client.load_balancers.begin_stop(GROUP_NAME, lb.name).wait()

    # Stop all application gateways in the subnet
    ags = network_client.application_gateways.list(GROUP_NAME)
    for ag in ags:
        if SUBNET_NAME in ag.backend_address_pools:
            network_client.application_gateways.begin_stop(GROUP_NAME, ag.name).wait()

    # Stop all virtual network gateways in the subnet
    vngs = network_client.virtual_network_gateways.list(GROUP_NAME)
    for vng in vngs:
        if SUBNET_NAME in vng.ip_configurations:
            network_client.virtual_network_gateways.begin_stop(GROUP_NAME, vng.name).wait()

    # Stop all VPN gateways in the subnet
    vpns = network_client.virtual_network_gateways.list(GROUP_NAME)
    for vpn in vpns:
        if SUBNET_NAME in vpn.ip_configurations:
            network_client.virtual_network_gateways.begin_stop(GROUP_NAME, vpn.name).wait()

def detach_subnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)

    # Detach subnet from network security group
    if subnet.network_security_group is not None:
        subnet_parameters = Subnet(ip_configurations=[], service_endpoints=[], delegation=None, route_table=None, network_security_group=None)
        network_client.subnets.begin_create_or_update(
            GROUP_NAME,
            VNET_NAME,
            SUBNET_NAME,
            subnet_parameters
        ).wait()

    # Detach subnet from route table
    if subnet.route_table is not None:
        subnet_parameters = Subnet(ip_configurations=None, service_endpoints=None, delegation=None, route_table=None, network_security_group=None)
        network_client.subnets.begin_create_or_update(GROUP_NAME, VNET_NAME, SUBNET_NAME, subnet_parameters).wait()

    # Detach subnet from network interface cards
    nics = network_client.network_interfaces.list(GROUP_NAME)
    for nic in nics:
        if nic.ip_configurations:
            for config in nic.ip_configurations:
                if config.subnet is not None and config.subnet.id.split('/')[-1] == subnet.id:
                    config.subnet = None
                    network_client.network_interfaces.begin_create_or_update(
                        GROUP_NAME,
                        nic.name,
                        nic
                    ).wait()
    print("Subnet {} detached successfully.")

def detach_vnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
    subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
    
    # Detach VNet from subnets
    # Erreur 
    """
    Message: 
        Address prefix string for resource 
        /subscriptions/6f54edf1-b08a-4da6-b85c-84b1d697b280/resourceGroups/group-appwebpython/providers/Microsoft.Network/virtualNetworks/vnet-debphp1/subnets/subnet-debphp1 
        cannot be null or empty.
    """

    vnet_prefix = vnet.address_space.address_prefixes[0]
    
    #subnet_parameters = Subnet(ip_configurations=[], service_endpoints=[], delegation=None, route_table=None, network_security_group=None)
    subnet_parameters = Subnet(
        address_prefix=subnet.address_prefix, 
        ip_configurations=[], 
        service_endpoints=[], 
        delegation=None, 
        route_table=None, 
        network_security_group=None
    )
    network_client.subnets.begin_create_or_update(
        GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        subnet_parameters
    ).wait()

    # Detach VNet from network interface cards
    nics = network_client.network_interfaces.list(GROUP_NAME)
    for nic in nics:
        if nic.ip_configurations:
            for config in nic.ip_configurations:
                subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
                config.subnet = subnet
                if subnet is not None and subnet.id.split('/')[-3] == VNET_NAME:
                    network_client.network_interfaces.begin_create_or_update(
                        GROUP_NAME,
                        nic.name,
                        nic
                    ).wait()
                    
    # Detach VNet from virtual machines
    vms = compute_client.virtual_machines.list(GROUP_NAME)
    for vm in vms:
        for nic_ref in vm.network_profile.network_interfaces:
            nic_id = nic_ref.id
            nic = network_client.network_interfaces.get(GROUP_NAME, nic_id.split('/')[-1])
            if nic.ip_configurations:
                for config in nic.ip_configurations:
                    if config.subnet is not None and config.subnet.id.split('/')[-3] == VNET_NAME:
                        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
                        config.subnet = subnet
                        config.subnet.id = subnet.id  # set subnet ID
                        network_client.network_interfaces.begin_create_or_update(
                            GROUP_NAME,
                            nic.name,
                            nic
                        ).wait()

    print("Virtual network {} detached successfully.".format(VNET_NAME))

def subnet_exists(subnet_name, vnet_name, group_name):
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    try:
        network_client.subnets.get(group_name, vnet_name, subnet_name)
        return True
    except CloudError as e:
        if e.status_code == 404:
            return False
        else:
            raise e

def vnet_exists(vnet_name, group_name):
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    try:
        network_client.virtual_networks.get(group_name, vnet_name)
        return True
    except CloudError as e:
        if e.status_code == 404:
            return False
        else:
            raise e


def list_used_subnets_and_vnets():
    credential, subscription = get_credentials()
    compute_client = ComputeManagementClient(credential, subscription)
    network_client = NetworkManagementClient(credential, subscription)

    # Get the VM
    vm = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)

    # Get the NICs attached to the VM
    nics = vm.network_profile.network_interfaces

    for nic_ref in nics:
        # Get the NIC object
        nic_id = nic_ref.id
        nic_obj = network_client.network_interfaces.get(nic_id.split('/')[4], nic_id.split('/')[8])

        # Get the subnet and VNet for the NIC
        if nic_obj.ip_configurations:
            config = nic_obj.ip_configurations[0]
            subnet_id = config.subnet.id
            vnet_id = config.subnet.id.split('/')[8]
            subnet_name = config.subnet.id.split('/')[10]
            print(f"NIC {nic_obj.name} is attached to subnet {subnet_name} in VNet {vnet_id}")


def delete_vnet_subnet():
    # Afficher les subnets et vnets utilisés par la VM
    list_used_subnets_and_vnets()
    
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    
    # Get the virtual machine object
    vm = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
    nics = vm.network_profile.network_interfaces
    
    # Delete subnet
    try:
        subnet_operation = network_client.subnets.begin_delete(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        subnet_operation.wait()
    except:
        print(f"An error occurred while deleting subnet {SUBNET_NAME} in VNet {VNET_NAME}.")
        return False

    # Delete virtual network
    try:
        vnet_operation = network_client.virtual_networks.begin_delete(GROUP_NAME, VNET_NAME)
        vnet_operation.wait()
    except:
        print(f"An error occurred while deleting VNet {VNET_NAME}.")
        return False
    
    print(f"VNet {VNET_NAME} and subnet {SUBNET_NAME} were deleted successfully.")
    return True

def list_ip_configurations():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)

    # Get the NIC by name
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)

    # List all IP configurations for the NIC
    for config in nic.ip_configurations:
        print("IP Configuration Name: {}".format(config.name))
        print("Subnet Name: {}".format(config.subnet.name))
        if config.public_ip_address:
            print("Public IP Address Name: {}".format(config.public_ip_address.name))
            print("Public IP Address ID: {}".format(config.public_ip_address.id))
        else:
            print("No Public IP Address associated with this IP Configuration")
        print("Private IP Address: {}".format(config.private_ip_address))
        print("Private IP Allocation Method: {}".format(config.private_ip_allocation_method))
        print("----------------------------------------------------")


def detach_network_interface():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    
    # Get the NIC by name
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)

    # Detach NIC from any virtual machine
    if nic.virtual_machine:
        print("Detaching NIC {} from VM {}".format(NIC_NAME, VM_NAME))
        nic.ip_configurations = []
        nic = network_client.network_interfaces.begin_create_or_update(GROUP_NAME, nic.name, nic).result()
        print("Detached NIC {} successfully from VM {}".format(NIC_NAME, VM_NAME))  
        return True
    else:
        print("NIC {} is not attached to any virtual machine".format(NIC_NAME))
        return False

def delete_network_interface():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    
    # Get the NIC by name
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    
    # Delete the NIC
    print("Deleting network interface: {}".format(NIC_NAME))
    network_client.network_interfaces.begin_delete(GROUP_NAME, NIC_NAME).wait()
    print("NIC {} deleted successfully".format(NIC_NAME))

def detach_public_ip_address():
    """
    Détacher l'Adresse IP publique d'un VM
    """
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    is_nic_exists = False
    # Récupérer l'interface réseau
    for nic in network_client.network_interfaces.list(GROUP_NAME):
        if nic.name == NIC_NAME:
            is_nic_exists = True
            break  # pour sortir de la boucle si le nic a été trouvé
    if is_nic_exists:
        nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    else:
        return

    # Vérifier s'il y a une Adresse IP publique attachée à l'interface réseau
    if nic.ip_configurations[0].public_ip_address is not None:
        # Récupérer l'Adresse IP publique
        public_ip_address = network_client.public_ip_addresses.get(GROUP_NAME, nic.ip_configurations[0].public_ip_address.id)
        # Détacher l'Adresse IP publique de l'interface réseau
        nic.ip_configurations[0].public_ip_address = None
        nic = network_client.network_interfaces.create_or_update(GROUP_NAME, NIC_NAME, nic)
        print("L'Adresse IP publique {} a été détachée de l'interface réseau {}.".format(public_ip_address.name, NIC_NAME ))
    else:
        print("Il n'y a pas d'Adresse IP publique attachée à l'interface réseau {}.".format(NIC_NAME))

def delete_network_security_group():
    """
    Supprimer un Groupe de sécurité réseau
    """
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    try:
        # Vérifier si le Groupe de sécurité réseau existe
        network_client.network_security_groups.get(GROUP_NAME, NSG_NAME)
    except CloudError as ex:
        if 'was not found' in str(ex):
            print("Le Groupe de sécurité réseau {} n'existe pas.".format(NSG_NAME))
            return
        else:
            raise
    else:
        # Supprimer le Groupe de sécurité réseau
        network_client.network_security_groups.begin_delete(GROUP_NAME, NSG_NAME).wait()
        print("Le Groupe de sécurité réseau {} a été supprimé.".format(NSG_NAME))

def delete_public_ip_address():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)

    # Récupérer la liste des adresses IP publiques dans le groupe de ressources
    public_ips = network_client.public_ip_addresses.list(GROUP_NAME)
    # Chercher l'adresse IP publique avec le nom recherché
    public_ip = None
    for item in public_ips:
        if item.name == IP_NAME:
            public_ip = item
            break

    if public_ip is None:
        print("Public IP address '{}' not found".format(IP_NAME))
        return

    # Supprimer l'adresse IP publique
    network_client.public_ip_addresses.begin_delete(GROUP_NAME, public_ip.name).wait()
    print("Public IP address '{}' deleted".format(IP_NAME))

def detach_network_security_group():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    
    # Récupérer la liste des NSG dans le groupe de ressources
    nsg_list = network_client.network_security_groups.list(GROUP_NAME)
    
    if not nsg_list:
        print("No network security groups found in resource group '{}'".format(GROUP_NAME))
        return False
    
    # Chercher le NSG avec le nom recherché
    nsg = None
    for item in nsg_list:
        if item.name == NSG_NAME:
            nsg = item
            break
    
    if nsg is None:
        print("Network Security Group '{}' not found".format(NSG_NAME))
        return False
    
    # Détacher le NSG de toutes les interfaces réseau qui y sont associées
    try:
        for nic in nsg.network_interfaces:
            network_interface = network_client.network_interfaces.get(GROUP_NAME, network_interface_name=NIC_NAME)
            network_interface.network_security_group = None
            network_client.network_interfaces.begin_create_or_update(
                resource_group_name=network_interface.id.split('/')[4],
                network_interface_name=network_interface.name,
                parameters=network_interface
            ).wait()
            print("Network security group '{}' detached from network interface '{}'".format(NSG_NAME, nic.id))
    except TypeError:
        print("No network interfaces found for Network Security Group '{}'".format(NSG_NAME))
        return False

    if nsg.network_interfaces is None:
        print("No network interfaces found for Network Security Group '{}'".format(NSG_NAME))
        return False
    
    # Vérifier si le NSG est encore attaché à des interfaces réseau
    still_attached = False
    for nic in nsg.network_interfaces:
        network_interface = network_client.network_interfaces.get(GROUP_NAME, network_interface_name=NIC_NAME)
        if network_interface.network_security_group is not None:
            still_attached = True
            break
    if still_attached:
        print("Network Security Group '{}' is still attached to at least one network interface".format(NSG_NAME))
        return False
    else:
        print("Network Security Group '{}' detached from all network interfaces".format(NSG_NAME))
        return True




def delete_virtual_machine():
    credential, subscription = get_credentials()
    resource_client = ResourceManagementClient(credential, subscription)
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    # Get the resource group and virtual machine
    ################################################
    is_vm_exists = False
    for vm in compute_client.virtual_machines.list(GROUP_NAME):
        if(vm.name == VM_NAME):
            is_vm_exists = True
    if(is_vm_exists == False):
        return
            #virtual_machine = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
    # Delete VM
    
    try:
        async_vm_delete = compute_client.virtual_machines.begin_delete(GROUP_NAME, VM_NAME)
        async_vm_delete.wait()
        net_del_poller = network_client.network_interfaces.begin_delete(GROUP_NAME, NIC_NAME)
        net_del_poller.wait()
        disks_list = compute_client.disks.list_by_resource_group(GROUP_NAME)
        disk_handle_list = []
        ## a changer ?
        async_disk_handle_list = []
        for disk in disks_list:
            if VM_NAME in disk.name:
                async_disk_delete = compute_client.disks.begin_delete(GROUP_NAME, disk.name)
                async_disk_handle_list.append(async_disk_delete)
        for async_disk_delete in disk_handle_list:
            async_disk_delete.wait()
        print("Queued disks will be deleted now...")
    except CloudError:
        print('A VM delete operation failed: {}'.format(traceback.format_exc()))
        return False
    print("Deleted VM {}".format(VM_NAME))
    return True

def create_nic(network_client):
    """
        Create a Network Interface for a VM.
    """
    # Create VNet
    print('{} > Create Vnet'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    async_vnet_creation = network_client.virtual_networks.begin_create_or_update(     
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
    async_subnet_creation = network_client.subnets.begin_create_or_update(
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
    async_nic_creation = network_client.network_interfaces.begin_create_or_update(
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
    credential, subscription = get_credentials()
    compute_client = ComputeManagementClient(credential, subscription)
    virtual_machine = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
    nic_id = virtual_machine.network_profile.network_interfaces[0].id
    nic_info = network_client.network_interfaces.get(GROUP_NAME, nic_id.split('/')[-1])
    nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)

    return network_client.network_interfaces.get(GROUP_NAME, nic_info.name)

def create_public_ip(network_client, compute_client):
    # Get the network interface of the VM
    # Récupérez l'interface réseau associée à la machine virtuelle
    credential, subscription = get_credentials()
    compute_client = ComputeManagementClient(credential, subscription)
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
                domain_name_label=DNS_NAME
            )
        )
    async_public_ip_creation = network_client.public_ip_addresses.begin_create_or_update(
        GROUP_NAME,
        IP_NAME,
        public_ip_parameters
    )
    print('{} > Create IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
 
    public_ip_info = async_public_ip_creation.result()
    local_ip_address = public_ip_info.ip_address
    ip_config = nic.ip_configurations[0]
    ip_config.public_ip_address = public_ip_info
    async_nic_update = network_client.network_interfaces.begin_create_or_update(
        GROUP_NAME,
        NIC_NAME,
        nic
    )
    print('{} > Update IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    # Wait for the update operation to complete
    nic_info = async_nic_update.result()
    
    return local_ip_address

def create_security_rule(network_client, compute_client):
    # Empty the NSG
    network_client.network_security_groups.begin_create_or_update(
        GROUP_NAME, 
        NSG_NAME, 
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
    
    nsg = network_client.network_security_groups.begin_create_or_update(
        GROUP_NAME,
        NSG_NAME,
        parameters= {
            'location': LOCATION,
            'security_rules': [security_rule]
        }
    )
    nsg.wait()
    
    
    # Add the security rule to the network security group of the VM
    res = network_client.security_rules.begin_create_or_update(
        resource_group_name=GROUP_NAME, 
        network_security_group_name=NSG_NAME, 
        security_rule_name=security_rule.name, 
        security_rule_parameters=security_rule
    )
    res.wait()
    network_interface = network_client.network_interfaces.get(
        GROUP_NAME, 
        NIC_NAME
    )
    network_interface = network_client.network_interfaces.begin_create_or_update(
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

    result = network_client.network_interfaces.begin_create_or_update(
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

    network_interface = network_client.network_interfaces.begin_create_or_update(
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

# Resource Group
GROUP_NAME = 'group-appwebpython'

data_conn = get_json_data('../data/azure.json')
data_config = get_json_data('../data/config.json')


VM_NAME = data_config['name_virtual_machine']
LOCATION = data_config['location']
USERNAME = data_config['username']
PASSWORD = data_config['password']

timer_duration = int(data_config['TimerDuration'])*60
name_os = data_config['operating_system']
ip_address = data_config['ip_address']
tenant = data_conn['TENANT']
client = data_conn['CLIENT']
secret = data_conn['SECRET']
subscription = data_conn['SUBSCRIPTION']

# Network
VNET_NAME = 'vnet-' + VM_NAME
SUBNET_NAME = 'subnet-' + VM_NAME

# VM
OS_DISK_NAME = 'osdisk-' + VM_NAME
DATA_DISK_NAME ='datadisk-' + VM_NAME
IP_CONFIG_NAME = 'ip-config-' + VM_NAME
NIC_NAME = 'nic-' + VM_NAME
IP_NAME = 'ip-' + VM_NAME
DNS_NAME = 'dns-' + VM_NAME
NSG_NAME = 'nsg-' + VM_NAME

STORAGE_ACCOUNT_NAME = haikunator.haikunate(delimiter='')

#La valeur retourné par get_api() pose problème, pour le moment je fixe la version de l'api
API_VERSION = '2019_02_01'

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
    createVM()

#vm_names = ["vm1", "vm2", "vm3"]
#threads = []
#for vm_name in vm_names:
#    thread = threading.Thread(target=create_and_delete_vm, args=(vm_name,))
#    threads.append(thread)

# Start all threads
#for thread in threads:
#    thread.start()

# Wait for all threads to finish
#for thread in threads:
#    thread.join()