---
phase: "04"
slug: "stage-wrappers"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-10-11"
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| model output → developer terminal | Raw LLM text is untrusted and printed | model reply strings, error fragments |
| forwarded call kwargs → stdout | kwargs may carry credentials | api_key and other redact_keys |
| test patches → class attributes | wraps on library classes must not leak past a test | class attribute monkeypatches |
| model-derived extraction text / source slices → terminal | Slices and extraction text from untrusted model output | extraction text, source slices |
| wrapper → Annotator | wrappers must not alter pipeline objects | parse/align return and yield objects |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering/Spoofing | `_print_block` / `_safe_text` | medium | mitigate | All str payloads via `_safe_text`; Test B | closed |
| T-04-02 | Information disclosure | model wrapper kwargs | medium | mitigate | `redact(..., keys=config['redact_keys'])`; Test D | closed |
| T-04-03 | Denial of service / integrity | chunk/model generators | medium | mitigate | `next()` loop, lazy same-object yields; Tests A/E/F | closed |
| T-04-04 | Tampering | test class-attribute patches | low | mitigate | `mock.patch.object` via `enter_context`; Test E | closed |
| T-04-SC | Tampering | package installs | low | accept | No packages added | closed |
| T-04-05 | Tampering/Spoofing | parse callout error text | medium | mitigate | Error text via `_safe_text`; Test K | closed |
| T-04-06 | Tampering | `make_parse_wrapper` | medium | mitigate | Returns original `out`; snapshots before return; Test H | closed |
| T-04-07 | Repudiation | empty-parse callout | low | mitigate | Re-run diagnosis; Test J matrix | closed |
| T-04-08 | Denial of service | diagnosis re-run | low | accept | Re-run only on empty result, local parse | closed |
| T-04-09 | Tampering/Spoofing | `_source_slice`, align lines | medium | mitigate | Slice/extraction text via `repr`/`_safe_text` | closed |
| T-04-10 | Tampering | `make_align_wrapper` | medium | mitigate | Lazy yields + `finally` snapshot; Test N | closed |
| T-04-11 | Elevation / persistence of patches | `trace_probes` integration | high | accept | Deferred — Phase 3/`trace_probes` + Tests R/S not required to seal Phase 4; `_patch_stages` covers test path (T-04-04) | closed |
| T-04-12 | Information disclosure | records after failed call | low | accept | Partial records hold redacted primitives; local stdout only | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-SC | T-04-SC | No new packages; stdlib + existing .venv only | user (UAT/secure-phase) | 2026-10-11 |
| AR-04-08 | T-04-08 | Diagnosis re-run only on empty parse result; pure local parse of a short string; no model call | user (UAT/secure-phase) | 2026-10-11 |
| AR-04-11 | T-04-11 | Production `trace_probes` install/restore (Tests R/S) deferred with Phase 3 Task 2; Phase 4 ships wrappers exercised via `_patch_stages` which restores class attrs (T-04-04). Revisit when Phase 3 lands. | user (UAT/secure-phase) | 2026-10-11 |
| AR-04-12 | T-04-12 | Partial records after failed calls hold already-redacted primitives; printed to local stdout only | user (UAT/secure-phase) | 2026-10-11 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-11 | 13 | 13 | 0 | gsd-security-auditor + user accept T-04-11 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-11
