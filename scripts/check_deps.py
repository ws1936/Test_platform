"""Check which packages from requirements.txt are installed."""

import importlib.metadata as md
import re
import sys
from pathlib import Path


def parse_requirements(path: Path) -> dict:
    """Parse a pip requirements file into {normalized_name: raw_line}."""
    reqs = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Match name (with extras allowed) op version
        m = re.match(
            r"^([A-Za-z0-9_.\-]+)(\[[^\]]+\])?\s*([=<>!~]+)\s*([0-9][^\s]*)",
            line,
        )
        if m:
            name = m.group(1).lower().replace("-", "_").replace(".", "_")
            reqs[name] = (line, m.group(3), m.group(4))
    return reqs


def installed_versions() -> dict:
    out = {}
    for pkg in md.distributions():
        n = pkg.metadata["Name"].lower().replace("-", "_").replace(".", "_")
        out[n] = pkg.metadata["Version"]
    return out


def main() -> int:
    req_path = Path(__file__).resolve().parent.parent / "requirements.txt"
    reqs = parse_requirements(req_path)
    installed = installed_versions()

    # Build a unified list (preserve requirements order + show extras)
    print(f"{'PACKAGE':<30} {'REQUIRED':<22} {'INSTALLED':<15} STATUS")
    print("-" * 80)

    missing = []
    wrong_version = []
    for name, (line, op, ver) in reqs.items():
        ins = installed.get(name)
        status = "OK" if ins else "MISSING"
        print(f"{name:<30} {line:<22} {str(ins or '-'):<15} {status}")
        if not ins:
            missing.append(line)
        elif ins != ver:
            wrong_version.append((name, ver, ins))

    print()
    print(f"Total required: {len(reqs)}")
    print(f"Installed:      {len(reqs) - len(missing)}")
    print(f"Missing:        {len(missing)}")
    print(f"Wrong version:  {len(wrong_version)}")

    if missing:
        print("\nMissing packages to install:")
        for m in missing:
            print(f"  {m}")

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
