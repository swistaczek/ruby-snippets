# Ruby & Rails Patterns Collection

## Project Overview

This repository curates production-ready Ruby and Rails patterns extracted from real-world open-source codebases. It serves as a comprehensive knowledge base for Context7, making battle-tested patterns easily discoverable through AI-powered search.

**Project Type:** Pattern collection repository
**Primary Language:** Ruby (Rails)
**Context7 Library:** `/swistaczek/ruby-snippets`
**Repository:** https://github.com/swistaczek/ruby-snippets

## Project Structure

```
ruby-snippets/
├── .claude/
│   └── agents/              # Pattern extraction agents
│       ├── rails-models.md
│       ├── rails-controllers.md
│       ├── rails-frontend.md
│       ├── rails-infrastructure.md
│       ├── rails-guide-writer.md
│       └── rails-docs-linker.md
├── once-campfire/          # Basecamp Campfire patterns (85 patterns)
│   ├── rails-patterns.md
│   └── README.md
├── fizzy/                  # 37signals Fizzy patterns (40 patterns)
│   ├── rails-patterns.md
│   └── README.md
├── docs/                   # GitHub Pages (interactive browser)
└── context7.json          # Context7 configuration
```

## Indexed Projects

### Once Campfire (Basecamp)
- **Path:** `once-campfire/`
- **Technology:** Rails 7 + Hotwire (Turbo + Stimulus)
- **Patterns:** 85 covering models, controllers, frontend, infrastructure
- **Source:** https://github.com/basecamp/once-campfire

### Fizzy (37signals)
- **Path:** `fizzy/`
- **Technology:** Rails main branch + Hotwire + Solid Stack (Queue/Cache/Cable)
- **Patterns:** 40 covering models, controllers, frontend, infrastructure
- **Source:** https://github.com/basecamp/fizzy

## Pattern Extraction Agents

This project includes specialized Claude Code agents that analyze Rails codebases and generate comprehensive pattern documentation.

### Agent Configuration

When using these agents with your own Rails project, customize this section:

```markdown
## Your Rails Project Configuration

**Project Name:** [Your Project Name]
**Description:** [Brief description of your Rails app]
**Source Repository:** [GitHub/GitLab URL]
**Rails Version:** [e.g., 7.1+]

### Directory Structure
- Models: `app/models/`
- Controllers: `app/controllers/`
- Views: `app/views/`
- JavaScript: `app/javascript/controllers/`
- Channels: `app/channels/`
- Jobs: `app/jobs/`

### Technology Stack
- **Frontend:** [Hotwire / React / ViewComponent / etc.]
- **Background Jobs:** [Sidekiq / Resque / ActiveJob / etc.]
- **Database:** [PostgreSQL / MySQL / SQLite]
- **Other Key Gems:** [List important gems]

### Output Configuration
- **Output Directory:** `docs/`
- **Output Filename:** `rails-patterns.md`
- **Documentation Title:** `Rails Patterns Guide`
```

### Available Agents

#### 1. Pattern Analyst Agents

**@rails-models** - ActiveRecord Model Patterns
- Analyzes `app/models/` for model patterns
- Extracts concerns, associations, STI, callbacks, scopes, validations
- Returns JSON with 6-8 model patterns and code snippets

**@rails-controllers** - Controller Patterns
- Analyzes `app/controllers/` for controller patterns
- Extracts authentication, authorization, lean controller design, Turbo integration
- Returns JSON with 6-8 controller patterns and code snippets

**@rails-frontend** - Frontend Patterns
- Analyzes frontend code (Stimulus, Turbo, React, ViewComponent, etc.)
- Extracts framework-specific patterns and best practices
- Returns JSON with 6-8 frontend patterns and code snippets

**@rails-infrastructure** - Infrastructure & Deployment
- Analyzes background jobs, database, caching, configuration
- Extracts Sidekiq/Resque patterns, database optimizations, deployment configs
- Returns JSON with 6-8 infrastructure patterns and code snippets

#### 2. Coordinator Agent

**@rails-guide-writer** - Pattern Guide Generator
- Orchestrates all analyst agents
- Reads this CLAUDE.md for project configuration
- Generates comprehensive Markdown pattern guide
- Output: `[project-name]/rails-patterns.md`

**Usage:**
```
@rails-guide-writer
```

The agent will:
1. Read this CLAUDE.md for project context
2. Invoke all 4 analyst agents sequentially
3. Compile results into clean Markdown with YAML frontmatter
4. Write to configured output path

#### 3. Enhancement Agent

**@rails-docs-linker** - Documentation Link Enhancer
- Reads generated Markdown guide
- Uses Context7 MCP to find relevant Rails documentation
- Adds clickable links to Rails API and Guides
- Updates Markdown in-place

**Usage:**
```
@rails-docs-linker
```

Run this after generating the initial guide to enhance it with documentation links.

## Context7 Integration

### Query Patterns from This Repository

Use the Context7 MCP or library ID to query indexed patterns:

```
Library ID: /swistaczek/ruby-snippets
```

