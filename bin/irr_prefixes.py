#!/usr/bin/env python3
"""
BGP Prefix List Generator using bgpq4
Fetches allowed prefixes from IRR databases for downstream customers
"""

import subprocess
import sys
import yaml
import json
import argparse
from pathlib import Path


def query_bgpq4(as_set_or_asn, ipv4=True, max_length=None):
    """
    Query bgpq4 for prefixes from IRR database
    
    Args:
        as_set_or_asn: AS number (e.g., "AS38760") or AS-SET (e.g., "AS-CUSTOMER")
        ipv4: True for IPv4, False for IPv6
        max_length: Maximum prefix length to accept
    
    Returns:
        List of prefixes
    """
    cmd = ["bgpq4", "-j"]  # JSON output
    
    if ipv4:
        cmd.append("-4")
    else:
        cmd.append("-6")
    
    if max_length:
        cmd.extend(["-m", str(max_length)])
    
    # Add the AS-SET or ASN
    cmd.append(as_set_or_asn)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Warning: bgpq4 returned error for {as_set_or_asn}: {result.stderr}")
            return []
        
        # Parse JSON output
        data = json.loads(result.stdout)
        
        # bgpq4 returns format: {"NN": [{"prefix": "x.x.x.x/y", "exact": true}, ...]}
        prefixes = []
        for key in data:
            if isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict) and "prefix" in item:
                        prefixes.append(item["prefix"])
                    elif isinstance(item, str):
                        prefixes.append(item)
        
        return prefixes
    
    except subprocess.TimeoutExpired:
        print(f"Error: bgpq4 timeout for {as_set_or_asn}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse bgpq4 output: {e}")
        return []
    except FileNotFoundError:
        print("Error: bgpq4 not found. Install with: apt install bgpq4")
        return []


def update_downstream_prefixes(peers_file, dry_run=False):
    """
    Update allowed_prefixes for all downstream peers using bgpq4
    """
    with open(peers_file, 'r') as f:
        peers_data = yaml.safe_load(f)
    
    downstream = peers_data.get("peers", {}).get("downstream", {})
    
    if not downstream:
        print("No downstream peers found")
        return
    
    updated = False
    
    for peer_name, peer_config in downstream.items():
        asn = peer_config.get("asn")
        as_set = peer_config.get("as_set")  # Optional: use AS-SET instead of ASN
        
        # Determine what to query
        query = as_set if as_set else f"AS{asn}"
        
        print(f"\n{'='*60}")
        print(f"Processing: {peer_name} ({query})")
        print(f"{'='*60}")
        
        # Query bgpq4
        prefixes = query_bgpq4(query, ipv4=True, max_length=24)
        
        if prefixes:
            print(f"Found {len(prefixes)} prefixes from IRR:")
            for prefix in prefixes[:10]:  # Show first 10
                print(f"  - {prefix}")
            if len(prefixes) > 10:
                print(f"  ... and {len(prefixes) - 10} more")
            
            if not dry_run:
                peer_config["allowed_prefixes"] = prefixes
                peer_config["irr_source"] = query
                peer_config["irr_updated"] = True
                updated = True
                print(f"✓ Updated allowed_prefixes for {peer_name}")
            else:
                print(f"[DRY RUN] Would update {len(prefixes)} prefixes")
        else:
            print(f"⚠ No prefixes found in IRR for {query}")
            print(f"  Keeping existing allowed_prefixes (if any)")
    
    if updated and not dry_run:
        # Backup original file
        backup_file = peers_file.replace('.yaml', '.yaml.backup')
        with open(backup_file, 'w') as f:
            with open(peers_file, 'r') as orig:
                f.write(orig.read())
        
        # Write updated file
        with open(peers_file, 'w') as f:
            yaml.dump(peers_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"\n✓ Saved updated peers.yaml")
        print(f"  Backup: {backup_file}")


def generate_bird_prefix_list(as_set_or_asn, name=None):
    """
    Generate BIRD-format prefix list directly
    """
    prefixes = query_bgpq4(as_set_or_asn, ipv4=True)
    
    if not prefixes:
        print(f"No prefixes found for {as_set_or_asn}")
        return
    
    list_name = name or f"pfx_{as_set_or_asn.replace('-', '_').lower()}"
    
    print(f"# Prefix list for {as_set_or_asn}")
    print(f"# Generated from IRR database")
    print(f"# Total prefixes: {len(prefixes)}")
    print(f"define {list_name} = [")
    for i, prefix in enumerate(prefixes):
        comma = "," if i < len(prefixes) - 1 else ""
        print(f"    {prefix}{comma}")
    print("];")


def main():
    parser = argparse.ArgumentParser(
        description="BGP Prefix List Generator using bgpq4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all downstream peers in peers.yaml
  %(prog)s update-peers
  
  # Dry run - show what would be updated
  %(prog)s update-peers --dry-run
  
  # Query specific ASN
  %(prog)s query AS38760
  
  # Query AS-SET
  %(prog)s query AS-CUSTOMER-SET
  
  # Generate BIRD prefix list
  %(prog)s bird-list AS38760 --name pfx_customer1
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Update peers command
    update_parser = subparsers.add_parser("update-peers", help="Update downstream peers from IRR")
    update_parser.add_argument("--dry-run", action="store_true", help="Show what would be updated")
    update_parser.add_argument("--peers-file", default="data/peers.yaml", help="Path to peers.yaml")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query IRR for prefixes")
    query_parser.add_argument("as_set", help="AS number (AS38760) or AS-SET (AS-CUSTOMER)")
    
    # BIRD list command
    bird_parser = subparsers.add_parser("bird-list", help="Generate BIRD prefix list")
    bird_parser.add_argument("as_set", help="AS number or AS-SET")
    bird_parser.add_argument("--name", help="Prefix list name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "update-peers":
        update_downstream_prefixes(args.peers_file, dry_run=args.dry_run)
    
    elif args.command == "query":
        prefixes = query_bgpq4(args.as_set)
        if prefixes:
            print(f"Prefixes for {args.as_set}:")
            for prefix in prefixes:
                print(f"  {prefix}")
            print(f"\nTotal: {len(prefixes)} prefixes")
        else:
            print(f"No prefixes found for {args.as_set}")
    
    elif args.command == "bird-list":
        generate_bird_prefix_list(args.as_set, args.name)


if __name__ == "__main__":
    main()
