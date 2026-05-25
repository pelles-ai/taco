#!/usr/bin/env python3
"""
gen-sdk-reference.py — auto-generate the TACO SDK Reference docs.

Walks the curated public API surface of the `taco` package, introspects
each symbol with `inspect`, and emits one MDX file per group at
website/docs/sdk-reference/{slug}.md.

Run from the website/ directory after installing the SDK:

    cd ../sdk && pip install -e .[all]
    cd ../website && python scripts/gen-sdk-reference.py

The generated files carry a "this file is generated" banner. Edit this
script (or the source docstrings/signatures) and re-run; do not edit
the generated MDX by hand.
"""

from __future__ import annotations

import inspect
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ----------------------------------------------------------------------
# Config — curated grouping of the public API
# ----------------------------------------------------------------------

REPO_BLOB = "https://github.com/pelles-ai/taco/blob/main/sdk"


@dataclass
class SymbolSpec:
    name: str
    # "class": render a full class page (constructor + methods)
    # "function": render a function entry
    # "constant": render a constant entry (value + type)
    # "alias": render a short "see ..." entry
    kind: str = "class"
    alias_target: str | None = None


@dataclass
class GroupSpec:
    slug: str
    label: str
    description: str
    symbols: list[SymbolSpec]
    sidebar_position: int


GROUPS: list[GroupSpec] = [
    GroupSpec(
        slug="agent-cards",
        label="Agent Cards",
        description=(
            "Construct, validate, and serve the Agent Card a TACO agent "
            "advertises at `/.well-known/agent-card.json`."
        ),
        sidebar_position=1,
        symbols=[
            SymbolSpec("ConstructionAgentCard", "class"),
            SymbolSpec("ConstructionSkill", "class"),
            SymbolSpec("AgentCard", "class"),
            SymbolSpec("AgentSkill", "class"),
            SymbolSpec("AgentCapabilities", "class"),
            SymbolSpec("AgentExtension", "class"),
            SymbolSpec("AgentConstructionExt", "class"),
            SymbolSpec("SkillConstructionExt", "class"),
            SymbolSpec("get_construction_ext", "function"),
            SymbolSpec("get_skill_construction_ext", "function"),
            SymbolSpec("apply_construction_extension_declaration", "function"),
            SymbolSpec("X_CONSTRUCTION_EXTENSION_URI", "constant"),
        ],
    ),
    GroupSpec(
        slug="server",
        label="Server",
        description=(
            "Run a TACO-compatible A2A server. Register typed handlers per "
            "task type, optionally serve the live Monitor UI, and persist tasks."
        ),
        sidebar_position=2,
        symbols=[
            SymbolSpec("A2AServer", "class"),
        ],
    ),
    GroupSpec(
        slug="client",
        label="Client",
        description=(
            "Call another TACO agent over A2A. Async HTTP, JSON-RPC and "
            "streaming, push notification config management, and the standard "
            "`A2A-Version` headers."
        ),
        sidebar_position=3,
        symbols=[
            SymbolSpec("TacoClient", "class"),
            SymbolSpec("TacoClientError", "class"),
            SymbolSpec("RpcError", "class"),
        ],
    ),
    GroupSpec(
        slug="agent",
        label="Agent (server + client pool)",
        description=(
            "`TacoAgent` bundles `A2AServer` with a pool of `TacoClient`s, for "
            "agents that both receive and call other agents."
        ),
        sidebar_position=4,
        symbols=[
            SymbolSpec("TacoAgent", "class"),
        ],
    ),
    GroupSpec(
        slug="registry",
        label="Registry",
        description=(
            "In-memory discovery layer with optional JSON persistence. Find "
            "agents by trade, task type, CSI division, or trust tier."
        ),
        sidebar_position=5,
        symbols=[
            SymbolSpec("AgentRegistry", "class"),
        ],
    ),
    GroupSpec(
        slug="tasks-and-messages",
        label="Tasks & Messages",
        description=(
            "The core A2A protocol types: tasks, their lifecycle states, "
            "messages, parts, and the event types streamed during a task."
        ),
        sidebar_position=6,
        symbols=[
            SymbolSpec("Task", "class"),
            SymbolSpec("TaskStatus", "class"),
            SymbolSpec("TaskState", "class"),
            SymbolSpec("Message", "class"),
            SymbolSpec("Role", "class"),
            SymbolSpec("Part", "class"),
            SymbolSpec("TextPart", "class"),
            SymbolSpec("DataPart", "class"),
            SymbolSpec("FilePart", "class"),
            SymbolSpec("Artifact", "class"),
        ],
    ),
    GroupSpec(
        slug="helpers",
        label="Helpers",
        description=(
            "Convenience constructors and extractors for messages, parts, and "
            "artifacts. Use these instead of constructing A2A types directly."
        ),
        sidebar_position=7,
        symbols=[
            SymbolSpec("make_message", "function"),
            SymbolSpec("make_text_part", "function"),
            SymbolSpec("make_data_part", "function"),
            SymbolSpec("make_artifact", "function"),
            SymbolSpec("extract_text", "function"),
            SymbolSpec("extract_structured_data", "function"),
            SymbolSpec("get_text_parts", "function"),
            SymbolSpec("get_data_parts", "function"),
            SymbolSpec("get_file_parts", "function"),
            SymbolSpec("get_message_text", "function"),
            SymbolSpec("new_text_artifact", "function"),
            SymbolSpec("new_data_artifact", "function"),
            SymbolSpec("new_agent_text_message", "function"),
            SymbolSpec("new_agent_parts_message", "function"),
        ],
    ),
    GroupSpec(
        slug="persistence",
        label="Persistence",
        description=(
            "`TaskStore` interface and the bundled `JsonFileTaskStore` for "
            "single-process agents that need on-disk task persistence."
        ),
        sidebar_position=8,
        symbols=[
            SymbolSpec("TaskStore", "class"),
        ],
    ),
    GroupSpec(
        slug="push-notifications",
        label="Push Notifications",
        description=(
            "Multi-subscriber push notification configs per task. Used by "
            "`TacoClient.create_push_config()` and friends."
        ),
        sidebar_position=9,
        symbols=[
            SymbolSpec("PushNotificationConfig", "class"),
            SymbolSpec("PushNotificationAuthenticationInfo", "class"),
            SymbolSpec("TaskPushNotificationConfig", "class"),
        ],
    ),
    GroupSpec(
        slug="enums",
        label="Enums",
        description=(
            "Construction-domain enumerations used across the schemas, agent "
            "cards, and task types."
        ),
        sidebar_position=10,
        symbols=[
            SymbolSpec("Trade", "class"),
            SymbolSpec("ProjectType", "class"),
            SymbolSpec("Integration", "class"),
            SymbolSpec("Certification", "class"),
            SymbolSpec("Availability", "class"),
            SymbolSpec("BOMUnit", "class"),
            SymbolSpec("FlagSeverity", "class"),
            SymbolSpec("RFICategory", "class"),
            SymbolSpec("RFIPriority", "class"),
        ],
    ),
]

