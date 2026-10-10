# 04 — Resolve the pending OpenEye academic licence request

Type: task
Status: open
Blocked by: —
Map: [Synthetic Task Scaling at <8B](../map.md)

## Question

Did the OpenEye academic / non-commercial licence request succeed, and what changes if it did?

The user has submitted a request; no response as of 2026-10-09. Research found that **every
OpenEye academic option requires the applicant to be employed by and actively participating in
research or teaching at an accredited degree-granting institution**, and no prices are published
anywhere — so a grant to an unaffiliated individual would be unexpected. The map currently
assumes **denial** and designs entirely around open tools.

This ticket exists so the assumption is tracked rather than forgotten, and so the follow-on
consequences are written down before the answer arrives.

Work to do:

1. Track the request to a definite yes or no. If no response within a reasonable window, chase
   it once, then record it as denied and move on — the map must not stall on it.
2. If **denied** (expected): confirm the three consequences already recorded on the map —
   POSIT + Chemgauss4 substituted (ticket 03), the 15 OpenEye properties dropped from the 116,
   and the `.oedu` design-unit filter criterion dropped from the PLINDER filter (ticket 05).
   Verify no other part of the spec silently depends on OpenEye. **Then close this ticket as the
   confirmed baseline, not as a failure.**
3. If **granted**: this is the single highest-leverage change to the map. Rule out of scope
   nothing; instead record which decisions reopen, and re-ticket them:
   - Tier-2 oracle fidelity (ticket 03's substitution may become unnecessary)
   - the 15 OpenEye properties return to the Tier-1 property pool, changing ticket 06
   - the `.oedu` filter criterion returns to ticket 05's PLINDER filter
   - verify the licence terms permit **publishing results and code** from a public portfolio
     repo, which is the destination's whole point — a licence that forbids this is worse than
     no licence, and that must be checked before any OpenEye tool enters the pipeline.

Note that even a grant does **not** unlock SQM2.20, which is separately unavailable and already
out of scope.

## Answer

<!-- append on resolution -->
