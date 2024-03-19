import select
import socket
import threading
import atexit
import time
from ReNode.app.utils import intTryParse
from PyQt5.QtCore import QObject, QThread


import socket
import time
from ReNode.app.utils import intTryParse
from PyQt5.QtCore import QThread, pyqtSignal

class DummyDebuggerServer(object):
    def stop(self):
        pass

class DebuggerServer(QObject):
    started = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, server_ip="127.0.0.1", server_port=9987, run_now=False, nodeGraphRef=None):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_socket = None
        self.client_socket = None
        self.active = False
        self.nodeGraphComponent = nodeGraphRef

        if run_now:
            self.start()

    def start(self):
        self.threadObj = QThread(self)
        self.threadObj.setObjectName("debugger server")
        self.moveToThread(self.threadObj)
        self.threadObj.started.connect(self.start_internal)
        self.started.connect(self.threadObj.start)
        self.stopped.connect(self.threadObj.quit)
        self.stopped.connect(self.threadObj.wait)

        self.threadObj.finished.connect(self.handle_finished)

        self.threadObj.start()

    def handle_finished(self):
        self.server_socket.close()
        self.client_socket.close()
        self.stopped.emit()

    def start_internal(self):
        self.active = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.listen(1)

        print(f"Python server listening on {self.server_ip}:{self.server_port}")

        while self.active:
            try:
                self.client_socket, client_address = self.server_socket.accept()

                print(f"Connection established with {client_address}")
                
                self.handle_client()
            except Exception as e:
                
                print(f"Exception: {e}")
                # Handle exceptions as needed

    def stop(self):
        self.active = False
        self.server_socket.close()

    def handle_client(self):
        self.client_socket.setblocking(False)
        buffer = b''
        while self.active:
            try:
                ready_to_read, _, _ = select.select([self.client_socket], [], [], 0)
                if ready_to_read:
                    data = self.client_socket.recv(1024)
                    if not data:
                        print("Client disconnected")
                        break

                    buffer += data
                    while b"\0" in buffer:
                        data, buffer = buffer.split(b"\0", 1)
                        self.handle_client_message(data.decode('utf-8'))

            except BlockingIOError:
                print("BlockingIOError")
                pass

        self.client_socket.close()

    def handle_client_message(self, message):
        parts = message.split("@")
        if not parts:
            return
        msg_type = parts[0]
        if msg_type == "nlink":
            if len(parts) != 4:
                return
            # source id, toportid (output_index), graphpath
            for tab in self.nodeGraphComponent.sessionManager.getAllTabs():
                if tab.graph.graphPath == parts[3]:
                    tab.graph.on_node_linked.emit(intTryParse(parts[1], -1),intTryParse(parts[2],-1), parts[3])
                    break

