# BGP Framework Configuration Manual

Complete reference guide for all YAML configuration parameters.

---

## Quick Start

### 1. Generate Configuration
```bash
python3 bin/generate_config.py --config-dir <config_dir> --output-dir <output_dir>
```

### 2. Apply to BIRD
```bash
docker cp output/bird.conf br2-yk:/etc/bird/bird.conf
docker exec br2-yk birdc configure
```

### 3. Verify
```bash
docker exec br2-yk birdc "show protocols"
docker exec br2-yk birdc "show route export <protocol_name> count"
```

---

## File Structure

```
├── bin/
│   └── generate_config.py      # Config generator script
├── templates/
│   ├── protocol.j2             # BGP protocol template
│   ├── filter_import.j2        # Import filter template
│   ├── filter_export.j2        # Export filter template
│   ├── filter_import_v6.j2     # IPv6 import filter
│   ├── filter_export_v6.j2     # IPv6 export filter
│   └── static_routes.j2        # Static routes + prefix-lists
├── <config-dir>/               # Your configuration
│   ├── router.yaml             # Router identity
│   ├── peers.yaml              # BGP peers
│   ├── prefixes.yaml           # Prefix definitions
│   ├── blackhole.yaml          # Blackhole routes
│   └── bogon_filter.yaml       # Bogon ASN filtering
└── <output-dir>/
    └── bird.conf               # Generated BIRD config
```

---

## Table of Contents

