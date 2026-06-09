# 💥 Dose – Advanced DDoS/DoS TOOL

**Dose**  is a powerful, multi‑threaded network stress testing and denial‑of‑service (DoS) simulation tool written in Python. It supports both **Layer 7 (HTTP/HTTPS)** and **Layer 4 (TCP/UDP/ICMP/RAW)** attack vectors, proxy rotation, amplification techniques, and game‑specific floods (Minecraft, FiveM, TeamSpeak, etc.).

> ⚠️ **Legal Disclaimer**  
> This tool is intended **exclusively for authorised security testing, research, and educational purposes**. Unauthorised use against any system without explicit permission is **illegal** in most jurisdictions. The authors assume no liability for misuse. Use at your own risk.

---

## 📦 Features

- **Layer 7 (Application)** – HTTP/HTTPS floods
  - `GET`, `POST`, `HEAD`, `CFB`, `BYPASS`, `OVH`, `STRESS`, `DYN`, `SLOW`, `NULL`, `COOKIE`, `PPS`, `EVEN`, `GSB`, `DGB`, `AVB`, `CFBUAM`, `APACHE`, `XMLRPC`, `BOT`, `BOMB`, `DOWNLOADER`, `KILLER`, `TOR`, `RHEX`, `STOMP`, `QUIC`, `SLOWLORIS`
  - Asynchronous I/O (`asyncio` + `aiohttp`) for high concurrency
  - Rotating User‑Agents, Referers, and custom headers
  - Proxy support (HTTP, SOCKS4, SOCKS5)

- **Layer 4 (Transport/Network)** – Raw packet floods & amplification
  - `TCP`, `UDP`, `SYN`, `ICMP`, `OVH‑UDP`, `VSE`, `TS3`, `MINECRAFT`, `MCBOT`, `CPS`, `CONNECTION`, `FIVEM`, `FIVEM‑TOKEN`, `MCPE`, `QUIC‑FLOOD`
  - Amplification vectors: `MEM`, `NTP`, `DNS`, `ARD`, `CLDAP`, `CHAR`, `RDP`, `SSDP`
  - Built‑in Minecraft & FiveM protocol emulation
  - Raw socket support (requires root on Linux)

- **Proxy Management**
  - Automatic proxy download from configurable providers (`config.json`)
  - Proxy validation (threaded checker)
  - Persistent proxy cache (`files/proxies/`)

- **Console Tools** – Interactive diagnostics
  - `DSTAT` – real‑time traffic & system stats
  - `PING` – ICMP latency test
  - `INFO` – GeoIP lookup (via ipwhois.app)
  - `TSSRV` – TeamSpeak SRV record resolver
  - `CHECK` – basic HTTP availability check
  - `CFIP`, `DNS` (planned)

- **Reflector File Support** – For amplification attacks (NTP, DNS, CLDAP, etc.)

---

## 🛠️ Installation

### Prerequisites
- **Python 3.8+**
- Linux / macOS / Windows (raw sockets may require Linux or WSL2)
- Root/Administrator privileges **only** for raw methods (SYN, ICMP, custom UDP raw)

### Install dependencies
```bash
git clone https://github.com/yourusername/dose.git
cd dose
pip install -r requirements.txt
```

**`requirements.txt`** (create if missing):
```
aiohttp
PyRoxy
certifi
dnspython
icmplib
impacket
psutil
requests
yarl
```

> On Linux, you may need `sudo apt install python3-dev build-essential` for `impacket`.

### Configuration
- Edit `config.json` to add your proxy providers and Minecraft protocol defaults.
- Example structure:
```json
{
    "proxy-providers": [
        {
            "type": "SOCKS5",
            "url": "https://example.com/proxies.txt",
            "timeout": 30
        }
    ],
    "MINECRAFT_DEFAULT_PROTOCOL": 74,
    "MCBOT": "Bot"
}
```

---

## 🎮 Usage

The script is named **`dose.py`**. Replace `stressnet.py` with `dose.py` in all examples.

### Command Line Syntax

#### Layer 7 (HTTP/HTTPS)
```bash
python dose.py <method> <url> <proxy_type> <threads> <proxy_file> <rpc> <duration>
```

| Argument      | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `method`      | One of the Layer‑7 methods (e.g., `GET`, `POST`, `CFB`, `SLOWLORIS`)        |
| `url`         | Target URL (with or without `http://`/`https://`)                           |
| `proxy_type`  | `0` = HTTP, `1` = SOCKS4, `2` = SOCKS5 (or custom mapping)                 |
| `threads`     | Number of concurrent worker threads                                         |
| `proxy_file`  | Filename inside `files/proxies/` (will be auto‑downloaded if missing)       |
| `rpc`         | Requests per coroutine (concurrent HTTP sessions per thread)                |
| `duration`    | Attack duration in seconds                                                  |

