# Initial decisions

- Reuse the HumanEval+/HumanEval-X GPT-4o workflow philosophy as the baseline.
- Do not copy blindly: Defects4J is project-level, not micro-SUT-level.
- Operational unit for GPT-4o baseline: one chosen target class inside one full Defects4J project.
- Keep deterministic seeds: `seed = sut_index * 10000 + rep`.
- Preserve raw model output, cleaned test file, logs, and `metrics/status.json` even on failure.
- Target-map seed currently follows the effective non-AI EvoSuite final targets because they are already class-targeted and operationally validated.
- Before full batch, run smoke on representative cases: Closure_77f, JacksonDatabind_17f, JacksonXml_5f, JxPath_22f, Mockito_19f, Time_24f.
