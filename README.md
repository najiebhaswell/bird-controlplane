# BIRD Control Plane - VyOS-Style CLI for BIRD2

A comprehensive CLI management system for BIRD2 routing daemon, featuring VyOS-style command syntax, traffic engineering, and modular configuration generation.

## Features

- **VyOS-Style CLI**: Familiar `set/no/show/commit` command structure
- **BGP Management**: Complete BGP peer lifecycle management
- **Traffic Engineering**: LocalPref, AS-Path, Prefix-list based routing policies
- **Route Maps**: Full match/set support with prefix-lists, community-lists, AS-path lists
- **Modular Config**: Generates clean, organized BIRD configuration files
- **IPv4/IPv6 Separation**: IPv6 is opt-in (not auto-created)

## Quick Start

### 1. Installation

#### Option A: Debian Package (Recommended for Production)
```bash
sudo dpkg -i bird-controlplane_1.0.0_amd64.deb
sudo apt install -f  # Install dependencies if needed
```

**Using the CLI:**
When installed via package, the command is:
```bash
bird-cli
```

#### Option B: Manual Installation (Development)
```bash
# Start backend
./start_klishd

# Connect to CLI
./cli
```


### 3. Basic Configuration
```bash
# Enter configuration mode
configure terminal

# Create a BGP peer
set protocols bgp neighbor 192.168.1.1 remote-as 65001
set protocols bgp neighbor 192.168.1.1 description "My-Peer"

# Apply and reload BIRD
commit
```

## Project Structure

```
bird-controlplane/
├── bin/
│   ├── bird-mgmt          # Backend management script
│   └── generate           # BIRD config generator
├── config/
│   ├── router.yaml        # Router identity (ASN, router-id)
│   ├── peers.yaml         # BGP peer definitions
│   ├── policy.yaml        # Policy objects (prefix-lists, route-maps)
│   └── blackhole.yaml     # Blackhole routes
├── klish-conf/
│   └── policy.xml         # CLI command definitions
├── templates/
│   ├── protocol.j2        # BGP protocol template
│   ├── filter_import.j2   # Import filter template
│   └── filter_export.j2   # Export filter template
├── output/                 # Generated BIRD config (5 files)
├── examples/
│   └── test_scenario.sh   # Example configuration script
├── cli                     # CLI client binary
└── start_klishd            # Daemon startup script
```

## Generated Configuration Files

After running `commit`, the following files are generated:

| File | Description |
|------|-------------|
| `bird.conf` | Main config with includes |
| `functions.conf` | System helper functions |
| `static-routes.conf` | Static and blackhole routes |
| `route-maps.conf` | Policy objects + route-map functions |
| `bgp.conf` | BGP filters + protocol definitions |

## Command Reference

### BGP Neighbor Commands

```bash
# Create peer
set protocols bgp neighbor <IP> remote-as <ASN>
set protocols bgp neighbor <IP> description <TEXT>

# Shutdown/Enable
set protocols bgp neighbor <IP> shutdown
no protocols bgp neighbor <IP> shutdown

# Delete peer
no protocols bgp neighbor <IP>

# Apply route-map
set protocols bgp neighbor <IP> address-family ipv4-unicast route-map import <NAME>
set protocols bgp neighbor <IP> address-family ipv4-unicast route-map export <NAME>

# Redistribute
set protocols bgp neighbor <IP> redistribute static
set protocols bgp neighbor <IP> redistribute connected
```

### Policy Commands

#### Prefix Lists (IPv4)
```bash
set policy prefix-list <NAME> rule <NUM> action permit|deny
set policy prefix-list <NAME> rule <NUM> prefix <PREFIX>
```

#### Community Lists
```bash
set policy community-list <NAME> rule <NUM> action permit|deny
set policy community-list <NAME> rule <NUM> regex <PATTERN>
# Example: regex "55666:100"
```

#### Large Community Lists
```bash
set policy large-community-list <NAME> rule <NUM> action permit|deny
set policy large-community-list <NAME> rule <NUM> regex <PATTERN>
# Example: regex "55666:0:100"
```

