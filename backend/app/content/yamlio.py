"""YAML loading with YAML 1.2 booleans.

PyYAML follows YAML 1.1, where unquoted ``yes``/``no``/``on``/``off`` become booleans. Our
content uses ``yes``/``no`` as tristate fact values, so only ``true``/``false`` may be booleans.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


class ContentLoader(yaml.SafeLoader):
    pass


# Drop the YAML 1.1 bool resolver and install a YAML 1.2 one.
ContentLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
ContentLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.load(f, Loader=ContentLoader)  # noqa: S506 - SafeLoader subclass


def loads_yaml(text: str) -> Any:
    return yaml.load(text, Loader=ContentLoader)  # noqa: S506 - SafeLoader subclass
