# Rubrica

Rubrica is a standalone GenLayer Intelligent Contract primitive for **rubric-committed contest escrow**.

A sponsor locks a GEN prize and commits, in one transaction, a scoring rubric, a submission deadline, a judging window, a minimum passing score and a band width. Entrants submit one HTTPS URL plus the SHA-256 of the text published there. After submissions close, validators independently fetch each entry, verify the committed hash, and score it from 0 to 100 against the committed rubric. Deterministic contract code alone moves the money: the highest consensus score wins the whole prize if it reaches the minimum score, otherwise the sponsor is refunded in full.

Rubrica is an escrow primitive, not a frontend, marketplace or identity system.

## Why GenLayer?

Whether a piece of writing is accurate, clear or original cannot be decided by ordinary deterministic contract code. Today that judgement is made by a person or a single off-chain model, so the sponsor can quietly change the rules or favour an entrant. Rubrica removes both levers: the rubric is fixed before any entry exists, the entry bytes are hash-bound, and the score is accepted only when independent validators agree.

## How consensus is used

Scoring is subjective, so exact agreement between validators on a 0 to 100 number would almost never happen. But accepting "close enough" numbers is also unsafe: two scores a point apart can sit on opposite sides of the pass line or change the winner. Rubrica solves this by making the *payment-relevant value* the thing validators agree on exactly.

- Raw scores are quantized into **bands** of a width the sponsor commits (5, 10, 20, 25 or 50 points). With width 10 the bands are 0-9, 10-19, ... 90-100. A score of 100 belongs to the top band.
- The **minimum score must sit exactly on a band edge** (a multiple of the width, never inside a band).
- The leader and every validator fetch the entry, check the hash, score it, and convert the score to a band. They are **equivalent only when they reach the same band** (or the same kind of failure). Rationale text is never compared and never affects payment.
- Only the band is stored. The raw score is discarded.

Safety property: any two results the consensus rule accepts are identical in everything the contract stores and pays from, so they produce the same winner and the same payout. Scores on opposite sides of a band edge, including the pass line, are never equivalent, so consensus simply fails and nothing changes. The tests check this exhaustively for every allowed width.

The cost is honesty about precision: an entry scored right at a band edge may need a retry, and entries in the same band tie (earliest wins). Validators disagreeing leaves state untouched; it can never produce a wrong payout.

## Lifecycle

1. `create_contest(title, rubric, submit_by, judge_window, min_score, band_width)` (payable) locks the prize and returns the contest id.
2. `submit_entry(contest_id, url, content_hash)` is open to everyone except the sponsor, one entry per address, up to 20 entries, until `submit_by`.
3. After `submit_by`, anyone may call `judge_entry(contest_id, entry_index)` for each pending entry until the judging window closes.
4. `settle(contest_id)` is permissionless. It is allowed when every entry is judged, or when the judging window has ended.
5. `cancel_contest(contest_id)` lets the sponsor reclaim the prize only while the contest has no entries.

## Payment rules

- The winner is the entry in the highest band. Entries in the same band tie, and the earliest submission wins.
- If the best band's lower edge is at least `min_score`, 100% of the prize is dispatched to the winner.
- Otherwise (including no entries, or none scored) 100% is dispatched back to the sponsor.
- Unjudged entries when the window ends are ignored; they cannot win.
- Contract state is debited before any transfer, and a contest can be settled only once.

## Failure handling

- **Fetch or LLM failure, empty page, malformed output:** the entry stays pending with a 15-minute retry cooldown. These never score, disqualify or move money.
- **Hash mismatch or oversize page:** counts as an integrity strike. Two strikes disqualify the entry. The first strike allows for a transient error page being served.
- **No validator agreement:** the transaction does not change state.
- **Prompt injection:** the rubric and entry are passed as one JSON data block that is declared untrusted, and the model is told not to follow instructions inside it.

## What the hash covers

The hash is the SHA-256 of the page text after collapsing every run of whitespace into one space. Line endings and trailing blank lines therefore do not matter. It binds the text, not the author, the truth of the claims, or who controls the URL.

## Limits

| Setting | Value |
|---|---|
| Minimum prize | 0.001 GEN |
| Entries per contest | 20 |
| Entry text size | 12,000 bytes |
| Rubric / title length | 1,500 / 120 characters |
| Band width | 5, 10, 20, 25 or 50 points |
| Minimum score | multiple of the band width, from one band up to just below the top band |
| Judge retry cooldown | 15 minutes |

## Repository layout

- `contracts/rubrica.py`: the contract.
- `tests/`: a local harness and 76 direct tests.
- `docs/DESIGN.md`: state design and security reasoning.
- `docs/DEPLOYMENT.md`: how to deploy and exercise it on Studio Next.
- `scripts/`: `preflight.py` release gate, `export_abi.py`, `hash_entry.py`.
- `artifacts/rubrica.abi.json`: public method list.
- `examples/`: demo rubric, sample entries and their hashes.
- `evidence/`: local test output and a template for the live Studio Next run.

## Run the checks

```
python scripts/preflight.py
```

This needs only Python 3.10 or newer; no packages are installed.
