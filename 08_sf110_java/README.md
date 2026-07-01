# SF110 Java artefacts

This directory contains cleaned artefacts for the SF110 Java experiments.

Important notes:

- SF110 does not include official/dataset test suites in this evaluation; therefore no official baseline is provided.
- Some hosted-model results may not exist for this dataset. Missing hosted-model folders, including Claude when unavailable, are not treated as errors.
- The repository preserves the available generated-test outputs, analysis tables, scripts and metadata.
- Full SF110 project sources, raw generated tests, repeated model outputs, logs, figures, backups and build artefacts were intentionally excluded.

Structure:

- `suts_metadata/`: metadata and lightweight descriptors for the SF110 SUTs.
- `scripts/`: available analysis and execution scripts.
- `results/analysis_tables/`: final analysis table(s) used in the dissertation.
- `results/cluster_summaries/`: compact per-model/source summaries for available cluster outputs.
- `results/available_outputs/`: compact available output summaries discovered under the SF110 output root.

Additional note:

- `results/final_source_summaries/` stores compact summaries for the final source roots referenced by the SF110 analysis table, including EvoSuite, Randoop, GPT-4o, GPT-5.5 and the effective cluster evaluation.
