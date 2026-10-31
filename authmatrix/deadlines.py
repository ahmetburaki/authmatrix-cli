"""Absolute monotonic deadlines across TCP, TLS, HTTP headers and body reads."""
import functools
import http.client
import io
import socket
import time


DEFAULT_REQUEST_TIMEOUT = 10.0
DEFAULT_RUN_TIMEOUT = 120.0
IDLE_TIMEOUT = 5.0


def timeout_seconds(value):
    if type(value) not in (int, float) or not 0 < value <= 3600:
        raise ValueError("Timeout must be a finite positive number up to 3600 seconds")
    return float(value)


class DeadlineExceeded(TimeoutError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class Budget:
    def __init__(self, request_end, run_end):
        self.request_end = request_end
        self.run_end = run_end
        self._socket_limit = None

    def remaining(self):
        now = time.monotonic()
        if now >= self.run_end:
            raise DeadlineExceeded("run_timeout")
        if now >= self.request_end:
            raise DeadlineExceeded("request_timeout")
        return min(self.request_end, self.run_end) - now

    def socket_timeout(self):
        remaining = self.remaining()
        self._socket_limit = None if remaining > IDLE_TIMEOUT else (
            "run_timeout" if self.run_end <= self.request_end else "request_timeout")
        return min(IDLE_TIMEOUT, remaining)

    def raise_timeout(self):
        self.remaining()
        # Socket timers can expire just before the monotonic clock reaches the
        # deadline. Preserve the limit that supplied this operation's allowance.
        if self._socket_limit is not None:
            raise DeadlineExceeded(self._socket_limit) from None


class _DeadlineReader(io.RawIOBase):
    def __init__(self, sock, budget):
        self.sock = sock
        self.budget = budget
        # SocketIO owns a reference even if getresponse detaches conn.sock.
        self.stream = sock.makefile("rb", buffering=0)

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(self.budget.socket_timeout())
        try:
            count = self.stream.readinto(buffer)
        except TimeoutError:
            self.budget.raise_timeout()
            raise
        self.budget.remaining()
        return count

    def close(self):
        try:
            self.stream.close()
        finally:
            super().close()


class _ResponseSocket:
    def __init__(self, sock, budget):
        self.sock = sock
        self.budget = budget

    def makefile(self, mode):
        if mode != "rb":
            raise ValueError("Only binary response reads are supported")
        return io.BufferedReader(_DeadlineReader(self.sock, self.budget))


class _DeadlineResponse(http.client.HTTPResponse):
    def __init__(self, sock, *args, budget, **kwargs):
        super().__init__(_ResponseSocket(sock, budget), *args, **kwargs)


class _DeadlineConnection:
    def __init__(self, host, port, *, budget):
        self.budget = budget
        super().__init__(host, port, timeout=budget.socket_timeout())
        self._create_connection = self._connect_socket
        self.response_class = functools.partial(_DeadlineResponse, budget=budget)

    def _connect_socket(self, address, timeout, source_address):
        sock = socket.create_connection(address, self.budget.socket_timeout(), source_address)
        try:
            # HTTPSConnection uses this updated allowance for TLS after TCP.
            sock.settimeout(self.budget.socket_timeout())
            return sock
        except BaseException:
            sock.close()
            raise

    def connect(self):
        try:
            super().connect()
        except TimeoutError:
            self.budget.raise_timeout()
            raise
        self.sock.settimeout(self.budget.socket_timeout())

    def send(self, data):
        self.budget.remaining()
        if self.sock is not None:
            self.sock.settimeout(self.budget.socket_timeout())
        try:
            super().send(data)
        except TimeoutError:
            self.budget.raise_timeout()
            raise
        self.budget.remaining()


class HTTPConnection(_DeadlineConnection, http.client.HTTPConnection):
    pass


class HTTPSConnection(_DeadlineConnection, http.client.HTTPSConnection):
    pass
