#!/usr/bin/env bash
set -euo pipefail

: "${GEN_TIMEOUT_S:=200}"
: "${GEN_EMPTY_RETRY_MAX:=15}"
: "${GENERATION_RETRY_SLEEP_S:=2}"
: "${RUN_MUTATION:=1}"
: "${MODEL_NAME:=gpt4o}"

: "${PYTEST_TIMEOUT_S:=60}"
: "${MUTATION_TIMEOUT_S:=180}"

: "${TEST_COMPILE_TIMEOUT_S:=${PYTEST_TIMEOUT_S}}"
: "${RAW_TIMEOUT_S:=${PYTEST_TIMEOUT_S}}"
: "${FINAL_TIMEOUT_S:=${PYTEST_TIMEOUT_S}}"
: "${PIT_TIMEOUT_S:=${MUTATION_TIMEOUT_S}}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${SUT_ID:?set SUT_ID}"
: "${SUT_ROOT:?set SUT_ROOT}"
: "${TARGET_CLASS:?set TARGET_CLASS}"
: "${SUT_INDEX:?set SUT_INDEX}"
: "${REP:=1}"
: "${OUT_BASE:?set OUT_BASE}"
: "${DEFECTS4J_BIN:=$HOME/datasets/defect4j/defects4j/framework/bin/defects4j}"
: "${MOCK_GENERATION:=0}"
: "${FORCE_RAW_TEST_FILE:=}"
RUN_DIR="$OUT_BASE/$SUT_ID/run_0001/$SUT_INDEX-$REP"
RAW_DIR="$RUN_DIR/raw"
WORK_DIR="$RUN_DIR/work"
MET_DIR="$RUN_DIR/metrics"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$RAW_DIR" "$WORK_DIR" "$MET_DIR" "$LOG_DIR"
SEED=$(( SUT_INDEX * 10000 + REP ))
TEST_CLASS_NAME="GPT4O_${SUT_ID}_Rep${REP}_Test"
TEST_PACKAGE="$(printf '%s' "$TARGET_CLASS" | sed 's/\.[^.]*$//')"
TEST_FULL_CLASS_NAME="$TEST_PACKAGE.$TEST_CLASS_NAME"
STATUS_JSON="$MET_DIR/status.json"
cat > "$STATUS_JSON" <<JSON
{
  "model_name": "$MODEL_NAME",
  "sut_id": "$SUT_ID",
  "sut_root": "$SUT_ROOT",
  "target_class": "$TARGET_CLASS",
  "sut_index": $SUT_INDEX,
  "rep": $REP,
  "seed": $SEED,
  "final_status": "started",
  "line_pct_penalized": 0.0,
  "branch_pct_penalized": 0.0,
  "pit_score_pct_penalized": 0.0
}
JSON
update_status() {
  python3 - "$STATUS_JSON" "$1" <<'PY'
import json, sys
p = sys.argv[1]
patch = json.loads(sys.argv[2])
obj = json.load(open(p, 'r', encoding='utf-8'))
obj.update(patch)
json.dump(obj, open(p, 'w', encoding='utf-8'), indent=2)
PY
}
log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_DIR/main.log"; }
log "compile/export baseline for $SUT_ID"
if ! bash -lc "cd '$SUT_ROOT' && '$DEFECTS4J_BIN' compile" >"$LOG_DIR/defects4j_compile.stdout.log" 2>"$LOG_DIR/defects4j_compile.stderr.log"; then
  update_status '{"final_status":"sut_compile_fail"}'
  exit 0
fi
for prop in dir.bin.classes dir.src.classes cp.compile cp.test; do
  bash -lc "cd '$SUT_ROOT' && '$DEFECTS4J_BIN' export -p $prop" >"$WORK_DIR/${prop//./_}.txt" 2>>"$LOG_DIR/defects4j_export.stderr.log" || true
done
TARGET_CLASS_SOURCE_FILE="$WORK_DIR/target_class_source.txt"
RELATED_CONTEXT_FILE="$WORK_DIR/related_context.txt"
if ! python3 "$ROOT_DIR/scripts/extract_target_context.py" \
  --sut-root "$SUT_ROOT" \
  --dir-src-file "$WORK_DIR/dir_src_classes.txt" \
  --target-class "$TARGET_CLASS" \
  --out-source "$TARGET_CLASS_SOURCE_FILE" \
  --out-related "$RELATED_CONTEXT_FILE" \
  >"$LOG_DIR/context_extract.stdout.log" 2>"$LOG_DIR/context_extract.stderr.log"; then
  update_status '{"final_status":"target_context_extract_fail"}'
  exit 0
