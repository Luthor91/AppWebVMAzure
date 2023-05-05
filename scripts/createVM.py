import subprocess, traceback, platform, json, time, os, threading, azure
from colorama import Back, Fore, Style, deinit, init
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
    print(Fore.WHITE + '{} > Create Resource Group {} for Virtual Machine {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), GROUP_NAME, name_os))
    # Check if the resource group exists
    rg_exists = resource_client.resource_groups.check_existence(GROUP_NAME)
    print('\tResource Group exists =>\t' +str(rg_exists))
    if rg_exists == False:
        resource_client.resource_groups.create_or_update(
            GROUP_NAME, 
            {
                "location": LOCATION
            }
        )

    try:
        # Create a NIC
        print('{} > Create Vnet, Subnet and NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        nic = create_nic(network_client)

        #Create VM
        vm_parameters = create_vm_parameters(nic.id, VM_RESOURCES)
        async_vm_creation = compute_client.virtual_machines.begin_create_or_update(
            GROUP_NAME, 
            VM_NAME, 
            vm_parameters
        )
        async_vm_creation.wait()

        # Tag the VM
        print(Fore.WHITE +'{} > Adding Tag Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        print(Fore.WHITE +'{} > Create empty managed Data Disk and attach it'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

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
        virtual_machine = compute_client.virtual_machines.get(
            GROUP_NAME,
            VM_NAME
        )

        # Attach data disk
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
        print(Fore.WHITE +'{} > Create and Update Public IP Address'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ip_address = create_public_ip(network_client, compute_client)
        try:
            print(Fore.WHITE +"{} > Public ip address : {} is {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), VM_NAME, ip_address))
        except:
             print(Fore.RED +"{} > No public IP address was found for this machine".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))  
        
        print(Fore.WHITE +'{} > Create Port 22 conn'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        print(Fore.WHITE +'{} > Start VM {} Virtual Machine'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name_os))
        async_vm_start = compute_client.virtual_machines.begin_start(
            GROUP_NAME, 
            VM_NAME
        )
        async_vm_start.wait()
        
        print(Fore.WHITE +'{} > Start terminal on OS : {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), platform.system()))
       
        info = "Machine: " + VM_NAME + " OS: " + name_os + "  Password: " + PASSWORD + "  Commande :"
        command = ""
        
        
        if check_os(name_os) != 'w':
        # L'OS de la VM est un Linux :
            command += "ssh " + USERNAME + "@" + ip_address + " -p 22"
        else:
        # L'OS de la VM est un Windows :
            command += "rdesktop -u " + USERNAME + " -p " + PASSWORD + " " + ip_address + ":3389"
        
        if platform.system().lower().startswith('w'):
        # L'OS physique est un Windows :
            os.system('start cmd /k echo ' + '"' + info + command + '"')
        else:
        # L'OS physique est un Linux :
            os.system('xterm -hold -e "echo ' + info + command + '; exec $SHELL" &')
            
        # timer defined by user
        print(Fore.WHITE +'{} > Waiting {} minutes before deleting'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(timer_duration/60)))
        time.sleep(timer_duration)
        
        # Delete VM
        #print('{} > List NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        #list_ip_configurations()
        print(Fore.WHITE +'\n{} > Stopping every service'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = stop_everything_in_subnet()
        print(Fore.WHITE +"\tSortie =>\tDétacher nsg : " + str(res))
        print(Fore.WHITE +'\n{} > Detach Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_network_security_group()
        print(Fore.WHITE +"\tSortie =>\tDétacher nsg : " + str(res))
        print('\n{} > Detach Virtual Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_subnet()
        print(Fore.WHITE +"\tSortie =>\tDétacher subnet : " + str(res))
        print('\n{} > Detach Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_network_interface()
        print(Fore.WHITE +"\tSortie =>\tDétacher nic : " + str(res))
        print('\n{} > Detach Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_public_ip_address()
        print(Fore.WHITE +"\tSortie =>\tDétacher ip publique : " + str(res))

        print(Fore.WHITE +'\n{} > Delete VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_virtual_machine()
        print(Fore.WHITE +"\tSortie =>\tSupprimer vm : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_public_ip_address()
        print(Fore.WHITE +"\tSortie =>\tSupprimer adresse ip : " + str(res))

        print(Fore.WHITE +'\n{} > Detach Virtual Network'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_vnet()
        print(Fore.WHITE +"\tSortie =>\tDétacher vnet : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Virtual Network and Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_vnet_subnet()
        print(Fore.WHITE +"\tSortie =>\tSupprimer vnet et subnet : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_network_security_group()
        print(Fore.WHITE +"\tSortie =>\tSupprimer nsg : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_network_interface()
        print(Fore.WHITE +"\tSortie =>\tSupprimer nic : " + str(res))
    except CloudError:
        print(Fore.RED +'A VM operation failed:\n{}'.format(traceback.format_exc()))
    else:
        print(Fore.GREEN +'\nAll operations completed successfully!\n')
    finally:
        # Delete VM
        #print('{} > List NIC'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        #list_ip_configurations()
        print(Fore.WHITE +'\n{} > Stopping every service'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        stop_everything_in_subnet()
        print(Fore.WHITE +'\n{} > Detach Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_network_security_group()
        print(Fore.WHITE +"\tSortie =>\tDétacher nsg : " + str(res))
        print('\n{} > Detach Virtual Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_subnet()
        print(Fore.WHITE +"\tSortie =>\tDétacher subnet : " + str(res))
        print('\n{} > Detach Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_network_interface()
        print(Fore.WHITE +"\tSortie =>\tDétacher nic : " + str(res))
        print('\n{} > Detach Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_public_ip_address()
        print(Fore.WHITE +"\tSortie =>\tDétacher ip publique : " + str(res))

        print(Fore.WHITE +'\n{} > Delete VM'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_virtual_machine()
        print(Fore.WHITE +"\tSortie =>\tSupprimer vm : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Public IP'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_public_ip_address()
        print(Fore.WHITE +"\tSortie =>\tSupprimer adresse ip : " + str(res))

        print(Fore.WHITE +'\n{} > Detach Virtual Network'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = detach_vnet()
        print(Fore.WHITE +"\tSortie =>\tDétacher vnet : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Virtual Network and Subnets'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_vnet_subnet()
        print(Fore.WHITE +"\tSortie =>\tSupprimer vnet et subnet : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Network Security Group'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_network_security_group()
        print(Fore.WHITE +"\tSortie =>\tSupprimer nsg : " + str(res))
        print(Fore.WHITE +'\n{} > Delete Network Interface'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        res = delete_network_interface()
        print(Fore.WHITE +"\tSortie =>\tSupprimer nic : " + str(res))
        
        
def stop_everything_in_subnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
    except:
        print(Fore.RED + f"\tError =>\tFailed to get Subnet {SUBNET_NAME}.")
        return False
    failed_services = []

    # Stop all network interfaces in the subnet
    nics = network_client.network_interfaces.list(GROUP_NAME)
    for nic in nics:
        if nic.ip_configurations is not None:
            for config in nic.ip_configurations:
                if config.subnet is not None and config.subnet.id.split('/')[-3] == VNET_NAME and config.subnet.name == SUBNET_NAME:
                    try:
                        network_client.network_interfaces.begin_stop(GROUP_NAME, nic.name).wait()
                    except:
                        failed_services.append("network interface: " + nic.name)

    # Stop all public IP addresses in the subnet
    public_ips = network_client.public_ip_addresses.list(GROUP_NAME)
    for ip in public_ips:
        if ip.ip_configuration is not None and ip.ip_configuration.subnet is not None and ip.ip_configuration.subnet.name == SUBNET_NAME:
            try:
                network_client.public_ip_addresses.begin_delete(GROUP_NAME, ip.name).wait()
            except:
                failed_services.append("public IP address: " + ip.name)

    # Stop all network security groups in the subnet
    nsgs = network_client.network_security_groups.list(GROUP_NAME)
    for nsg in nsgs:
        if nsg.subnets is None:
            continue
        if SUBNET_NAME in nsg.subnets:
            try:
                network_client.network_security_groups.begin_delete(GROUP_NAME, nsg.name).wait()
            except:
                failed_services.append("network security group: " + nsg.name)

    # Stop all load balancers in the subnet
    lbs = network_client.load_balancers.list(GROUP_NAME)
    for lb in lbs:
        if SUBNET_NAME in lb.backend_address_pools:
            try:
                network_client.load_balancers.begin_stop(GROUP_NAME, lb.name).wait()
            except:
                failed_services.append("load balancer: " + lb.name)

    # Stop all application gateways in the subnet
    ags = network_client.application_gateways.list(GROUP_NAME)
    for ag in ags:
        if SUBNET_NAME in ag.backend_address_pools:
            try:
                network_client.application_gateways.begin_stop(GROUP_NAME, ag.name).wait()
            except:
                failed_services.append("application gateway: " + ag.name)

    # Stop all virtual network gateways in the subnet
    vngs = network_client.virtual_network_gateways.list(GROUP_NAME)
    for vng in vngs:
        if SUBNET_NAME in vng.ip_configurations:
            try:
                network_client.virtual_network_gateways.begin_stop(GROUP_NAME, vng.name).wait()
            except:
                failed_services.append("virtual network gateway: " + vng.name)

    # Stop all VPN gateways in the subnet
    vpns = network_client.virtual_network_gateways.list(GROUP_NAME)
    for vpn in vpns:
        if SUBNET_NAME in vpn.ip_configurations:
            try:
                network_client.virtual_network_gateways.begin_stop(GROUP_NAME, vpn.name).wait()
            except:
                failed_services.append("VPN gateway: " + vpn.name)

    if len(failed_services) > 0:
        all_services_unstopped = ",".join(failed_services)
        print(Fore.RED + f"\tError =>\tFailed to stop services {all_services_unstopped}.")
        return False
    else:
        print(Fore.GREEN + f"\tFinished =>\tAll services stopped successfully in Subnet {SUBNET_NAME}.")
        return True



def detach_subnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
    except:
        print(Fore.RED + f"\tError =>\tFailed to get Subnet {SUBNET_NAME}.")
        return False
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

    if subnet.network_security_group is None and subnet.route_table is None and not any(
        nic.ip_configurations[0].subnet.id.split('/')[-1] == subnet.id for nic in nics if nic.ip_configurations
    ):
        print(Fore.GREEN + "\tFinished =>\tSubnet {} detached successfully.".format(SUBNET_NAME))
        return True
    else:
        print(Fore.RED + "\tError =>\tFailed to detach subnet {}.".format(SUBNET_NAME))
        return False

def detach_vnet():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    try:
        vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
    except:
        print(Fore.RED + f"\tError =>\tFailed to get Vnet {SUBNET_NAME}.")
        return False
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
    except:
        print(Fore.RED + f"\tError =>\tFailed to get Subnet {SUBNET_NAME}.")
        return False

    vnet_prefix = vnet.address_space.address_prefixes[0]

    subnet_parameters = Subnet(
        address_prefix=subnet.address_prefix,
        service_endpoints=[],
        route_table=None,
        network_security_group=None
    )
    network_client.subnets.begin_create_or_update(
        GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        subnet_parameters
    ).wait()

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

    # Vérifier si le VNet est toujours attaché aux ressources
    nics = network_client.network_interfaces.list(GROUP_NAME)
    for nic in nics:
        if nic.ip_configurations:
            for config in nic.ip_configurations:
                if config.subnet is not None and config.subnet.id.split('/')[-3] == VNET_NAME:
                    print(Fore.RED + "\tError =>\tFailed to detach vnet {}.".format(SUBNET_NAME))
                    return False

    vms = compute_client.virtual_machines.list(GROUP_NAME)
    for vm in vms:
        for nic_ref in vm.network_profile.network_interfaces:
            nic_id = nic_ref.id
            nic = network_client.network_interfaces.get(GROUP_NAME, nic_id.split('/')[-1])
            if nic.ip_configurations:
                for config in nic.ip_configurations:
                    if config.subnet is not None and config.subnet.id.split('/')[-3] == VNET_NAME:
                        print(Fore.RED + "\tError =>\tFailed to detach vnet {}.".format(SUBNET_NAME))
                        return False
    print(Fore.GREEN + "\tFinished =>\Vnet {} detached successfully.".format(SUBNET_NAME))
    return True

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
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)

    # Delete subnet
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        subnet_operation = network_client.subnets.begin_delete(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        subnet_operation.wait()
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.RED + f"\tError => \tSubnet {SUBNET_NAME} not found in VNet {VNET_NAME}")
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while deleting subnet {SUBNET_NAME} in VNet {VNET_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
        return False

    # Delete virtual network
    try:
        vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
        vnet_operation = network_client.virtual_networks.begin_delete(GROUP_NAME, VNET_NAME)
        vnet_operation.wait()
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.RED + f"\tError => \tVNet {VNET_NAME} not found" + Style.RESET_ALL)
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while deleting VNet {VNET_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
        return False

    # Check if the subnet and virtual network have been deleted successfully
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
        print(Fore.RED + f"\tError => \tSubnet {SUBNET_NAME} or VNet {VNET_NAME} still exist")
        return False
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.GREEN + f"VNet {VNET_NAME} and subnet {SUBNET_NAME} were deleted successfully.")
            return True
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while checking if the VNet {VNET_NAME} and subnet {SUBNET_NAME} were deleted")
            print(Fore.YELLOW + f"Message => \t{ex}")
            return False


def _delete_vnet_subnet():
    # Afficher les subnets et vnets utilisés par la VM
    #list_used_subnets_and_vnets()

    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)

    # Get the virtual machine object
    try:
        vm = compute_client.virtual_machines.get(GROUP_NAME, VM_NAME)
        nics = vm.network_profile.network_interfaces
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.RED + f"\tError => \tVirtual machine {VM_NAME} not found in resource group {GROUP_NAME}")
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while getting virtual machine {VM_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
        return False
    
    # Delete subnet
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        subnet_operation = network_client.subnets.begin_delete(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        subnet_operation.wait()
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.RED + f"\tError => \tSubnet {SUBNET_NAME} not found in VNet {VNET_NAME}")
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while deleting subnet {SUBNET_NAME} in VNet {VNET_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
        return False

    # Delete virtual network
    try:
        vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
        vnet_operation = network_client.virtual_networks.begin_delete(GROUP_NAME, VNET_NAME)
        vnet_operation.wait()
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.RED + f"\tError => \tVNet {VNET_NAME} not found" + Style.RESET_ALL)
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while deleting VNet {VNET_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
        return False

    # Check if the subnet and virtual network have been deleted successfully
    try:
        subnet = network_client.subnets.get(GROUP_NAME, VNET_NAME, SUBNET_NAME)
        vnet = network_client.virtual_networks.get(GROUP_NAME, VNET_NAME)
        print(Fore.RED + f"\tError => \tSubnet {SUBNET_NAME} or VNet {VNET_NAME} still exist")
        return False
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.GREEN + f"VNet {VNET_NAME} and subnet {SUBNET_NAME} were deleted successfully.")
            return True
        else:
            print(Fore.RED + f"\tError => \tAn \tError occurred while checking if the VNet {VNET_NAME} and subnet {SUBNET_NAME} were deleted")
            print(Fore.YELLOW + f"Message => \t{ex}")
            return False



def list_ip_configurations():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)

    try:
        # Get the NIC by name
        nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    except ModuleNotFoundError:
        print(Fore.MAGENTA + "\tWarning => \tNIC {} not found in resource group {}".format(NIC_NAME, GROUP_NAME))
        return
    # Provisoire
    if nic is null:
        return
    # List all IP configurations for the NIC
    print(Fore.WHITE +"List IP configuration for the NIC")
    print("----------------------------------------------------")
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

    try:
        # Get the NIC by name
        nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
    except HttpResponseError as ex:
        if ex.status_code == 404:
            print(Fore.MAGENTA +"\tWarning => \tNIC {} not found in resource group {}".format(NIC_NAME, GROUP_NAME))
            return False
        else:
            print(Fore.RED +f"\tError => \tFailed to get NIC {NIC_NAME}")
            print(Fore.YELLOW + f"Message => \t{ex}")
            return False

    # Detach NIC from any virtual machine
    if nic.virtual_machine:
        # Check if the NIC has any IP configurations
        if len(nic.ip_configurations) > 0:
            nic.ip_configurations = []
            try:
                nic = network_client.network_interfaces.begin_create_or_update(GROUP_NAME, nic.name, nic).result()
            except HttpResponseError as ex:
                if ex.status_code == 400 and 'InvalidIPConfigCount' in ex.message:
                    print(Fore.MAGENTA +f"\tWarning => \tDetaching NIC failed: NIC {NIC_NAME} must have one or more IP configurations.")
                else:
                    print(Fore.RED +f"\tError => \tDetaching NIC {NIC_NAME} failed")
                    print(Fore.YELLOW + f"Message => \t{ex}")
                return False
            print(Fore.GREEN +"\tFinished => \tDetached NIC {} successfully from VM {}".format(NIC_NAME, VM_NAME))
            return True
        else:
            print(Fore.RED +"\tError => \tNIC {} does not have any IP configurations".format(NIC_NAME))
            return False
    else:
        print(Fore.RED +"\tError => \tNIC {} is not attached to any virtual machine".format(NIC_NAME))
        return False




def delete_network_interface():
    """
    Supprimer une interface réseau
    """
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    is_nic_exists = False

    # Vérifier si l'interface réseau existe
    for nic in network_client.network_interfaces.list(GROUP_NAME):
        if nic.name == NIC_NAME:
            is_nic_exists = True
            break

    if is_nic_exists:
        try:
            # Supprimer la configuration IP de l'interface réseau
            nic = network_client.network_interfaces.get(GROUP_NAME, NIC_NAME)
            new_ip_configs = []
            for config in nic.ip_configurations:
                if config.name != PUBLIC_IP_NAME:
                    new_ip_configs.append(config)
            nic.ip_configurations = new_ip_configs
            network_client.network_interfaces.begin_create_or_update(GROUP_NAME, NIC_NAME, nic).wait()

            # Supprimer l'interface réseau
            network_client.network_interfaces.begin_delete(GROUP_NAME, NIC_NAME).wait()
            print(Fore.GREEN +"\tFinished => \tNIC {} deleted".format(NIC_NAME))
            return True
        except CloudError as ex:
            if 'NicInUse' in ex.message:
                # Dissocier l'interface réseau de la ressource existante
                vm_id = ex.inner_exception.error.details[0].target.split('/')[-1]
                vm = compute_client.virtual_machines.get(GROUP_NAME, vm_id)
                nic_id = ex.inner_exception.error.details[0].resource.split('/')[-1]
                nic = network_client.network_interfaces.get(GROUP_NAME, nic_id)
                nic_config_name = ex.inner_exception.error.details[0].name
                for nic_config in vm.network_profile.network_interfaces:
                    if nic_config.id == nic.id and nic_config.name == nic_config_name:
                        nic_config.id = None
                        nic_config.ip_configurations = []
                compute_client.virtual_machines.begin_create_or_update(GROUP_NAME, vm_id, vm).wait()
                # Supprimer l'interface réseau
                network_client.network_interfaces.begin_delete(GROUP_NAME, NIC_NAME).wait()
                print(Fore.GREEN +"\tFinished => \tNIC {} deleted after being dissociated from VM {}".format(NIC_NAME, vm_id))
                return True
            else:
                print(Fore.RED +f"\tError => \tError while deleting NIC {NIC_NAME}")
                print(Fore.YELLOW + f"Message => \t{ex}")
                return False
    else:
        print(Fore.MAGENTA +"\tWarning => \tNIC {} doesn't exist".format(NIC_NAME))
        return False





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
        return False

    # Vérifier s'il y a une Adresse IP publique attachée à l'interface réseau
    if nic.ip_configurations[0].public_ip_address is not None:
        # Récupérer l'Adresse IP publique
        try:
            public_ip_address = network_client.public_ip_addresses.get(GROUP_NAME, nic.ip_configurations[0].public_ip_address.id)
        except azure.core.exceptions.ResourceNotFoundError as ex:
            print(Fore.MAGENTA +"\tWarning => \tFetching Public IP \tError, resource not found")
            return False
        
        # Détacher l'Adresse IP publique de l'interface réseau
        nic.ip_configurations[0].public_ip_address = None
        nic = network_client.network_interfaces.create_or_update(GROUP_NAME, NIC_NAME, nic)
        print(Fore.GREEN +"\tFinished => \tPublic IP {} detached from NIC {}.".format(public_ip_address.name, NIC_NAME ))
        return True
    else:
        print(Fore.RED +"\tError => \tNo Public IP attached to NIC {}.".format(NIC_NAME))
        return False




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
            print(Fore.RED + "\tError => \tNSG {} doesn't exists".format(NSG_NAME))
            return False
        else:
            raise
    except Exception as ex:
        print(Fore.MAGENTA + "\tWarning => \tAn \tError occurred while deleting NSG {}".format(NSG_NAME))
        print(Fore.YELLOW + f"Message => \t{ex}")
        return False
    else:
        # Supprimer le Groupe de sécurité réseau
        network_client.network_security_groups.begin_delete(GROUP_NAME, NSG_NAME).wait()
        print(Fore.GREEN +"\tFinished => \tNSG {} deleted.".format(NSG_NAME))
        return True

def delete_public_ip_address():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)

    # Récupérer la liste des adresses IP publiques dans le groupe de ressources
    public_ips = network_client.public_ip_addresses.list(GROUP_NAME)
    
    # Chercher l'adresse IP publique avec le nom recherché
    public_ip = next((item for item in public_ips if item.name == PUBLIC_IP_NAME), None)

    if public_ip is None:
        print(Fore.MAGENTA +"\tWarning => \tPublic IP address '{}' not found".format(PUBLIC_IP_NAME))
        return False

    # Supprimer l'adresse IP publique
    network_client.public_ip_addresses.begin_delete(GROUP_NAME, public_ip.name).wait()
    print(Fore.GREEN +"\tFinished => \tPublic IP address '{}' deleted".format(PUBLIC_IP_NAME))
    return True

def detach_network_security_group():
    credential, subscription = get_credentials()
    network_client = NetworkManagementClient(credential, subscription)
    compute_client = ComputeManagementClient(credential, subscription)
    
    # Récupérer la liste des NSG dans le groupe de ressources
    nsg_list = network_client.network_security_groups.list(GROUP_NAME)
    
    if not nsg_list:
        print(Fore.RED +"\tError => \tNo network security groups found in resource group '{}'".format(GROUP_NAME))
        return False
    
    # Chercher le NSG avec le nom recherché
    nsg = None
    for item in nsg_list:
        if item.name == NSG_NAME:
            nsg = item
            break
    
    if nsg is None:
        print(Fore.MAGENTA +"\tWarning => \tNetwork Security Group '{}' not found".format(NSG_NAME))
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
            print(Fore.GREEN +"\tFinished => \tNetwork security group '{}' detached from network interface '{}'".format(NSG_NAME, nic.id))
    except TypeError:
        print(Fore.RED +"\tError => \tNo network interfaces found for Network Security Group '{}'".format(NSG_NAME))
        return False

    if nsg.network_interfaces is None:
        print(Fore.RED +"\tError => \tNo network interfaces found for Network Security Group '{}'".format(NSG_NAME))
        return False
    
    # Vérifier si le NSG est encore attaché à des interfaces réseau
    still_attached = False
    for nic in nsg.network_interfaces:
        network_interface = network_client.network_interfaces.get(GROUP_NAME, network_interface_name=NIC_NAME)
        if network_interface.network_security_group is not None:
            still_attached = True
            break
    if still_attached:
        print(Fore.RED +"\tError => \tNetwork Security Group '{}' is still attached to at least one network interface".format(NSG_NAME))
        return False
    else:
        print(Fore.GREEN +"\tFinished => \tNetwork Security Group '{}' detached from all network interfaces".format(NSG_NAME))
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
    except CloudError:
        print(Fore.RED +'\tError => \tA VM delete operation failed: {}'.format(traceback.format_exc()))
        return False
    print(Fore.GREEN +"\tFinished => \tDeleted VM {}".format(VM_NAME))
    return True

def create_nic(network_client):
    """
        Create a Network Interface for a VM.
    """
    # Create VNet
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
        PUBLIC_IP_NAME,
        public_ip_parameters
    )
 
    public_ip_info = async_public_ip_creation.result()
    local_ip_address = public_ip_info.ip_address
    ip_config = nic.ip_configurations[0]
    ip_config.public_ip_address = public_ip_info
    async_nic_update = network_client.network_interfaces.begin_create_or_update(
        GROUP_NAME,
        NIC_NAME,
        nic
    )
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
PUBLIC_IP_NAME = 'public-ip-' + VM_NAME
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
    init() # sous windows
    print(Style.NORMAL)
    createVM()
    print(Style.RESET_ALL)

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