"""Read AMD GPU activity from DRM client fdinfo counters."""

import os
import threading
import time


DRM_DEVICE_PREFIX = "/dev/dri/"
REDISCOVER_SECONDS = 15.0
YOUNG_PROCESS_SECONDS = 120.0
FULL_RESCAN_SECONDS = 300.0


def _engine_counter(text):
    client_id = None
    is_amdgpu = False
    total_ns = 0

    for line in text.splitlines():
        if line.startswith("drm-driver:"):
            is_amdgpu = line.partition(":")[2].strip() == "amdgpu"
        elif line.startswith("drm-client-id:"):
            client_id = line.partition(":")[2].strip() or None
        elif line.startswith("drm-engine-") and not line.startswith("drm-engine-capacity-"):
            fields = line.partition(":")[2].split()
            if len(fields) >= 2 and fields[1] == "ns" and fields[0].isdigit():
                total_ns += int(fields[0])

    return (client_id, total_ns) if is_amdgpu else None


class DrmFdinfoSampler:
    """Sample cumulative AMDGPU engine time without repeatedly scanning /proc."""

    def __init__(self, proc="/proc", clock=time.monotonic, clock_ns=time.monotonic_ns):
        self._proc = str(proc)
        self._clock = clock
        self._clock_ns = clock_ns
        self._lock = threading.Lock()
        self._busy_lock = threading.Lock()
        self._fdinfo_paths = []
        self._discovered_at = None
        self._full_scan_at = None
        self._by_pid = {}
        self._previous = None
        self._previous_at_ns = None

    def _read(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:
            return None

    def _uptime(self):
        text = self._read(os.path.join(self._proc, "uptime"))
        try:
            return float(text.split()[0]) if text else None
        except (IndexError, ValueError):
            return None

    def _started(self, pid):
        text = self._read(os.path.join(self._proc, pid, "stat"))
        if not text:
            return None
        fields = text.rpartition(")")[2].split()
        try:
            return int(fields[19]) / os.sysconf("SC_CLK_TCK")
        except (IndexError, ValueError, OSError):
            return None

    def _scan_pid(self, pid):
        paths = []
        fd_dir = os.path.join(self._proc, pid, "fd")
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            return paths
        for fd in fds:
            try:
                target = os.readlink(os.path.join(fd_dir, fd))
            except OSError:
                continue
            if target.startswith(DRM_DEVICE_PREFIX):
                paths.append(os.path.join(self._proc, pid, "fdinfo", fd))
        return paths

    def _discover(self, now):
        try:
            pids = [name for name in os.listdir(self._proc) if name.isdigit()]
        except OSError:
            return []

        if self._full_scan_at is None or now - self._full_scan_at >= FULL_RESCAN_SECONDS:
            self._full_scan_at = now
            self._by_pid = {}

        uptime = self._uptime()
        by_pid = {}
        for pid in pids:
            known = self._by_pid.get(pid)
            if known is None:
                by_pid[pid] = (self._started(pid), self._scan_pid(pid))
                continue
            started, paths = known
            young = (
                started is not None
                and uptime is not None
                and uptime - started < YOUNG_PROCESS_SECONDS
            )
            by_pid[pid] = (started, self._scan_pid(pid)) if not paths and young else known
        self._by_pid = by_pid
        return [path for _started, paths in by_pid.values() for path in paths]

    def sample(self):
        """Return cumulative engine nanoseconds indexed by DRM client id."""
        with self._lock:
            now = self._clock()
            if self._discovered_at is None or now - self._discovered_at >= REDISCOVER_SECONDS:
                self._fdinfo_paths = self._discover(now)
                self._discovered_at = now

            counters = {}
            alive = []
            for path in self._fdinfo_paths:
                text = self._read(path)
                if text is None:
                    continue
                alive.append(path)
                parsed = _engine_counter(text)
                if parsed is None:
                    continue
                client_id, total_ns = parsed
                key = client_id or path
                counters[key] = max(counters.get(key, 0), total_ns)
            self._fdinfo_paths = alive
            return counters

    def busy_percent(self):
        """Return aggregate GPU busy percentage, or None until a baseline exists."""
        with self._busy_lock:
            current = self.sample()
            now_ns = self._clock_ns()
            previous = self._previous
            previous_at_ns = self._previous_at_ns
            self._previous = current
            self._previous_at_ns = now_ns
            if previous is None or previous_at_ns is None:
                return None

            elapsed_ns = now_ns - previous_at_ns
            if elapsed_ns <= 0:
                return None
            shared_clients = previous.keys() & current.keys()
            if not shared_clients:
                return None
            delta_ns = sum(
                max(0, current[client_id] - previous[client_id])
                for client_id in shared_clients
            )
            return max(0.0, min(100.0, delta_ns / elapsed_ns * 100.0))