fi
python3 "$ROOT_DIR/scripts/render_defects4j_prompt.py" \
  --template "$ROOT_DIR/prompts/defects4j_java_junit_gpt4o_prompt_v1.txt" \
  --out "$RAW_DIR/prompt.txt" \
  --test-package "$TEST_PACKAGE" \
  --test-class-name "$TEST_CLASS_NAME" \
  --target-class "$TARGET_CLASS" \
  --sut-id "$SUT_ID" \
  --target-source-file "$TARGET_CLASS_SOURCE_FILE" \
  --related-context-file "$RELATED_CONTEXT_FILE"
log "generation stage"
if [[ -n "$FORCE_RAW_TEST_FILE" ]]; then
  cp "$FORCE_RAW_TEST_FILE" "$RAW_DIR/model_raw_output.java.txt"
  {
    echo -e "forced_raw_test_file\t$FORCE_RAW_TEST_FILE"
    echo -e "model_name	$MODEL_NAME"
    echo -e "timeout_s\t$GEN_TIMEOUT_S"
    echo -e "exit_code\t0"
    echo -e "attempt\t1"
    echo -e "max_attempts\t1"
  } > "$RAW_DIR/generation_meta.tsv"
  gen_exit=0
elif [[ "$MOCK_GENERATION" == "1" ]]; then
  cat > "$RAW_DIR/model_raw_output.java.txt" <<JAVA
package $TEST_PACKAGE;
import org.junit.Test;
import static org.junit.Assert.*;
public class $TEST_CLASS_NAME {
  @Test
  public void placeholder() {
    assertTrue(true);
  }
}
JAVA
  {
    echo -e "mock_generation\ttrue"
    echo -e "model_name	$MODEL_NAME"
    echo -e "timeout_s\t$GEN_TIMEOUT_S"
    echo -e "exit_code\t0"
    echo -e "attempt\t1"
    echo -e "max_attempts\t1"
  } > "$RAW_DIR/generation_meta.tsv"
  gen_exit=0
else
  gen_attempt=1
  gen_exit=0
  while :; do
    gen_exit=0
    : > "$RAW_DIR/model_raw_output.java.txt"
    : > "$LOG_DIR/generation.stderr.log"

    timeout "$GEN_TIMEOUT_S" python3 "$ROOT_DIR/common/iaedu_from_prompt.py" "$RAW_DIR/prompt.txt" \
      > "$RAW_DIR/model_raw_output.java.txt" \
      2> "$LOG_DIR/generation.stderr.log" || gen_exit=$?
    gen_exit=${gen_exit:-0}

    {
      echo -e "model\tgpt-iaedu"
      echo -e "model_name	$MODEL_NAME"
      echo -e "prompt_file\t$RAW_DIR/prompt.txt"
      echo -e "output_file\t$RAW_DIR/model_raw_output.java.txt"
      echo -e "timeout_s\t$GEN_TIMEOUT_S"
      echo -e "exit_code\t${gen_exit:-0}"
      echo -e "attempt\t${gen_attempt}"
      echo -e "max_attempts\t${GEN_EMPTY_RETRY_MAX}"
    } > "$RAW_DIR/generation_meta.tsv"

    if [[ "${gen_exit:-0}" -ne 0 ]]; then
      break
    fi

    if grep -q '[^[:space:]]' "$RAW_DIR/model_raw_output.java.txt"; then
      break
    fi

    if [[ "$gen_attempt" -ge "$GEN_EMPTY_RETRY_MAX" ]]; then
      break
    fi

    gen_attempt=$((gen_attempt + 1))
    sleep "$GENERATION_RETRY_SLEEP_S"
  done
fi
update_status "{\"generation_exit_code\": ${gen_exit:-0}}"
if [[ "${gen_exit:-0}" -ne 0 ]]; then
  update_status '{"final_status":"generation_failure"}'
  exit 0
fi
if ! grep -q '[^[:space:]]' "$RAW_DIR/model_raw_output.java.txt"; then
  update_status '{"final_status":"generation_empty_output"}'
  exit 0
