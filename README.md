## UDP_relay

Forward UDP packets between two endpoints, with each of them being either listening on port or making connection.

### Usage

```
usage: udp_relay.py [-h] [-v] [config]

positional arguments:
  config         Path to configuration file, default is udp_relay.ini

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Show debug output
```

`udp_relay.py` takes one positional argument, which is path to configuration file. If not specified, default `udp_relay.ini` in working directory is used.
Example of configuration is provided in [udp_relay.ini.example](udp_relay.ini.example). Rename and adjust it as needed, then run the script.

### Configuration

Configuration file is based on basic INI format, with `[section]`s containing `key = value` pairs. 
Here example of simple config, that will make UDP_relay to wait for connections on port `53` and relay received packages to server on `127.0.0.1:5353`, and pass anything it replies back.

```
[left]
mode: bind
host: 0.0.0.0
port: 53

[right]
mode: connect
port: 5353
```

It consists of two sections, representing two `sides` of data exchange, [left] and [right], each specifying `host`, `port` and `mode` parameters.
Default host value is `127.0.0.1`. To allow connections from other machines on network use special value `0.0.0.0`.
There are four possible `mode`s:
- `bind` - to listen on specified host:port
- `connect` - to connect to specified host:port
- `bind-relay` and `connect-relay` - same as above, should be used when interacting with another copy of UDP_relay.py

See [example config](udp_relay.ini.example) for adjusting defaults values.
