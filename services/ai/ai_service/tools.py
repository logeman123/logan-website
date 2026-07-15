import logging

from rpc.content_rpc.client import ContentSource
from rpc.exceptions import RPCError

logger = logging.getLogger(__name__)

TOOL_SPECS = [
    {
        "name": "list_projects",
        "description": "List Logan's projects. Optional boolean 'featured' filter.",
        "input_schema": {
            "type": "object",
            "properties": {"featured": {"type": "boolean"}},
        },
    },
    {
        "name": "get_project",
        "description": "Get one of Logan's projects by its slug.",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
]


def execute_tool(content: ContentSource, name: str, args: dict) -> str:
    try:
        if name == "list_projects":
            rows = content.list_projects(featured=args.get("featured"))
            return "\n".join(f"{p.slug}: {p.title} — {p.blurb}" for p in rows) or "No projects found."
        if name == "get_project":
            slug = args.get("slug")
            if not slug:
                return "(tool error: missing required argument 'slug')"
            p = content.get_project(slug)
            return (f"{p.title} ({p.year})\nRole: {p.role}\nTech: {', '.join(p.tech)}\n"
                    f"{p.blurb}\nHighlights: {'; '.join(p.highlights)}")
        return f"Unknown tool: {name}"
    except RPCError as exc:
        logger.warning("content tool %s failed: %s", name, exc)
        return f"(tool error fetching content: {exc})"
