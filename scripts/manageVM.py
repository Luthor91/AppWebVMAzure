import subprocess, traceback, platform, json, time, os, threading, azure, webbrowser, argparse
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

def switch_case(case):
    # appel de la fonction associée à la valeur de la case
    func = switcher.get(case, lambda: print("Case non valide"))
    return func

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

def get_credentials():
    subscription_id = subscription
    credentials = ClientSecretCredential(
        client_id=client,
        client_secret=secret,
        tenant_id=tenant
    )
    return credentials, subscription_id

def get_json_data(url):
    with open(url, 'r') as f:
        contenu = f.read()        
        donnees = json.loads(contenu)
        return donnees
    
def listVM(vm_name):
    # Recherche des ressources du groupe de ressources
    try:
        resources = resource_client.resources.list_by_resource_group(GROUP_NAME, expand="resourceType")
        # Parcours des ressources trouvées
        for resource in resources:
            # Si la ressource appartient à la VM recherchée, on l'affiche
            if vm_name in resource.name:
                print(f"{resource.type} -> {resource.name}")
    except Exception:
        # Affichage en cas d'erreur
        print(Fore.RED + "Erreur lors de la recherche des ressources")

def stopVM(vm_name):
    try:
        compute_client = ComputeManagementClient(credentials, subscription_id)
        async_vm_stop = compute_client.virtual_machines.power_off(GROUP_NAME, vm_name)
        async_vm_stop.wait()
        print(f"La VM {vm_name} a été arrêtée")
    except CloudError as e:
        print(str(e))

def restartVM(vm_name):
    compute_client = ComputeManagementClient(credentials, subscription_id)
    try:
        async_vm_restart = compute_client.virtual_machines.begin_restart(
            GROUP_NAME, vm_name
        )
        async_vm_restart.wait()
        print(Fore.GREEN + f"La VM {vm_name} a été redémarrée avec succès")
    except CloudError as e:
        print(Fore.RED + f"Erreur lors du redémarrage de la VM {vm_name}")
        print(f"{traceback.format_exc()}")

def startVM(vm_name):
    try:
        vm = compute_client.virtual_machines.get(GROUP_NAME, vm_name)
        async_vm_start = compute_client.virtual_machines.start(GROUP_NAME, vm_name)
        async_vm_start.wait()
        print(Fore.GREEN + f"La VM {vm_name} a été démarrée avec succès !")
    except CloudError as e:
        print(Fore.RED + f"Erreur lors du démarrage de la VM {vm_name} : {e}")

def deleteVM(vm_name):
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
    
    
data_conn = get_json_data('../data/azure.json')
tenant = data_conn['TENANT']
client = data_conn['CLIENT']
secret = data_conn['SECRET']
subscription = data_conn['SUBSCRIPTION']
GROUP_NAME = 'group-appwebpython'
credentials, subscription_id = get_credentials()
resource_client = ResourceManagementClient(credentials, subscription_id)

parser = argparse.ArgumentParser()
parser.add_argument('nameVM', help='nom de la vm')
parser.add_argument('type', help="type d'operation")
args = parser.parse_args()
vm_name = args.nameVM
func = args.type
switcher = {
    'list': listVM,
    'stop': stopVM,
    'restart': restartVM,
    'start': startVM,
    'delete': deleteVM
}

if __name__ == "__main__":
    init() # sous windows
    print(Style.NORMAL)
    func = switch_case(func)
    func(vm_name)
    print(Style.RESET_ALL)
    
    #url = "http://localhost/php/listVM.php"
    #webbrowser.open_new_tab(url)