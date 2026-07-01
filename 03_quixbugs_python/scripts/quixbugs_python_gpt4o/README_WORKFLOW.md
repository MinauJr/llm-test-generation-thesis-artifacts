# QuixBugs Python — GPT-4o workflow

Dataset: QuixBugs Python  
SUT root: ~/projetos/SUTs/quixbugs  
SUT pattern: [0-9][0-9][0-9]_python_*  
Target module: sut  
Import root: SUT directory itself  

Final intended contract:

REPEATS=5
GEN_TIMEOUT_S=200
GEN_EMPTY_RETRY_MAX=15
GENERATION_RETRY_SLEEP_S=2
PYTEST_TIMEOUT_S=60
MUTATION_TIMEOUT_S=180
RUN_MUTATION=1

Methodological rule:
- retry generation only when GPT-4o returns true empty/whitespace output
- do not retry non-empty but bad tests
- preserve prompt, raw output, generation metadata, logs, status.json, coverage, mutation artefacts
- use _dev_ and _smoke_ outputs before final screen batch
