===== BUGSINPY GPT-4o CHECKPOINT 001 =====
Tue Apr 28 08:18:25 WEST 2026

Repo: /home/jpaiva/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o
SUT root: /home/jpaiva/projetos/SUTs/BugsInPy_OK -> /home/jpaiva/projetos/SUTs/BugsInPy
Target map GPT-4o: /home/jpaiva/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o/configs/bugsinpy_gpt4o_target_map.tsv

SUT/import readiness:
===== SUMMARY =====
target_rows=16
sut_dirs_ok=16/16
imports_ok=15/16
wrote=/home/jpaiva/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o/configs/bugsinpy_gpt4o_target_map.tsv
wrote=/home/jpaiva/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o/_dev/_inspect/bugsinpy_target_import_check.tsv
wrote=/home/jpaiva/projetos/llm_test_generation_gpt4o/bugsinpy_gpt4o/_dev/_inspect/bugsinpy_target_import_check.json

Known current caveat:
- PySnooper_3f direct import fails in the current shell because dependency 'future' is missing.
- Do not patch SUT or install dependencies yet; first inspect runner/dependency strategy.
