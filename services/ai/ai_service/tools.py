"""The tools the model may call, plus the code that actually runs them.

This module is where "the LLM's tool surface" meets "the content microservice". It has
two halves:

1. ``TOOL_SPECS`` — JSON-Schema descriptions of the callable tools, in exactly the shape
   the Anthropic Messages API expects for its ``tools`` parameter. These are advertised to
   the model so it knows what it can call and with what arguments.

2. ``execute_tool`` — the dispatcher that, when the model requests a tool, calls the REAL
   content service (over RPC) to fetch grounding data and returns it as a plain string the
   model can read back.

The elegant part of the whole system: the AI tool names here (``list_projects`` /
``get_project``) are the SAME operations the content service exposes as RPC tools. So the
model's "tool surface" and the service's "RPC surface" are one and the same — grounding
the LLM is just a normal service-to-service call. And because ``execute_tool`` receives a
``ContentSource`` (a Protocol), it never knows or cares whether it's hitting a real content
service over HTTP or an in-process fake in a test.
"""

import logging

# ContentSource is a *Protocol* (structural interface) describing the content operations we
# depend on. We import the type only for the annotation / dependency-inversion seam; the
# concrete client (ContentRpcClient) is injected by deps.py, never constructed here.
from rpc.content_rpc.client import ContentSource
# The base class of the shared RPC error hierarchy. Catching it below is how this service
# degrades gracefully when the content service is slow, down, or returns an error.
from rpc.exceptions import RPCError

logger = logging.getLogger(__name__)

# The tool catalog advertised to the model. Each entry is a JSON-Schema-shaped dict matching
# Anthropic's ``tools`` format: a ``name`` (used to dispatch in execute_tool), a natural-
# language ``description`` the model reads to decide *when* to call it, and an
# ``input_schema`` constraining the arguments. Keep names in sync with execute_tool's branches.
TOOL_SPECS = [
    {
        "name": "list_projects",
        "description": "List Logan's projects. Optional boolean 'featured' filter.",
        "input_schema": {
            "type": "object",
            # No "required" list => the model may call this with no arguments at all.
            "properties": {"featured": {"type": "boolean"}},
        },
    },
    {
        "name": "get_project",
        "description": "Get one of Logan's projects by its slug.",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            # slug is mandatory here; we still defensively re-check it in execute_tool
            # because a model can violate its own schema.
            "required": ["slug"],
        },
    },
]


def execute_tool(content: ContentSource, name: str, args: dict) -> str:
    """Run the tool the model asked for and return a human/model-readable string result.

    Called once per requested tool by the agentic loop in chat.py. ``content`` is injected
    (dependency inversion) so this function is agnostic to transport; ``name``/``args`` come
    straight from the model's ToolUse block.

    Design choice: this ALWAYS returns a string and NEVER raises. Whatever comes back —
    real data, an "unknown tool" note, or a caught error message — is fed to the model as a
    tool_result. That's deliberate: a failed tool call becomes information the model can
    reason about and recover from, rather than an exception that crashes the request.
    """
    try:
        if name == "list_projects":
            # Cross-service call: this is the ai -> content RPC hop that grounds the answer.
            # args.get("featured") is None when the model omitted the optional filter.
            rows = content.list_projects(featured=args.get("featured"))
            # Flatten typed Project rows into one line each; the ``or`` supplies a friendly
            # message (rather than an empty string) when there are no matching projects.
            return "\n".join(f"{p.slug}: {p.title} — {p.blurb}" for p in rows) or "No projects found."
        if name == "get_project":
            slug = args.get("slug")
            # Defensive guard: the schema marks slug required, but models can still omit it.
            # Return a readable error string so the model can correct itself next turn.
            if not slug:
                return "(tool error: missing required argument 'slug')"
            # The other ai -> content RPC hop: fetch one full project by slug.
            p = content.get_project(slug)
            # Render the rich Project contract into a compact, model-friendly text block.
            return (f"{p.title} ({p.year})\nRole: {p.role}\nTech: {', '.join(p.tech)}\n"
                    f"{p.blurb}\nHighlights: {'; '.join(p.highlights)}")
        # The model named a tool we don't implement — report it as data, not a crash.
        return f"Unknown tool: {name}"
    except RPCError as exc:
        # GRACEFUL DEGRADATION: any RPC failure (content unreachable, 4xx/5xx, transport
        # error wrapped as ServiceError by the ServiceClient) is caught here. We log it for
        # operators and hand the model a note instead of propagating, so /chat never 500s
        # just because content had a hiccup.
        logger.warning("content tool %s failed: %s", name, exc)
        return f"(tool error fetching content: {exc})"
