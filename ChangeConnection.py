from cuttlefish.params import SelectParam
from cuttlefish.plugins import CuttlePlugin
from cuttlefish.actions import CuttleAction

import dbus
import subprocess

import logging
logger = logging.getLogger('cuttlefish.plugins.ChangeConnection')

DBUS_ADDR_NM = 'org.freedesktop.NetworkManager'
DBUS_PATH_NM = '/org/freedesktop/NetworkManager'


def get_known_connections():
  connections = {}
  
  bus = dbus.SystemBus()
  
  settings_obj = bus.get_object(DBUS_ADDR_NM, DBUS_PATH_NM + '/Settings')
  
  for connection_settings_path in settings_obj.ListConnections():
    connection_settings_obj = bus.get_object(DBUS_ADDR_NM, connection_settings_path)

    try:
      connection_options = connection_settings_obj.GetSettings()
      connection_id = str(connection_options['connection']['id'])
      connections[connection_id] = connection_id
    except:
      continue

  return connections


class ChangeConnection(CuttleAction):
  CATEGORY = 'Network'
  PARAMS = {
    'connection_id' : ''
  }

  class Editor(CuttlePlugin.Editor):
    def begin(self):
      known_connections = get_known_connections()
      return {
          'connection_id' : SelectParam('Connection', known_connections, str)
        }

  def __init__(self, active):
    CuttleAction.__init__(self)
    self._active = active

  def execute(self):
    action = 'up' if self._active else 'down'
    subprocess.check_output(['nmcli', 'con', action, 'id', self._params['connection_id']])


class ActivateConnection(ChangeConnection, CuttlePlugin):
  NAME = 'Activate Network Connection'
  DESCP = 'Activate a network connection which has been saved by NetworkManager.'

  def __init__(self):
    ChangeConnection.__init__(self, True)
    CuttlePlugin.__init__(self)
    

class DeactivateConnection(ChangeConnection, CuttlePlugin):
  NAME = 'Deactivate Network Connection'
  DESCP = 'Deactivate a network connection which has been saved by NetworkManager.'

  def __init__(self):
    ChangeConnection.__init__(self, False)
    CuttlePlugin.__init__(self)
