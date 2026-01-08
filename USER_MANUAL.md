# BIRD Management CLI User Manual

Tools `bin/bird-mgmt` adalah interface utama untuk operasional BGP. Tools ini memanipulasi file YAML konfigurasi dan meng-generate ulang `bird.conf` secara otomatis.

## 1. Persiapan & Dasar

Jalankan tanpa argumen untuk melihat help:
```bash
cd ~/br2-plan/bird-cfg
./bin/bird-mgmt --help
```

---

## 2. Validasi & Deployment

### Validasi Config
Generate ulang config dan cek syntax BIRD tanpa apply.
```bash
./bin/bird-mgmt validate
```
*Output: "✓ Generation successful" dan "✓ BIRD Syntax Valid".*

### Deploy ke Router
Generate, Validate, Backup existing config, Copy ke `/etc/bird/bird.conf`, dan Reload BIRD.
```bash
./bin/bird-mgmt deploy
```
> **Note:** Config existing di `/etc/bird/bird.conf` akan di-backup otomatis ke `/etc/bird/bird.conf.backup-YYYYMMDD-HHMMSS`

---

## 3. Monitoring

### Show Peers
Melihat status semua sesi BGP (IPv4 & IPv6).
```bash
./bin/bird-mgmt show-peers
```
**Kolom:**
- **State**: `Established` (Hijau) = UP. `Idle`/`Connect` (Kuning/Merah) = DOWN.
- **Imp/Exp**: Jumlah prefix yang diterima (Import) dan dikirim (Export).

### Show Traffic Engineering
Melihat rules TE yang aktif.
```bash
./bin/bird-mgmt show-te
```

### Show Blackholes
Melihat IP yang sedang di-RTBH.
```bash
./bin/bird-mgmt show-blackhole
```

---

## 4. Manajemen Prefix List
Mengelola daftar prefix (whitelist) di `prefixes.yaml`.

### Menambah Prefix
**Command:** `add-prefix <group> <prefix> [--ipv6]`
```bash
# IPv4
./bin/bird-mgmt add-prefix msa 103.111.222.0/24

# IPv6
./bin/bird-mgmt add-prefix msa 2400:aaaa::/32 --ipv6
```

### Menghapus Prefix
**Command:** `remove-prefix <group> <prefix>`
```bash
./bin/bird-mgmt remove-prefix msa 103.111.222.0/24
```

### Auto-Inject IPv6 Neighbor
Otomatis menambahkan `neighbor_ip_v6` ke peer yang belum dual-stack.
```bash
./bin/bird-mgmt inject-ipv6
```

---

## 5. Traffic Engineering (Prefix-Based)
Mengatur routing berdasarkan **Prefix** spesifik.

### Set Local Preference (Import/Upload)
Mengatur prioritas jalur masuk untuk prefix tujuan tertentu.
**Command:** `set-localpref-import-prefix <prefix> <peer> <value>`

```bash
./bin/bird-mgmt set-localpref-import-prefix 8.8.8.8/32 lintas_iptx 500
```

### Set Local Preference (Export/Download)
Mengatur prioritas jalur keluar untuk prefix milik kita.
**Command:** `set-localpref-export-prefix <prefix> <peer> <value>`

```bash
./bin/bird-mgmt set-localpref-export-prefix 103.100.0.0/24 kledo 200
```

---

## 6. Traffic Engineering (ASN-Based)
Mengatur routing berdasarkan **ASN** lawan.
**PENTING:** Gunakan flag `--ipv6` untuk rule IPv6.

### Set Local Preference by ASN (Import)
**Command:** `set-localpref-import-asn <asn> <peer> <value> [--ipv6]`

```bash
# IPv4
./bin/bird-mgmt set-localpref-import-asn 15169 biix 300

# IPv6
./bin/bird-mgmt set-localpref-import-asn 15169 biix 300 --ipv6
```

### Set Local Preference by ASN (Export)
**Command:** `set-localpref-export-asn <asn> <peer> <value> [--ipv6]`

---

## 7. Filtering (Reject/Allow)
Memblokir atau mengizinkan route spesifik.

### Filter by Prefix
**Commands:**
- `reject-import-prefix <peer> <prefix>`
- `reject-export-prefix <peer> <prefix>`
- `allow-import-prefix <peer> <prefix>` (Hapus reject)
- `allow-export-prefix <peer> <prefix>` (Hapus reject)

```bash
./bin/bird-mgmt reject-import-prefix msa 0.0.0.0/0
```

### Filter by ASN
**Commands:**
- `reject-import-asn <peer> <asn> [--ipv6]`
- `reject-export-asn <peer> <asn> [--ipv6]`
- `allow-import-asn <peer> <asn> [--ipv6]`
- `allow-export-asn <peer> <asn> [--ipv6]`

```bash
./bin/bird-mgmt reject-import-asn openixp 12345
./bin/bird-mgmt reject-import-asn openixp 12345 --ipv6
```

---

## 8. Failover Emergency
Memindahkan trafik dari satu peer ke peer lain dengan menukar Local Preference.
**Command:** `failover <primary_peer> <backup_peer>`

```bash
./bin/bird-mgmt failover primary_isp backup_isp
```
*(Jangan lupa `deploy` setelah command ini)*

---

## 9. DDoS Mitigation (Blackhole)
Mengirim route ke blackhole (Drop).

### Tambah Blackhole
**Command:** `add-blackhole <prefix> [reason]`
```bash
./bin/bird-mgmt add-blackhole 103.10.10.5/32 "UDP Flood"
```

### Hapus Blackhole
**Command:** `remove-blackhole <prefix>`
```bash
./bin/bird-mgmt remove-blackhole 103.10.10.5/32
```

---

## 10. Static Routes
Mengelola static routes di `router.yaml`.

### Lihat Static Routes
```bash
./bin/bird-mgmt show-static-routes
```

### Tambah Static Route
**Command:** `add-static-route <prefix> <via>`
```bash
./bin/bird-mgmt add-static-route 10.10.10.0/24 192.168.1.1
```

### Hapus Static Route
**Command:** `remove-static-route <prefix>`
```bash
./bin/bird-mgmt remove-static-route 10.10.10.0/24
```
