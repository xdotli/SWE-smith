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


@dataclass
class MedusajsMedusa56ed9cf9(TypeScriptProfile):
    """Medusa - E-commerce platform with comprehensive test coverage."""
    owner: str = "medusajs"
    repo: str = "medusa"
    commit: str = "56ed9cf9"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800  # 30 min for integration tests
    timeout_ref: int = 3600  # 1 hour for full suite

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class AppsmithorgAppsmith7046aeb3(TypeScriptProfile):
    """Appsmith - Open-source internal tool builder with comprehensive tests."""
    owner: str = "appsmithorg"
    repo: str = "appsmith"
    commit: str = "7046aeb3"
    test_cmd: str = "cd app/client && pnpm test -- --run"
    timeout: int = 1800  # 30 min for large test suite
    timeout_ref: int = 3600  # 1 hour for full suite
    arch: str = "x86_64"

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm yarn
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
WORKDIR /testbed/app/client
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class HoppscotchHoppscotchMain(TypeScriptProfile):
    """Hoppscotch - Open source API development ecosystem."""
    owner: str = "hoppscotch"
    repo: str = "hoppscotch"
    commit: str = "main"
    test_cmd: str = "pnpm test"
    timeout: int = 1200  # 20 min for tests

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git postgresql-client
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class NocodbNocodbDevelop(TypeScriptProfile):
    """NocoDB - Open source Airtable alternative."""
    owner: str = "nocodb"
    repo: str = "nocodb"
    commit: str = "develop"
    test_cmd: str = "cd packages/nocodb && pnpm test"
    timeout: int = 1800  # 30 min for tests

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm lerna
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class CalcomCalComMain(TypeScriptProfile):
    """Cal.com - Open-source scheduling platform with good test coverage."""
    owner: str = "calcom"
    repo: str = "cal.com"
    commit: str = "main"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class TwentyhqTwentyMain(TypeScriptProfile):
    """Twenty - Modern CRM with good test coverage."""
    owner: str = "twentyhq"
    repo: str = "twenty"
    commit: str = "main"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

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
class PostHogPosthogMain(TypeScriptProfile):
    """PostHog - Product analytics platform with test coverage."""
    owner: str = "PostHog"
    repo: str = "posthog"
    commit: str = "main"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

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
class DubincDubMain(TypeScriptProfile):
    """Dub - Link management platform with test coverage."""
    owner: str = "dubinc"
    repo: str = "dub"
    commit: str = "main"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_jest(log)


@dataclass
class TinacmsTinacmsAc595220(TypeScriptProfile):
    """TinaCMS - Git-backed CMS with 141+ Vitest tests."""
    owner: str = "tinacms"
    repo: str = "tinacms"
    commit: str = "ac595220"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


@dataclass
class SanityIoSanity615e6c01(TypeScriptProfile):
    """Sanity - Content platform with GROQ query tests (447+ Vitest + Playwright tests)."""
    owner: str = "sanity-io"
    repo: str = "sanity"
    commit: str = "615e6c01"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800  # 30 min for comprehensive test suite
    timeout_ref: int = 3600  # 1 hour for full suite

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


@dataclass
class KeystonejsKeystone052f5b1b(TypeScriptProfile):
    """Keystone - Headless CMS with document editor and 142+ Vitest tests."""
    owner: str = "keystonejs"
    repo: str = "keystone"
    commit: str = "052f5b1bfdc76868125722ea385c59ffae7eb000"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test"
    timeout: int = 1800
    timeout_ref: int = 3600

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
        return parse_log_vitest(log)


@dataclass
class TriggerdotdevTriggerd1c3bfb9(TypeScriptProfile):
    """Trigger.dev - Background jobs platform with comprehensive Vitest tests."""
    owner: str = "triggerdotdev"
    repo: str = "trigger.dev"
    commit: str = "d1c3bfb9c98a94269654550de65c809012dc2001"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm test -- --run"
    timeout: int = 1800  # 30 min for monorepo tests
    timeout_ref: int = 3600  # 1 hour for full suite

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm turbo
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout {self.commit}
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


@dataclass
class DirectusDirectus447c91d0(TypeScriptProfile):
    """Directus - Headless CMS with 582+ Vitest tests for API logic."""
    owner: str = "directus"
    repo: str = "directus"
    commit: str = "447c91d0"
    test_cmd: str = "NODE_OPTIONS='--max-old-space-size=8192' pnpm --recursive --filter '!tests-blackbox' test"
    timeout: int = 1800  # 30 min for comprehensive test suite
    timeout_ref: int = 3600  # 1 hour for full suite

    @property
    def dockerfile(self):
        return f"""FROM node:20-bullseye
RUN apt update && apt install -y git
RUN npm install -g pnpm
RUN git clone https://github.com/{self.mirror_name} /testbed
WORKDIR /testbed
RUN git checkout main
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN pnpm install
"""

    def log_parser(self, log: str):
        return parse_log_vitest(log)


# Register all TypeScript profiles with the global registry
from swesmith.profiles.base import registry

for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, TypeScriptProfile)
        and obj.__name__ != "TypeScriptProfile"
    ):
        registry.register_profile(obj)
