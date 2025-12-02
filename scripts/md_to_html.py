#!/usr/bin/env python3
"""
Markdown to HTML converter for Ruby & Rails Patterns Collection.
Converts once-campfire/rails-patterns.md to docs/index.html with interactive features.
"""

import re
import yaml
from datetime import datetime
from pathlib import Path
import html as html_module

def parse_markdown_file(md_path):
    """Parse markdown file and extract frontmatter and content."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract YAML frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        content = content[frontmatter_match.end():]
    else:
        frontmatter = {}

    return frontmatter, content

def categorize_pattern(section_name):
    """Map section name to category slug."""
    section_lower = section_name.lower()
    if 'model' in section_lower:
        return 'models'
    elif 'controller' in section_lower:
        return 'controllers'
    elif 'frontend' in section_lower or 'hotwire' in section_lower:
        return 'frontend'
    elif 'infrastructure' in section_lower:
        return 'infrastructure'
    return 'other'

def extract_keywords(description, pattern_name):
    """Extract keywords from pattern description and name."""
    # Combine pattern name and description
    text = f"{pattern_name} {description}".lower()

    # Remove common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'can', 'using', 'use', 'uses', 'used'}

    # Extract words (alphanumeric + underscores)
    words = re.findall(r'\b[a-z_][a-z0-9_]*\b', text)
    keywords = [w for w in words if w not in common_words and len(w) > 2]

    # Deduplicate and return
    return ' '.join(sorted(set(keywords)))

def parse_patterns(content):
    """Parse markdown content and extract patterns organized by section."""
    sections = {}
    current_section = None
    current_pattern = None

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # H2 section header
        if line.startswith('## ') and not line.startswith('## Table'):
            section_name = line[3:].strip()
            current_section = section_name
            sections[current_section] = []
            i += 1
            continue

        # H3 pattern header
        if line.startswith('### ') and current_section:
            pattern_name = line[4:].strip()
            current_pattern = {
                'name': pattern_name,
                'description': '',
                'rails_docs': '',
                'source': '',
                'code': '',
                'category': categorize_pattern(current_section)
            }
            sections[current_section].append(current_pattern)
            i += 1
            continue

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Skip table of contents and intro
        if current_pattern is None:
            i += 1
            continue

        # Rails Docs link
        if line.startswith('**Rails Docs:**'):
            # Extract link from markdown: [text](url)
            link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', line)
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)
                current_pattern['rails_docs'] = f'<a href="{link_url}" target="_blank">{link_text}</a>'
            i += 1
            continue

        # Source link
        if line.startswith('**Source:**'):
            # Extract link from markdown: [text](url)
            link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', line)
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)
                current_pattern['source'] = f'<a href="{link_url}" target="_blank">{link_text}</a>'
            i += 1
            continue

        # Code block start
        if line.startswith('```'):
            code_lines = []
            i += 1
            # Collect code lines until closing ```
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            # Escape HTML and join
            code_content = '\n'.join(code_lines)
            escaped_code = html_module.escape(code_content)
            current_pattern['code'] = escaped_code
            i += 1
            continue

        # Description (any other text before Rails Docs/Source/Code)
        if current_pattern and not current_pattern['description'] and not line.startswith('**'):
            current_pattern['description'] = line.strip()

        i += 1

    return sections

def generate_html(sections, frontmatter, template_path, output_path):
    """Generate HTML from parsed patterns using template."""

    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Build content HTML
    content_html = []
    total_patterns = 0

    for section_name, patterns in sections.items():
        if not patterns:
            continue

        # Section header
        content_html.append(f'<h2 id="{categorize_pattern(section_name)}">{section_name} ({len(patterns)} patterns)</h2>')

        for pattern in patterns:
            total_patterns += 1

            # Extract keywords for search
            keywords = extract_keywords(pattern['description'], pattern['name'])

            # Pattern div with data attributes
            pattern_html = f'''<div class="pattern" data-category="{pattern['category']}" data-keywords="{keywords}" data-name="{pattern['name'].lower()}">
  <h3>{pattern['name']}</h3>
  <p>{pattern['description']}</p>'''

            # Add Rails docs link if available
            if pattern['rails_docs']:
                pattern_html += f'\n  <div class="docs">Rails Docs: {pattern["rails_docs"]}</div>'

            # Add source link if available
            if pattern['source']:
                pattern_html += f'\n  <div class="file">source: {pattern["source"]}</div>'

            # Add code block with copy button
            if pattern['code']:
                pattern_html += f'''
  <pre><code>{pattern['code']}</code><button class="copy-btn" onclick="copyCode(this)">Copy</button></pre>'''

            pattern_html += '\n</div>\n'
            content_html.append(pattern_html)

    # Replace template placeholders
    html_output = template.replace('{{TITLE}}', frontmatter.get('title', 'Ruby & Rails Patterns'))
    html_output = html_output.replace('{{PROJECT_NAME}}', frontmatter.get('title', 'Ruby & Rails Patterns'))
    html_output = html_output.replace('{{DESCRIPTION}}', frontmatter.get('description', ''))
    html_output = html_output.replace('{{CONTENT}}', '\n'.join(content_html))
    html_output = html_output.replace('{{TIMESTAMP}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    return total_patterns

def merge_sections(all_sections):
    """Merge sections from multiple pattern files."""
    merged = {}
    for sections in all_sections:
        for section_name, patterns in sections.items():
            if section_name not in merged:
                merged[section_name] = []
            merged[section_name].extend(patterns)
    return merged

def main():
    """Main conversion process."""
    # Paths
    project_root = Path(__file__).parent.parent
    template_path = project_root / 'template.html'
    output_path = project_root / 'docs' / 'index.html'

    # Pattern files to process
    pattern_files = [
        project_root / 'once-campfire' / 'rails-patterns.md',
        project_root / 'fizzy' / 'rails-patterns.md',
    ]

    all_sections = []
    total_parsed = 0

    for md_path in pattern_files:
        if not md_path.exists():
            print(f"⚠ Skipping {md_path} (not found)")
            continue

        print(f"Processing {md_path.parent.name}/{md_path.name}...")

        # Parse markdown
        frontmatter, content = parse_markdown_file(md_path)
        print(f"  ✓ Parsed: {frontmatter.get('title', md_path.parent.name)}")

        # Extract patterns
        sections = parse_patterns(content)
        section_count = sum(len(patterns) for patterns in sections.values())
        print(f"  ✓ Extracted {section_count} patterns")
        total_parsed += section_count

        all_sections.append(sections)

    # Merge all sections
    merged_sections = merge_sections(all_sections)
    print(f"\n✓ Merged {total_parsed} patterns from {len(pattern_files)} files")

    # Combined frontmatter
    combined_frontmatter = {
        'title': 'Ruby & Rails Patterns Collection',
        'description': 'Production-ready patterns from Basecamp Campfire and 37signals Fizzy'
    }

    # Generate HTML
    total_patterns = generate_html(merged_sections, combined_frontmatter, template_path, output_path)
    print(f"✓ Generated HTML with {total_patterns} patterns")

    # Report file size
    file_size = output_path.stat().st_size
    print(f"✓ Output: {output_path} ({file_size:,} bytes)")
    print("\nDone! 🎉")

if __name__ == '__main__':
    main()
