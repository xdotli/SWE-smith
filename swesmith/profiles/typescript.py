"""TypeScript repository profiles."""

import re
from dataclasses import dataclass
from swebench.harness.constants import TestStatus
from swesmith.profiles.base import RepoProfile
from swesmith.profiles.javascript import parse_log_jest, parse_log_vitest


@dataclass
class TypeScriptProfile(RepoProfile):
    """Base class for TypeScript repos using pnpm."""
    pass


def default_typescript_dockerfile(
    mirror_name: str,
    commit: str,
    node_version: str = "20",
    package_manager: str = "pnpm"
) -> str:
    """Generate default Dockerfile for TypeScript repos."""
    pm_install_cmd = {
        "pnpm": "RUN npm install -g pnpm",
        "npm": "",
        "yarn": "RUN npm install -g yarn"
    }.get(package_manager, "RUN npm install -g pnpm")

    install_cmd = f"{package_manager} install"

    return f"""FROM node:{node_version}-bullseye
RUN apt update && apt install -y git
{pm_install_cmd}
RUN git clone https://github.com/{mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {commit}
RUN {install_cmd}
"""


@dataclass
class TjCommanderJs395cf714(TypeScriptProfile):
    owner: str = "tj"
    repo: str = "commander.js"
    commit: str = "395cf714"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class ExcalidrawExcalidraw8d18078f(TypeScriptProfile):
    owner: str = "excalidraw"
    repo: str = "excalidraw"
    commit: str = "8d18078f"
    test_cmd: str = "pnpm test -- --run"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


@dataclass
class PayloadcmsPayload053256d5(TypeScriptProfile):
    owner: str = "payloadcms"
    repo: str = "payload"
    commit: str = "053256d5"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800  # 30 min for e2e tests
    timeout_ref: int = 3600  # 1 hour for full suite

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class StrapiStrapiMain(TypeScriptProfile):
    owner: str = "strapi"
    repo: str = "strapi"
    commit: str = "main"
    test_cmd: str = "pnpm test -- --run"
    arch: str = "x86_64"  # Force x86_64 since image was built for that platform

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


# JavaScript libraries with good test coverage
@dataclass
class MarkedjsMarkedDbf29d91(TypeScriptProfile):
    """Markdown parser with excellent test coverage."""
    owner: str = "markedjs"
    repo: str = "marked"
    commit: str = "dbf29d91"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class IamkunDayjsC8a26460(TypeScriptProfile):
    """Date library with extensive tests."""
    owner: str = "iamkun"
    repo: str = "dayjs"
    commit: str = "c8a26460"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class AxiosAxiosEf36347f(TypeScriptProfile):
    """HTTP client with comprehensive tests."""
    owner: str = "axios"
    repo: str = "axios"
    commit: str = "ef36347f"
    test_cmd: str = "npm test"
    arch: str = "x86_64"
    pltf: str = "linux/x86_64"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class DateFnsDateFns(TypeScriptProfile):
    """date-fns - Modern JavaScript date utility library with comprehensive tests."""
    owner: str = "date-fns"
    repo: str = "date-fns"
    commit: str = "main"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class LodashLodash(TypeScriptProfile):
    """Lodash - JavaScript utility library with extensive test coverage."""
    owner: str = "lodash"
    repo: str = "lodash"
    commit: str = "main"
    test_cmd: str = "npm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN npm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class ColinhacksZodMain(TypeScriptProfile):
    """Zod - TypeScript schema validation with excellent test coverage."""
    owner: str = "colinhacks"
    repo: str = "zod"
    commit: str = "main"
    test_cmd: str = "pnpm test"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


# Register all TypeScript profiles with the global registry
from swesmith.profiles.base import registry

for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, TypeScriptProfile)
        and obj.__name__ != "TypeScriptProfile"
    ):
        registry.register_profile(obj)
