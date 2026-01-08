# Guide: Menambahkan Downstream Customer

Panduan step-by-step untuk menambahkan customer downstream dengan auto prefix generation dari IRR.

---

## Contoh: Customer MSA (AS38760)

### Step 1: Tambahkan Peer ke `config/peers.yaml`

```bash
nano config/peers.yaml
```

Tambahkan di section `downstream`:

```yaml
peers:
  downstream:
    customer_msa:                     # Nama peer (lowercase, underscore)
      description: MSA Dimensi Cloud  # Deskripsi customer
      asn: 38760                      # AS Number customer
      neighbor_ip: 192.168.200.1      # IP neighbor (customer)
      neighbor_ip_v6: fd00:200::1     # IPv6 neighbor (optional)
      local_ip_v6: fd00:200::2        # IPv6 local (optional)
      type: downstream                # Wajib: downstream
      max_prefixes: 1000              # Limit prefix
      localpref_import: 500           # LocalPref untuk route customer
      graceful_restart: true          # Enable GR
      
      # ========== AUTO PREFIX GENERATION ==========
      auto_prefix: true               # Enable auto prefix dari IRR
      # as_set: AS-MSA                # Optional: AS-SET di IRR (default: AS{asn})
      # downstream_asns:              # Optional: Transit customer ASNs
      #   - 65100
      #   - 65200
      
      # Manual allowed prefixes (optional, untuk prefix di luar IRR)
      allowed_prefixes:
        # - 103.100.100.0/24          # Uncomment jika ada prefix manual
      
      # Reference ke prefix list dari IRR
      import_allowed_prefix_lists:
        - customer_msa_prefixes       # Nama prefix group (otomatis dari update-prefixes)
      
      communities:
        info: 4
```

**PENTING:** 
- Nama peer (`customer_msa`) harus sesuai dengan nama prefix group (`customer_msa_prefixes`)
- Format: `{nama_peer}_prefixes`

---

### Step 2: Generate Prefix List dari IRR

Jalankan command untuk query prefix dari IRR database:

```bash
sudo ./bin/bird-mgmt update-prefixes customer_msa
```

**Output:**
```
[Updating Prefix Lists from IRR]

  Processing customer_msa (AS38760)...
    Querying AS38760...
    ✓ Found 17 IPv4, 7 IPv6 prefixes

✓ Prefix lists updated in /home/najib/bird-cfg/config/prefixes.yaml
Run './bin/generate && ./bin/bird-mgmt deploy' to apply changes
```

**Apa yang terjadi:**
- bgpq4 query IRR database (APNIC/IDNIC) untuk AS38760
- Prefix otomatis disimpan ke `prefixes.yaml` sebagai group `customer_msa_prefixes`
- Peer config otomatis di-update dengan `import_allowed_prefix_lists`

---

### Step 3: Verify Prefix di `prefixes.yaml`

```bash
cat config/prefixes.yaml
```

Pastikan ada section baru:

```yaml
prefix_groups:
  customer_msa_prefixes:
    description: Auto-generated prefixes for MSA Dimensi Cloud
    auto_generated: true
    source_asns:
    - 38760
    ipv4:
    - 103.217.208.0/22
    - 103.4.52.0/23
    - 103.99.164.0/22
    # ... dst
    ipv6:
    - 2001:df2:a00::/48
    - 2400:9b60::/32
    # ... dst
```

---

### Step 4: Generate & Deploy Configuration

```bash
# Generate BIRD config
sudo ./bin/generate

# Deploy ke /etc/bird dan reload BIRD
sudo ./bin/bird-mgmt deploy
```

**Output sukses:**
```
✓ Generation successful
✓ BIRD Syntax Valid
✓ Deployed modular config & Reloaded BIRD
```

---

### Step 5: Verify Peer Status

```bash
sudo ./bin/bird-mgmt show-peers
```

**Output:**
```
Peer Key         Protocol Name                ASN    Type         Neighbor IP      State
--------------------------------------------------------------------------------------
customer_msa     ebgp_downstream_customer_... 38760  downstream   192.168.200.1    Idle
```

Status `Idle` = normal (menunggu neighbor connect)

---

## Update Prefix List (Re-sync dari IRR)

Jika customer menambah prefix di IRR, jalankan lagi:

```bash
sudo ./bin/bird-mgmt update-prefixes customer_msa
sudo ./bin/generate && sudo ./bin/bird-mgmt deploy
```

---

## Troubleshooting

### Error: `CF_SYM_UNDEFINED` saat deploy

**Penyebab:** Nama peer di `peers.yaml` tidak match dengan nama prefix group di `prefixes.yaml`

**Contoh:**
- Peer name: `customer_msa`
- Prefix group: `customer_a_prefixes` ❌ (salah)

**Solusi:**
```bash
# Rename group di prefixes.yaml
sed -i 's/customer_a_prefixes/customer_msa_prefixes/g' config/prefixes.yaml

# Atau jalankan ulang update-prefixes
sudo ./bin/bird-mgmt update-prefixes customer_msa
```

---

### Error: `bgpq4: command not found`

**Solusi:**
```bash
sudo apt update
sudo apt install bgpq4
```

---

## Menghapus Customer

### 1. Hapus peer dari `peers.yaml`
```bash
nano config/peers.yaml
# Hapus section customer_msa
```

### 2. (Optional) Hapus prefix group dari `prefixes.yaml`
```bash
nano config/prefixes.yaml
# Hapus section customer_msa_prefixes
```

### 3. Generate & Deploy
```bash
sudo ./bin/generate && sudo ./bin/bird-mgmt deploy
```

---

## Best Practices

1. **Naming Convention:**
   - Gunakan nama peer konsisten: `customer_[nama_singkat]`
   - Prefix group otomatis: `{nama_peer}_prefixes`

2. **IRR Database:**
   - Pastikan customer sudah registrasi AS dan prefix di IRR (APNIC/IDNIC)
   - Update prefix list berkala (monthly) dengan `update-prefixes`

3. **Backup:**
   - Config selalu di-backup otomatis ke `output.backup-*` (max 7)
   - `/etc/bird` di-backup ke `/etc/bird.backup-*` saat deploy

4. **Monitoring:**
   - Check peer status: `sudo ./bin/bird-mgmt show-peers`
   - Check BIRD log: `sudo tail -f /var/log/bird.log`

---

## Reference

- **README.md** - Daftar semua commands
- **MANUAL.md** - Dokumentasi lengkap format YAML
- **config/peers.yaml** - Contoh konfigurasi peer
