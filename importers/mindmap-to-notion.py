#!/usr/bin/env python3
"""
FreeMind Mindmap to Notion Importer

Parses .mm (FreeMind XML) files and creates pages in a Notion
"Technical Reference" database. Each mindmap becomes a page with
structured content (headings, toggles, bullet lists).

Requirements:
    pip install requests

Usage:
    export NOTION_TOKEN="ntn_your_token_here"
    python3 mindmap-to-notion.py --inventory inventory.json --parent-page PAGE_ID

    Or with an existing database:
    python3 mindmap-to-notion.py --inventory inventory.json --database DB_ID
"""

import xml.etree.ElementTree as ET
import requests
import json
import time
import re
import os
import sys
import argparse
from html.parser import HTMLParser

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
RATE_LIMIT_SLEEP = 0.4

SECRET_PATTERNS = [
    r'gsk_[A-Za-z0-9]{20,}',
    r'sk-[A-Za-z0-9]{20,}',
    r'AIza[A-Za-z0-9_-]{35}',
    r'ghp_[A-Za-z0-9]{36}',
    r'glpat-[A-Za-z0-9_-]{20}',
    r'ntn_[A-Za-z0-9]{40,}',
    r'(?i)password\s*[:=]\s*\S+',
    r'(?i)api[_-]?key\s*[:=]\s*\S+',
    r'(?i)secret\s*[:=]\s*\S+',
    r'(?i)credential\s*[:=]\s*\S+',
]

SKIP_FILES_DEFAULT = {
    "To Do", "Completed To Do", "Scammers", "Nick Cage",
    "Mr Beer", "Lessons", "Pro Tips",
    "Hardware", "Network",
    "Temp", "personal", "Social", "Free Node",
    "New-To-Do", "New Puppet", "New Puppet-1", "Keros",
}

SKIP_CATEGORIES_DEFAULT = {"mr-beer"}

CATEGORY_MAP = {
    "development": "development",
    "system-administration": "system-administration",
    "kcs": "kcs",
    "root": "personal",
    "redhat-laptop_it": "development",
    "redhat-laptop_personal-it": "personal",
    "free-node": "development",
    "mathematica": "development",
}

SUBCATEGORY_MAP = {
    "salesforce": "salesforce",
    "linux": "linux",
    "windows": "windows",
    "mac": "mac",
    "vista": "windows",
    "xp": "windows",
}

TAG_WHITELIST = {
    "linux", "bash", "git", "docker", "kubernetes", "ansible", "puppet",
    "jenkins", "maven", "java", "python", "javascript", "rest-api",
    "salesforce", "apex", "jboss", "jee", "solr", "elasticsearch",
    "dd-wrt", "networking", "dns", "dhcp", "ssh", "ssl", "firewall",
    "fedora", "centos", "rhel", "debian", "raspbian", "freebsd",
    "virtualization", "kvm", "xen", "vagrant", "virtualbox",
    "rpm", "systemd", "cron", "nfs", "samba",
    "grafana", "prometheus", "splunk", "elk", "neo4j", "graphql",
    "mysql", "postgresql", "mongodb", "chromadb",
    "openshift", "helm", "etcd", "containers",
    "vim", "eclipse", "netbeans", "ide",
    "testing", "junit", "mockito", "karate", "jmeter",
    "kde", "garden", "yard", "android", "chrome", "firefox",
    "aws", "iot", "configuration", "backup",
}


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def content_depth(nodes):
    if nodes < 10: return "stub"
    if nodes < 50: return "light"
    if nodes < 200: return "moderate"
    return "deep"


def has_secrets(text):
    for pat in SECRET_PATTERNS:
        if re.search(pat, text):
            return True
    return False


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return ''.join(self.parts).strip()


def extract_html_text(html_str):
    ext = HTMLTextExtractor()
    try:
        ext.feed(html_str)
        return ext.get_text()
    except Exception:
        return re.sub(r'<[^>]+>', '', html_str).strip()


