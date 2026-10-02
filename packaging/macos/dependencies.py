"""Bounded Mach-O closure, native relocation and fail-closed final audit."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SYSTEM = ("/usr/lib/", "/System/Library/")
MAGIC = {
    b"\xcf\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
}


@dataclass(frozen=True)
class Info:
    architectures: tuple[str, ...]
    dependencies: tuple[str, ...]
    rpaths: tuple[str, ...]
    install_id: str | None
    executable: bool = False


def output(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def macho_output(options: list[str], binary: Path) -> str:
    # otool-classic treats trailing parentheses as archive-member syntax.
    with binary.open("rb") as stream:
        descriptor = stream.fileno()
        return subprocess.check_output(
            ["/usr/bin/otool", *options, f"/dev/fd/{descriptor}"],
            pass_fds=(descriptor,),
            text=True,
            stderr=subprocess.STDOUT,
        )


def read_info(binary: Path) -> Info:
    text = macho_output(["-L"], binary)
    identities = macho_output(["-D"], binary).splitlines()[1:]
    identity = identities[0].strip() if identities else None
    dependencies = tuple(line.strip().split(" (compatibility", 1)[0] for line in text.splitlines()[1:])
    commands = macho_output(["-l"], binary)
    rpaths = tuple(re.findall(r"cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset", commands))
    return Info(
        tuple(output(["/usr/bin/lipo", "-archs", str(binary)]).split()),
        tuple(d for d in dependencies if d != identity),
        rpaths,
        identity,
        "EXECUTE" in macho_output(["-hv"], binary),
    )


def expand(name: str, binary: Path, executable: Path) -> Path:
    if name.startswith("@loader_path/"):
        return binary.parent / name[len("@loader_path/") :]
    if name == "@loader_path":
        return binary.parent
    if name.startswith("@executable_path/"):
        return executable.parent / name[len("@executable_path/") :]
    if name == "@executable_path":
        return executable.parent
    if name.startswith("/"):
        return Path(name)
    raise ValueError(f"Unresolved Mach-O reference: {name}")


def resolve(name: str, binary: Path, executable: Path, info: Info, entry_info: Info) -> Path:
    if name.startswith("@rpath/"):
        suffix = name[len("@rpath/") :]
        candidates = [
            expand(rpath, owner, executable) / suffix
            for owner, value in [(binary, info), (executable, entry_info)]
            for rpath in value.rpaths
        ]
    else:
        candidates = [expand(name, binary, executable)]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve(strict=True)
    raise ValueError(f"Unresolved non-system dependency: {name}")


def dependency_closure(executable: Path, *, read=read_info, architecture="arm64") -> dict[Path, Info]:
    executable = executable.resolve(strict=True)
    entry_info = read(executable)
    pending, result = [executable], {}
    while pending:
        binary = pending.pop()
        if binary in result:
            continue
        if len(result) >= 256:
            raise ValueError("Native dependency closure exceeds bounded limit")
        info = read(binary)
        if architecture not in info.architectures:
            raise ValueError(f"Incompatible native binary: {binary.name}")
        result[binary] = info
        pending.extend(
            resolve(name, binary, executable, info, entry_info)
            for name in info.dependencies
            if not name.startswith(SYSTEM)
        )
    return result


def audit_binary(binary: Path, root: Path, executable: Path, *, read=read_info, architecture="arm64") -> Info:
    root = root.resolve(strict=True)
    if not binary.resolve(strict=True).is_relative_to(root):
        raise ValueError("Native binary escapes bundle")
    info, entry_info = read(binary), read(executable)
    if architecture not in info.architectures:
        raise ValueError("Runtime native architecture mismatch")
    if info.install_id and info.install_id.startswith("/") and not info.install_id.startswith(SYSTEM):
        raise ValueError("Runtime retains an absolute non-system install ID")
    for rpath in info.rpaths:
        if rpath.startswith("/") and not rpath.startswith(SYSTEM):
            raise ValueError("Runtime retains an absolute non-system rpath")
        if not rpath.startswith(SYSTEM) and not expand(rpath, binary, executable).resolve().is_relative_to(root):
            raise ValueError("Runtime rpath escapes bundle")
    for name in info.dependencies:
        if name.startswith(SYSTEM):
            continue
        if name.startswith("/"):
            raise ValueError("Runtime retains an absolute non-system dependency")
        if not resolve(name, binary, executable, info, entry_info).is_relative_to(root):
            raise ValueError("Runtime dependency escapes bundle")
    return info


def is_macho(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(4) in MAGIC


def audit_tree(root: Path, executable: Path, *, read=read_info, exclude: Path | None = None) -> list[dict[str, object]]:
    result, seen = [], set()
    for directory, names, files in os.walk(root):
        if exclude is not None:
            names[:] = [name for name in names if Path(directory) / name != exclude]
        for name in [*names, *files]:
            p = Path(directory) / name
            if p.is_symlink() and not p.resolve(strict=True).is_relative_to(root.resolve()):
                raise ValueError("Bundle symlink escapes runtime")
        for name in files:
            p = Path(directory) / name
            real = p.resolve(strict=True)
            if real in seen or not is_macho(p):
                continue
            seen.add(real)
            if len(seen) > 4096:
                raise ValueError("Runtime native inventory exceeds bounded limit")
            context = p if read(p).executable else executable
            info = audit_binary(p, root, context, read=read)
            result.append(
                {
                    "path": p.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "architectures": info.architectures,
                    "dependencies": info.dependencies,
                }
            )
    return result


def stage_closure(executable: Path, destination: Path, *, closure=None, run=subprocess.check_call) -> Path:
    """Only mutate fresh copies; input binaries and their signatures stay intact."""
    executable = executable.resolve(strict=True)
    closure = dependency_closure(executable) if closure is None else closure
    if destination.exists():
        raise ValueError("Dependency staging destination must be new")
    by_name = {}
    for source in closure:
        if source != executable and source.name in by_name:
            raise ValueError("Ambiguous native dependency basename")
        by_name[source.name] = source
    destination.mkdir(parents=True)
    libraries = destination / "ffmpeg-libs"
    libraries.mkdir()
    targets = {
        source: destination / "ffmpeg" if source == executable else libraries / source.name for source in closure
    }
    entry_info = closure[executable]
    for source, target in targets.items():
        shutil.copy2(source, target)
        info = closure[source]
        if info.install_id:
            run(["/usr/bin/install_name_tool", "-id", f"@loader_path/{target.name}", str(target)])
        for name in info.dependencies:
            if name.startswith(SYSTEM):
                continue
            dependency = resolve(name, source, executable, info, entry_info)
            relative = os.path.relpath(targets[dependency], target.parent)
            run(["/usr/bin/install_name_tool", "-change", name, "@loader_path/" + relative, str(target)])
        for rpath in info.rpaths:
            run(["/usr/bin/install_name_tool", "-delete_rpath", rpath, str(target)])
        run(["/usr/bin/codesign", "--force", "--sign", "-", str(target)])
    audit_tree(destination, destination / "ffmpeg")
    return destination / "ffmpeg"
