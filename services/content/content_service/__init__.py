"""content_service — the data-owning microservice of the monorepo.

This package IS one of the three FastAPI microservices in the system:

    web (BFF, :8000)  ->  content (:8001)  ->  data/projects/*.md
                      \\-> ai      (:8002)  --(RPC)--> content

`content` is the ONLY service that owns portfolio/project data. Everyone else
(the `web` BFF that renders pages, and the `ai` chat service that grounds its
answers) reaches this data exclusively over HTTP+JSON RPC — never by importing
these modules or touching the Markdown files directly. That boundary is the
whole point of splitting the app into services: `content` can change how it
stores projects (Markdown today, a database tomorrow) without any other service
noticing, as long as the RPC contracts in `rpc/content_rpc` stay stable.

An empty ``__init__.py`` would be enough to mark this directory as an importable
Python package; this docstring adds no runtime behavior and merely documents the
package's role. The interesting pieces live in the sibling modules:

  * ``config.py``      — typed settings (token, data directory) from env/.env
  * ``repository.py``  — the ContentRepository Protocol + two implementations
                         (Markdown-file-backed for prod, in-memory for tests)
  * ``tools.py``       — wraps a repository as RPC tools (list_projects/get_project)
  * ``deps.py``        — the single place concrete implementations are chosen (DI)
  * ``main.py``        — assembles the FastAPI app and mounts the shared RPC router
"""