def parse_mindmap(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        map_node = root if root.tag == 'node' else root.find('.//node')
        return map_node
    except ET.ParseError:
        return None


def node_text(node):
    text = node.get('TEXT', '')
    rc = node.find('richcontent')
    if rc is not None:
        html = ET.tostring(rc, encoding='unicode', method='html')
        extracted = extract_html_text(html)
        if extracted and not text:
            text = extracted
        elif extracted and text:
            text = f"{text}\n{extracted}"
    return text.strip()


def collect_blocks(node, depth=0, max_blocks=95):
    blocks = []
    if depth > 5:
        return blocks

    for child in node.findall('node'):
        if len(blocks) >= max_blocks:
            break

        text = node_text(child)
        if not text:
            continue
        if has_secrets(text):
            text = "[REDACTED]"
        text = text[:2000]

        grandchildren = list(child.findall('node'))

        if depth == 0:
            blocks.append(make_text_block("heading_2", text))
            sub = collect_blocks(child, 1, max_blocks - len(blocks))
            blocks.extend(sub)
        elif len(grandchildren) >= 3:
            blocks.append(make_toggle_block(text, child, depth + 1, max_blocks - len(blocks)))
        elif grandchildren:
            blocks.append(make_bullet_with_children(text, child, depth + 1, max_blocks - len(blocks)))
        else:
            blocks.append(make_text_block("bulleted_list_item", text))

    return blocks[:max_blocks]


def make_text_block(block_type, text):
    text = text[:2000]
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def make_bullet_with_children(text, node, depth, remaining):
    """Bullet item with nested children (for nodes with 1-2 children)."""
    text = text[:2000]
    child_blocks = []
    for child in list(node.findall('node'))[:10]:
        if len(child_blocks) >= min(remaining - 1, 10):
            break
        ct = node_text(child)
        if not ct:
            continue
        if has_secrets(ct):
            ct = "[REDACTED]"
        ct = ct[:2000]
        gc = list(child.findall('node'))
        if gc:
            nested = []
            for g in gc[:5]:
                gt = node_text(g)
                if gt and not has_secrets(gt):
                    nested.append(make_text_block("bulleted_list_item", gt[:2000]))
            if nested:
                child_blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": ct}}],
                        "children": nested[:5]
                    }
                })
            else:
                child_blocks.append(make_text_block("bulleted_list_item", ct))
        else:
            child_blocks.append(make_text_block("bulleted_list_item", ct))

    if not child_blocks:
        return make_text_block("bulleted_list_item", text)

    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "children": child_blocks[:10]
        }
    }


def make_toggle_block(text, node, depth, remaining):
    """Toggle for nodes with 3+ children — worth collapsing."""
    text = text[:2000]
    children_blocks = []
    for child in list(node.findall('node'))[:20]:
        if len(children_blocks) >= min(remaining - 1, 20):
            break
        child_text = node_text(child)
        if not child_text:
            continue
        if has_secrets(child_text):
            child_text = "[REDACTED]"
        child_text = child_text[:2000]

        grandchildren = list(child.findall('node'))
        if len(grandchildren) >= 3 and depth < 3:
            children_blocks.append(make_toggle_block(child_text, child, depth + 1, remaining - len(children_blocks)))
        elif grandchildren:
            children_blocks.append(make_bullet_with_children(child_text, child, depth + 1, remaining - len(children_blocks)))
        else:
            children_blocks.append(make_text_block("bulleted_list_item", child_text))

    if not children_blocks:
        return make_text_block("bulleted_list_item", text)

    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "children": children_blocks[:20]
        }
    }


def notion_api(method, endpoint, headers, payload=None, retries=3):
    url = f"{NOTION_BASE}{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.request(method, url, headers=headers, json=payload, timeout=30)

            if resp.status_code == 429:
                wait = float(resp.headers.get('Retry-After', 2 ** (attempt + 1)))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                time.sleep(2 ** (attempt + 1))
                continue

            if resp.status_code >= 400:
                print(f"  API error {resp.status_code}: {resp.text[:200]}")
                return None

            time.sleep(RATE_LIMIT_SLEEP)
            return resp.json()

        except requests.exceptions.Timeout:
            time.sleep(2 ** (attempt + 1))
        except Exception as e:
            print(f"  Request error: {e}")
            time.sleep(2 ** (attempt + 1))

    return None


