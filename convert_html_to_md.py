#!/usr/bin/env python3
"""
Convert Basecamp Rails Guide HTML to Markdown format for Context7 indexing.
"""

import html
import re
from pathlib import Path

def unescape_html_entities(text):
    """Unescape HTML entities like &lt; &gt; &amp;"""
    return html.unescape(text)

def extract_patterns_from_html(html_content):
    """Parse HTML and extract patterns into structured data"""
    patterns = []

    # Split by h2 sections (Models, Controllers, Frontend, Infrastructure)
    sections = re.split(r'<h2[^>]*id="([^"]+)"[^>]*>([^<]+)</h2>', html_content)

    # Process sections (skip first empty element)
    for i in range(1, len(sections), 3):
        if i + 2 >= len(sections):
            break

        section_id = sections[i]
        section_name = sections[i + 1]
        section_content = sections[i + 2]

        # Extract individual patterns from this section
        pattern_blocks = re.findall(
            r'<div class="pattern[^"]*">(.*?)</div>\s*(?=<div class="pattern|<h2|<div class="generated|$)',
            section_content,
            re.DOTALL
        )

        section_patterns = []
        for block in pattern_blocks:
            pattern = {}

            # Extract title
            title_match = re.search(r'<h3>([^<]+)</h3>', block)
            if title_match:
                pattern['title'] = title_match.group(1).strip()

            # Extract description
            desc_match = re.search(r'<p>([^<]+)</p>', block)
            if desc_match:
                pattern['description'] = desc_match.group(1).strip()

            # Extract docs link (optional)
            docs_match = re.search(r'<div class="docs"><a href="([^"]+)"[^>]*>([^<]+)</a></div>', block)
            if docs_match:
                pattern['docs_url'] = docs_match.group(1)
                pattern['docs_label'] = docs_match.group(2)

            # Extract source file link
            file_match = re.search(r'<div class="file"><a href="([^"]+)"[^>]*>([^<]+)</a></div>', block)
            if file_match:
                pattern['source_url'] = file_match.group(1)
                pattern['source_file'] = file_match.group(2)

            # Extract code
            code_match = re.search(r'<pre><code>(.*?)</code></pre>', block, re.DOTALL)
            if code_match:
                code = code_match.group(1)
                # Unescape HTML entities
                code = unescape_html_entities(code)
                pattern['code'] = code.strip()

            section_patterns.append(pattern)

        patterns.append({
            'section_id': section_id,
            'section_name': section_name,
            'patterns': section_patterns
        })

    return patterns

def generate_markdown(patterns):
    """Generate markdown from structured pattern data"""
    lines = []

    # Add frontmatter
    lines.append('---')
    lines.append('title: Basecamp Rails Patterns - Campfire')
    lines.append('description: Real-world Ruby on Rails patterns from Basecamp\'s open-source Campfire chat application')
    lines.append('topics: rails, ruby, hotwire, turbo, stimulus, activerecord, actioncable, sqlite, patterns')
    lines.append('source: https://github.com/basecamp/once-campfire')
    lines.append('---')
    lines.append('')

    # Add title and description
    lines.append('# Basecamp Rails Patterns - Campfire')
    lines.append('')
    lines.append('Comprehensive guide extracted from Campfire open-source codebase. This is a production Rails 7 application built by Basecamp, showcasing modern Rails patterns with Hotwire, real-time features, and pragmatic architectural decisions.')
    lines.append('')

    # Add table of contents
    total_patterns = sum(len(section['patterns']) for section in patterns)
    lines.append('## Table of Contents')
    lines.append('')
    for section in patterns:
        lines.append(f"- [{section['section_name']}](#{section['section_id']}) ({len(section['patterns'])} patterns)")
    lines.append('')
    lines.append(f'**Total: {total_patterns} patterns**')
    lines.append('')

    # Add each section
    for section in patterns:
        lines.append(f"## {section['section_name']}")
        lines.append('')

        for pattern in section['patterns']:
            # Pattern title
            lines.append(f"### {pattern['title']}")
            lines.append('')

            # Description
            if 'description' in pattern:
                lines.append(pattern['description'])
                lines.append('')

            # Documentation link
            if 'docs_url' in pattern:
                lines.append(f"**Rails Docs:** [{pattern['docs_label']}]({pattern['docs_url']})")
                lines.append('')

            # Source file link
            if 'source_url' in pattern and 'source_file' in pattern:
                lines.append(f"**Source:** [{pattern['source_file']}]({pattern['source_url']})")
                lines.append('')

            # Code block
            if 'code' in pattern:
                lines.append('```ruby')
                lines.append(pattern['code'])
                lines.append('```')
                lines.append('')

    return '\n'.join(lines)

def main():
    # Read HTML file
    html_path = Path('/Users/ernest/projects/once-campfire/docs/basecamp-rails-guide.html')
    output_path = Path('/Users/ernest/projects/ruby-snippets/once-campfire/rails-patterns.md')

    print(f"Reading {html_path}...")
    html_content = html_path.read_text(encoding='utf-8')

    print("Parsing patterns...")
    patterns = extract_patterns_from_html(html_content)

    print(f"Found {len(patterns)} sections")
    for section in patterns:
        print(f"  - {section['section_name']}: {len(section['patterns'])} patterns")

    print("\nGenerating markdown...")
    markdown = generate_markdown(patterns)

    print(f"Writing to {output_path}...")
    output_path.write_text(markdown, encoding='utf-8')

    print(f"\n✅ Conversion complete! Generated {len(markdown.splitlines())} lines of markdown")

if __name__ == '__main__':
    main()
