from cuttlefish.params import SelectParam, StringParam
from cuttlefish.plugins import CuttlePlugin
from cuttlefish.events import CuttleEvent, DBusEvent

import dbus

import logging
logger = logging.getLogger('cuttlefish.plugins.OnDBusEvent')


class OnDBusEvent(CuttleEvent, CuttlePlugin):
    NAME = 'D-Bus Event'
    DESCP = 'React when receiving the specified D-Bus signal'
    CATEGORY = 'System'
    PARAMS = {
        'dbus_bus' : DBusEvent.USE_SESSION_BUS,
        'dbus_path' : '',
        'dbus_interface' : '',
        'dbus_signal' : '',
        # TODO: add desired values to compare with the signal parameters
    }

    class Editor(CuttlePlugin.Editor):
        ORDER = ['dbus_bus', 'dbus_path', 'dbus_interface', 'dbus_signal']
        DBUS_BUS_SELECTION = {
            DBusEvent.USE_SYSTEM_BUS : 'System Bus',
            DBusEvent.USE_SESSION_BUS : 'Session Bus',
        }

        def begin(self):
            return {
                'dbus_bus' : SelectParam('D-Bus to use', self.DBUS_BUS_SELECTION, int),
                'dbus_path' : StringParam('D-Bus path (empty means all)'),
                'dbus_interface' : StringParam('D-Bus interface (empty means all)'),
                'dbus_signal' : StringParam('D-Bus signal (empty means all)'),
                # TODO: add desired values to compare with the signal parameters
            }


    def __init__(self):
        CuttleEvent.__init__(self)
        CuttlePlugin.__init__(self)
        self.dbusEvent = None

    def setup(self):
        __optional = lambda x: None if len(x) == 0 else str(x)

        signal = __optional(self._params['dbus_signal'])
        interface = __optional(self._params['dbus_interface'])
        path = __optional(self._params['dbus_path'])

        if self.dbusEvent is not None:
            self.dbusEvent.teardown()
        self.dbusEvent = DBusEvent(self._on_dbus_event, signal, interface, path, self._params['dbus_bus'])
        self.dbusEvent.setup()

    def teardown(self):
        if self.dbusEvent is not None:
            self.dbusEvent.teardown()
        # teardown does not properly unregister the signal callback, reset the dbus event handler variable to indicate teardown
        self.dbusEvent = None

    def triggerOnStartup(self):
        self._trigger()

    def _on_dbus_event(self, *args):
        # teardown does not properly unregister the signal callback, check if we were already torn down...
        if self.dbusEvent is not None:
            # TODO: compare signal parameters with desired values here
            self._trigger(*args)

    def _trigger(self, *args):
        self.logger.debug(repr(args))
        self.logger.debug(repr(self._params))
        self.trigger()
