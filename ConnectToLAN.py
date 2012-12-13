from cuttlefish.params import SelectParam
from cuttlefish.plugins import CuttlePlugin
from cuttlefish.events import DBusEvent

import dbus
import re
import subprocess

import logging
logger = logging.getLogger('cuttlefish.plugins.ConnectToLAN')

DBUS_ADDR_PROPS = 'org.freedesktop.DBus.Properties'
DBUS_ADDR_NM = 'org.freedesktop.NetworkManager'
DBUS_PATH_NM = '/org/freedesktop/NetworkManager'


def get_mac_from_ip(ip):
  try:
    # send pings to ip until one answer received or 3 sec timeout
    out = subprocess.check_output(['ping', '-c', '1', '-w', '3', ip])
  except subprocess.CalledProcessError:
    logger.warning('error pinging ip "%s"' % ip)
    return None
  
  try:
    # get mac address for ip from arp cache
    out = subprocess.check_output(['arp', '-n', ip])
  except subprocess.CalledProcessError:
    logger.warning('error getting MAC address for ip "%s" from arp cache' % ip)
    return None

  # check for valid mac address
  match = re.search('([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', out)
  if match:
    mac = match.group()
    logger.debug('IP: "%s" -> MAC: "%s"' % (ip, mac))
    return mac
  
  return None


def get_dbus_nm_props(addr=DBUS_ADDR_NM, path=DBUS_PATH_NM, bus=dbus.SystemBus()):
  obj = bus.get_object(addr, path)
  props = dbus.Interface(obj, DBUS_ADDR_PROPS)
  return props
  

def get_wired_dhcp_macs():
  dhcp_macs = {}
  nm_props = get_dbus_nm_props()
  for ac_path in nm_props.Get(DBUS_ADDR_NM, 'ActiveConnections'):
    ac_props = get_dbus_nm_props(path=ac_path)
    
    for dev_path in ac_props.Get(DBUS_ADDR_NM + '.Connection.Active', 'Devices'):
      dev_props = get_dbus_nm_props(path=dev_path)

      try:
        # check if this is a wired device
        dev_props.Get(DBUS_ADDR_NM + '.Device.Wired', 'HwAddress')
      except:
        logger.debug('skipping wireless device: ' + dev_path)
        continue
      
      interface_name = dev_props.Get(DBUS_ADDR_NM + '.Device', 'Interface')
      
      dhcp_path = dev_props.Get(DBUS_ADDR_NM + '.Device', 'Dhcp4Config')
      dhcp_props = get_dbus_nm_props(path=dhcp_path)
    
      try:
        dhcp_options = dhcp_props.Get(DBUS_ADDR_NM + '.DHCP4Config', 'Options')
      except:
        continue

      dhcp_ip = dhcp_options.get('server_name', dhcp_options.get('dhcp_server_identifier', None))
      if dhcp_ip is None:
        continue
      dhcp_ip = str(dhcp_ip)
      
      dhcp_mac = get_mac_from_ip(dhcp_ip)

      if dhcp_mac is not None:
        dhcp_macs[dhcp_mac] = '%s [%s] (%s)' % (dhcp_mac, dhcp_ip, interface_name)
    
  return dhcp_macs


class ConnectToLAN(DBusEvent, CuttlePlugin):
  NAME = 'Connect to LAN'
  DESCP = 'React when connecting to a specified wired network (identified by the MAC address of the DHCP server)'
  CATEGORY = 'Network'
  PARAMS = {
    'dhcp_mac' : '',
    'interface_name' : '',
  }

  #http://projects.gnome.org/NetworkManager/developers/api/09/spec.html#type-NM_STATE
  NM_STATE_CONNECTED_GLOBAL = 70

  class Editor(CuttlePlugin.Editor):
    NOT_CONNECTED = ' (not connected)'
    
    def begin(self):
      dhcp_macs = get_wired_dhcp_macs()
      if self._params['dhcp_mac'] != '' and self._params['dhcp_mac'] not in dhcp_macs:
        dhcp_macs[self._params['dhcp_mac']] = self._params['dhcp_mac'] + self.NOT_CONNECTED
      return {
          'dhcp_mac' : SelectParam('MAC of the DHCP server of this network', dhcp_macs, str)
        }
    
    def finish(self, ui):
      if 'dhcp_mac' in ui:
        self._params['interface_name'] = ui['dhcp_mac'].get_caption().rstrip(self.NOT_CONNECTED)

  def __init__(self):
    DBusEvent.__init__(self, self._on_connect_state_changed, 'StateChanged', DBUS_ADDR_NM, DBUS_PATH_NM, DBusEvent.USE_SYSTEM_BUS)
    CuttlePlugin.__init__(self)

  def triggerOnStartup(self):
    nmobj = self._bus.get_object(DBUS_ADDR_NM, DBUS_PATH_NM)
    nmprops = dbus.Interface(nmobj, DBUS_ADDR_PROPS)
    self._on_connect_state_changed(nmprops.Get(DBUS_ADDR_NM, 'State'))

  def _on_connect_state_changed(self, state):
    self.logger.debug('state %d' % state)
    if state == self.NM_STATE_CONNECTED_GLOBAL:
      dhcp_macs = get_wired_dhcp_macs()
      if self._params['dhcp_mac'] in dhcp_macs:
        self.trigger()

