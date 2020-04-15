import json
import asyncio
import logging
import threading

from .helpers import threadsafe_JSON
from .eva_ws import ws_connect
from .eva_errors import EvaDisconnectionError


class EvaState:
    """
    TODO
    """
    def __init__(self, host_ip, session_token, starting_state):
        self.host_ip = host_ip
        self.session_token = session_token
        self.starting_state = starting_state

        self.__logger = logging.getLogger('automata.Eva:{}'.format(host_ip))

        # Create the threadsafe_JSON used to merge ws update events onto the Eva snapshot
        self.__state = threadsafe_JSON()
        self.__state.update(starting_state)

        self.__state_handler_function = None
        self.__async_running = True
        self.__ws_msg_count = 0

        # Start the async thread
        self.__thread = threading.Thread(target=self.__start_loop)
        self.__thread.start()

        # TODO: need to check that websocket connects here

    def __start_loop(self):
        self.__loop = asyncio.new_event_loop()
        self.__logger.debug("Async loop started")
        self.__loop.run_until_complete(self.__ws_update_handler())
        self.__logger.debug("Async loop stopped")


    async def __ws_update_handler(self):
        # TODO need to handle exceptions and pass them to the main thread
        self.__websocket = await ws_connect(self.host_ip, self.session_token)

        while self.__async_running:
            try:
                # TODO: need to tune the timeout
                ws_msg_json = await asyncio.wait_for(self.__websocket.recv(), timeout=1)
            except asyncio.TimeoutError:
                continue

            ws_msg = json.loads(ws_msg_json)

            # TODO: need to ignore non state_change messages, this may be a bit brittle
            if 'changes' in ws_msg:
                new_state = self.__state.merge_update(ws_msg['changes'])

                self.__logger.debug('ws msg received: {}'.format(self.__ws_msg_count))
                self.__ws_msg_count += 1

                if self.__state_handler_function is not None:
                    self.__state_handler_function(ws_msg['changes'])

        self.__logger.debug('closing websocket')
        await self.__websocket.close()


    def close(self):
        """
        close() disconnects eva_object from Eva.
        close() is idempotent: it doesn’t do anything once the connection is closed.
        Once close() has been called you cannot reconnect with this object, make a
        new object instance instead.
        """
        if self.__async_running:
            self.__async_running = False
            self.__thread.join()


    def state(self):
        if not self.__async_running:
            raise EvaDisconnectionError()
        return self.__state.get()


    def add_state_change_handler(self, state_handler_function):
        # TODO: should be able to add multiple handlers and give handler ID on success
        if not self.__async_running:
            raise EvaDisconnectionError()

        if self.__state_handler_function is not None:
            raise ValueError

        # TODO lock needed
        self.__state_handler_function = state_handler_function


    def remove_state_change_handler(self):
        # TODO: should pass in a handler ID
        if not self.__async_running:
            raise EvaDisconnectionError()

        # TODO lock needed
        self.__state_handler_function = None