#### AS-Path Lists
```bash
set policy as-path-list <NAME> rule <NUM> action permit|deny
set policy as-path-list <NAME> rule <NUM> origin <ASN>    # Match by origin AS
set policy as-path-list <NAME> rule <NUM> as <ASN>        # Match path contains AS
```

#### Route Maps
```bash
# Create rule
set policy route-map <NAME> rule <NUM> action permit|deny

# Match conditions
set policy route-map <NAME> rule <NUM> match prefix-list <PLIST>
set policy route-map <NAME> rule <NUM> match as-path list <ASPATH>
set policy route-map <NAME> rule <NUM> match community list <CLIST>
set policy route-map <NAME> rule <NUM> match large-community list <LCLIST>

# Set actions
set policy route-map <NAME> rule <NUM> set local-preference <VALUE>
set policy route-map <NAME> rule <NUM> set community <VALUE>
```

### Static Routes
```bash
set protocols static route <PREFIX> via <NEXTHOP>
set protocols static route <PREFIX> blackhole
no protocols static route <PREFIX>
```

### Show Commands
```bash
show bgp neighbors
show static routes
show policy prefix-list
show policy route-map
```

## Traffic Engineering Examples

### Prefer Google via Telkom (LocalPref)
```bash
# Create AS-path list for Google
set policy as-path-list GOOGLE rule 10 action permit
set policy as-path-list GOOGLE rule 10 origin 15169

# Create import route-map
set policy route-map IMPORT_TELKOM rule 10 action permit
set policy route-map IMPORT_TELKOM rule 10 match as-path list GOOGLE
set policy route-map IMPORT_TELKOM rule 10 set local-preference 500
set policy route-map IMPORT_TELKOM rule 100 action permit

# Apply to peer
set protocols bgp neighbor 192.168.1.1 address-family ipv4-unicast route-map import IMPORT_TELKOM
```

### Export Specific Prefixes Only
```bash
# Define prefixes
set policy prefix-list MY_PREFIXES rule 10 action permit
set policy prefix-list MY_PREFIXES rule 10 prefix 111.68.26.0/24

# Create export route-map
set policy route-map EXPORT_UPSTREAM rule 10 action permit
set policy route-map EXPORT_UPSTREAM rule 10 match prefix-list MY_PREFIXES
set policy route-map EXPORT_UPSTREAM rule 999 action deny

# Apply
set protocols bgp neighbor 192.168.1.1 address-family ipv4-unicast route-map export EXPORT_UPSTREAM
```

### Block Specific AS to Downstream
```bash
# Block Amazon routes to customer
set policy as-path-list AMAZON rule 10 action permit
set policy as-path-list AMAZON rule 10 origin 16509

set policy route-map EXPORT_CUSTOMER rule 10 action deny
set policy route-map EXPORT_CUSTOMER rule 10 match as-path list AMAZON
set policy route-map EXPORT_CUSTOMER rule 100 action permit

set protocols bgp neighbor 10.0.0.1 address-family ipv4-unicast route-map export EXPORT_CUSTOMER
```

## IPv6 Support

IPv6 is **opt-in** (not created by default). To enable IPv6 for a peer:

```bash
# This automatically enables IPv6 channel for the peer
set protocols bgp neighbor <IP> address-family ipv6-unicast route-map import <NAME>
set protocols bgp neighbor <IP> address-family ipv6-unicast route-map export <NAME>
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Klish3    │────▶│  bird-mgmt  │────▶│  YAML Config │
│  (CLI UI)   │     │  (Backend)  │     │    Files     │
└─────────────┘     └─────────────┘     └──────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌──────────────┐
                    │  generate   │────▶│  BIRD Config │
                    │  (Jinja2)   │     │    Files     │
                    └─────────────┘     └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │    BIRD2     │
                                        │   Daemon     │
                                        └──────────────┘
```

## Requirements

- Python 3.8+
- BIRD 2.x
- Klish 3.x (included in klish-src/)

### Python Dependencies
```bash
pip install -r requirements.txt
```

## Building Klish

```bash
cd klish-src
./autogen.sh
./configure
make
sudo make install
```

## License

MIT License

## Author

G-Media Network Operations