**Example queries:**
- "Show me Rails CurrentAttributes patterns from /swistaczek/ruby-snippets"
- "How does Basecamp implement real-time features with Turbo Streams?"
- "Examples of SQLite full-text search in Rails"
- "Authentication patterns in Rails controllers"

### Context7 MCP Tools

The agents use these MCP tools for Rails documentation:

```
mcp__Context7__resolve-library-id("rails")
mcp__Context7__get-library-docs(
  context7CompatibleLibraryID: "/websites/guides_rubyonrails",
  topic: "pattern name or concept"
)
```

## Agent Workflow

### Generating a Complete Pattern Guide

```bash
# 1. Ensure your Rails project has this CLAUDE.md configured
# 2. Invoke the coordinator agent
@basecamp-guide-writer

# 3. (Optional) Enhance with Rails documentation links
@rails-docs-linker
```

### Querying Specific Pattern Categories

```bash
# Get only model patterns
@basecamp-models

# Get only frontend patterns
@basecamp-frontend
```

## Customizing for Your Rails Project

To use these agents with your Rails project:

### Step 1: Copy Agents
```bash
cp -r .claude/agents /path/to/your/rails/project/.claude/
```

### Step 2: Create/Update CLAUDE.md

In your Rails project root, create `CLAUDE.md` with this structure:

```markdown
# [Your Project Name]

## Your Rails Project Configuration

**Project Name:** My Rails App
**Description:** E-commerce platform built with Rails 7
**Source Repository:** https://github.com/yourorg/yourapp
**Rails Version:** 7.1+

### Directory Structure
- Models: `app/models/`
- Controllers: `app/controllers/`
- Views: `app/views/`
- JavaScript: `app/javascript/controllers/`
- Channels: `app/channels/`
- Jobs: `app/jobs/`

### Technology Stack
- **Frontend:** Hotwire (Turbo + Stimulus)
- **Background Jobs:** Sidekiq
- **Database:** PostgreSQL
- **Other Key Gems:** devise, pundit, ransack

### Output Configuration
- **Output Directory:** `docs/`
- **Output Filename:** `rails-patterns.md`
- **Documentation Title:** `My Rails App - Patterns Guide`

## Pattern Extraction Agents

[Include agent documentation from this file]
```

### Step 3: Run Agent

```bash
cd /path/to/your/rails/project
@basecamp-guide-writer
```

The agents will:
- Read your CLAUDE.md for project-specific configuration
- Auto-detect Rails structure and technologies
- Generate a customized pattern guide for YOUR project

## Smart Defaults

If CLAUDE.md is missing or incomplete, agents will auto-detect:
- Project name from git remote or directory name
- Rails version from `Gemfile`
- Frontend framework from `package.json` or `importmap.rb`
- Background job system from `Gemfile`
- Database from `config/database.yml`
- Standard Rails directory structure (`app/models/`, etc.)

## Output Format

Generated guides are Markdown files with YAML frontmatter:
- **Frontmatter:** title, description, topics, source URL
- **Table of Contents:** Section links with pattern counts
- **Patterns:** H3 headings, descriptions, source links, code blocks
- **Source attribution:** Links to GitHub files
- **Rails docs links:** Added by rails-docs-linker agent
- **Generation timestamp:** Footer with date

## Best Practices

### Pattern Quality
- Agents extract **real production code**, not synthetic examples
- Maximum 20 lines per snippet for readability
- 6-8 patterns per section (focused on most valuable patterns)
- Includes file paths and source attribution

### When to Re-generate
- After significant code changes
- When adding new patterns or features
- Periodically to keep documentation fresh
- After updating Rails or major gems

### Combining with Context7
1. Generate pattern guide with agents (project-specific, detailed)
2. Index repo with Context7 (searchable, queryable, shareable)
3. Reference in other projects' CLAUDE.md files

## Troubleshooting

**Agents not finding files?**
- Verify directory paths in your CLAUDE.md
- Ensure you're running from project root
- Check that Rails app follows standard structure

**Generated guide has wrong project name?**
- Add `## Your Rails Project Configuration` section to CLAUDE.md
- Specify `**Project Name:**` explicitly

**Missing documentation links?**
- Ensure Context7 MCP is configured in `.claude/settings.local.json`
- Run `@rails-docs-linker` after generating the guide
- Check MCP server status with `/mcp list`

## Contributing New Patterns

To add patterns from a new Rails project to this repository:

1. Clone the source repository locally (temporary, for extraction)
2. Run `@rails-guide-writer` against the cloned project
3. Create new directory: `[project-name]/`
4. Move generated `rails-patterns.md` to the new directory
5. Add `README.md` with project overview and source link
6. (Optional) Run `@rails-docs-linker` to add Rails documentation links
7. Delete the cloned source repository
8. Commit and push (triggers Context7 re-indexing)

---

**For more information:**
- Pattern collection: [README.md](./README.md)
- Context7 library: `/swistaczek/ruby-snippets`
- Example patterns: [once-campfire/rails-patterns.md](./once-campfire/rails-patterns.md), [fizzy/rails-patterns.md](./fizzy/rails-patterns.md)
