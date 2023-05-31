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

Configuration file uses basic INI format, with `[section]`s containing `key = value` pairs.
Here example of simple config, that will make UDP_relay to wait for connections on port `5551`, relay received packages to server on `127.0.0.1:4000`, and pass anything it replies back.

```
[left]
mode: bind
host: 0.0.0.0
port: 5551

[right]
mode: connect
port: 4000
```

It consists of two sections, representing two `sides` of data exchange, [left] and [right], each specifying `host`, `port` and `mode` parameters.
Default host value is `127.0.0.1`. To allow connections from other machines on network use special value `0.0.0.0`.
There are four possible `mode`s:
- `bind` - to listen on specified host:port
- `connect` - to connect to specified host:port
- `bind-relay` and `connect-relay` - same as above, should be used when interacting with another copy of UDP_relay.py

See [example config](udp_relay.ini.example) for adjusting defaults values.

### Connecting hosts

This script can be used to connect client-server pair of apps running on two machines that are behind NAT or for some other reason cannot accept incoming connections, through third host, accepting connections from both of them and forwarding data back and forth. Assuming server program is waiting for connections on UDP port `4000`, client software insists on connecting to `127.0.0.1:4000`, and host, sending data between client and server machine (relay host) is avaliable on `example.com` with ports `5551` and `5552` open, configuration of three UDP_relay instances would then look like this:

On client machine:
```
[left]
mode: bind
host: 127.0.0.1
port: 4000

[right]
mode: connect-relay
host: example.com
port: 5551
```

On server machine:
```
[left]
mode: connect
host: 127.0.0.1
port: 4000

[right]
mode: connect-relay
host: example.com
port: 5552
```

On relay host:
```
[left]
mode: bind-relay
host: 0.0.0.0
port: 5551

[right]
mode: bind-relay
host: 0.0.0.0
port: 5552
```

Note how script on relay host has both sockets in server mode. While UDP socket has no explicit connected state, it still needs to know host:port pair of other side of data exchange, which can be known from first received datagram. Normally first package is send from client in application traffic, but relay can't forward it to server machine before receiving at least one package from it, because it doesn't know values of host:port pair of socket on the other side of connection. This is where connection modes `bind-relay` and `connect-relay` come to play.

### Ping messages

On startup and then on regular intervals, UDP_relay will in `connect-relay` mode send, and in `bind-relay` mode exclude from relayed traffic some arbitrary message, that serves as a mean to establish connection between `connect-relay` client and `bind-relay` server UDP sockets.

Properties of these messages are set in optional config section `[common]` with following parameters:
- `ping_msg` - a string that will be used for ping message. It should be something that is expected to never come up in relayed application traffic, since it will be always silently dropped
- `ping_interval` - how often said phrase should be send, default is every 60 seconds

Other options, avaliable in `[common]` section are
- `host` - default hostname, used when not specified in [left] or [right]
- `udp_max_size` - maximum size of UDP package UDP_relay will read and send over, in bytes. Default value of 4096 should work most of the times, but it can be increased up to around 65k.

Since UDP_relay instance on relay host needs to receive ping message from server machine, it is better to be started before one on it, but even if it is not the case, connection still should be established after no more than `ping_interval` seconds when ping message gets send.

UDP protocol doesn't have connection in a sense TCP has, so the same server socket listening on specific port will receive packages from any client sending them there. Clients are identified by host:port pair from which packages come, and there is no way for UDP_relay to know if client is still waiting for packages on specific port or has already terminated.

As only one client connection is expected in any given moment, after receiving new package from different host:port pair UDP_relay assumes client has simple restarted and from that moment will direct all traffic to that new address. While it allows elements of relay chain to just continue working after restarts, it makes hijacking traffic extremely easy, so UDP_relay should be used with caution on public networks.
