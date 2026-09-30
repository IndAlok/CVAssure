# RESULTS_TABLE — the coverage input CSV

**Owner:** Person 5 produces it. **Person 1 consumes it.** Column names frozen day 1,
`contracts-v1`. Person 1 wrote the header; **Person 5 owns the rows and the numbers.**

---

## 1. One CSV, these columns, this order

```text
attack_class,variant,dataset,n_seeds,detection_rate_mean,detection_rate_std,precision_mean,recall_mean,auroc_mean,false_alarm_rate_mean,runtime_s_median,access_level,notes
```

| column | type | meaning |
|---|---|---|
| `attack_class` | string | must match a row name in `configs/coverage_rules.yaml` |
| `variant` | string | the specific scenario, e.g. `patch-16x16`, `fog-haze-0.4` |
| `dataset` | string | e.g. `synthetic-s42`, or a public dataset + licence |
| `n_seeds` | int | **seeds, not samples.** 3 is the minimum for a Supported row |
| `detection_rate_mean` | float 0–1 | fraction of seeded attacks detected |
| `detection_rate_std` | float | across seeds. A high std is itself a finding |
| `precision_mean` | float 0–1 | true positives over everything flagged |
| `recall_mean` | float 0–1 | same as detection rate for a single attack family; both are kept for the report |
| `auroc_mean` | float 0–1 | score separation on the control |
| `false_alarm_rate_mean` | float 0–1 | **on a clean control set.** Without this, no row can be Supported |
| `runtime_s_median` | float | median over seeds, seconds, this machine |
| `access_level` | string | `white-box` \| `gray-box` \| `black-box` |
| `notes` | string | free text, including what was not done |

Empty cells are legal and mean **not measured**. An empty `detection_rate_mean` yields
`Untested`, never a guess and never a zero.

---

## 2. The rows that must exist

| `attack_class` | no row means |
|---|---|
| `Patch / blend trigger in data` | Untested |
| `Label flipping` | Untested |
| `Near-duplicate flooding` | Untested |
| `OOD insertion` | Untested |
| `Model substitution` | Untested |
| `Backdoored model` | Untested |
| `Record tampering / replay` | Untested |
| `Natural shift (fog vs patch)` | Untested |
| `Cross-asset linking` | Untested |
| `Adaptive attackers` | **Unsupported**, declared. Do not measure |
| `Imperceptible clean-label perturbations` | **Unsupported**, declared. Do not measure |
| `Hardware / compiler backdoors` | **Unsupported**, declared. Do not measure |

`Cross-asset linking` is a coverage row like any other. It needs the four variants from
`MANIFEST.md` §4 and at least 3 seeds, because **the negative controls are the measurement**:
a linker that links everything scores 1.0 recall and demonstrates nothing.

**`n_seeds >= 3` is a hard floor for Supported.** One seed is an anecdote. The judge will ask
how many seeds, and the CSV is where the answer lives.

---

## 3. The clean control, and why it is the important column

`false_alarm_rate_mean` is measured on a **clean control set with no attack of that family**.
It is what separates a detector from a noise generator, and the status rule gates on it:

```text
Supported  requires  detection_rate_mean >= 0.80
                    AND false_alarm_rate_mean <= 0.05
                    AND n_seeds >= 3
```

A row with 0.99 detection and 0.4 false alarms is **Partial**, not Supported. Say so. The
whole credibility of the coverage statement rests on being willing to publish the bad column.

---

## 4. Status is derived, never hand-written

| status | when |
|---|---|
| `Supported` | all three conditions above hold |
| `Partial` | a number exists but the rule fails, or it exists for only one access tier |
| `Untested` | the class is known and there is no usable row |
| `Unsupported` | declared list only. **A measured row never flips this** |

Put the reason in `notes` and it appears in the coverage statement as a limitation:
`black-box sweep only`, `n=2 seeds`, `std 0.21 across seeds`, `calibration fitted on the
same seeds it is reported on`.

Missing CSV file: every non-declared row is `Untested` and the CLI prints a one-line warning.
**A missing file is a legitimate state**, not an error. Coverage ships as Untested until day 7.

---

## 5. Format of a measured cell

```text
0.92 ± 0.03 (5 seeds, synthetic-s42)
```

mean ± std, seed count, dataset. Nothing else is a valid measured cell. No `xx%`, no `N`, no
`TBD` dressed up as a rate, no single run reported as a mean.

---

## 6. Rules for the numbers

- **No invented values.** Every number in this CSV came from a run you can point at. If you did
  not run it, the cell is empty.
- **`n_seeds` counts seeds, not samples or images.** 10 000 images from one seed is one seed.
- **Record the access level per row.** A black-box-only measurement is Partial, and the reason
  is the tier, not the score.
- **`runtime_s_median` is on the machine named in `docs/p1/POLICY.md` / the runtime line**,
  CPU-only, offline. A GPU number in an air-gapped demo is a different product.
- **Data is synthetic or public-licence.** Put the licence in `dataset`: `synthetic-s42`, or
  `cocodataset-val2017 (CC BY 4.0)`. No classified, operational or service-generated data.

---

## 7. Where it lands

```text
demo/results_table.csv        # P5 writes, gitignored if it holds only synthetic numbers
configs/coverage_rules.yaml   # P1 owns: status thresholds, declared-unsupported list
out/coverage.json             # P1 generates from the two above
```

P1 reads the CSV. P1 never writes to it, and never edits your numbers to make a status look
better. If a threshold is wrong, we change the threshold in config with a dated row in
`docs/p1/DECISIONS.md` and a changelog line, in front of everyone.

---

## 8. Acknowledgement

Tagging `contracts-v1` confirms the column names and the twelve required `attack_class` values.

- [ ] **P5** — column names, row names, CSV by day 7. **PENDING day 1**
- [ ] **P1** — reads the CSV, derives status, never edits your numbers. Acknowledged
- [ ] **P2** — will own the data-family rows. **PENDING**
- [ ] **P3** — will own the model-family rows. **PENDING**
- [ ] **P4** — will own the record-family rows. **PENDING**