# Symbols that already have a dedicated explorer page under /docs/schemas/
# — we link to those instead of generating a reference page here.
SCHEMA_SYMBOL_TO_DOC = {
    "BOMV1": "/docs/schemas/bom-v1",
    "RFIV1": "/docs/schemas/rfi-v1",
    "EstimateV1": "/docs/schemas/estimate-v1",
    "QuoteV1": "/docs/schemas/quote-v1",
    "ScheduleV1": "/docs/schemas/schedule-v1",
    "ChangeOrderV1": "/docs/schemas/change-order-v1",
}


# ----------------------------------------------------------------------
# Introspection helpers
# ----------------------------------------------------------------------


def _safe_signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "()"


def _format_signature(name: str, sig_str: str, *, max_inline: int = 90) -> str:
    """Pretty-print a signature: one line when short, one-arg-per-line otherwise."""
    full = f"{name}{sig_str}"
    if len(full) <= max_inline:
        return full
    # Best-effort multiline split
    if not (sig_str.startswith("(") and sig_str.endswith(")")):
        return full
    inner = sig_str[1:-1]
    # naive comma split that respects bracket depth
    parts: list[str] = []
    depth = 0
    cur = []
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    if not parts:
        return full
    body = ",\n    ".join(parts)
    return f"{name}(\n    {body},\n)"


def _github_link(obj: Any) -> str | None:
    """Build a github.com/.../sdk/taco/foo.py#L42 link from a live object."""
    try:
        fp = inspect.getsourcefile(obj)
        line = inspect.getsourcelines(obj)[1]
    except (TypeError, OSError):
        return None
    if not fp:
        return None
    parts = Path(fp).parts
    # Anchor on the "sdk/taco/" segment — it's unambiguous even though the
    # outer repo root is also called "taco".
    for i in range(len(parts) - 1):
        if parts[i] == "sdk" and parts[i + 1] == "taco":
            rel = "/".join(parts[i + 1:])  # drop the "sdk" prefix; REPO_BLOB already includes it
            return f"{REPO_BLOB}/{rel}#L{line}"
    return None


