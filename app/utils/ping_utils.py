import subprocess
import platform
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

PING_CACHE = {}
CACHE_TTL = 60

SLOW_LIMIT_MS = 150

PING_MAX_WORKERS = 6
CONFIG_MAX_WORKERS = 4
PING_PROCESS_TIMEOUT_SECONDS = 2
PING_RETRIES = 0


def _ping_once(ip):
    try:
        system = platform.system().lower()

        param = "-n" if system == "windows" else "-c"
        timeout = "-w" if system == "windows" else "-W"
        timeout_value = "1000" if system == "windows" else "1"

        start_time = time.time()

        result = subprocess.run(
            ["ping", param, "1", timeout, timeout_value, ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=PING_PROCESS_TIMEOUT_SECONDS
        )

        latency = round((time.time() - start_time) * 1000)

        output = result.stdout.lower()

        if "ttl=" in output:
            return "online", latency

        return "offline", None

    except subprocess.TimeoutExpired:
        return "offline", None

    except Exception:
        return "error", None


def _ping_with_retry(ip, retries=PING_RETRIES):
    status, latency = _ping_once(ip)

    if status == "online":
        return status, latency

    for _ in range(retries):
        status, latency = _ping_once(ip)

        if status == "online":
            return status, latency

    return status, latency


def ping_ip_cached(ip):
    now = time.time()

    if ip in PING_CACHE:
        if now - PING_CACHE[ip]["time"] < CACHE_TTL:
            return PING_CACHE[ip]["status"]

    status, latency = _ping_with_retry(ip)

    PING_CACHE[ip] = {
        "status": status,
        "latency": latency,
        "time": now
    }

    return status


def ping_info_cached(ip):
    now = time.time()

    if ip in PING_CACHE:
        if now - PING_CACHE[ip]["time"] < CACHE_TTL:
            status = PING_CACHE[ip]["status"]
            latency = PING_CACHE[ip]["latency"]

            return {
                "status": status,
                "latency": latency,
                "quality": _get_quality(status, latency)
            }

    status, latency = _ping_with_retry(ip)

    PING_CACHE[ip] = {
        "status": status,
        "latency": latency,
        "time": now
    }

    return {
        "status": status,
        "latency": latency,
        "quality": _get_quality(status, latency)
    }


def _get_quality(status, latency):
    if status == "online":
        if latency is not None and latency > SLOW_LIMIT_MS:
            return "slow"
        return "normal"

    if status == "offline":
        return "offline"

    return "error"


def ping_lote(ips):
    results = {}

    ips_unicos = []

    for ip in ips:
        if ip and ip not in ips_unicos:
            ips_unicos.append(ip)

    with ThreadPoolExecutor(max_workers=PING_MAX_WORKERS) as executor:
        futures = {executor.submit(ping_info_cached, ip): ip for ip in ips_unicos}

        for future in as_completed(futures):
            ip = futures[future]
            try:
                results[ip] = future.result()
            except Exception:
                results[ip] = {
                    "status": "error",
                    "latency": None,
                    "quality": "error"
                }

    return results


def _resolve_hostname(nome):
    try:
        resolved_ip = socket.gethostbyname(nome)

        return {
            "status": "resolved",
            "ip": resolved_ip
        }

    except Exception:
        return {
            "status": "error",
            "ip": None
        }


def verificar_config_hardware(ip_configurado, nome):
    resolved = _resolve_hostname(nome)

    if resolved["status"] != "resolved":
        return {
            "status": "error",
            "nome_status": "error",
            "ip_configurado": ip_configurado,
            "ip_resolvido": None,
            "latency": None,
            "quality": "error"
        }

    ip_resolvido = resolved["ip"]

    nome_status, latency = _ping_with_retry(nome)

    if nome_status != "online":
        return {
            "status": "offline",
            "nome_status": nome_status,
            "ip_configurado": ip_configurado,
            "ip_resolvido": ip_resolvido,
            "latency": latency,
            "quality": _get_quality(nome_status, latency)
        }

    if str(ip_configurado).strip() != str(ip_resolvido).strip():
        return {
            "status": "ip_diferente",
            "nome_status": nome_status,
            "ip_configurado": ip_configurado,
            "ip_resolvido": ip_resolvido,
            "latency": latency,
            "quality": _get_quality(nome_status, latency)
        }

    return {
        "status": "ok",
        "nome_status": nome_status,
        "ip_configurado": ip_configurado,
        "ip_resolvido": ip_resolvido,
        "latency": latency,
        "quality": _get_quality(nome_status, latency)
    }


def verificar_config_lote(hardwares):
    results = {}

    with ThreadPoolExecutor(max_workers=CONFIG_MAX_WORKERS) as executor:
        futures = {
            executor.submit(verificar_config_hardware, hardware.get("ip"), hardware.get("nome")): hardware
            for hardware in hardwares
        }

        for future in as_completed(futures):
            hardware = futures[future]
            chave = hardware.get("ip")

            try:
                results[chave] = future.result()
            except Exception:
                results[chave] = {
                    "status": "error",
                    "nome_status": "error",
                    "ip_configurado": hardware.get("ip"),
                    "ip_resolvido": None,
                    "latency": None,
                    "quality": "error"
                }

    return results