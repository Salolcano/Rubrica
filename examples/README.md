# Example contest material

A ready-made demo you can run on Studio Next without writing any code.

**Contest title:** Best explainer: why do cats purr?

**Rubric (paste exactly):**
Score 0 to 100. Award up to 40 points for factual accuracy, up to 30 for clarity, up to 20 for at least one concrete example, and up to 10 for a balanced conclusion. Penalise vague or unsupported claims.

**Suggested settings:** minimum score 50, band width 10.

The three text files in this folder are sample entries (strong, average, weak). To use them,
publish this repository on GitHub and use each file's **Raw** URL as the entry URL. The
`content_hash` for each file is printed by `python scripts/hash_entry.py examples/<file>`:

- `entry_1_strong.txt`: `0x778bbca91f486765550c996801f570cb91af295c123f757b4e0f2d69d7243a2d`
- `entry_2_average.txt`: `0x7e91c7c73da389dafc5ae1a439ed169c61a6753796961e65ce70d5469b1223e1`
- `entry_3_weak.txt`: `0xa284adf2a05864d72b76db4022e10aa89eff70de35d81da19c864b007936cd55`

Whatever URL you use must return the same text you hashed (extra spaces or blank lines are fine).