1. [router.yaml](#routeryaml)
2. [peers.yaml](#peersyaml)
3. [prefixes.yaml](#prefixesyaml)
4. [blackhole.yaml](#blackholeyaml)
5. [Community Reference](#community-reference)
6. [Filter Logic](#filter-logic)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)
9. [LocalPref Guide](#localpref-guide)

---

## router.yaml

Basic router configuration.

```yaml
# Router identification
name: BR2-YK                    # Router name (used in protocol names)
asn: 55666                      # AS number
router_id: 10.251.251.100       # Router ID (usually loopback IP)

# Local addresses for BGP sessions
local_addresses:
  ipv4: 10.251.251.100          # Default source for BGP
  ipv6: null                     # IPv6 source (optional)

# Global BGP settings
bgp:
  graceful_restart: true        # Enable graceful restart
  hold_time: 60                 # BGP hold timer (seconds)
  keepalive: 20                 # Keepalive interval (seconds)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | ✅ | Router hostname |
| `asn` | integer | ✅ | Local AS number |
| `router_id` | string | ✅ | BIRD router ID |
| `local_addresses.ipv4` | string | ✅ | Source IPv4 for BGP |
| `local_addresses.ipv6` | string | ❌ | Source IPv6 for BGP |
| `bgp.graceful_restart` | boolean | ❌ | Enable GR (default: true) |
| `bgp.hold_time` | integer | ❌ | Hold timer (default: 90) |
| `bgp.keepalive` | integer | ❌ | Keepalive (default: 30) |

---

## peers.yaml

BGP peer configuration organized by category.

### Structure

```yaml
peers:
  # Intercity iBGP peers (between cities)
  intercity:
    peer_name:
      type: ibgp
      role: intercity
      # ... config

  # Backbone iBGP peers (same location)
  backbone:
    peer_name:
      type: ibgp
      role: backbone
      # ... config

  # Upstream eBGP peers (transit providers)
  upstream:
    peer_name:
      type: upstream
      # ... config

  # Downstream eBGP peers (customers)
  downstream:
    peer_name:
      type: downstream
      # ... config

  # IX (Internet Exchange) peers
  ix:
    peer_name:
      type: ix
      # ... config

  # Bilateral peers (content providers, CDN)
  bilateral:
    peer_name:
      type: bilateral
      # ... config

  # Regional peers (optional)
  regional:
    peer_name:
      type: regional
      # ... config
```

### Peer Types

#### 1. iBGP Intercity Peers

```yaml
peers:
  intercity:
    ict_jkt_linknet:
      description: BR2-JKT via Linknet
      asn: 55666                    # Same AS (iBGP)
      neighbor_ip: 10.1.2.10        # Remote IP
      local_ip: 10.1.2.9            # Local IP
      interface: eth3               # Interface name
      type: ibgp                    # Peer type
      role: intercity               # Role for filtering
      region: jakarta               # Region tag
      provider: linknet             # Provider name
      graceful_restart: true        # Enable GR
      hold_time: 60                 # Hold timer
      next_hop_self: true           # Set next-hop to self
      route_reflector_client: false # RR client
      
      # Traffic engineering
      localpref_import: 200         # LocalPref for routes FROM this peer
      localpref_export: 100         # LocalPref for routes TO this peer
      
      # Priority prefixes - override LocalPref for specific prefixes
      priority_prefixes_import:
        - prefix: 1.1.1.0/24
          localpref: 300            # Higher = more preferred
        - prefix: 8.8.8.0/24
          localpref: 250
      
      # Community-based filtering (optional)
      import_accept_communities:
        - "(55666, 4, 1)"            # Accept downstream routes
      import_reject_communities:
        - "(55666, 3, 9999)"         # Reject routes from AS9999
      
      # Block specific ASNs or prefixes (optional)
      import_discard_asns:
        - 12345                     # Block routes from this AS
      import_discard_prefixes:
        - 192.0.2.0/24              # Block documentation prefix
```

#### 2. iBGP Backbone Peers

```yaml
peers:
  backbone:
    br1_yk:
      description: BR1-YK
      asn: 55666
      neighbor_ip: 10.1.3.5
      local_ip: 10.1.3.6
      interface: eth4
      type: ibgp
      role: backbone
      region: yogyakarta
      graceful_restart: true
      hold_time: 60
      next_hop_self: true
      route_reflector_client: true  # This peer is our RR client
      
    distribution_router:
      description: Distribution Router
      asn: 55666
      neighbor_ip: 10.4.1.6
      local_ip: 10.4.1.5
      interface: eth11
      type: ibgp
      role: backbone
      region: yogyakarta
      is_dr: true                   # Distribution router flag
      import_community: "55666:1111" # Filter by community
```

#### 3. Upstream eBGP Peers

```yaml
peers:
  upstream:
    lintas_as4800:
      description: LINTAS AS4800
      asn: 4800                     # Remote AS
      neighbor_ip: 10.2.48.1
      local_ip: 10.2.48.2
      interface: eth6
      type: upstream                # Upstream type
      provider: lintas              # Provider name
      
      # Upstream-specific settings
      accept_default_route: true    # Accept 0.0.0.0/0
      accept_full_table: true       # Accept full BGP table
      allow_local_as: 1             # Allow AS loop (for multi-homing)
      localpref_import: 100         # Default LocalPref
      
      # Specify which prefix-lists to advertise
      export_prefix_lists:
        - gmedia_yk                 # → GMEDIA_YK_V4, GMEDIA_YK_V6
        - gmedia_srk                # → GMEDIA_SRK_V4, GMEDIA_SRK_V6
        - gmedia_jkt                # → GMEDIA_JKT_V4
        - downstream_msa_dimensi    # → DOWNSTREAM_MSA_DIMENSI_V4
      
      # Per-prefix LocalPref override (traffic engineering)
      import_localpref_by_prefix:
        - prefix: 8.8.8.0/24
          localpref: 300            # Prefer this upstream for Google DNS
        - prefix: 1.1.1.0/24
          localpref: 250            # Prefer for Cloudflare
      
      # Per-ASN LocalPref override (prefer this upstream for routes from specific AS)
      import_localpref_by_asn:
        - asn: 13335                # Cloudflare
          localpref: 250
        - asn: 15169                # Google
          localpref: 200
      
      # Community-based filtering (optional)
      import_accept_communities:
        - "(55666, 4, 1)"            # Accept only downstream routes on import
      import_reject_communities:
        - "(55666, 3, 9999)"         # Reject routes from AS9999 on import
      export_accept_communities:
        - "(55666, 4, 1)"            # Only export downstream routes
      
      # Block specific ASNs or prefixes on import (optional)
      import_discard_asns:
        - 12345                     # Block routes from this AS
      import_discard_prefixes:
        - 192.0.2.0/24              # Block documentation prefix
      
      # Per-prefix prepending (optional)
      own_prefix_prepend:
        - prefix: 103.247.120.0/24
          prepend: 2                # Prepend 2x for this prefix
```

#### 4. Downstream eBGP Peers

```yaml
peers:
  downstream:
    msa_dimensi:
      description: MSA Dimensi Cloud
      asn: 38760                    # Customer AS
      neighbor_ip: 10.3.38.2
      local_ip: 10.3.38.1
      interface: eth8
      type: downstream
      max_prefixes: 50              # Max prefix limit
      localpref_import: 500         # LocalPref for customer routes
      graceful_restart: true
      hold_time: 60
      
      # Customer allowed prefixes (manual, required for filtering)
      allowed_prefixes:
        - 103.217.208.0/24
        - 103.217.209.0/24
        - 103.217.208.0/22
      
      # ========== AUTO PREFIX GENERATION (bgpq4) ==========
      # Automatically generate prefix list from IRR database
      auto_prefix: true             # Enable auto prefix generation
      as_set: AS-MSADIMENSI         # AS-SET object (optional, default: AS{asn})
      downstream_asns:              # Customer's downstream ASNs (transit customers)
        - 65300                     # Include prefixes from these ASNs too
        - 65301
      # Run: ./bin/bird-mgmt update-prefixes msa_dimensi
      # This queries IRR via bgpq4 and saves prefixes to prefixes.yaml
      
      # Selective export to upstreams
      export_to_upstreams:          # Only export to these upstreams
        - lintas_as4800
        - telkom_as7713
      
      # Per-prefix export rules
      prefix_export_rules:
        - prefix: 103.217.208.0/24
          upstreams:
            lintas_as4800: 0        # No prepend
            telkom_as7713: 2        # Prepend 2x
```

> **Auto Prefix Generation:**
> - Jalankan `./bin/bird-mgmt update-prefixes` untuk generate prefix list dari IRR
> - Prefix otomatis disimpan ke `prefixes.yaml` sebagai group `{customer_name}_prefixes`
> - Filter import akan menggunakan prefix ini jika ada di `import_allowed_prefix_lists`
> - Memerlukan `bgpq4` terinstall (`apt install bgpq4`)

#### 5. IX (Internet Exchange) Peers

```yaml
peers:
  ix:
    iix_route_server:
      description: IIX Route Server
      asn: 7713                       # IX RS ASN
      
      # IPv4 peering
      neighbor_ip: 103.28.72.1        # IX RS IPv4
      local_ip: 103.28.72.10          # Your IX port IPv4
      
      # IPv6 peering (OPTIONAL - if different from IPv4 neighbor)
      # When specified, generates SEPARATE protocol block
      neighbor_ip_v6: "2001:7f9:100::1"   # IX RS IPv6
      local_ip_v6: "2001:7f9:100::10"     # Your IX port IPv6
      
      interface: eth10                # Required for IX (shared LAN)
      type: ix
      ix_name: iix
      graceful_restart: true
      hold_time: 60
      localpref_import: 150           # Higher than upstream (100)
      
      # Per-prefix LocalPref override (prefer IX for specific prefixes)
      import_localpref_by_prefix:
        - prefix: 8.8.8.0/24
          localpref: 300              # Prefer IX for Google DNS
      
      # Per-ASN LocalPref override
      import_localpref_by_asn:
        - asn: 13335                  # Cloudflare
          localpref: 280              # Prefer IX for Cloudflare routes
      
      export_prefix_lists:
        - gmedia_yk
        - gmedia_srk
        - downstream_msa_dimensi
```

**IX Protocol Generation:**

| Configuration | Generated Protocols |
|--------------|---------------------|
| `neighbor_ip` only | 1 protocol with ipv4{} + ipv6{} channels |
| `neighbor_ip` + `neighbor_ip_v6` (different) | 2 separate protocols: `*_v4` and `*_v6` |

**IX vs Upstream differences:**
- **LocalPref**: IX: 200 (higher than upstream 100) for peering preference
- **Export**: Only own + downstream (no transit routes from upstream)
- **Community**: Tagged with `(ASN, 5, PEER_ASN)` for IX routes
- **Interface**: Required for link-local or shared LAN subnet

#### 6. Bilateral Peers (Content Providers)

```yaml
peers:
  bilateral:
    cloudflare_cdn:
      description: Cloudflare CDN
      asn: 13335
      neighbor_ip: 192.168.50.1
      local_ip: 192.168.50.2
      type: bilateral
      localpref_import: 350         # Higher than IX (200)
      max_prefixes: 100
      graceful_restart: true
      
      export_prefix_lists:
        - gmedia_yk
        - gmedia_srk
```

**Bilateral vs IX differences:**
- **LocalPref**: Bilateral: 350 (higher than IX 200) for direct peering preference
- **Export**: Only own + downstream (same as IX, no transit)
- **Community**: Tagged with `(ASN, 7, PEER_ASN)` for bilateral routes

### LocalPref Hierarchy

Standard BGP preference rules (higher = more preferred):

| Peer Type | Default LocalPref | Description |
|-----------|-------------------|-------------|
| Downstream | 500 | Customer routes (highest priority) |
| Bilateral | 350 | Direct peering with content providers |
| IXP | 200 | Internet Exchange peers |
| iBGP | 150 | Internal backbone routes |
| Upstream | 100 | Transit (lowest priority) |

### Complete Parameter Reference

#### Basic Parameters

| Parameter | Type | Applies To | Description |
|-----------|------|------------|-------------|
| `description` | string | all | Human-readable peer name |
| `asn` | integer | all | Peer AS number (same AS for iBGP) |
| `neighbor_ip` | string | all | Remote BGP IPv4 address |
| `local_ip` | string | all | Local BGP IPv4 address |
| `neighbor_ip_v6` | string | ix, upstream | Remote IPv6 (generates separate protocol) |
| `local_ip_v6` | string | ix, upstream | Local IPv6 address |
| `interface` | string | all | Interface name (required for IX) |
| `type` | string | all | `ibgp`, `upstream`, `downstream`, `ix`, `regional` |

#### iBGP Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `role` | string | `intercity` or `backbone` - affects community tagging |
| `next_hop_self` | boolean | Set next-hop to self on export |
| `route_reflector_client` | boolean | Peer is route reflector client |
| `is_dr` | boolean | Peer is Distribution Router |
| `import_community` | string | Filter import by community (DR) |
| `priority_prefixes_import` | list | Per-prefix LocalPref override |
| `import_allowed_prefix_lists` | list | **NEW** Accept only routes matching these prefix groups |
| `export_allowed_prefix_lists` | list | **NEW** Export only routes matching these prefix groups |
| `export_only_prefix_lists` | list | **NEW** Strict export mode - ONLY these prefixes (no fallback) |

#### Upstream/IX Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `accept_default_route` | boolean | Accept 0.0.0.0/0 from peer |
| `accept_full_table` | boolean | Accept full BGP table |
| `allow_local_as` | integer | Allow own AS in path N times |
| `ix_name` | string | IX exchange name for tagging |
| `own_prefix_prepend` | list | Per-prefix AS prepending |
| `import_discard_asns` | list | Reject routes from these ASNs on **import** |
| `import_discard_prefixes` | list | Reject these prefixes on **import** |
| `export_discard_asns` | list | Reject routes from these ASNs on **export** |
| `export_discard_prefixes` | list | Reject these prefixes on **export** |
| `import_localpref_by_prefix` | list | Set LocalPref by prefix on **import** |
| `import_localpref_by_asn` | list | Set LocalPref by origin ASN on **import** |
| `export_localpref_by_prefix` | list | Set LocalPref by prefix on **export** (iBGP) |
| `export_localpref_by_asn` | list | Set LocalPref by origin ASN on **export** (iBGP) |

#### Downstream Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_prefixes` | integer | Maximum prefix limit (action: disable) |
| `allowed_prefixes` | list | IPv4 prefixes to accept from customer |
| `allowed_prefixes_v6` | list | IPv6 prefixes to accept from customer |
| `export_to_upstreams` | list | Only export to these upstream peers |
| `prefix_export_rules` | list | Per-prefix/upstream export rules |
| `content_provider` | boolean | **NEW** Mark as content provider (CDN, cache) |
| `import_community_tag` | string | **NEW** Custom community tag for content provider routes |
| `import_discard_prefixes` | list | **NEW** Reject these prefixes from downstream |

#### Universal Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `graceful_restart` | boolean | Enable graceful restart |
| `hold_time` | integer | BGP hold timer (seconds) |
| `localpref_import` | integer | LocalPref for imported routes |
| `localpref_export` | integer | LocalPref for exported routes |
| `export_prefix_lists` | list | Named prefix-lists to advertise |
| `import_accept_communities` | list | Accept routes with these communities on **import** |
| `import_reject_communities` | list | Reject routes with these communities on **import** |
| `export_accept_communities` | list | Accept routes with these communities on **export** |
| `export_reject_communities` | list | Reject routes with these communities on **export** |

### export_prefix_lists Parameter

The `export_prefix_lists` parameter specifies which named prefix-lists to advertise. **Supported by all peer types.**

```yaml
# Example for upstream
peers:
  upstream:
    transit_isp:
      export_prefix_lists:
        - gmedia_yk            # → if (net ~ GMEDIA_YK_V4) then accept;
        - gmedia_srk           
        - downstream_customer

# Example for downstream (limit what customer sees)
  downstream:
    customer_abc:
      export_prefix_lists:
        - gmedia_yk            # Only export these to customer
        - full_table_group     # Not other customers, not upstream routes
```
- Explicit control over what prefixes are advertised
- Same prefix-list names work for both IPv4 and IPv6
- Prefix group must exist in `prefixes.yaml`
- IPv6 rules only generated if `ipv6:` is defined in the prefix_group

### import_accept/reject_communities (Import Filter)

Filter routes on import by large community:

```yaml
peers:
  upstream:
    transit_isp:
      # Accept routes with these communities on IMPORT
      import_accept_communities:
        - "(55666, 4, 1)"       # Accept downstream routes only
        - "(55666, 1, 1000)"    # Accept own prefixes
      
      # Reject routes with these communities on IMPORT  
      import_reject_communities:
        - "(55666, 3, 4800)"    # Reject routes learned from AS4800
```

### export_accept/reject_communities (Export Filter)

Filter routes on export by large community:

```yaml
peers:
  upstream:
    transit_isp:
      # Accept routes with these communities on EXPORT
      export_accept_communities:
        - "(55666, 4, 1)"       # Only export downstream routes
      
      # Reject routes with these communities on EXPORT
      export_reject_communities:
        - "(55666, 3, 7713)"    # Don't export routes from Telkom to this upstream
```

### import_discard_asns / import_discard_prefixes (Import Filter)

Block specific ASNs or prefixes on import:

```yaml
peers:
  upstream:
    transit_isp:
      # Reject routes from these ASNs on import
      import_discard_asns:
        - 12345                 # Block competitor
        - 67890                 # Block problematic AS
      
      # Reject these prefixes on import
      import_discard_prefixes:
        - 192.0.2.0/24          # Block documentation prefix
        - 198.51.100.0/24       # Block test prefix
```

### export_discard_asns / export_discard_prefixes (Export Filter)

Block specific ASNs or prefixes on export:

```yaml
peers:
  upstream:
    transit_isp:
      # Don't export routes from these ASNs
      export_discard_asns:
        - 7713                  # Don't export Telkom routes to this peer
      
      # Don't export these prefixes
      export_discard_prefixes:
        - 103.217.208.0/22      # Don't export this downstream to this peer
```

### priority_prefixes_import

Per-prefix LocalPref override on iBGP import:

```yaml
peers:
  intercity:
    ict_jkt_linknet:
      localpref_import: 100     # Default LocalPref
      
      # Override for specific prefixes
      priority_prefixes_import:
        - prefix: 8.8.8.0/24
          localpref: 300        # Highest priority for Google DNS
        - prefix: 1.1.1.0/24
          localpref: 250        # High priority for Cloudflare
```

### import_localpref_by_prefix (Upstream/IX)

Set LocalPref based on specific prefixes on import:

```yaml
peers:
  upstream:
    transit_isp:
      localpref_import: 100     # Default
      
      # Per-prefix LocalPref override
      import_localpref_by_prefix:
        - prefix: 8.8.8.0/24
          localpref: 300        # Prefer this upstream for Google DNS
        - prefix: 1.1.1.0/24
          localpref: 250        # Prefer for Cloudflare
```

### import_localpref_by_asn

Set LocalPref based on origin AS:

```yaml
peers:
  upstream:
    transit_isp:
      localpref_import: 100     # Default
      
      # Per-ASN LocalPref override (based on origin AS)
      import_localpref_by_asn:
        - asn: 13335            # Cloudflare
          localpref: 250        # Prefer this upstream for Cloudflare routes
        - asn: 15169            # Google
          localpref: 200        # Medium preference for Google
```

### own_prefix_prepend

Per-prefix AS prepending on export:

```yaml
peers:
  upstream:
    transit_isp:
      # Prepend for traffic engineering
      own_prefix_prepend:
        - prefix: 103.247.120.0/24
          prepend: 2            # Prepend 2x (make path longer)
        - prefix: 49.128.176.0/24
          prepend: 1            # Prepend 1x
```

### import_allowed_prefix_lists (iBGP) - NEW

Accept only routes matching specific prefix groups from iBGP peers. Useful for controlling which routes are received from specific iBGP peers.

```yaml
peers:
  backbone:
    br1ncdc:
      description: BR1-NCDC
      type: ibgp
      role: backbone
      # Only accept routes matching these prefix groups
      import_allowed_prefix_lists:
        - gmedia_yk           # Accept GMedia YK prefixes
        - gmedia_jkt          # Accept GMedia JKT prefixes
        - downstream_ggc      # Accept GGC (content provider) prefixes
```

**Generated Filter:**
```bird
filter ibgp_br1ncdc_import {
    # Only accept routes matching these prefix-lists (IPv4)
    if (net ~ GMEDIA_YK_V4) then { bgp_local_pref = 100; accept; }
    if (net ~ GMEDIA_JKT_V4) then { bgp_local_pref = 100; accept; }
    if (net ~ DOWNSTREAM_GGC_V4) then { bgp_local_pref = 100; accept; }
    # Reject everything else
    reject;
}
```

### export_allowed_prefix_lists (iBGP) - NEW

Export only routes matching specific prefix groups to iBGP peers. Prevents exporting unwanted routes (like default routes) to specific iBGP peers.

```yaml
peers:
  backbone:
    br1ncdc:
      description: BR1-NCDC
      type: ibgp
      role: backbone
      # Only export these prefix groups to this peer (both IPv4 and IPv6)
      export_allowed_prefix_lists:
        - ggc_yk              # Only export GGC prefixes
```

**Generated Filter (IPv4 and IPv6):**
```bird
filter ibgp_br1ncdc_export {
    # Only export routes matching these prefix-lists (IPv4)
    if (net ~ GGC_YK_V4) then accept;
    # Reject everything else not in allowed prefix-lists
    reject;
}

filter ibgp_br1ncdc_export_v6 {
    # Only export routes matching these prefix-lists (IPv6)
    if (net ~ GGC_YK_V6) then accept;
    # Reject everything else not in allowed prefix-lists
    reject;
}
```

### export_only_prefix_lists (iBGP) - NEW

Strict export mode - ONLY export these prefixes with device routes. No other routes are exported.

```yaml
peers:
  backbone:
    br1ncdc:
      # Strict mode: ONLY export GGC prefixes + device routes
      export_only_prefix_lists:
        - ggc_yk
```

**Generated Filter:**
```bird
filter ibgp_br1ncdc_export {
    # Only export routes matching these prefix-lists (strict mode)
    if (net ~ GGC_YK_V4) then accept;
    # Export device routes with community tag
    if (source = RTS_DEVICE) then {
        bgp_community.add((55666, 1111));
        accept;
    }
    # Reject everything else
    reject;
}
```

### content_provider (Downstream) - NEW

Mark a downstream peer as a content provider (CDN, cache) and apply custom community tagging for traffic engineering.

```yaml
peers:
  downstream:
    ggc_yk:
      description: Google Global Cache YK
      asn: 36040
      neighbor_ip: 43.245.187.65
      local_ip: 43.245.187.64
      type: downstream
      max_prefixes: 50
      localpref_import: 500
      
      # Mark as content provider
      content_provider: true
      # Custom community tag for content provider routes
      import_community_tag: "(55666, 6, 36040)"
      
      # Optionally reject specific prefixes (like default route)
      import_discard_prefixes:
        - 0.0.0.0/0             # Reject default route from content provider
```

**Generated Filter:**
```bird
filter ebgp_downstream_ggc_yk_import {
    # ... martian filtering ...
    
    # Discard specific prefixes on import
    prefix set import_discard_prefixes_ggc_yk;
    import_discard_prefixes_ggc_yk = [ 0.0.0.0/0 ];
    if net ~ import_discard_prefixes_ggc_yk then reject;
    
    # Tag all downstream routes with same community
    bgp_large_community.add((55666, 4, 1));
    
    # Content Provider tagging - custom community
    bgp_large_community.add((55666, 6, 36040));
    
    # Downstream must originate from their own AS
    if bgp_path.last != 36040 then reject;
    # ...
}
```

### no_transit_nap (Router-wide) - NEW

Define ASNs that should not appear in transit paths. Routes containing these ASNs in the AS path are rejected. Commonly used to prevent transit of IX/NAP routes.

**Configuration in `bogon_filter.yaml`:**
```yaml
# ASNs that should not appear in transit paths
no_transit_nap:
  - 56258     # IXP ASN
  - 58463     # IXP ASN  
  - 58552     # NAP ASN
  - 17451     # IXP ASN
  - 7597      # IIX
  - 7717      # OpenIXP
  - 4761      # NAP
  - 17922     # IXP
  - 9448      # IXP
  - 4800      # Lintas Arta (NAP)
  - 7713      # Telkom (NAP)
```

**Generated Filter (applied to all iBGP import filters):**
```bird
filter ibgp_br1ncdc_import {
    # No-transit NAP filtering
    int set no_transit_nap;
    no_transit_nap = [56258,58463,58552,17451,7597,7717,4761,17922,9448,4800,7713];
    if bgp_path ~ no_transit_nap then reject;
    # ...
}
```

---

## prefixes.yaml

Prefix definitions and router-specific settings.

### Structure

```yaml
# Named prefix groups (like Cisco prefix-lists)
prefix_groups:
  group_name:
    asn: 12345          # Optional: ASN for downstream groups
    ipv4:
      - prefix1
      - prefix2
    ipv6:
      - prefix1

# Router-specific settings
router_prefixes:
  originate:            # Groups to generate static routes for
    - group1
  accept_ibgp:          # Groups to accept from iBGP peers
    - group2
    - group3

# Bogon/martian prefixes
bogon_prefixes:
  ipv4:
    - 10.0.0.0/8
    - ...
```

### Generated Global Prefix-Lists

The framework generates global prefix-lists at the top of the BIRD config:

```bird
# From router_prefixes.originate groups
define OWN_PREFIXES_V4 = [
    49.128.176.0/24,
    49.128.177.0/24,
    ...
];

# From router_prefixes.accept_ibgp groups
define REMOTE_PREFIXES_V4 = [
    49.128.179.0/24,
    49.128.181.0/24,
    ...
];
```

These prefix-lists are used in export filters:
- `OWN_PREFIXES_V4` - Prefixes this router originates
- `REMOTE_PREFIXES_V4` - Prefixes from other AS routers (via iBGP)

### Example

```yaml
prefix_groups:
  # Own prefixes (this router originates)
  gmedia_yk:
    ipv4:
      - 49.128.176.0/24
      - 49.128.177.0/24
      - 111.68.24.0/24
      - 203.30.236.0/23
      
  # Prefixes from other regions
  gmedia_srk:
    ipv4:
      - 49.128.179.0/24
      - 49.128.181.0/24
      
  gmedia_jkt:
    ipv4:
      - 112.78.34.0/24
      - 116.254.114.0/24

  # Downstream customer prefixes
  downstream_msa_dimensi:
    asn: 38760
    ipv4:
      - 103.217.208.0/24
      - 103.217.209.0/24
      - 103.217.208.0/22

  downstream_jcamp:
    asn: 46050
    ipv4:
      - 203.161.184.0/23
      - 103.30.146.0/23

# Router-specific configuration
router_prefixes:
  # Generate static blackhole routes for these groups
  originate:
    - gmedia_yk
    
  # Accept from iBGP and export to upstreams
  accept_ibgp:
    - gmedia_srk
    - gmedia_jkt

# Community for own prefixes (Large Community format)
own_community: "(55666, 1, 1000)"
downstream_community: "(55666, 4, 1)"

bogon_prefixes:
  ipv4:
    - 0.0.0.0/8
    - 10.0.0.0/8
    - 127.0.0.0/8
    - 169.254.0.0/16
    - 172.16.0.0/12
    - 192.0.2.0/24
    - 192.168.0.0/16
```

---

## blackhole.yaml

Static blackhole routes for DDoS protection.

```yaml
blackhole_routes_v4:
  - route: 103.247.120.0/22
    description: DDoS target protection
    
  - route: 111.68.24.0/24
    description: Prefix origination

blackhole_routes_v6: []
```

---

## Community Reference

### Route Source Communities (Informational)

Routes are automatically tagged on import based on source type:

| Community | Source | Description |
|-----------|--------|-------------|
| `(ASN, 1, 0)` | iBGP (generic) | Generic iBGP source |
| `(ASN, 1, 1)` | iBGP Intercity | Intercity iBGP peer (`role: intercity`) |
| `(ASN, 1, 2)` | iBGP Backbone | Backbone iBGP peer (`role: backbone`) |
| `(ASN, 1, 3)` | iBGP DR | Distribution Router (`is_dr: true`) |
| `(ASN, 1, 1000)` | Static | Own network prefix (originated by AS) |
| `(ASN, 3, PEER_ASN)` | Upstream | Learned from upstream peer |
| `(ASN, 3, 0)` | Upstream | Default route from upstream |
| `(ASN, 3, 1)` | Upstream | Full table marker |
| `(ASN, 4, 1)` | Downstream | Customer route (all downstreams share this tag) |
| `(ASN, 5, PEER_ASN)` | IX | Learned from IX peer PEER_ASN |
| `(ASN, 7, PEER_ASN)` | Bilateral | Learned from bilateral peer (content provider) |

### Action Communities - No Export

| Community | Action |
|-----------|--------|
| `(ASN, 100, PEER_ASN)` | No-export to specific PEER_ASN |
| `(ASN, 110, 0)` | No-export to ALL upstreams |
| `(ASN, 120, 0)` | No-export to ALL IX peers |
| `(ASN, 130, 0)` | No-export to ALL bilateral peers |

### Action Communities - Prepend

| Community | Action |
|-----------|--------|
| `(ASN, 101, PEER_ASN)` | Prepend 1x to specific PEER_ASN |
| `(ASN, 102, PEER_ASN)` | Prepend 2x to specific PEER_ASN |
| `(ASN, 103, PEER_ASN)` | Prepend 3x to specific PEER_ASN |
| `(ASN, 111, 0)` | Prepend 1x to ALL upstreams |
| `(ASN, 112, 0)` | Prepend 2x to ALL upstreams |
| `(ASN, 113, 0)` | Prepend 3x to ALL upstreams |
| `(ASN, 121, 0)` | Prepend 1x to ALL IX peers |
| `(ASN, 122, 0)` | Prepend 2x to ALL IX peers |
| `(ASN, 123, 0)` | Prepend 3x to ALL IX peers |

### Usage Examples

```yaml
# In prefixes.yaml - tag prefixes with action communities
prefix_groups:
  gmedia_yk:
    ipv4:
      - 49.128.176.0/24
    # These routes will have communities applied
    communities:
      - "(55666, 102, 4800)"    # Prepend 2x to AS4800 (Lintas)
      - "(55666, 120, 0)"       # No-export to all IX
```

Or via static routes configuration in BIRD:

```bird
protocol static static_special {
    route 103.247.120.0/24 blackhole {
        bgp_large_community.add((55666, 1, 1000));    # Mark as own prefix
        bgp_large_community.add((55666, 101, 7713)); # Prepend 1x to Telkom
        bgp_large_community.add((55666, 120, 0));    # No-export to all IX
    };
}
```

> **Note**: All communities use BGP Large Community format (ASN, X, Y).

---

## Filter Logic

### Import Filter Flow

```
Route received
    │
    ▼
[Martian/Bogon Check] → Reject if matches
    │
    ▼
[Bogon ASN Check] → Reject if AS path contains bogon ASN
    │
    ▼
[Type-specific Logic]
    │
    ├─ iBGP: Accept all, add (55666,1,0) community
    │
    ├─ Upstream: Tag with (55666,3,ASN), accept
    │
    └─ Downstream: Check allowed_prefixes, tag (55666,4,1)
        │
        └─ Reject if prefix not in allowed list
```

### Export Filter Flow

```
Route to export
    │
    ▼
[Type-specific Logic]
    │
    ├─ iBGP:
    │   ├─ Accept static routes (own prefixes), tag (ASN,1,1000)
    │   ├─ Accept downstream routes (ASN,4,1)
    │   ├─ Accept own network routes (ASN,1,1000)
    │   └─ Reject others
    │
    └─ Upstream:
        ├─ Accept own static routes
        ├─ Accept own iBGP routes (empty AS path)
        ├─ Accept remote own prefixes (accept_ibgp)
        ├─ Accept downstream routes (55666,4,1)
        └─ Reject others
```

---

## Usage Examples

### Adding a New Upstream

```yaml
# In peers.yaml
peers:
  upstream:
    new_upstream:
      description: New Provider AS12345
      asn: 12345
      neighbor_ip: 203.0.113.1
      local_ip: 203.0.113.2
      interface: eth7
      type: upstream
      provider: newprovider
      accept_default_route: true
      accept_full_table: true
      # Specify which prefix-lists to advertise
      export_prefix_lists:
        - gmedia_yk              # Your own prefixes
        - gmedia_srk             # Remote AS prefixes
        - downstream_customer_1  # Customer prefixes
```

### Adding a New Downstream

```yaml
# In peers.yaml
peers:
  downstream:
    new_customer:
      description: New Customer AS99999
      asn: 99999
      neighbor_ip: 10.99.99.2
      local_ip: 10.99.99.1
      interface: eth15
      type: downstream
      max_prefixes: 100
      localpref_import: 500
      allowed_prefixes:
        - 198.51.100.0/24
        - 198.51.101.0/24
```

### Adding New Own Prefixes

```yaml
# In prefixes.yaml
prefix_groups:
  gmedia_yk:
    ipv4:
      - 49.128.176.0/24
      - 49.128.177.0/24
      - NEW.PREFIX.0.0/24   # Add new prefix here

router_prefixes:
  originate:
    - gmedia_yk  # Will generate static route for all prefixes
```

### Adding an IX Peer

```yaml
# In peers.yaml
peers:
  ix:
    openixp:
      description: OpenIXP Route Server
      asn: 56202
      # IPv4 RS
      neighbor_ip: 218.100.27.253
      local_ip: 218.100.27.100
      # IPv6 RS (generates separate protocol)
      neighbor_ip_v6: "2001:7fa:11::253"
      local_ip_v6: "2001:7fa:11::100"
      interface: eth12
      type: ix
      ix_name: openixp
      localpref_import: 150         # Prefer IX over upstream (100)
      export_prefix_lists:
        - gmedia_yk
        - gmedia_srk
        - downstream_msa_dimensi
```

### Adding IPv6 to Prefix Group

```yaml
# In prefixes.yaml
prefix_groups:
  gmedia_yk:
    ipv4:
      - 49.128.176.0/24
      - 49.128.177.0/24
    ipv6:
      - 2401:1700:55::/48
      - 2401:1700:56::/48
```

> When `ipv6:` is defined, the framework generates:
> - `define GMEDIA_YK_V6 = [ 2401:1700:55::/48, ... ];`
> - IPv6 export filter uses this prefix-list

---

## Troubleshooting

### Route not exported to upstream
1. Check if prefix is in `own_prefixes` or has `(ASN,1,1000)` large community
2. Check if downstream has `(ASN,4,1)` large community
3. Verify `allowed_prefixes` for downstream customers
4. Check `export_prefix_lists` includes the correct prefix group

### Route not received from downstream
1. Check `allowed_prefixes` includes the prefix
2. Verify prefix is within `max_prefixes` limit
3. Check BGP session is Established

### Traffic not using preferred path
1. Check `localpref_import` values
2. Verify `priority_prefixes_import` for specific overrides
3. Check AS path prepending settings

### IX session not working
1. Verify `interface` is correctly specified (required for shared LAN)
2. Check IPv6 neighbor uses correct address format
3. For link-local IPv6, ensure interface is configured

---

## LocalPref Guide

### Default Values by Peer Type

| Peer Type | Default LocalPref | Purpose |
|-----------|-------------------|---------|
| Upstream | 100 | Transit traffic (lowest priority) |
| IX | 150 | Peering traffic (preferred over upstream) |
| Downstream | 500 | Customer traffic (highest priority) |
| iBGP | 100 | Internal routes (preserve original) |

### Traffic Engineering Examples

```yaml
# Prefer Linknet for Jakarta traffic
peers:
  intercity:
    ict_jkt_linknet:
      localpref_import: 200     # Higher = preferred
      
    ict_jkt_telkom:
      localpref_import: 100     # Lower = backup

# Priority for specific prefixes
    ict_jkt_linknet:
      priority_prefixes_import:
        - prefix: 1.1.1.0/24
          localpref: 300        # Highest priority for this prefix
```

### Best Practices

1. **Downstream > IX > Upstream**: Customer routes should always have highest LocalPref
2. **Use priority_prefixes**: For specific traffic engineering without changing global preference
3. **Document your scheme**: Maintain consistent LocalPref values across all routers
4. **Monitor with communities**: Use community tags to track route source

---

## Generated Output Reference

### Named Prefix-Lists

```bird
# Per-group prefix-lists (from prefix_groups)
define GMEDIA_YK_V4 = [ 49.128.176.0/24, 49.128.177.0/24, ... ];
define GMEDIA_YK_V6 = [ 2401:1700:55::/48, 2401:1700:56::/48 ];
define DOWNSTREAM_MSA_DIMENSI_V4 = [ 103.217.208.0/24, ... ];

# Aggregate prefix-lists (from router_prefixes)
define OWN_PREFIXES_V4 = [ ... ];      # All originate groups
define REMOTE_PREFIXES_V4 = [ ... ];   # All accept_ibgp groups
```

### Filter Names

| Peer Type | Import Filter | Export Filter |
|-----------|--------------|---------------|
| iBGP | `ibgp_<name>_import` | `ibgp_<name>_export` |
| Upstream | `ebgp_upstream_<name>_import` | `ebgp_upstream_<name>_export` |
| Downstream | `ebgp_downstream_<name>_import` | `ebgp_downstream_<name>_export` |
| IX | `ebgp_ix_<name>_import` | `ebgp_ix_<name>_export` |

### Protocol Names

| Peer Type | IPv4 Protocol | IPv6 Protocol |
|-----------|---------------|---------------|
| iBGP | `ibgp_<name>` | (same, with ipv6 channel) |
| Upstream | `ebgp_upstream_<name>` | (same, with ipv6 channel) |
| IX (same neighbor) | `ebgp_ix_<name>` | (same, with ipv6 channel) |
| IX (different v6) | `ebgp_ix_<name>_v4` | `ebgp_ix_<name>_v6` |
