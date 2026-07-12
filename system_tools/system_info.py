"""
system_info.py — CPU, RAM, disk, battery, processes, network.
"""

import platform

import psutil

from langchain_core.tools import tool

from system_tools.safety import logger


@tool
def get_system_stats() -> str:
    """
    Get a summary of current system resource usage:
    CPU, RAM, disk, battery, OS info, and uptime.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        boot_time = psutil.boot_time()

        import datetime
        uptime_seconds = (datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)).total_seconds()
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        lines = [
            "💻 System Stats",
            f"  OS: {platform.system()} {platform.release()} ({platform.machine()})",
            f"  CPU: {cpu_percent}% usage ({cpu_count} cores)",
            f"  RAM: {mem.percent}% used ({mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB)",
            f"  Disk C:\\: {disk.percent}% used ({disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB)",
            f"  Uptime: {hours}h {minutes}m {seconds}s",
        ]

        # Battery (if available)
        battery = psutil.sensors_battery()
        if battery:
            plug = "🔌 Plugged in" if battery.power_plugged else "🔋 On battery"
            lines.append(f"  Battery: {battery.percent}% ({plug})")

        result = "\n".join(lines)
        logger.log("get_system_stats", {}, result)
        return result
    except Exception as e:
        msg = f"❌ Error getting system stats: {e}"
        logger.log("get_system_stats", {}, msg, status="error")
        return msg


@tool
def list_processes(sort_by: str = "cpu", limit: int = 15) -> str:
    """
    List the top running processes sorted by CPU or memory usage.

    Args:
        sort_by: Sort criterion — "cpu" or "memory" (default "cpu")
        limit: Maximum number of processes to return (default 15)
    """
    try:
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        procs.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)

        lines = [f"📊 Top {limit} processes (sorted by {sort_by}):\n"]
        lines.append(f"  {'PID':<8} {'Name':<30} {'CPU%':<8} {'MEM%':<8}")
        lines.append(f"  {'---':<8} {'---':<30} {'---':<8} {'---':<8}")
        for p in procs[:limit]:
            lines.append(
                f"  {p['pid']:<8} {(p['name'] or 'N/A')[:29]:<30} "
                f"{(p.get('cpu_percent') or 0):<8.1f} {(p.get('memory_percent') or 0):<8.1f}"
            )

        result = "\n".join(lines)
        logger.log("list_processes", {"sort_by": sort_by, "limit": limit}, f"{len(procs)} total processes")
        return result
    except Exception as e:
        msg = f"❌ Error listing processes: {e}"
        logger.log("list_processes", {}, msg, status="error")
        return msg


@tool
def get_network_info() -> str:
    """
    Get network interface information: IP addresses, MAC addresses,
    and current connectivity status.
    """
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io = psutil.net_io_counters()

        lines = ["🌐 Network Info\n"]
        lines.append(f"  Total Sent: {io.bytes_sent / (1024**2):.1f} MB")
        lines.append(f"  Total Received: {io.bytes_recv / (1024**2):.1f} MB\n")

        for iface, addr_list in addrs.items():
            is_up = stats.get(iface, None)
            status = "🟢 UP" if (is_up and is_up.isup) else "🔴 DOWN"
            lines.append(f"  {iface} [{status}]")
            for addr in addr_list:
                if addr.family.name == "AF_INET":
                    lines.append(f"    IPv4: {addr.address}")
                elif addr.family.name == "AF_INET6":
                    lines.append(f"    IPv6: {addr.address}")

        result = "\n".join(lines)
        logger.log("get_network_info", {}, "Network info retrieved")
        return result
    except Exception as e:
        msg = f"❌ Error getting network info: {e}"
        logger.log("get_network_info", {}, msg, status="error")
        return msg


@tool
def kill_process(pid_or_name: str) -> str:
    """
    Kill a process by PID (number) or by name (e.g. "notepad.exe").

    Args:
        pid_or_name: Process ID as a number, or process name string
    """
    try:
        # If it's a number, kill by PID
        if pid_or_name.isdigit():
            pid = int(pid_or_name)
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            proc.wait(timeout=5)
            logger.log("kill_process", {"pid": pid}, f"Killed {name} (PID {pid})")
            return f"✅ Killed process: {name} (PID {pid})"
        else:
            # Kill by name
            killed = 0
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if proc.info["name"] and proc.info["name"].lower() == pid_or_name.lower():
                        proc.terminate()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed > 0:
                logger.log("kill_process", {"name": pid_or_name}, f"Killed {killed} instances")
                return f"✅ Killed {killed} instance(s) of {pid_or_name}"
            else:
                return f"⚠️ No running process found with name: {pid_or_name}"

    except psutil.NoSuchProcess:
        return f"⚠️ Process not found: {pid_or_name}"
    except psutil.AccessDenied:
        return f"⛔ Access denied — cannot kill {pid_or_name} (may need admin privileges)"
    except Exception as e:
        msg = f"❌ Error killing process: {e}"
        logger.log("kill_process", {"pid_or_name": pid_or_name}, msg, status="error")
        return msg