fi
python3 "$ROOT_DIR/scripts/parse_and_clean_gpt4o_java.py" --raw "$RAW_DIR/model_raw_output.java.txt" --clean "$WORK_DIR/clean_test.java" --meta "$WORK_DIR/clean_meta.json" --package "$TEST_PACKAGE" --class-name "$TEST_CLASS_NAME"
python3 "$ROOT_DIR/scripts/enrich_java_imports_from_context.py" \
  --java-file "$WORK_DIR/clean_test.java" \
  --target-source-file "$TARGET_CLASS_SOURCE_FILE" \
  --related-context-file "$RELATED_CONTEXT_FILE" \
  >"$LOG_DIR/import_enrich.stdout.log" 2>"$LOG_DIR/import_enrich.stderr.log" || true

if python3 - "$WORK_DIR/clean_meta.json" <<'PY'
import json, sys
meta=json.load(open(sys.argv[1], 'r', encoding='utf-8'))
raise SystemExit(1 if meta.get('structural_errors') else 0)
PY
then :; else
  update_status '{"final_status":"invalid_structural_output"}'
  exit 0
fi
log "runner materialisation placeholder"
if ! python3 "$ROOT_DIR/scripts/build_defects4j_system_deps.py" \
  --sut-root "$SUT_ROOT" \
  --dir-bin-file "$WORK_DIR/dir_bin_classes.txt" \
  --cp-compile-file "$WORK_DIR/cp_compile.txt" \
  --out-xml "$WORK_DIR/system_deps.xml" \
  --out-jar "$WORK_DIR/sut_classes.jar" \
  --manifest "$WORK_DIR/system_deps_manifest.json" \
  >"$LOG_DIR/system_deps.stdout.log" 2>"$LOG_DIR/system_deps.stderr.log"; then
  update_status '{"final_status":"runner_dep_materialization_fail"}'
  exit 0
fi

LOCAL_SUT_GID="defects4j.local"
LOCAL_SUT_AID="$(printf '%s' "$SUT_ID" | tr '[:upper:]' '[:lower:]')"
LOCAL_SUT_VER="1.0"

set +e
mvn -q install:install-file   -Dfile="$WORK_DIR/sut_classes.jar"   -DgroupId="$LOCAL_SUT_GID"   -DartifactId="$LOCAL_SUT_AID"   -Dversion="$LOCAL_SUT_VER"   -Dpackaging=jar   -DgeneratePom=true   >"$LOG_DIR/local_sut_install.stdout.log" 2>"$LOG_DIR/local_sut_install.stderr.log"
LOCAL_SUT_INSTALL_RC=$?
set -e

if [[ "${LOCAL_SUT_INSTALL_RC:-0}" -ne 0 ]]; then
  update_status '{"final_status":"local_sut_install_fail"}'
  exit 0
fi

mkdir -p "$WORK_DIR/testrunner/src/test/java/$(printf '%s' "$TEST_PACKAGE" | tr . /)"
cp "$WORK_DIR/clean_test.java" "$WORK_DIR/testrunner/src/test/java/$(printf '%s' "$TEST_PACKAGE" | tr . /)/$TEST_CLASS_NAME.java"

mkdir -p "$WORK_DIR/testrunner/src/main/java/dummy"
cat > "$WORK_DIR/testrunner/src/main/java/dummy/Dummy.java" <<'JAVA'
package dummy;
public class Dummy { public static int ping(){ return 1; } }
JAVA

python3 - "$ROOT_DIR/templates/pom.xml.in" "$WORK_DIR/system_deps.xml" "$WORK_DIR/testrunner/pom.xml" "$SUT_ID" "$REP" "$TEST_CLASS_NAME" "$TARGET_CLASS" "$TEST_FULL_CLASS_NAME" <<'PY2'
from pathlib import Path
import sys
pom_tpl, sysdeps, out, sut_id, rep, test_class_name, target_class, test_fqcn = sys.argv[1:9]
text = Path(pom_tpl).read_text(encoding='utf-8')
text = text.replace('{{ARTIFACT_ID}}', f'{sut_id.lower()}-rep{rep}')
text = text.replace('{{SYSTEM_DEPS}}', Path(sysdeps).read_text(encoding='utf-8'))
text = text.replace('{{TEST_CLASS_NAME}}', test_class_name)
text = text.replace('{{TARGET_CLASS}}', target_class)
text = text.replace('{{TEST_FULL_CLASS_NAME}}', test_fqcn)
Path(out).write_text(text, encoding='utf-8')
PY2

