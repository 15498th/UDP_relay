#!/usr/bin/env python3

import argparse
import configparser
import logging
import select
import socket
from typing import Dict

DEFAULT_CONFIG_PATH = 'udp_relay.ini'
DEFAULT_SECTION = 'common'
DEFAULT_ADDRESS = '127.0.0.1'
UDP_MAX_SIZE = 4096
PING_INTERVAL = 60
PING_MSG = "long random phrase that is unlikely to exist in payload"

SIDES = ['left', 'right']
MODES = ['bind', 'connect', 'bind-relay', 'connect-relay']


def set_logger(log_level):
    log_format = '[%(asctime)s] %(message)s'
    datefmt = '%Y/%m/%d %H:%M:%S'
    logging.basicConfig(level=log_level, format=log_format, datefmt=datefmt)

def try_parse(value, parse=lambda x: x, msg=None):
    '''return parse(value) or raise ValueError if exception happens'''
    try:
        return parse(value)
    except Exception as e:
        if msg is not None:
            raise ValueError(msg) from e
        else:
            raise

def parse_config_var(conf, name, parser, section=None):
    value = conf.get(name)
    msg = f'invalid {name} parameter: {value}'
    if section is not None:
        msg = f'Error in section {section}: ' + msg
    return try_parse(value, parser, msg)

def parse_host(host):
    try:
        socket.gethostbyaddr(host)
    except Exception as e:
        if isinstance(e, socket.gaierror):
            raise
    return host

def parse_port(port):
    p = int(port)
    if 1 <= p and p <= 0xFFFF:
        return p
    else:
        raise ValueError('Not in valid port range')

def pprint_list(lst):
    return ', '.join(item for item in lst)

def read_config(path):

    defaults = dict(host=DEFAULT_ADDRESS,
                    udp_max_size=UDP_MAX_SIZE,
                    ping_interval=PING_INTERVAL,
                    ping_msg=PING_MSG)
    c = configparser.ConfigParser(default_section=DEFAULT_SECTION)
    c[DEFAULT_SECTION] = defaults
    # open explicitly to cause exception on error
    # configparser will silently ignore non-existing file
    file = open(path, 'rt')
    c.read_file(file)

    conf = {}

    to_bytes = lambda string: string.encode('utf8')
    parsers = {'udp_max_size': int, 'ping_interval': int, 'ping_msg': to_bytes, 'host': parse_host}
    for name, parser in parsers.items():
        conf[name] = parse_config_var(c.defaults(), name, parser, DEFAULT_SECTION)

    for name, section in c.items():
        if name.lower() == c.default_section.lower():
            continue
        if name not in SIDES:
            sides = pprint_list(SIDES)
            msg = f'Invalid side in section name {name}. Valid sides = {sides}'
            raise ValueError(msg)
        mode = section.get('mode')
        if mode not in MODES:
            modes = pprint_list(MODES)
            msg = f'Invalid mode in section name {name}. Valid sides = {sides}'
            raise ValueError(msg)
        bind = mode in ['bind', 'bind-relay']
        ping = mode in ['bind-relay', 'connect-relay']
        ping_msg = conf['ping_msg'] if ping else None
        udp_max_size = conf['udp_max_size']
        host = parse_config_var(section, 'host', parse_host, name)
        port = parse_config_var(section, 'port', parse_port, name)
        relay = dict(port=port, host=host, bind=bind, ping_msg=ping_msg, recv_size=udp_max_size, name=name)
        conf[name] = relay
    return conf

class Relay:

    def __init__(self, name, host, port, bind=False, ping_msg=None, recv_size=1024):
        self.name = name
        self.size = recv_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        if bind:
            try:
                self.sock.bind((host, port))
                logging.info(f'[{self.name}] listening on {host}:{port}')
            except OSError as e:
                msg = f'[{self.name}] Error binding to {host}:{port}: {e.strerror}'
                raise OSError(msg) from e
            self.remote = None
        else:
            self.remote = (host, port)
            logging.info(f'[{self.name}] relaying to {host}:{port}')
        self.ping_msg = ping_msg
        self.send_ping = not bind and ping_msg is not None
        self.ping()

    def recv(self):
        try:
            data, address = self.sock.recvfrom(self.size)
        except OSError as e:
            logging.debug(f'[{self.name}] on recv: {e}')
            return None
        if self.remote != address:
            logging.info(f'[{self.name}]: update remote from {self.remote} to {address}')
            self.remote = address
        if self.ping_msg is not None:
            if data == self.ping_msg:
                return None
        return data

    def send(self, data):
        if self.remote is None:
            logging.debug(f'[{self.name}]: asked to send when remote is not yet set')
            return
        try:
            self.sock.sendto(data, self.remote)
        except OSError as e:
            logging.debug(f'[{self.name}] on send: {e}')
            return

    def ping(self):
        if self.send_ping:
            self.send(self.ping_msg)
            logging.debug(f'[{self.name}]: send ping')

def run(sockets: Dict[socket.socket, Relay], ping_interval):
    while True:
        readable, _, _ = select.select(sockets.keys(), [], [], ping_interval)
        if not readable:
            for relay in sockets.values():
                relay.ping()
        for sock in readable:
            data = sockets[sock].recv()
            if data is not None:
                for other_sock in sockets:
                    if other_sock is not sock:
                        sockets[other_sock].send(data)

def main():
    description = 'Pipe data between two UDP sockets'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('config', nargs='?',
                        default=DEFAULT_CONFIG_PATH,
                        help='Path to configuration file')
    parser.add_argument('--verbose', '-v',
                        action='store_true', default=False,
                        help='Show debug output')
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    set_logger(log_level)

    if args.config == DEFAULT_CONFIG_PATH:
        logging.info(f'Path to configuration file not specified, using default {DEFAULT_CONFIG_PATH}')

    try:
        conf = read_config(args.config)
        relays = [Relay(**conf[side]) for side in SIDES]
    except Exception as e:
        logging.error(e)
        return

    sockets = {relay.sock: relay for relay in relays}

    try:
        run(sockets, conf['ping_interval'])
    except KeyboardInterrupt:
        logging.info('Stopping...')
    finally:
        for sock in sockets:
            sock.close()


if __name__ == '__main__':
    main()
