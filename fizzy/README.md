# Fizzy

Kanban tracking tool for issues and ideas by [37signals](https://37signals.com).

## Source

- **Repository:** https://github.com/basecamp/fizzy
- **License:** O'Saasy License
- **Rails Version:** Rails main branch (bleeding edge)

## Technology Stack

- **Frontend:** Hotwire (Turbo + Stimulus), Importmap, Propshaft
- **Background Jobs:** Solid Queue (database-backed)
- **Caching:** Solid Cache
- **Real-time:** Solid Cable (ActionCable)
- **Database:** SQLite + MySQL support
- **Deployment:** Kamal + Docker

## Key Features

- **Multi-tenancy:** URL path-based account scoping
- **Authentication:** Passwordless magic link auth
- **Kanban boards:** Cards, columns, drag-and-drop
- **Entropy system:** Auto-postponement of stale cards
- **Full-text search:** Sharded SQLite FTS5
- **Push notifications:** Web Push with VAPID

## Patterns

See [rails-patterns.md](./rails-patterns.md) for 40 extracted patterns covering:
- Models (10 patterns)
- Controllers (10 patterns)
- Frontend/Hotwire (10 patterns)
- Infrastructure (10 patterns)

## Extraction Date

December 2025
