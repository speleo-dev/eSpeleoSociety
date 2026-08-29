# eSpeleo Security Hardening - Master Plan

> **Execution strategy:** Use superpowers:subagent-driven-development for parallel task execution

**Goal:** Fix all 7 critical + 4 high priority security issues before production

**Timeline:** 2-3 weeks (15-20 dev days)

**Risk mitigation:** Each phase is independently testable and deployable

---

## Quick Reference

| Phase | Findings | Files | Est. Days | Priority |
|-------|----------|-------|-----------|----------|
| 1 | #1-3 Auth fail-open | `backend/auth.py`, `dev_server.py` | 2-3 | Critical |
| 2 | #4-5 Secrets/Encryption | `crypto_utils.py`, `config.py` | 2-3 | Critical |
| 3 | #6 Birth date encryption | `db.py`, migrations | 1-2 | Critical |
| 4 | #9-12 UI bugs | `dialogs/*.py` | 2-3 | High |
| 5 | #18 Atomic eCP | `db.py`, `ecp_issuance.py` | 2-3 | High |

**Total:** 9-14 days core development + 3-6 days testing/docs

---

## Phase Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Auth Fail-Closed (2-3 days)                      │
│  ├─ Task 1.1: Require JWKS in production                   │
│  ├─ Task 1.2: Enforce JWT exp claim                        │
│  ├─ Task 1.3: Algorithm confusion protection               │
│  └─ Task 1.4: Remove hardcoded defaults                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: Secrets Security (2-3 days)                      │
│  ├─ Task 2.1: PBKDF2 key derivation                        │
│  ├─ Task 2.2: AES-GCM encryption                           │
│  ├─ Task 2.3: Atomic file writes                           │
│  └─ Task 2.4: Deprecate old crypto                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: DB Encryption (1-2 days)                         │
│  ├─ Task 3.1: pgp_sym_encrypt for birth dates              │
│  └─ Task 3.2: Migration script                             │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: UI Bug Fixes (2-3 days)                          │
│  ├─ Task 4.1: Notifications checkbox                       │
│  ├─ Task 4.2: Photo hash from content                      │
│  ├─ Task 4.3: Cancel portrait reset                        │
│  └─ Task 4.4: President validation                         │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: Atomic eCP Issuance (2-3 days)                   │
│  ├─ Task 5.1: Transaction wrapper for eCP issuance         │
│  ├─ Task 5.2: Rollback on partial failure                  │
│  └─ Task 5.3: Integration tests                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Plans

### Phase 1: Auth Hardening
**File:** `docs/superpowers/plans/2026-07-17-security-hardening-phase1.md`

```bash
# Execute with:
rtk execute docs/superpowers/plans/2026-07-17-security-hardening-phase1.md
```

**Key changes:**
- `backend/auth.py` - fail-closed auth, exp enforcement
- Tests: 8+ new security tests

---

### Phase 2: Secrets Hardening  
**File:** `docs/superpowers/plans/2026-07-17-security-hardening-phase2.md`

```bash
# Execute with:
rtk execute docs/superpowers/plans/2026-07-17-security-hardening-phase2.md
```

**Key changes:**
- New `crypto_utils.py` - PBKDF2 + AES-GCM
- `config.py` - atomic file writes
- Tests: 10+ new crypto tests

---

### Phase 3-4: DB Encryption + UI Bugs
**File:** `docs/superpowers/plans/2026-07-17-security-hardening-phase3-4.md`

```bash
# Execute with:
rtk execute docs/superpowers/plans/2026-07-17-security-hardening-phase3-4.md
```

**Key changes:**
- `db.py` - pgp_sym_encrypt for birth dates
- `dialogs/*.py` - UI bug fixes
- Tests: 8+ new tests

---

### Phase 5: Atomic eCP Issuance
**Quick spec:**

```python
# Current (4 separate transactions):
def issue_ecp(...):
    insert_ecp(...)           # T1
    update_ecp_record(...)    # T2  <- FAILS HERE = orphan
    update_member_ecp_hash(...) # T3
    update_ecp_request_status(...) # T4

# Target (1 atomic transaction):
def issue_ecp_atomic(...):
    with db.transaction() as tx:
        insert_ecp(..., tx)
        update_ecp_record(..., tx)
        update_member_ecp_hash(..., tx)
        update_ecp_request_status(..., tx)
        # All succeed or all rollback
```

**Files:**
- `espeleo/db.py` - add transaction context manager
- `espeleo/ecp_issuance.py` - wrap in transaction
- `tests/test_ecp_atomic.py` - failure injection tests

---

## Verification Checklist

### Before Each Phase
- [ ] Run existing tests: `pytest tests/ -v`
- [ ] Verify no regressions
- [ ] Review security test coverage

### After Each Phase  
- [ ] Run new tests: `pytest tests/test_*<phase>*.py -v`
- [ ] Run full suite: `pytest tests/ -v`
- [ ] Update `CODE_AUDIT.md` status
- [ ] Commit with descriptive message

### Final Verification
- [ ] All 25 audit findings reviewed
- [ ] Security tests: 30+ covering new code
- [ ] No hardcoded secrets in code
- [ ] All critical paths tested

---

## Git Workflow

```bash
# Create feature branch
git checkout -b security-hardening-2026-07

# After each phase
git add <files>
git commit -m "security(phase<N>): <summary>"

# Push for review
git push origin security-hardening-2026-07

# Create PR on GitHub
gh pr create --title "Security Hardening: Critical Fixes" \
             --body "Fixes audit findings #1-7, #9-12, #18"
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing secrets | Phase 2 maintains backward compatibility |
| DB migration failures | Phase 3 uses additive migration (new column) |
| UI regressions | Phase 4 has comprehensive tests |
| Transaction deadlocks | Phase 5 uses short transactions, proper ordering |
| Production deployment | Each phase independently deployable |

---

## Success Criteria

✅ All critical security issues fixed (#1-7)
✅ All high-priority bugs fixed (#9-12, #18)
✅ 100% test coverage for new security code
✅ No plaintext secrets on disk
✅ Production requires JWKS
✅ All JWTs have exp claim
✅ UI bugs no longer silent
✅ eCP issuance is atomic

---

## Next Steps

1. **Start Phase 1:** Execute auth hardening plan
2. **Parallel option:** Phase 2 can start after Phase 1 Task 1
3. **Review:** Request code review after each phase
4. **Deploy:** Phase 1-2 can deploy independently

**Command to start:**
```bash
rtk execute docs/superpowers/plans/2026-07-17-security-hardening-phase1.md
```
