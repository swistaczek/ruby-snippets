# Once Campfire - Rails Patterns

Code patterns extracted from [Once Campfire](https://github.com/basecamp/once-campfire), Basecamp's open-source chat application built with Rails 7 and Hotwire.

## About

Once Campfire is a production real-time chat app showcasing modern Rails patterns:
- Rails 7+ with Hotwire (Turbo + Stimulus)
- ActionCable for real-time messaging
- SQLite with FTS5 full-text search
- ActionText and ActiveStorage
- Minimal dependencies, pragmatic architecture

## Contents

### [rails-patterns.md](./rails-patterns.md)

**85 production-ready patterns** across four categories:

- **Models** (26) - Current Attributes, concerns, STI, associations, FTS5 search, ActionText mentions
- **Controllers** (16) - Lean design, authentication, authorization, Turbo Stream responses
- **Frontend** (26) - Turbo Streams, Stimulus controllers, ActionCable integration
- **Infrastructure** (17) - Background jobs, web push, database optimization

Each pattern includes description, Rails docs link, source link, and complete code example.

## Source

All patterns from: https://github.com/basecamp/once-campfire

**Credits:** Basecamp (37signals) | MIT License
