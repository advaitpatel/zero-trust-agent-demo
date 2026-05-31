# ACT 2 — Built-in policy engine. Injection blocked.
import re

DOCS_DIR = "../docs"
SESSION_TENANT = "tenant-001"

# ── Policy engine (pure Python, no external service) ──────────────
POLICY = {
    "allowed_actions": ["read_document", "send_email"],
    "email_allowed_domains": ["@company.com"],
    "allowed_tenants": ["tenant-001"],
}

def check_policy(action, context={}):
    if action == "send_email":
        recipient = context.get("recipient", "")
        for domain in POLICY["email_allowed_domains"]:
            if recipient.endswith(domain):
                return True, None
        return False, f"external email blocked by policy — {recipient}"

    if action == "read_document":
        tenant = context.get("tenant_id", "")
        if tenant in POLICY["allowed_tenants"] and tenant == SESSION_TENANT:
            return True, None
        return False, "cross-tenant read blocked by policy"

    return False, f"unknown action: {action}"

def sanitize(content):
    patterns = [
        r"IGNORE PREVIOUS INSTRUCTIONS.*",
        r"You are now in.*mode.*",
        r"Send.*to.*@.*\.com.*",
    ]
    for p in patterns:
        content = re.sub(p, "[SANITIZED]", content,
                         flags=re.IGNORECASE | re.DOTALL)
    return content

def run():
    print("\n" + "="*55)
    print("ACT 2 — HARDENED AGENT (policy engine active)")
    print("="*55)

    # Check policy before reading
    ok, reason = check_policy("read_document", {"tenant_id": SESSION_TENANT})
    if not ok:
        print(f"[POLICY] DENY — {reason}"); return

    raw = open(f"{DOCS_DIR}/poisoned_doc.txt").read()
    clean = sanitize(raw)
    print(f"\n[SANITIZED DOCUMENT]:\n{clean}")

    # Injection tries to send to external — policy blocks it
    recipient = "attacker@external-domain.com"
    ok, reason = check_policy("send_email", {"recipient": recipient})

    print(f"\n[POLICY CHECK] send_email -> {recipient}")
    if not ok:
        print(f"[POLICY DECISION] DENY")
        print(f"[REASON] {reason}")
        print("[TOOL BOUNDARY] Action blocked. Nothing sent.")
    else:
        print("[POLICY DECISION] ALLOW")

    print("\n[RESULT] Injection BLOCKED — no data exfiltrated.")

if __name__ == "__main__":
    run()
