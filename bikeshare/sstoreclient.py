import socket
import json

# Class which acts as an interface to S-Store.
class sstoreclient(object):
    addr = None
    port = None
    s = None
    pipe = None
    buf = None
    connected = False
    
    def __init__(self, addr='localhost', port=6000):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.pipe = self.s.makefile()
        self.addr = addr
        self.port = port
        self.buf = ''
        self.connected = False

    def connect(self):
        if not self.connected:
            self.s.connect((self.addr, self.port))
            self.connected = True
        return True

    def disconnect(self):
        try:
            self.s.close()
        finally:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.pipe.close()
        finally:
            self.pipe = self.s.makefile()
        self.connected = False
        return True

    def reconnect(self):
        self.disconnect()
        self.connect()
        return True

    def call_proc(self, proc='', args=[], keepalive=False):
        # Connect first, if necessary.
        if not self.connected:
            self.connect()
        # Clear buffer.
        self.buf = ''
        # Construct the object which will be converted to JSON and sent to the
        # database client.
        call = dict()
        call['proc'] = proc
        call['args'] = list()
        for arg in args:
            call['args'] += [arg]
        # Send JSON to the database client, then receive results.
        try:
            self.pipe.write(json.dumps(call) + "\n")
            try:
                self.pipe.flush()
            except Exception as e:
                # If socket was terminated prematurely, attempt to reconnect.
                if e.errno == 32:
                    self.reconnect()
                    self.pipe.write(json.dumps(call) + "\n")
                    self.pipe.flush()
                else:
                    raise e
        except Exception as e:
            # If socket was terminated prematurely, attempt to reconnect.
            if e.errno == 32:
                self.reconnect()
                self.pipe.write(json.dumps(call) + "\n")
                self.pipe.flush()
            else:
                raise e
        self.buf = self.pipe.readline()
        rtn = json.loads(self.buf)
        # If we haven't instructed the connection to stay open, disconnect.
        if not keepalive:
            self.disconnect()
        return rtn
