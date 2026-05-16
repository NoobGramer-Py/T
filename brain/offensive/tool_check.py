"""
Tool availability checker for T's offensive module.
Verifies whether a tool is installed on the attack VM and returns the install command.
"""

from .tool_catalog import get as catalog_get, Tool
from .vm_bridge    import vm
from core.logger   import get_logger

log = get_logger("offensive.tool_check")


async def check(tool_name: str) -> tuple[bool, str]:
    """
    Check if tool_name exists on the VM.
    Returns (found: bool, install_cmd: str).
    install_cmd is empty string if found.
    """
    entry: Tool | None = catalog_get(tool_name)
    install_cmd = entry.install_cmd if entry else f"apt install -y {tool_name}"

    found = await vm.check_tool(tool_name)
    if found:
        log.info(f"tool check OK: {tool_name}")
        return True, ""

    log.info(f"tool check MISSING: {tool_name}")
    return False, install_cmd


async def install(tool_name: str) -> str:
    """
    Install a tool on the VM using its catalog install_cmd.
    Returns the combined stdout (streamed) as a string.
    """
    entry: Tool | None = catalog_get(tool_name)
    cmd = entry.install_cmd if entry else f"apt install -y {tool_name}"

    # Prepend sudo and set DEBIAN_FRONTEND=noninteractive for apt
    if cmd.startswith("apt"):
        cmd = f"DEBIAN_FRONTEND=noninteractive sudo {cmd}"
    elif cmd.startswith("pip3") or cmd.startswith("gem"):
        cmd = f"sudo {cmd}"

    log.info(f"installing {tool_name} on VM: {cmd}")
    lines: list[str] = []
    async for line in vm.run(cmd, timeout=180):
        lines.append(line)

    return "\n".join(lines)