**Example:**
```bash
python dose.py GET https://example.com 2 200 proxies.txt 50 60
```

#### Layer 4 (Network)
```bash
python dose.py <method> <ip:port> <threads> <duration> [reflector_file|proxy_type proxy_file]
```

| Argument               | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `method`               | Layer‑4 method (e.g., `TCP`, `UDP`, `SYN`, `MINECRAFT`, `NTP`)              |
| `ip:port`              | Target IP and port                                                          |
| `threads`              | Number of attack threads                                                     |
| `duration`             | Attack duration (seconds)                                                   |
| `reflector_file`       | (Amplification methods) Path to file with reflector list (within `files/`)  |
| `proxy_type` + `proxy_file` | (Optional) Proxy type and filename for connection‑based methods        |

**Examples:**
```bash
# SYN flood (requires root)
sudo python dose.py SYN 192.168.1.100:80 4 30

# NTP amplification using reflectors.txt
python dose.py NTP 203.0.113.5:123 100 60 reflectors.txt

# Minecraft bot attack with proxies
python dose.py MCBOT 127.0.0.1:25565 50 120 2 myproxies.txt
```

### Interactive Console
```bash
python dose.py TOOLS
```
Inside the console:
- `HELP` – show available commands
- `DSTAT` – live network/cpu/memory monitor
- `PING` – ping a host
- `INFO` – geolocation of IP/domain
- `TSSRV` – query TeamSpeak SRV records
- `CHECK` – HTTP status check
- `CLEAR` / `EXIT`

### Additional Commands
- `python dose.py STOP` – kills all python dose processes
- `python dose.py HELP` – show usage

---

## ⚙️ How It Works

- **Layer 7** – Uses `asyncio` + `aiohttp` with a rotating pool of user‑agents, referers, and optional proxies. Each worker maintains a persistent session to maximise throughput.
- **Layer 4 (TCP/UDP)** – Traditional socket flood with randomised payload sizes.
- **SYN Flood** – Crafts raw IP/TCP packets with the `IP_HDRINCL` socket option (Linux only, root required).
- **Amplification** – Sends small queries to public reflectors (DNS, NTP, CLDAP, SSDP, etc.) which respond with much larger packets, multiplying the traffic volume.
- **Game Protocols** – Implements custom handshakes for Minecraft (`0x00` handshake, login/register), FiveM (`getinfo`), TeamSpeak (`05 ca 7f...`), etc.

---

## 📊 Performance Considerations

| Factor                | Impact                                                                 |
|-----------------------|------------------------------------------------------------------------|
| **Bandwidth**         | The single most limiting resource – a 1 Gbps link can saturate small targets. |
| **CPU / RAM**         | Layer‑7 async floods consume more CPU; raw floods are very light.      |
| **Proxies**           | Good proxies increase L7 effectiveness but add latency.                |
| **Reflectors**        | For amplification, the quality and quantity of reflectors determine the multiplier (up to 500×). |
| **Mitigation**        | Modern firewalls, DDoS mitigation services (Cloudflare, Akamai) and rate‑limiting render most methods ineffective. |

> Realistic **Layer‑7** throughput from a single machine: 10k–50k requests/sec (depending on target latency).  
> **Layer‑4 raw** floods can push line rate (e.g., 1.4 million pps on a 1 GbE NIC).

---

## 🧪 Testing Environment

Always obtain **written permission** before testing any system. Recommended safe lab setup:

- Two isolated VMs or containers
- Target running a simple HTTP server (e.g., `python -m http.server 8080`)
- Monitor with `tcpdump`, `iftop`, or `nload`
- Use `DSTAT` console tool for real‑time metrics

---

## 📝 To‑Do / Roadmap

- [ ] Add HTTP/2 support
- [ ] Implement DNS over HTTPS for evasion
- [ ] Add randomised packet pacing to bypass simple rate limits
- [ ] Support for IPv6 amplification
- [ ] Distributed mode (master‑worker)

---

## 🤝 Contributing

Contributions are welcome for **educational and defensive research purposes**. Please open an issue or pull request with any improvements, bug fixes, or new attack vectors (provided they are well‑documented for testing).

---

## ⚖️ License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.  
However, note that using this tool against unauthorised targets violates computer fraud laws in most countries.

---

## 🏁 Final Word

**Dose** is a **proof‑of‑concept** tool to help security professionals understand network flood attacks and test their own infrastructure. Always act responsibly and within the law.

> *“With great power comes great responsibility.”* – Uncle Ben
```