if ! python3 "$ROOT_DIR/scripts/patch_pom_for_local_sut.py"   --pom "$WORK_DIR/testrunner/pom.xml"   --group-id "$LOCAL_SUT_GID"   --artifact-id "$LOCAL_SUT_AID"   --version "$LOCAL_SUT_VER"   >"$LOG_DIR/pom_patch.stdout.log" 2>"$LOG_DIR/pom_patch.stderr.log"; then
  update_status '{"final_status":"pom_patch_fail"}'
  exit 0
fi

log "compile gate: maven test-compile"
set +e
(
  cd "$WORK_DIR/testrunner" && timeout "$TEST_COMPILE_TIMEOUT_S" mvn -q test-compile
) >"$LOG_DIR/mvn_test_compile.stdout.log" 2>"$LOG_DIR/mvn_test_compile.stderr.log"
TEST_COMPILE_RC=$?
set -e

echo "$TEST_COMPILE_RC" > "$MET_DIR/generated_test_compile_exit_code.txt"
update_status "{\"generated_test_compile_exit_code\": ${TEST_COMPILE_RC:-0}}"

if [[ "${TEST_COMPILE_RC:-0}" -ne 0 ]]; then
  update_status '{"final_status":"generated_test_compile_fail"}'
  exit 0
fi

log "raw execution gate: maven test"
set +e
(
  cd "$WORK_DIR/testrunner" && timeout "$RAW_TIMEOUT_S" mvn -q -Dtest="$TEST_CLASS_NAME" test
) >"$LOG_DIR/mvn_test.stdout.log" 2>"$LOG_DIR/mvn_test.stderr.log"
RAW_RC=$?
set -e

echo "$RAW_RC" > "$MET_DIR/raw_test_exit_code.txt"
update_status "{\"raw_test_exit_code\": ${RAW_RC:-0}}"

cp "$WORK_DIR/clean_test.java" "$WORK_DIR/clean_test_sanitized.java"

if [[ "${RAW_RC:-0}" -ne 0 ]]; then
  log "sanitization gate: ignore failing raw test methods"
  set +e
  python3 "$ROOT_DIR/scripts/sanitize_junit4_java_by_surefire.py"     --java-file "$WORK_DIR/clean_test_sanitized.java"     --surefire-dir "$WORK_DIR/testrunner/target/surefire-reports"     --skipped-out "$MET_DIR/skipped_tests.txt"     >"$LOG_DIR/sanitize.stdout.log" 2>"$LOG_DIR/sanitize.stderr.log"
  SANITIZE_RC=$?
  set -e

  echo "$SANITIZE_RC" > "$MET_DIR/sanitize_exit_code.txt"
  update_status "{\"sanitize_exit_code\": ${SANITIZE_RC:-0}}"

  cp "$WORK_DIR/clean_test_sanitized.java" "$WORK_DIR/testrunner/src/test/java/$(printf '%s' "$TEST_PACKAGE" | tr . /)/$TEST_CLASS_NAME.java"
else
  echo "" > "$MET_DIR/skipped_tests.txt"
fi

cp "$WORK_DIR/clean_test_sanitized.java" "$WORK_DIR/final_canonical_test.java"

DIR_BIN_REL="$(head -n 1 "$WORK_DIR/dir_bin_classes.txt")"
SUT_BIN_DIR="$SUT_ROOT/$DIR_BIN_REL"
if [[ ! -d "$SUT_BIN_DIR" ]]; then
  update_status '{"final_status":"coverage_prep_missing_bin_dir"}'
  exit 0
fi

rm -rf "$WORK_DIR/testrunner/target/classes"
mkdir -p "$WORK_DIR/testrunner/target/classes"
cp -a "$SUT_BIN_DIR"/. "$WORK_DIR/testrunner/target/classes"/

