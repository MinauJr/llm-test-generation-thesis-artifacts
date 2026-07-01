# BugsInPy GPT-5.5 workflow policy

## Dataset

- 16 SUTs.
- 5 repetitions per SUT.
- 80 expected generation slots.
- The target map is frozen before final generation.

## Credentials and accounts

- Every worker must define `IAEDU_SECRETS_FILE`.
- Only account1.env, account2.env and account3.env are accepted.
- Previously exported IAEdu variables are unset before loading the account.
- No fixed `secrets.env` or `model_endpoints.env` fallback is permitted.
- Secret values must never be written to logs or outputs.

## Generated tests

- Empty model output is never a valid generation.
- The prompt, every attempt, raw response and materialised test are preserved.
- Structural extraction of a Python code block may be used only when logged.
- Generated assertions and test semantics must not be manually changed.
- A failing generated test must not be removed, skipped or disabled.
- The SUT must not be changed to improve metrics.

## Metrics

- Coverage is collected only after the generated suite executes successfully.
- Line and branch coverage must refer to the configured target module.
- Mutation must target only the configured SUT code.
- Missing metrics remain missing in individual run records.
- Missing metrics become zero only in the final strict-zero aggregation.
- Final `ok` requires executable tests and all three required metrics.

## Deterministic final selection

- Selection never considers metric values.
- Candidate runs are ordered by creation timestamp and canonical path.
- The first five valid repetitions per SUT are selected.
- Invalid and surplus runs remain preserved and documented.