def create_database(parent_page_id, headers):
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Technical Reference"}}],
        "properties": {
            "Topic": {"title": {}},
            "Category": {
                "select": {
                    "options": [
                        {"name": "development", "color": "blue"},
                        {"name": "system-administration", "color": "green"},
                        {"name": "personal", "color": "yellow"},
                        {"name": "kcs", "color": "purple"},
                        {"name": "hobby", "color": "orange"},
                    ]
                }
            },
            "Subcategory": {
                "select": {
                    "options": [
                        {"name": "linux", "color": "green"},
                        {"name": "windows", "color": "blue"},
                        {"name": "salesforce", "color": "purple"},
                        {"name": "networking", "color": "orange"},
                        {"name": "containers", "color": "red"},
                        {"name": "java", "color": "brown"},
                        {"name": "devops", "color": "gray"},
                        {"name": "monitoring", "color": "pink"},
                        {"name": "mac", "color": "default"},
                        {"name": "general", "color": "default"},
                    ]
                }
            },
            "Tags": {"multi_select": {"options": [{"name": t} for t in sorted(list(TAG_WHITELIST))[:50]]}},
            "Content Depth": {
                "select": {
                    "options": [
                        {"name": "stub", "color": "gray"},
                        {"name": "light", "color": "yellow"},
                        {"name": "moderate", "color": "blue"},
                        {"name": "deep", "color": "green"},
                    ]
                }
            },
            "Source File": {"rich_text": {}},
            "Node Count": {"number": {}},
            "Last Reviewed": {"date": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "imported", "color": "green"},
                        {"name": "needs-review", "color": "yellow"},
                        {"name": "outdated", "color": "red"},
                    ]
                }
            },
        }
    }

    result = notion_api("POST", "/databases", headers, payload)
    if result and "id" in result:
        print(f"Created database: {result['id']}")
        return result["id"]
    print(f"Failed to create database: {result}")
    return None


def infer_subcategory(entry):
    path_lower = entry["path"].lower()
    for key, sub in SUBCATEGORY_MAP.items():
        if f"/{key}/" in path_lower:
            return sub

    name_lower = entry["file"].lower()
    subcats = {
        "linux": ["bash", "rpm", "systemd", "fedora", "centos", "rhel", "debian", "raspbian",
                   "anaconda", "cheetah", "dvd", "screen", "kde", "lxde", "fvwm", "sound",
                   "x", "postfix", "mysql", "dhcp", "ssh", "plex", "mate", "xdm", "lxdm",
                   "jwm", "nx", "wol", "fuse", "jenkins", "apache", "udev", "alpine", "xfs",
                   "korn shell", "tftp", "cobbler", "pulp"],
        "containers": ["docker", "kubernetes", "helm", "etcd", "open shift", "openshift"],
        "java": ["ant", "maven", "jboss", "jee", "glassfish", "junit", "mockito", "archiva",
                 "beanshell", "log4j", "activemq", "groovy", "kotlin", "jmeter"],
        "networking": ["dd-wrt", "openwrt", "dns-320", "ssh", "dropbear", "f5"],
        "salesforce": ["apex", "database", "ui", "ide", "salesforce", "processes", "tooling"],
        "devops": ["ansible", "puppet", "cobbler", "git", "jenkins", "gerrit", "vagrant"],
        "monitoring": ["splunk", "elk", "new relic", "grafana", "prometheus"],
    }
    for sub, keywords in subcats.items():
        if name_lower in keywords:
            return sub
    return "general"


def infer_tags(entry):
    tags = set()
    name_lower = entry["file"].lower()
    for tag in TAG_WHITELIST:
        if tag == name_lower or tag.replace("-", " ") == name_lower.lower():
            tags.add(tag)
            break
    if entry["category"] in ("system-administration",) and "linux" in entry["path"].lower():
        tags.add("linux")
    return [{"name": t} for t in sorted(tags) if t in TAG_WHITELIST][:10]


