#!/usr/bin/env python3
"""Generate a simple HTML mapping matrix for the QUADRIGA schema."""

import json
import os
import sys
from pathlib import Path


def load_schemas(version_dir):
    """Load all JSON schema files, walk the schema tree in canonical order."""
    version = Path(version_dir)
    cache = {}  # filename -> parsed json

    def get_schema(filename):
        if filename not in cache:
            with open(version / filename) as fh:
                cache[filename] = json.load(fh)
        return cache[filename]

    rows = []  # list of (display_name, x_mappings_dict_or_None, depth, filename)
    mapped_schemas = set()
    visited = set()  # track visited files to avoid duplicates

    # Load @context for resolving prefixed URIs
    root = get_schema("schema.json")
    context = root.get("@context", {})

    def collect_mappings(xm):
        if xm is not None:
            for k in xm:
                if not k.startswith("$"):
                    mapped_schemas.add(k)

    def walk(filename, depth=0):
        """Recursively walk schema following $ref and properties in order."""
        if filename in visited:
            return
        visited.add(filename)

        data = get_schema(filename)
        # Display "case-study" instead of "schema" for the root element
        name = "case-study" if filename == "schema.json" else filename.replace(".json", "")
        xm = data.get("x-mappings")
        collect_mappings(xm)
        rows.append((name, xm, depth, filename))

        # Top-level $ref (e.g. author.json -> person.json)
        if "$ref" in data:
            walk(data["$ref"], depth + 1)

        # If it has properties, walk them in definition order
        def collect_refs(obj):
            """Recursively collect all $ref values from a JSON schema node."""
            refs = []
            if isinstance(obj, dict):
                if "$ref" in obj:
                    refs.append(obj["$ref"])
                for v in obj.values():
                    refs.extend(collect_refs(v))
            elif isinstance(obj, list):
                for item in obj:
                    refs.extend(collect_refs(item))
            return refs

        for prop_name, prop_val in data.get("properties", {}).items():
            if not isinstance(prop_val, dict):
                continue
            # Inline x-mappings on a property (e.g. assessment, date)
            if "x-mappings" in prop_val:
                pxm = prop_val["x-mappings"]
                collect_mappings(pxm)
                rows.append((prop_name, pxm, depth + 1, filename))
            elif "$ref" not in prop_val:
                # Property without x-mappings and not a $ref → internal
                rows.append((prop_name, None, depth + 1, filename))
            # Follow all $ref pointers (direct, oneOf, items, etc.)
            nested_refs = collect_refs(prop_val)
            has_direct_ref = "$ref" in prop_val
            for ref in nested_refs:
                if ref not in visited:
                    # Direct $ref: child of current schema (depth+1)
                    # Nested $ref (inside oneOf/items): child of property (depth+2)
                    ref_depth = depth + 1 if has_direct_ref else depth + 2
                    walk(ref, ref_depth)

        # If it's an array with items.$ref, follow that
        items = data.get("items", {})
        if isinstance(items, dict) and "$ref" in items:
            walk(items["$ref"], depth + 1)

    # Start from schema.json (the root)
    walk("schema.json")

    # Append any remaining files not reachable from schema.json
    for f in sorted(version.glob("*.json")):
        if f.name not in visited:
            walk(f.name, depth=0)

    # Remove reusable value types that are only used internally to specify value ranges
    internal_types = {"multilingual-text.json", "semver.json"}
    rows = [r for r in rows if r[3] not in internal_types]

    # Move reusable entity types (and their children) to the bottom of the table
    bottom_types = {"person.json"}
    bottom_rows = []
    remaining = []
    collecting = False
    collect_depth = 0
    for name, xm, depth, fn in rows:
        if fn in bottom_types:
            collecting = True
            collect_depth = depth
            bottom_rows.append((name, xm, 0, fn))
        elif collecting and depth > collect_depth:
            # Child row: adjust depth relative to the moved parent
            bottom_rows.append((name, xm, depth - collect_depth, fn))
        else:
            collecting = False
            remaining.append((name, xm, depth, fn))
    rows = remaining
    rows.extend(bottom_rows)

    # Desired column order for external schemas
    column_order = ["dc", "dcterms", "schema", "amb", "modalia", "hermes", "lrmi", "dcat"]
    ordered = [c for c in column_order if c in mapped_schemas]
    # Append any schemas not in the predefined order
    ordered += sorted(s for s in mapped_schemas if s not in column_order)

    return rows, ordered, context


def html_escape(text):
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def resolve_uri(target, context):
    """Resolve a prefixed target (e.g. dc:title) to a full URI using @context."""
    if not target:
        return ""
    # Already a full URI
    if target.startswith("http://") or target.startswith("https://"):
        return target
    # Try to resolve prefix
    if ":" in target:
        prefix, local = target.split(":", 1)
        base = context.get(prefix, "")
        if base:
            return base + local
    return ""


def tooltip_icon(comment):
    """Return a tooltip icon span if comment is present, else empty string."""
    if not comment:
        return ""
    return f' <span class="tip" data-tip="{html_escape(comment)}">ⓘ</span>'