log "final execution gate: maven test + jacoco report"
set +e
(
  cd "$WORK_DIR/testrunner" && timeout "$FINAL_TIMEOUT_S" mvn -q -Dtest="$TEST_CLASS_NAME" test jacoco:report
) >"$LOG_DIR/mvn_final.stdout.log" 2>"$LOG_DIR/mvn_final.stderr.log"
FINAL_RC=$?
set -e

echo "$FINAL_RC" > "$MET_DIR/final_test_exit_code.txt"
update_status "{\"final_test_exit_code\": ${FINAL_RC:-0}}"

if [[ "${FINAL_RC:-0}" -ne 0 ]]; then
  update_status '{"final_status":"final_execution_fail"}'
  exit 0
fi

COV_XML="$WORK_DIR/testrunner/target/site/jacoco/jacoco.xml"
set +e
python3 "$ROOT_DIR/scripts/parse_jacoco_target_class.py" \
  --xml "$COV_XML" \
  --target-class "$TARGET_CLASS" \
  --line-out "$MET_DIR/line_coverage_pct.txt" \
  --branch-out "$MET_DIR/branch_coverage_pct.txt" \
  >"$LOG_DIR/jacoco_parse.stdout.log" 2>"$LOG_DIR/jacoco_parse.stderr.log"
COV_RC=$?
set -e

LINE_PCT="$(cat "$MET_DIR/line_coverage_pct.txt" 2>/dev/null || echo 0)"
BRANCH_PCT="$(cat "$MET_DIR/branch_coverage_pct.txt" 2>/dev/null || echo 0)"
update_status "{\"coverage_exit_code\": ${COV_RC:-0}, \"line_pct_penalized\": ${LINE_PCT:-0}, \"branch_pct_penalized\": ${BRANCH_PCT:-0}}"

if [[ "${COV_RC:-0}" -ne 0 ]]; then
  update_status '{"final_status":"coverage_fail"}'
  exit 0
fi

PIT_RC=0
PIT_PARSE_RC=0
PIT_SCORE=0

if [[ "${RUN_MUTATION:-1}" == "1" ]]; then
  log "mutation gate: pitest"
  set +e
  (
    cd "$WORK_DIR/testrunner" && timeout "$PIT_TIMEOUT_S" mvn -q -DskipTests=false org.pitest:pitest-maven:mutationCoverage
  ) >"$LOG_DIR/pit.stdout.log" 2>"$LOG_DIR/pit.stderr.log"
  PIT_RC=$?
  set -e

  echo "$PIT_RC" > "$MET_DIR/pit_exit_code.txt"

  if [[ "$PIT_RC" -eq 124 ]]; then
    update_status "{\"pit_exit_code\": ${PIT_RC}, \"final_status\": \"pit_timeout\"}"
    exit 0
  fi

  PIT_XML="$(find "$WORK_DIR/testrunner/target" -type f -name mutations.xml | sort | tail -n 1)"
  if [[ -z "$PIT_XML" ]]; then
    update_status "{\"pit_exit_code\": ${PIT_RC:-0}, \"final_status\": \"pit_missing_xml\"}"
    exit 0
  fi

  set +e
  python3 "$ROOT_DIR/scripts/parse_pit_mutations.py" \
    --xml "$PIT_XML" \
    --score-out "$MET_DIR/mutation_score_pct.txt" \
    >"$LOG_DIR/pit_parse.stdout.log" 2>"$LOG_DIR/pit_parse.stderr.log"
  PIT_PARSE_RC=$?
  set -e

  PIT_SCORE="$(cat "$MET_DIR/mutation_score_pct.txt" 2>/dev/null || echo 0)"
  update_status "{\"pit_exit_code\": ${PIT_RC:-0}, \"pit_parse_exit_code\": ${PIT_PARSE_RC:-0}, \"pit_score_pct_penalized\": ${PIT_SCORE:-0}}"

  if [[ "${PIT_RC:-0}" -ne 0 ]]; then
    update_status '{"final_status":"pit_fail"}'
    exit 0
  fi

  if [[ "${PIT_PARSE_RC:-0}" -ne 0 ]]; then
    update_status '{"final_status":"pit_parse_fail"}'
    exit 0
  fi
fi

update_status "{\"final_status\": \"ok\", \"line_pct_penalized\": ${LINE_PCT:-0}, \"branch_pct_penalized\": ${BRANCH_PCT:-0}, \"pit_score_pct_penalized\": ${PIT_SCORE:-0}}"
exit 0
