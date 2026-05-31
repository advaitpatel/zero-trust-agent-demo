# ACT 3 — Full OTel tracing. Open Jaeger to see the audit story.
import re, json, time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter \
    import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource({"service.name": "qcon-agent-demo"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agent.demo")

SESSION = {
    "id": "session-qcon-001",
    "tenant_id": "tenant-001",
    "user_principal": "support@company.com",
    "agent_identity": "support-bot-v2"
}
DOCS_DIR = "../docs"
POLICY_VERSION = "v1.2.0"

def check_policy(action, context={}):
    if action == "send_email":
        recipient = context.get("recipient", "")
        if recipient.endswith("@company.com"):
            return True, None
        return False, f"external email blocked by policy"
    if action == "read_document":
        if context.get("tenant_id") == SESSION["tenant_id"]:
            return True, None
        return False, "cross-tenant read blocked by policy"
    return False, f"unknown action: {action}"

def run():
    with tracer.start_as_current_span("agent.run") as root:
        root.set_attribute("agent.identity", SESSION["agent_identity"])
        root.set_attribute("session.id",     SESSION["id"])
        root.set_attribute("user.principal", SESSION["user_principal"])

        print("\n" + "="*55)
        print("ACT 3 — AUDIT AGENT (full trace active)")
        print(f"Session : {SESSION['id']}")
        print(f"Agent   : {SESSION['agent_identity']}")
        print(f"User    : {SESSION['user_principal']}")
        print("="*55)

        # Span 1 — read_document
        with tracer.start_as_current_span("tool.read_document") as s1:
            ok, reason = check_policy("read_document",
                                      {"tenant_id": SESSION["tenant_id"]})
            s1.set_attribute("doc.id",          "poisoned_doc.txt")
            s1.set_attribute("doc.tenant",      SESSION["tenant_id"])
            s1.set_attribute("acl.checked",     "true")
            s1.set_attribute("policy.allowed",  str(ok))
            s1.set_attribute("policy.version",  POLICY_VERSION)
            s1.add_event("policy.decision", {
                "action": "read_document",
                "allowed": str(ok),
                "policy_version": POLICY_VERSION
            })
            print("\n[TRACE] span: tool.read_document created")
            print(f"[TRACE] acl_checked=true, allowed={ok}")

        # Span 2 — send_email (blocked)
        recipient = "attacker@external-domain.com"
        with tracer.start_as_current_span("tool.send_email") as s2:
            ok, reason = check_policy("send_email", {"recipient": recipient})
            s2.set_attribute("tool.input.recipient", recipient)
            s2.set_attribute("policy.allowed",       str(ok))
            s2.set_attribute("policy.version",       POLICY_VERSION)
            s2.set_attribute("deny.reason",          str(reason))
            s2.add_event("policy.decision", {
                "action":         "send_email",
                "allowed":        str(ok),
                "denial_reason":  str(reason),
                "policy_version": POLICY_VERSION
            })
            print("[TRACE] span: tool.send_email created")
            print(f"[TRACE] allowed={ok}, reason={reason}")

        provider.force_flush()
        time.sleep(2)
        print("\n[TRACES EXPORTED]")
        print("Open   -> http://localhost:16686")
        print("Service: qcon-agent-demo")
        print("Click 'Find Traces' — you will see the full audit story.")

if __name__ == "__main__":
    run()