def format_sub_cell(entry, context):
    """Format a single mapping entry as a sub-cell div. Returns HTML string."""
    relation = entry.get("relation", "")
    target = entry.get("target", "")
    comment = entry.get("$comment")
    short_rel = relation.replace("skos:", "") if relation else ""
    css_class = short_rel.lower() if short_rel else "unknown"

    if target:
        uri = resolve_uri(target, context)
        if uri:
            target_html = f'<a class="target" href="{html_escape(uri)}" target="_blank">{html_escape(target)}</a>'
        else:
            target_html = f'<span class="target">{html_escape(target)}</span>'
        content = f'<span class="label-box"><span class="relation">{short_rel}</span><span class="target-line">{target_html}{tooltip_icon(comment)}</span></span>'
    else:
        content = f'<span class="label-box"><span class="relation">{short_rel}</span>{tooltip_icon(comment)}</span>'

    return f'<div class="sub-cell {css_class}">{content}</div>'


def cell_content(xm, schema_name, context):
    """Return (html_content, td_css_class) for a given mapping entry."""
    if xm is None:
        return "", ""

    entry = xm.get(schema_name)
    if entry is None:
        return "N/A", "na"

    # Normalize to list
    entries = entry if isinstance(entry, list) else [entry]
    sub_cells = [format_sub_cell(e, context) for e in entries]

    # If single entry, use its color on the td; if multiple, colors are on sub-cells
    if len(entries) == 1:
        rel = entries[0].get("relation", "")
        td_css = rel.replace("skos:", "").lower() if rel else "unknown"
    else:
        td_css = "multi"

    return "".join(sub_cells), td_css


def general_comment(xm):
    """Extract the top-level $comment from x-mappings as a tooltip icon."""
    if xm is None:
        return ""
    comment = xm.get("$comment", "")
    return tooltip_icon(comment)


