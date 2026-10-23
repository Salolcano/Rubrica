# Rubrica design

## Purpose

Rubrica makes subjective judging of text submissions credibly neutral. It is meant to be reused by bounties, grants, hackathons and design or writing contests that need a payout decided by a rubric nobody can change afterwards.

## State

| Storage | Type | Purpose |
|---|---|---|
| `contest_count` | u256 | Last issued contest id. |
| `contests` | TreeMap[u256, Contest] | One record per contest: sponsor, committed rubric and its hash, prize, deadlines, minimum score, band width, status, counters, best entry and band, settlement. |
| `entries` | TreeMap[str, Entry] | Key `"<contest_id>:<index>"`. URL, committed hash, status, band (tier and its lower edge), rationale, strikes, cooldown. |
| `entrant_index` | TreeMap[str, u256] | Key `"<contest_id>:<address>"`, enforces one entry per address. |

Contest status: `open` then exactly one of `settled`, `refunded`, `cancelled`. Entry status: `pending` then `scored` or `disqualified`. There are no other transitions, and terminal states are never left.

## Where non-determinism is allowed

Only inside `judge_entry`, via `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`. Everything the observation needs is copied out of storage first. The observation returns a plain dict:

- `{"kind": "analysis", "tier": band index, "rationale": str}` (the raw 0 to 100 score is converted to a band inside the observation and discarded)
- `{"kind": "integrity_failure", "class": "hash_mismatch" | "artifact_too_large"}`
- `{"kind": "error", "class": "fetch_unavailable" | "empty_page" | "invalid_body" | "llm_execution_failure" | "malformed_*"}`

State is written only after consensus returns, so a failed consensus leaves storage untouched.

## Equivalence rule

`_equivalent(leader, mine)`:

1. Both results must be well formed.
2. Kinds must match.
3. Analyses: `leader.tier == mine.tier`.
4. Integrity failures: classes must match.
5. Errors: any two errors are equivalent (they only trigger a retry).

### Why bands instead of a numeric tolerance

An earlier version accepted any two scores within a sponsor-chosen tolerance and stored the leader's exact score. That is unsafe: with a tolerance of 5, scores of 59 and 61 are "equivalent" but sit on opposite sides of a pass line at 60, and two entries 3 points apart could swap rank depending on which validator happened to lead.

The fix is to make the value that decides payment the value validators agree on exactly:

- Scores are quantized to a band (`tier = min(score // width, 100 // width - 1)`) before comparison.
- The pass line must be a multiple of the width and below the top band, so it is always a band edge and never inside a band.
- Only the tier (and its lower edge) is stored; ranking uses the tier, ties go to the earliest entry; payment is `tier * width >= min_score`.

Therefore every pair of equivalent results stores identical state, and the winner and payout cannot depend on which compatible result became the accepted one. Rationale text is stored from the leader for display only; it is not compared and never read by payment code.

### Trade-off

Quantization moves the disagreement to band edges. A score that genuinely lies near an edge may fail consensus, in which case the transaction changes nothing and can be retried with a fresh leader and validator set. This is a liveness cost, never a safety cost. Wider bands fail less often but separate entries less finely.

## Money

`_send_gen` is the only place value leaves the contract. Callers set the terminal status and `paid_amount` first. Terminal states cannot be re-entered, so the prize leaves exactly once. There are no fees, splits or partial payouts.

## Time

All deadlines use unix seconds from the deterministic transaction time. Submission is open strictly before `submit_by`; judging is allowed from `submit_by` until `judge_by`; settlement is allowed once all entries are judged or `judge_by` has passed.

## Threats considered

| Threat | Mitigation |
|---|---|
| Sponsor changes rules after seeing entries | Rubric, band width, minimum score and deadlines are committed at creation and never editable. |
| Sponsor enters their own contest | Rejected. |
| Entrant swaps content after submitting | Hash is checked by every validator before the LLM sees the text. |
| Entrant tricks the judge with instructions in the text | Rubric and entry are one JSON data block labelled untrusted; escaped by `json.dumps`. |
| Transient page error disqualifies an honest entrant | Two integrity strikes are required, with a cooldown in between. |
| A single outage blocks the contest forever | Anyone can settle after `judge_by`; unjudged entries are ignored. |
| Spamming judge calls | Permissionless but rejected once judged, during cooldown, or outside the window. |
| One address floods entries | One entry per address and a 20-entry cap. |
| SSRF style URLs | HTTPS only, no credentials, no IP literals, no localhost or `.local`, port 443 only. |

## Known limits

- Sybil entrants are possible; Rubrica limits entries per address, not per person.
- The hash binds text, not authorship or truth.
- A page whose content depends on who fetches it will cause integrity failures.
- Validators share model biases; bands bound disagreement between validators but not common bias.
- Entries in the same band tie by design; sponsors who need finer ranking should choose a narrower band width.
- Only plain text entries are supported.
