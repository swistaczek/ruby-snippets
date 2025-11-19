# Ruby & Rails Patterns Collection

A curated collection of real-world Ruby and Rails patterns extracted from production codebases. This repository serves as a comprehensive knowledge base for Context7, providing developers with battle-tested patterns and best practices.

**Context7 Library:** `/swistaczek/ruby-snippets` | [View on Context7](https://context7.com/swistaczek/ruby-snippets)

## Purpose

This repository indexes production-ready code patterns from various Ruby/Rails projects, making them easily discoverable through Context7's AI-powered documentation search. Each pattern includes:

- Clear description of the problem it solves
- Complete, runnable code examples
- Links to official Rails documentation
- Links to original source files
- Context about when to use the pattern

## Included Projects

### [Once Campfire](./once-campfire/)
Basecamp's open-source chat application built with Rails 7 and Hotwire. Contains 90+ patterns covering:
- Modern ActiveRecord patterns (concerns, STI, associations)
- Hotwire integration (Turbo Streams, Stimulus controllers)
- Real-time features with ActionCable
- SQLite FTS5 full-text search
- Authentication and authorization patterns

_More projects will be added over time_

## For Context7

This repository is optimized for Context7 indexing:
- All documentation in Markdown format for optimal parsing
- Consistent code fence formatting with language identifiers
- Descriptive headings for pattern organization
- Source attribution and external documentation links
- Unified `context7.json` configuration at root

## Adding New Projects

To add a new project to this collection:

1. Create a new directory with the project name (e.g., `my-rails-app/`)
2. Add a `README.md` with project context and overview
3. Create documentation files in Markdown format following the existing pattern structure:
   ```markdown
   ## Category Name

   ### Pattern Name
   Description of what the pattern does and when to use it.

   **Rails Docs:** [Link if applicable]
   **Source:** [Link to original file]

   ```ruby
   # code example
   ```
   ```
4. Update this root README to list the new project
5. Commit and push to trigger Context7 re-indexing

## Structure

```
ruby-snippets/
├── context7.json           # Context7 configuration
├── README.md              # This file
├── once-campfire/         # Campfire patterns
│   ├── README.md
│   └── rails-patterns.md
└── [future-projects]/     # Additional projects
```

## Usage with Context7

Query these patterns using the library ID `/swistaczek/ruby-snippets`:

```javascript
// Use with Context7 MCP or Claude Code
// "Show me Rails CurrentAttributes patterns from /swistaczek/ruby-snippets"
// "How does Basecamp implement real-time features?"
// "Examples of SQLite full-text search in Rails"
```

## Contributing

This is a curated collection. Patterns are extracted from open-source codebases and formatted for educational purposes. Each pattern includes attribution and links to the original source.

## License

Documentation and pattern explanations are original content. Code examples are attributed to their respective projects and maintain their original licenses.