def create_page(db_id, entry, title, blocks, idmap, headers):
    if title in idmap:
        print(f"  SKIP (already imported): {title}")
        return idmap[title]

    category = CATEGORY_MAP.get(entry["category"], "personal")
    subcategory = infer_subcategory(entry)
    depth = content_depth(entry["nodes"])
    today = time.strftime("%Y-%m-%d")

    properties = {
        "Topic": {"title": [{"type": "text", "text": {"content": title}}]},
        "Category": {"select": {"name": category}},
        "Subcategory": {"select": {"name": subcategory}},
        "Content Depth": {"select": {"name": depth}},
        "Source File": {"rich_text": [{"type": "text", "text": {"content": entry["path"]}}]},
        "Node Count": {"number": entry["nodes"]},
        "Status": {"select": {"name": "imported"}},
        "Last Reviewed": {"date": {"start": today}},
    }

    tags = infer_tags(entry)
    if tags:
        properties["Tags"] = {"multi_select": tags}

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties,
        "children": blocks[:100],
    }

    result = notion_api("POST", "/pages", headers, payload)
    if not result or "id" not in result:
        print(f"  FAILED to create page: {title}")
        return None

    page_id = result["id"]
    print(f"  Created page: {title} ({page_id})")

    remaining = blocks[100:]
    while remaining:
        batch = remaining[:100]
        remaining = remaining[100:]
        notion_api("PATCH", f"/blocks/{page_id}/children", headers, {"children": batch})

    idmap[title] = page_id
    return page_id


def handle_amazon_split(entry, db_id, idmap, headers):
    root = parse_mindmap(entry["path"])
    if root is None:
        return

    aws_keywords = {'ec2', 'ecs', 's3', 'lambda', 'iam', 'rds', 'sqs', 'sns',
        'cloudfront', 'route 53', 'vpc', 'elb', 'cloud', 'aws', 'dynamodb',
        'kinesis', 'redshift', 'elastic', 'beanstalk', 'glacier', 'web service',
        'cloudwatch', 'cloudformation', 'sagemaker', 'api gateway', 'ecr'}

    aws_sections, device_sections = [], []
    for child in root.findall('node'):
        text = node_text(child).lower()
        if any(kw in text for kw in aws_keywords):
            aws_sections.append(child)
        else:
            device_sections.append(child)

    if not aws_sections and not device_sections:
        device_sections = list(root.findall('node'))

    for label, sections in [("Amazon AWS", aws_sections), ("Amazon Devices", device_sections)]:
        if label in idmap or not sections:
            continue
        blocks = []
        for section in sections[:30]:
            heading = node_text(section)
            if not heading or has_secrets(heading):
                continue
            blocks.append(make_text_block("heading_2", heading[:2000]))
            for child in section.findall('node'):
                if len(blocks) >= 95:
                    break
                child_text = node_text(child)
                if child_text and not has_secrets(child_text):
                    blocks.append(make_text_block("bulleted_list_item", child_text[:2000]))
            if len(blocks) >= 95:
                break

        if not blocks:
            blocks = [make_text_block("paragraph", f"Source: {entry['path']}")]

        sub_entry = dict(entry, file=label, nodes=sum(len(list(s.iter())) for s in sections),
                         category="system-administration")
        create_page(db_id, sub_entry, label, blocks, idmap, headers)


def resolve_title_collisions(entries):
    title_counts = {}
    for e in entries:
        title_counts[e["file"]] = title_counts.get(e["file"], 0) + 1

    titles, seen = {}, {}
    for e in entries:
        name = e["file"]
        if title_counts[name] > 1:
            cat = CATEGORY_MAP.get(e["category"], e["category"])
            subcat = infer_subcategory(e)
            suffix = subcat if subcat != "general" else cat
            title = f"{name} ({suffix})"
            if title in seen:
                title = f"{name} ({cat}/{subcat})"
        else:
            title = name
        titles[e["path"]] = title
        seen[title] = True
    return titles


def build_inventory(directories):
    inventory = []
    for dir_path in directories:
        for mm_file in sorted(Path(dir_path).rglob("*.mm")):
            try:
                tree = ET.parse(str(mm_file))
                root = tree.getroot()
                nodes = len(list(root.iter('node')))
            except Exception:
                nodes = 0

            rel = str(mm_file.relative_to(Path(dir_path).parent.parent))
            parts = rel.split('/')
            category = parts[1] if len(parts) > 2 else "root"

            inventory.append({
                "file": mm_file.stem,
                "path": str(mm_file),
                "collection": '/'.join(parts[:2]) if len(parts) > 1 else parts[0],
                "category": category,
                "nodes": nodes,
            })
    return inventory