def _public_methods(cls: type) -> list[tuple[str, Callable]]:
    out: list[tuple[str, Callable]] = []
    for name, member in inspect.getmembers(cls):
        if name.startswith("_"):
            continue
        if inspect.isfunction(member) or inspect.ismethod(member):
            # Skip methods inherited from object/BaseModel that aren't user-facing
            if name in {
                "model_config", "model_fields", "model_extra", "model_dump",
                "model_dump_json", "model_validate", "model_validate_json",
                "model_copy", "model_construct", "model_json_schema",
                "model_parametrized_name", "model_post_init", "model_rebuild",
                "model_validate_strings", "copy", "dict", "json",
                "schema", "schema_json", "update_forward_refs", "validate",
                "parse_obj", "parse_raw", "parse_file", "from_orm",
                "construct", "consume",
            }:
                continue
            out.append((name, member))
    return out


# ----------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------


def _slugify(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1-\2", s)
    return s.lower().replace("_", "-")


_BROKEN_MD_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((?:\.{1,2}/[^)]*\.mdx?(?:#[^)]*)?)\)"
)


def _render_docstring(doc: str | None) -> str:
    """Clean a docstring + neutralize links that would only resolve inside
    a third-party library's own docs (Pydantic, etc.). Such links point at
    relative .md files we don't have."""
    if not doc:
        return ""
    cleaned = inspect.cleandoc(doc)
    cleaned = _BROKEN_MD_LINK_RE.sub(r"\1", cleaned)
    return cleaned


def _render_constant(sym_name: str, value: Any) -> str:
    type_name = type(value).__name__
    if isinstance(value, str):
        v = f'"{value}"'
    elif isinstance(value, (int, float, bool)):
        v = repr(value)
    else:
        v = f"<{type_name}>"
    return (
        f"### `{sym_name}`\n\n"
        f"```python\n"
        f"{sym_name}: {type_name} = {v}\n"
        f"```\n"
    )


def _render_function_entry(sym_name: str, fn: Callable, *, level: int = 3) -> str:
    sig = _safe_signature(fn)
    pretty = _format_signature(sym_name, sig)
    doc = _render_docstring(inspect.getdoc(fn))
    gh = _github_link(fn)
    header = "#" * level
    source_line = f"\n[Source on GitHub]({gh})\n" if gh else ""
    return (
        f"{header} `{sym_name}()`\n"
        f"{source_line}\n"
        f"```python\n"
        f"{pretty}\n"
        f"```\n\n"
        f"{doc}\n"
    )


def _render_method(name: str, fn: Callable) -> str:
    is_async = inspect.iscoroutinefunction(fn)
    sig = _safe_signature(fn)
    prefix = "async def " if is_async else "def "
    pretty = _format_signature(f"{prefix}{name}", sig)
    doc = _render_docstring(inspect.getdoc(fn))
    return (
        f"### `{name}()`\n\n"
        f"```python\n"
        f"{pretty}\n"
        f"```\n\n"
        f"{doc or '*No docstring.*'}\n"
    )


def _render_typing_alias(sym_name: str, obj: Any) -> str:
    """For typing.Literal[...] / Union / TypeAlias values that aren't real classes."""
    repr_str = repr(obj).replace("typing.", "")
    return (
        f"## `{sym_name}`\n\n"
        f"*Type alias.*\n\n"
        f"```python\n"
        f"{sym_name} = {repr_str}\n"
        f"```\n"
    )


def _render_class(sym_name: str, cls: Any) -> str:
    """Full per-class section. Falls back to alias rendering for typing constructs."""
    if not inspect.isclass(cls):
        return _render_typing_alias(sym_name, cls)

    doc = _render_docstring(inspect.getdoc(cls))
    gh = _github_link(cls)
    source_line = f"\n[Source on GitHub]({gh})\n\n" if gh else ""

    try:
        ctor_sig = _safe_signature(cls)
        ctor_pretty = _format_signature(sym_name, ctor_sig)
        ctor_block = (
            f"#### Constructor\n\n"
            f"```python\n"
            f"{ctor_pretty}\n"
            f"```\n\n"
        )
    except Exception:
        ctor_block = ""

    methods = _public_methods(cls)
    if methods:
        method_blocks = "\n".join(_render_method(n, fn) for n, fn in methods)
        methods_section = f"#### Methods\n\n{method_blocks}\n"
    else:
        methods_section = ""

    bases_line = ""
    try:
        bases = [
            b.__name__ for b in cls.__bases__
            if getattr(b, "__module__", "") != "builtins"
            and getattr(b, "__name__", "object") != "object"
        ]
        if bases:
            bases_line = f"*Extends:* {', '.join(f'`{b}`' for b in bases)}\n\n"
    except AttributeError:
        pass

    return (
        f"## `{sym_name}`\n\n"
        f"{source_line}"
        f"{bases_line}"
        f"{doc or '*No class docstring.*'}\n\n"
        f"{ctor_block}"
        f"{methods_section}"
    )


def _render_group(spec: GroupSpec, taco_mod: Any) -> str:
    # YAML frontmatter — wrap description in double quotes and escape any
    # internal double-quote characters so backticks/colons/parens inside
    # the description don't confuse the parser.
    safe_desc = spec.description.replace('"', '\\"')
    safe_title = spec.label.replace('"', '\\"')
    parts = [
        f"---\n"
        f'title: "{safe_title}"\n'
        f'description: "{safe_desc}"\n'
        f"sidebar_position: {spec.sidebar_position}\n"
        f"---\n\n"
        f":::info Generated\n"
        f"This page is generated from the SDK source by "
        f"[`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).\n"
        f"Edit the source docstrings (or this script) and re-run; do not edit\n"
        f"this MDX by hand.\n"
        f":::\n\n"
        f"# {spec.label}\n\n"
        f"{spec.description}\n\n"
    ]

    for sym in spec.symbols:
        try:
            obj = getattr(taco_mod, sym.name)
        except AttributeError:
            print(f"  warning: {sym.name} not found in taco; skipping", file=sys.stderr)
            continue

        if sym.kind == "function":
            parts.append(_render_function_entry(sym.name, obj, level=2))
        elif sym.kind == "constant":
            parts.append(_render_constant(sym.name, obj))
        else:  # "class"
            parts.append(_render_class(sym.name, obj))
        parts.append("\n")

    return "".join(parts)


def _render_index(groups: list[GroupSpec]) -> str:
    rows = []
    for g in groups:
        first_symbols = ", ".join(f"`{s.name}`" for s in g.symbols[:3])
        if len(g.symbols) > 3:
            first_symbols += f" + {len(g.symbols) - 3} more"
        rows.append(f"| [{g.label}](./{g.slug}) | {first_symbols} |")
    rows_str = "\n".join(rows)

    schema_rows = "\n".join(
        f"| [`{name}`]({doc}) | TACO schema model — explore the typed structure interactively. |"
        for name, doc in SCHEMA_SYMBOL_TO_DOC.items()
    )

    return (
        f"---\n"
        f"title: SDK Reference\n"
        f"description: Per-symbol reference for the TACO Python SDK — auto-generated from source.\n"
        f"sidebar_position: 0\n"
        f"---\n\n"
        f":::info Generated\n"
        f"These pages are auto-generated from the SDK source by "
        f"[`website/scripts/gen-sdk-reference.py`](https://github.com/pelles-ai/taco/blob/main/website/scripts/gen-sdk-reference.py).\n"
        f":::\n\n"
        f"# SDK Reference\n\n"
        f"Every public class, function, and constant in `taco-agent`, "
        f"introspected directly from the source. For high-level usage examples, "
        f"see the [SDK Guide](../sdk) and the [Cookbook](../cookbook).\n\n"
        f"## Groups\n\n"
        f"| Group | Symbols |\n"
        f"|------|--------|\n"
        f"{rows_str}\n\n"
        f"## Schema models\n\n"
        f"Schema models have dedicated interactive pages with a live validator — "
        f"they are not duplicated here.\n\n"
        f"| Symbol | Page |\n"
        f"|------|------|\n"
        f"{schema_rows}\n\n"
        f"## Regenerating\n\n"
        f"```bash\n"
        f"cd sdk && pip install -e .[all]\n"
        f"cd ../website && python scripts/gen-sdk-reference.py\n"
        f"```\n"
    )


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> int:
    try:
        import taco
    except ImportError as exc:
        print(
            "ERROR: `taco` is not importable. Install the SDK first:\n"
            "  cd sdk && pip install -e .[all]\n"
            f"({exc})",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(__file__).resolve().parent.parent / "docs" / "sdk-reference"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Wipe previous output (except hand-edited files — we don't expect any)
    for existing in out_dir.glob("*.md"):
        existing.unlink()
    for existing in out_dir.glob("*.mdx"):
        existing.unlink()

    written = 0
    for g in GROUPS:
        content = _render_group(g, taco)
        path = out_dir / f"{g.slug}.md"
        path.write_text(content)
        written += 1
        print(f"  wrote {path.relative_to(out_dir.parent.parent)}")

    index_path = out_dir / "index.md"
    index_path.write_text(_render_index(GROUPS))
    written += 1
    print(f"  wrote {index_path.relative_to(out_dir.parent.parent)}")

    print(f"\nGenerated {written} files in {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