def generate_html(rows, columns, context):
    """Generate a self-contained HTML string."""
    # Build table rows with tree guide prefixes
    table_rows = []
    for idx, (name, xm, depth, filename) in enumerate(rows):
        cells = []
        has_mappings = xm is not None
        for col in columns:
            text, css_class = cell_content(xm, col, context)
            cells.append(f'<td class="{css_class}">{text}</td>')
        comment = general_comment(xm)
        row_class = ""
        element_link = f'<a href="{html_escape(filename)}" target="_blank">{name}</a>'

        indent_step = 20
        # Check if this row has children (next row is deeper)
        has_children = idx + 1 < len(rows) and rows[idx + 1][2] > depth
        if has_children:
            child_left = (depth + 1) * indent_step - 10
            start_stub = f'<span class="tree-start" style="left: {child_left}px"></span>'
        else:
            start_stub = ""
        if depth > 0:
            indent = f'style="padding-left: {depth * indent_step}px"'
            lines = []
            # Ancestor vertical continuation lines
            for level in range(1, depth):
                has_future = False
                for future_name, future_xm, future_depth, future_fn in rows[idx + 1:]:
                    if future_depth < level:
                        break
                    if future_depth == level:
                        has_future = True
                        break
                if has_future:
                    left = level * indent_step - 10
                    lines.append(f'<span class="tree-vline" style="left: {left}px"></span>')
            # Connector at current depth (├ or └)
            is_last = True
            for future_name, future_xm, future_depth, future_fn in rows[idx + 1:]:
                if future_depth < depth:
                    break
                if future_depth == depth:
                    is_last = False
                    break
            left = depth * indent_step - 10
            cls = "tree-last" if is_last else "tree-mid"
            lines.append(f'<span class="{cls}" style="left: {left}px"></span>')
            tree_html = "".join(lines)
        else:
            indent = ""
            tree_html = ""

        table_rows.append(
            f'  <tr class="{row_class}"><td class="element-name" {indent}>{tree_html}{start_stub}{element_link}{comment}</td>{"".join(cells)}</tr>'
        )

    col_headers = "".join(f"<th>{c}</th>" for c in columns)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUADRIGA Schema – Mapping Matrix</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 1rem;
    background: #fafafa;
    text-align: center;
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.5rem; }}
  .table-wrap {{
    overflow-x: auto;
    max-height: 90vh;
  }}
  .table-wrap table {{
    margin: 0 auto;
  }}
  table {{
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th, td {{
    border: 1.5px solid #333;
    padding: 4px 8px;
    text-align: center;
    white-space: nowrap;
    vertical-align: middle;
  }}
  thead th {{
    position: sticky;
    top: 0;
    background: #333;
    color: #fff;
    z-index: 2;
    border-color: #333;
  }}
  .element-name {{
    position: sticky;
    left: 0;
    background: #f0f0f0;
    text-align: left;
    font-weight: 600;
    z-index: 1;
  }}
  .tree-start {{
    position: absolute;
    top: calc(50% + 10px);
    bottom: 0;
    border-left: 1.5px solid #999;
  }}
  .tree-vline {{
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 1.5px solid #999;
  }}
  .tree-mid {{
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 1.5px solid #999;
  }}
  .tree-mid::after {{
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    width: 6px;
    border-top: 1.5px solid #999;
  }}
  .tree-last {{
    position: absolute;
    top: 0;
    height: 50%;
    border-left: 1.5px solid #999;
    border-bottom: 1.5px solid #999;
    width: 6px;
    border-bottom-left-radius: 3px;
  }}
  thead th:first-child {{
    z-index: 3;
    background: #333;
  }}
  /* relation colors – Okabe-Ito colorblind-safe palette */
  .exactmatch {{ background: #009e73; }}
  .closematch {{ background: #56b4e9; }}
  .narrowmatch {{ background: #e69f00; }}
  .broadmatch {{ background: #f0e442; }}
  .na {{ background: #ddd; }}
  .sub-cell {{
    padding: 3px 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .sub-cell + .sub-cell {{
    border-top: 1.5px solid #333;
  }}
  .multi {{
    padding: 0;
  }}
  .label-box {{
    display: inline-block;
    background: rgba(255,255,255,0.45);
    border-radius: 3px;
    padding: 1px 3px;
  }}
  .relation {{
    display: block;
    font-size: 0.75em;
  }}
  .target-line {{
    display: block;
  }}
  a.target, a.target:visited {{
    font-weight: 600;
    color: inherit;
    text-decoration: none;
  }}
  a.target:hover {{
    text-decoration: underline;
  }}
  .relation {{
    color: inherit;
    opacity: 0.8;
  }}
  .element-name a {{
    color: inherit;
    text-decoration: none;
  }}
  .element-name a:hover {{
    text-decoration: underline;
  }}
  .tip {{
    cursor: help;
    font-size: 0.85em;
    position: relative;
  }}
  #tooltip {{
    position: fixed;
    background: #333;
    color: #fff;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 0.82rem;
    max-width: 350px;
    white-space: normal;
    pointer-events: none;
    z-index: 1000;
    display: none;
    line-height: 1.4;
  }}
  .legend {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: center;
    margin-bottom: 0.75rem;
    font-size: 0.82rem;
    align-items: center;
  }}
  .legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .legend-swatch {{
    width: 14px;
    height: 14px;
    border: 1px solid #bbb;
    border-radius: 2px;
    display: inline-block;
  }}
</style>
</head>
<body>
<h1>QUADRIGA Schema – Mapping Matrix</h1>
<div class="legend">
  <span style="font-weight:600">SKOS Relations:</span>
  <span class="legend-item"><span class="legend-swatch exactmatch"></span> <a href="http://www.w3.org/2004/02/skos/core#exactMatch" target="_blank">exactMatch</a></span>
  <span class="legend-item"><span class="legend-swatch closematch"></span> <a href="http://www.w3.org/2004/02/skos/core#closeMatch" target="_blank">closeMatch</a></span>
  <span class="legend-item"><span class="legend-swatch broadmatch"></span> <a href="http://www.w3.org/2004/02/skos/core#broadMatch" target="_blank">broadMatch</a></span>
  <span class="legend-item"><span class="legend-swatch narrowmatch"></span> <a href="http://www.w3.org/2004/02/skos/core#narrowMatch" target="_blank">narrowMatch</a></span>
  <span class="legend-item"><span class="legend-swatch na"></span>N/A</span>
</div>
<div class="legend">
<p><i>The SKOS relation <a href="http://www.w3.org/2004/02/skos/core#relatedMatch" target="_blank">relatedMatch</a> was not used. Either an element could at least be mapped as <a href="http://www.w3.org/2004/02/skos/core#closeMatch" target="_blank">closeMatch</a> or it was not mapped.</i></p>
</div>
<div class="table-wrap">
<table>
<thead>
  <tr><th class="element-name">Element</th>{col_headers}</tr>
</thead>
<tbody>
{"".join(table_rows)}
</tbody>
</table>
</div>
<div id="tooltip"></div>
<script>
(function() {{
  var tip = document.getElementById('tooltip');
  document.addEventListener('mouseover', function(e) {{
    var el = e.target.closest('.tip');
    if (el && el.dataset.tip) {{
      tip.textContent = el.dataset.tip;
      tip.style.display = 'block';
      var r = el.getBoundingClientRect();
      tip.style.left = r.right + 6 + 'px';
      tip.style.top = r.top - 4 + 'px';
      // Keep tooltip on screen
      var tr = tip.getBoundingClientRect();
      if (tr.right > window.innerWidth) {{
        tip.style.left = (r.left - tr.width - 6) + 'px';
      }}
      if (tr.bottom > window.innerHeight) {{
        tip.style.top = (window.innerHeight - tr.height - 8) + 'px';
      }}
    }}
  }});
  document.addEventListener('mouseout', function(e) {{
    if (e.target.closest('.tip')) {{
      tip.style.display = 'none';
    }}
  }});
}})();
</script>
</body>
</html>"""


def main():
    version_dir = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    rows, columns, context = load_schemas(version_dir)
    html = generate_html(rows, columns, context)

    out_dir = Path("_build") / version_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mapping-matrix.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()