def main():
    parser = argparse.ArgumentParser(description="Import FreeMind mindmaps into Notion")
    parser.add_argument("--inventory", help="Path to inventory JSON file")
    parser.add_argument("--scan-dirs", nargs="+", help="Directories to scan for .mm files (instead of --inventory)")
    parser.add_argument("--parent-page", help="Notion page ID to create the database under")
    parser.add_argument("--database", help="Existing Notion database ID (skip creation)")
    parser.add_argument("--idmap", default="mindmap_import_map.json", help="Idempotency map file (default: mindmap_import_map.json)")
    parser.add_argument("--skip-files", nargs="*", help="Additional file names to skip")
    parser.add_argument("--dry-run", action="store_true", help="Parse and analyze without calling Notion API")
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: Set NOTION_TOKEN environment variable")
        sys.exit(1)

    headers = get_headers(token) if token else {}

    if args.inventory:
        with open(args.inventory) as f:
            inventory = json.load(f)
    elif args.scan_dirs:
        from pathlib import Path
        inventory = build_inventory(args.scan_dirs)
    else:
        print("ERROR: Provide --inventory or --scan-dirs")
        sys.exit(1)

    idmap = {}
    if os.path.exists(args.idmap):
        with open(args.idmap) as f:
            idmap = json.load(f)

    skip_files = SKIP_FILES_DEFAULT.copy()
    if args.skip_files:
        skip_files.update(args.skip_files)

    eligible = [e for e in inventory
                if e["file"] not in skip_files
                and e["category"] not in SKIP_CATEGORIES_DEFAULT
                and e["file"] != "Amazon"]

    print("=" * 60)
    print("Mindmap-to-Notion Import")
    print("=" * 60)
    print(f"\nTotal in inventory: {len(inventory)}")
    print(f"Eligible for import: {len(eligible)} + 2 (Amazon split)")
    print(f"Already imported: {len(idmap)}")

    if args.dry_run:
        titles = resolve_title_collisions(eligible)
        for e in eligible:
            t = titles.get(e["path"], e["file"])
            depth = content_depth(e["nodes"])
            print(f"  {t} [{depth}, {e['nodes']} nodes]")
        print(f"\nDry run complete. {len(eligible)} pages would be created.")
        return

    if args.database:
        db_id = args.database
    elif "tech_ref_db_id" in idmap:
        db_id = idmap["tech_ref_db_id"]
        print(f"\nUsing existing database: {db_id}")
    elif args.parent_page:
        print("\nCreating Technical Reference database...")
        db_id = create_database(args.parent_page, headers)
        if not db_id:
            print("FATAL: Could not create database")
            sys.exit(1)
        idmap["tech_ref_db_id"] = db_id
    else:
        print("ERROR: Provide --parent-page or --database")
        sys.exit(1)

    amazon_entry = next((e for e in inventory if e["file"] == "Amazon"), None)
    if amazon_entry and "Amazon AWS" not in idmap and "Amazon Devices" not in idmap:
        print("\n--- Splitting Amazon.mm ---")
        handle_amazon_split(amazon_entry, db_id, idmap, headers)

    titles = resolve_title_collisions(eligible)
    imported, skipped, failed = 0, 0, 0

    for i, entry in enumerate(eligible):
        title = titles.get(entry["path"], entry["file"])
        if title in idmap:
            skipped += 1
            continue

        print(f"\n[{i+1}/{len(eligible)}] {title} ({entry['nodes']} nodes)")

        root = parse_mindmap(entry["path"])
        if root is None:
            print("  SKIP: Could not parse XML")
            failed += 1
            continue

        full_text = ET.tostring(root, encoding='unicode')
        if has_secrets(full_text):
            print("  SKIP: Contains secrets")
            failed += 1
            continue

        blocks = collect_blocks(root, 0, 95)
        if not blocks:
            blocks = [make_text_block("paragraph", f"Source: {entry['path']}\nNodes: {entry['nodes']}")]

        page_id = create_page(db_id, entry, title, blocks, idmap, headers)
        if page_id:
            imported += 1
        else:
            failed += 1

        if imported % 10 == 0:
            with open(args.idmap, 'w') as f:
                json.dump(idmap, f, indent=2)

    with open(args.idmap, 'w') as f:
        json.dump(idmap, f, indent=2)

    print("\n" + "=" * 60)
    print(f"DONE: {imported} imported, {skipped} skipped (already done), {failed} failed")
    print(f"Database ID: {db_id}")
    print(f"Idempotency map: {args.idmap}")
    print("=" * 60)


if __name__ == "__main__":
    main()
