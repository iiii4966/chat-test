import asyncio
from dataclasses import dataclass
from functools import cached_property

from autobahn.asyncio.websocket import WebSocketServerProtocol, WebSocketServerFactory

"""

Todo

- implement channel layer (don't use global!)
- implement persist layer
- implement session
- how to test
- gracefully shutdown

"""

rooms = dict()


@dataclass(frozen=True)
class Room:
    id: int
    member: set

    def join(self, protocol):
        self.member.add(protocol)

    def exit(self, protocol):
        self.member.remove(protocol)

    @property
    def is_empty(self):
        return len(self.member) == 0


class MyServerProtocol(WebSocketServerProtocol):

    @property
    def room_id(self):
        """
        obtain room identifier on path
        """
        return self.http_request_path.strip("/")

    @property
    def room(self):
        if self.room_id in rooms:
            return rooms[self.room_id]
        return self.create_room()

    def create_room(self):
        room = Room(self.room_id, set())
        room.join(self)
        rooms[room.id] = room
        return room

    def remove_room(self):
        if self.room_id in rooms:
            del rooms[self.room_id]

    def enter_room(self):
        self.room.join(self)

    def exit_room(self):
        self.room.exit(self)
        if self.room.is_empty:
            self.remove_room()

    def onConnect(self, request):
        print("connected")

    def onOpen(self):
        self.enter_room()

    def onMessage(self, payload, is_binary):
        for member in self.room.member:
            member.sendMessage(payload, is_binary)

    def onClose(self, was_clean, code, reason):
        self.exit_room()
        print("disconnected")


class Application:

    def __init__(self,  protocol, host='127.0.0.1', port='9000'):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.url = f"ws://{host}:{port}"
        self.factory = WebSocketServerFactory(self.url)
        self.factory.protocol = protocol
        self.server = None

    @cached_property
    def loop(self):
        loop = asyncio.get_event_loop()
        return loop

    def run(self):
        runnable_server = self.loop.create_server(self.factory, '0.0.0.0', 9000)
        self.server = self.loop.run_until_complete(runnable_server)
        try:
            print("server run " + self.url)
            if self.loop.is_running():
                self.loop.stop()
            self.loop.run_forever()
        except KeyboardInterrupt:
            print("shutdown...")
        finally:
            self.stop()

    def stop(self):
        if self.server is None:
            raise Exception("server not running")
        self.server.close()
        self.loop.close()
        print("server closed")


if __name__ == '__main__':
    app = Application(MyServerProtocol)
    app.run()

