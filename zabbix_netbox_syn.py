from pyzabbix import ZabbixAPI
import pynetbox

# Conexão com o Zabbix
zabbix = ZabbixAPI("URL_ZABBIX")
zabbix.login("user", "password")

# Conexão com o Netbox
netbox = pynetbox.api(
    "https://IP_NETBOX/",
    token="SEU_TOKEN_NETBOX"
)

netbox.http_session.verify = False

# Primeiro, obtenha o ID do grupo BACKBONE
backbone_group_id = zabbix.hostgroup.get(filter={"name": "BACKBONE"})[0]['groupid']

# Agora, obtenha os hosts que fazem parte do grupo BACKBONE
zabbix_hosts = zabbix.host.get(groupids=backbone_group_id, output="extend")

for zabbix_host in zabbix_hosts:
    # Tente criar o dispositivo no Netbox ou obtenha se já existe
    try:
        corresponding_netbox_devices = netbox.dcim.devices.filter(name=zabbix_host['host'])
        corresponding_netbox_device = None

        for device in corresponding_netbox_devices:
            corresponding_netbox_device = device
            break  # Apenas pega o primeiro dispositivo correspondente


        if not corresponding_netbox_device:
            corresponding_netbox_device = netbox.dcim.devices.create(
                name=zabbix_host['host'],
                device_type=7,
                device_role=1,
                site=1,
            )
            print(f"Dispositivo criado: {corresponding_netbox_device.name}")
        else:
            print(f"Dispositivo encontrado: {corresponding_netbox_device.name}")

        # Se o dispositivo foi criado com sucesso ou já existe
        if corresponding_netbox_device:
            # Obter as interfaces atuais do dispositivo no NetBox
            existing_interfaces = netbox.dcim.interfaces.filter(device_id=corresponding_netbox_device.id)

            # Converter a lista de interfaces existentes em um conjunto de nomes para busca rápida
            existing_interface_names = {iface.name for iface in existing_interfaces}
            # Obter aplicações que contêm a palavra 'INTERFACE' no nome para o host específico
            zabbix_applications = zabbix.application.get(hostids=zabbix_host['hostid'], search={"name": "INTERFACE"}, output=["name"])
        
            for app in zabbix_applications:
                app_name = app['name']
                # Pular aplicação se apenas contém a palavra 'INTERFACE'
                if app_name.strip().lower() == 'interface':
                    continue
                
                # Remover a palavra 'INTERFACE' do nome da aplicação
                interface_name = app_name.replace('INTERFACE', '').strip()

                # Verifique se a interface já existe no NetBox
                if interface_name not in existing_interface_names:
                    # A interface não existe, crie-a
                    try:
                        new_interface = netbox.dcim.interfaces.create(
                            device=corresponding_netbox_device.id,
                            name=interface_name,
                            type="other"  # ou outro tipo conforme necessário
                        )
                        print(f"Interface '{interface_name}' criada com sucesso.")
                    except pynetbox.RequestError as e:
                        print(f"Erro ao criar interface '{interface_name}': {e.error}")
                else:
                    print(f"Interface '{interface_name}' já existe no dispositivo.")

    except pynetbox.RequestError as e:
        print(f"Erro ao criar/obter dispositivo {zabbix_host['host']}: {e.error}")
