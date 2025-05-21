import re
import yaml
from pathlib import Path

DOMAINS_FILE = "domains_seen.txt"
OUTPUT_FILE = "whitelist_generated.yaml"

def smart_regex(domain):
    """
    Generate a regex with:
    - [0-9]+ for numeric segments
    - .* for multi-subdomains
    - Escaped dots elsewhere
    """
    parts = domain.split('.')
    if len(parts) >= 3:
        domain_core = '.'.join(parts[-2:])
        subdomain = parts[0]
        if re.match(r'^[a-zA-Z\-]*\d+[a-zA-Z\-]*$', subdomain):
            sub_regex = re.sub(r'\d+', r'[0-9]+', subdomain)
            return f"{re.escape(sub_regex)}\\.{re.escape(domain_core)}"
        else:
            return f".*\\.{re.escape(domain_core)}"
    else:
        return re.escape(domain)

def prompt_user(domain, suggestion):
    print(f"[?] Domain: {domain}")
    print(f"    Suggested regex: \"{suggestion}\"")
    choice = input("Accept (y) / Skip (n) / Edit (e) / Quit (q)? ").strip().lower()
    if choice == "y":
        return suggestion
    elif choice == "e":
        custom = input("Enter custom regex: ").strip()
        return custom if custom else None
    elif choice == "q":
        return "QUIT"
    return None

def main():
    if not Path(DOMAINS_FILE).exists():
        print(f"[!] File not found: {DOMAINS_FILE}")
        return

    with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
        domains = sorted(set(line.strip() for line in f if line.strip()))

    print(f"[+] Loaded {len(domains)} unique domains\n")

    accepted_regexes = []

    for domain in domains:
        suggestion = smart_regex(domain)
        result = prompt_user(domain, suggestion)

        if result == "QUIT":
            break
        elif result:
            accepted_regexes.append(result)

    print("\n[~] Final regex list:")
    for r in accepted_regexes:
        print(f"  - \"{r}\"")

    save = input("\nSave these to whitelist_generated.yaml? (y/n): ").strip().lower()
    if save == "y":
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                yaml.dump({"whitelist": accepted_regexes}, f, default_flow_style=False)
            print(f"[✓] Saved to {OUTPUT_FILE}")
        except Exception as e:
            print(f"[!] Failed to save: {e}")
    else:
        print("[×] Discarded changes.")

if __name__ == "__main__":
    main()
