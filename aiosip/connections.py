import logging
import asyncio
import uuid


from .dialplan import Router

LOG = logging.getLogger(__name__)


class Connection:
    def __init__(self, local_addr, remote_addr, protocol, app):
        self.app = app
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self.protocol = protocol
        self.dialogs = {}

        self.closed = False

    def send_message(self, msg):
        if self.closed:
            raise ConnectionError

        if isinstance(self.protocol, asyncio.DatagramProtocol):
            self.protocol.send_message(msg, self.remote_addr)
        else:
            self.protocol.send_message(msg)

    def create_dialog(self, from_uri, to_uri, contact_uri=None, password=None, call_id=None, cseq=0, router=Router()):
        if self.closed:
            raise ConnectionError

        if not call_id:
            call_id = str(uuid.uuid4())

        dialog = self.app.dialog_factory(
            app=self.app,
            from_uri=from_uri,
            to_uri=to_uri,
            call_id=call_id,
            connection=self,
            contact_uri=contact_uri,
            password=password,
            cseq=cseq,
            router=router
        )

        self.dialogs[call_id] = dialog
        return dialog

    def close(self):
        print("CLOSING HERE", self)
        self.protocol.close()
        self.closed = True

    def _connection_lost(self):
        self.closed = True
        LOG.debug('Connection lost for %s', self.remote_addr)
        for dialog in self.dialogs.values():
            dialog._connection_lost()
        self.dialogs = {}

    def _stop_dialog(self, call_id):
        try:
            del self.dialogs[call_id]
        except KeyError:
            pass

    def close(self):
        LOG.debug('Closing connection for %s', self.remote_addr)
        self.closed = True
        self.protocol.transport.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self):
        from_uri = '{}:{}'.format(*self.remote_addr) if self.remote_addr else None
        to_uri = '{}:{}'.format(*self.local_addr) if self.local_addr else None

        return '<{} from={}, to={}, 0x{:x}>'.format(self.__class__.__name__,
                                                from_uri, to_uri, id(self.protocol))
