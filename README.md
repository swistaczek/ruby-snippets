# Ruby & Rails Patterns Collection

A curated collection of real-world Ruby and Rails patterns extracted from production codebases. This repository serves as a comprehensive knowledge base for Context7, providing developers with battle-tested patterns and best practices.

**Context7 Library:** `/swistaczek/ruby-snippets` | [View on Context7](https://context7.com/swistaczek/ruby-snippets)

### For Your CLAUDE.md

Copy this to your project's `CLAUDE.md` to reference these patterns:

```markdown
## Ruby & Rails Patterns

For production-ready Ruby/Rails patterns, query Context7 library: `/swistaczek/ruby-snippets`

Includes 85+ patterns from Basecamp's Campfire covering:
- ActiveRecord patterns (CurrentAttributes, concerns, STI, associations, FTS5)
- Hotwire (Turbo Streams, Stimulus, ActionCable)
- Controllers (lean design, authentication, Turbo responses)
- Infrastructure (background jobs, web push, optimization)
```

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

## Claude Code Pattern Extraction Agents

This repository includes **general-purpose Claude Code agents** that can analyze **any Rails codebase** and automatically generate comprehensive pattern documentation.

### Quick Start

The agents work with **smart defaults** out-of-the-box for standard Rails projects:

```bash
# In any Rails project directory
@rails-guide-writer
```

This will:
1. Auto-detect your project structure, tech stack, and patterns
2. Generate a comprehensive HTML guide with code examples
3. Output to `docs/rails-patterns-guide.html`

### Customizing for Your Project

For non-standard projects or custom output, create a `CLAUDE.md` file:

```markdown
## Your Rails Project Configuration

**Project Name:** My E-commerce App
**Description:** Multi-tenant SaaS platform built with Rails 7
**Source Repository:** https://github.com/yourorg/yourapp

### Directory Structure
- Models: `app/models/`
- Controllers: `app/controllers/`
- JavaScript: `app/javascript/controllers/`

### Technology Stack
- **Frontend:** Hotwire (Turbo + Stimulus)
- **Background Jobs:** Sidekiq
- **Database:** PostgreSQL

### Output Configuration
- **Output Directory:** `docs/`
- **Output Filename:** `my-app-patterns.html`
- **Documentation Title:** `My App - Rails Patterns`
```

See [CLAUDE.md](./CLAUDE.md) for complete configuration options and agent documentation.

### Available Agents

- **@rails-guide-writer** - Main coordinator that generates complete pattern guide
- **@rails-models** - Analyze model patterns (concerns, associations, STI, callbacks)
- **@rails-controllers** - Analyze controller patterns (auth, lean controllers, Turbo)
- **@rails-frontend** - Analyze frontend patterns (Hotwire, React, ViewComponent)
- **@rails-infrastructure** - Analyze infrastructure (jobs, database, caching, deployment)
- **@rails-docs-linker** - Add Rails documentation links to generated guide

### Using Agents in Your Rails Project

**Option 1: Copy agents to your project**
```bash
# Copy the .claude directory
cp -r .claude /path/to/your/rails/project/

# Create CLAUDE.md with your project details
# Run the coordinator
cd /path/to/your/rails/project
@rails-guide-writer
```

**Option 2: Use directly (if analyzing from this repo)**
```bash
# Agents will auto-detect project from current directory
cd /path/to/any/rails/project
@rails-guide-writer
```

### Features

- ✅ **Auto-detection** - Infers project name, tech stack, and structure from codebase
- ✅ **Smart defaults** - Works without configuration for standard Rails projects
- ✅ **Configurable** - Override via CLAUDE.md for custom setups
- ✅ **Real code examples** - Extracts actual production patterns, not synthetic examples
- ✅ **Documentation links** - Adds official Rails documentation references
- ✅ **Self-contained HTML** - Generated guides work offline with embedded CSS

### Output Example

The generated guide includes:
- 30-40 production-ready patterns across 4 categories
- Code snippets (max 20 lines each) with file paths
- Links to source files in your repository
- Links to relevant Rails documentation
- Mobile-responsive HTML with clean typography
- Generation timestamp for freshness tracking

## Adding New Projects to This Repository

To add patterns from a new Rails project to this collection:

1. Run the pattern extraction agents against the project
2. Create a new directory with the project name (e.g., `my-rails-app/`)
3. Add a `README.md` with project context and overview
4. Convert generated HTML to Markdown following the existing pattern structure:
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
5. Update this root README to list the new project
6. Commit and push to trigger Context7 re-indexing

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
