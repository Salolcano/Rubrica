# Deploying and testing Rubrica on Studio Next

Network details:

- Network: Studio Next
- RPC: https://studio-next.genlayer.com/api
- Chain ID: 61997
- Explorer: https://explorer-studio-dev.genlayer.com/

## 1. Check the repository locally (optional)

```
python scripts/preflight.py
```

It should end with `preflight=PASS`.

## 2. Deploy

1. Open Studio Next and select the **Studio Next** network (chain 61997).
2. Create a new contract file and paste the full contents of `contracts/rubrica.py`. The first two lines (`# v0.3.0` and the `Depends` line) must stay at the very top.
3. Deploy with no constructor arguments.
4. Copy the deployed contract address.

## 3. Run the demo

Use the material in `examples/README.md`.

1. Put the three sample entry files on GitHub and copy each file's Raw URL.
2. As the sponsor account, call `create_contest` with a value of at least 0.001 GEN:
   - `title`: Best explainer: why do cats purr?
   - `rubric`: the text from `examples/README.md`
   - `submit_by`: current unix time plus at least 600 seconds
   - `judge_window`: 3600
   - `min_score`: 50
   - `band_width`: 10 (the minimum score must be a multiple of this)
3. Switch to three different accounts and call `submit_entry(1, <raw url>, <hash>)` once from each, using the hashes listed in `examples/README.md`.
4. Wait until `submit_by` has passed.
5. Call `judge_entry(1, 1)`, `judge_entry(1, 2)`, `judge_entry(1, 3)` from any account.
6. Call `get_leaderboard(1)` to see scores and `get_entries(1)` for rationales.
7. Call `settle(1)`. The winner receives the full prize.

## 4. Record the run

Fill in `evidence/studio-next-run.md` with the contract address and transaction hashes so reviewers can follow the run on the explorer.

## Expected behaviour to confirm

- `judge_entry` on an entry whose page text changed after submission ends with `last_reason = hash_mismatch` and stays pending.
- `settle` before the window ends and before all entries are judged is rejected.
- A second `settle` is rejected.
