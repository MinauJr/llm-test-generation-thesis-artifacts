#!/usr/bin/env bash
set -u
set -o pipefail

SUT_NAME="${1:?usage: run_quixbugs_gpt55_one_sut.sh SUT_NAME}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUT_ROOT="${SUT_ROOT:-$HOME/projetos/SUTs/quixbugs}"
SUT_DIR="$SUT_ROOT/$SUT_NAME"

OUT_ROOT="${OUT_ROOT:-$REPO_ROOT/out/_dev_one_sut}"
RUN_ID="${RUN_ID:-run_0001}"
REPEATS="${REPEATS:-1}"

GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-200}"
GEN_EMPTY_RETRY_MAX="${GEN_EMPTY_RETRY_MAX:-15}"
GENERATION_RETRY_SLEEP_S="${GENERATION_RETRY_SLEEP_S:-2}"
MVN_TEST_TIMEOUT_S="${MVN_TEST_TIMEOUT_S:-120}"
PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-180}"
RUN_MUTATION="${RUN_MUTATION:-1}"

GENERATOR_CMD="${GENERATOR_CMD:-$REPO_ROOT/scripts/generator_cmd_iaedu.sh}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$REPO_ROOT/prompts/java_quixbugs_zero_shot_v1.txt}"

SUT_OUT="$OUT_ROOT/$SUT_NAME/$RUN_ID"

echo "===== QUIXBUGS JAVA GPT-5.5 ONE_SUT ====="
echo "REPO_ROOT=$REPO_ROOT"
echo "SUT_NAME=$SUT_NAME"
echo "SUT_DIR=$SUT_DIR"
echo "OUT_ROOT=$OUT_ROOT"
echo "SUT_OUT=$SUT_OUT"
echo "REPEATS=$REPEATS"
echo "GEN_TIMEOUT_S=$GEN_TIMEOUT_S"
echo "GEN_EMPTY_RETRY_MAX=$GEN_EMPTY_RETRY_MAX"
echo "MVN_TEST_TIMEOUT_S=$MVN_TEST_TIMEOUT_S"
echo "PIT_TIMEOUT_S=$PIT_TIMEOUT_S"
echo "RUN_MUTATION=$RUN_MUTATION"
echo "GENERATOR_CMD=$GENERATOR_CMD"
echo

if [ ! -d "$SUT_DIR" ]; then
  echo "ERROR missing SUT_DIR=$SUT_DIR" >&2
  exit 2
fi

TARGET_FILE="$(find "$SUT_DIR/src/main/java/mypkg" -maxdepth 1 -type f -name '*.java' | sort | head -1)"
if [ -z "${TARGET_FILE:-}" ]; then
  echo "ERROR no target file under $SUT_DIR/src/main/java/mypkg" >&2
  exit 3
fi

TARGET_CLASS="$(basename "$TARGET_FILE" .java)"
TARGET_FQCN="mypkg.$TARGET_CLASS"
TEST_CLASS="${TARGET_CLASS}GPT4oTest"

mkdir -p "$SUT_OUT"

detect_pit_version() {
  local v
  v="$(find "$HOME/.m2/repository/org/pitest/pitest-maven" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -1)"
  if [ -z "$v" ]; then
    v="1.23.0"
  fi
  echo "$v"
}

write_runner_pom() {
  local runner="$1"
  local pit_version="$2"

  cat > "$runner/pom.xml" <<POM
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>mypkg</groupId>
  <artifactId>sut</artifactId>
  <version>1.0-SNAPSHOT</version>

  <properties>
    <maven.compiler.source>11</maven.compiler.source>
    <maven.compiler.target>11</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.5</version>
      </plugin>

      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>0.8.12</version>
        <executions>
          <execution>
            <goals>
              <goal>prepare-agent</goal>
            </goals>
          </execution>
          <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
              <goal>report</goal>
            </goals>
          </execution>
        </executions>
      </plugin>

      <plugin>
        <groupId>org.pitest</groupId>
        <artifactId>pitest-maven</artifactId>
        <version>${pit_version}</version>
              <configuration>
          <timestampedReports>false</timestampedReports>
          <outputFormats>
            <param>XML</param>
            <param>HTML</param>
          </outputFormats>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
POM
}

write_status() {
  local status="$1"
  local note="$2"
  local status_json="$3"

  python3 - "$status_json" <<PY
import json
import os
import sys
from pathlib import Path

def as_int(x):
    if x is None or x == "":
        return None
    try:
        return int(x)
    except Exception:
        return x

def as_float(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        return x

p = Path(sys.argv[1])
p.parent.mkdir(parents=True, exist_ok=True)

metrics_path = p.parent / "java_metrics.json"
metrics = {}
if metrics_path.exists():
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        metrics = {}

d = {
    "dataset": "quixbugs_java",
    "language": "java",
    "model": "gpt-5.5",
    "sut_name": os.environ.get("SUT_NAME"),
    "run_id": os.environ.get("RUN_ID"),
    "rep_id": os.environ.get("REP_ID"),
    "repeat": as_int(os.environ.get("REP")),
    "status": "$status",
    "note": "$note",
    "run_dir": os.environ.get("RUN_DIR"),
    "sut_dir": os.environ.get("SUT_DIR"),
    "target_class": os.environ.get("TARGET_CLASS"),
    "target_fqcn": os.environ.get("TARGET_FQCN"),
    "test_class": os.environ.get("TEST_CLASS"),
    "generation_exit_code": as_int(os.environ.get("GENERATION_EXIT_CODE")),
    "generation_attempts": as_int(os.environ.get("GENERATION_ATTEMPTS")),
    "generation_empty_attempts": as_int(os.environ.get("GENERATION_EMPTY_ATTEMPTS")),
    "generation_final_attempt": as_int(os.environ.get("GENERATION_FINAL_ATTEMPT")),
    "normalize_exit_code": as_int(os.environ.get("NORMALIZE_EXIT_CODE")),
    "mvn_test_exit_code": as_int(os.environ.get("MVN_TEST_EXIT_CODE")),
    "pit_exit_code": as_int(os.environ.get("PIT_EXIT_CODE")),
    "run_mutation": as_int(os.environ.get("RUN_MUTATION")),
    "line_coverage_pct": metrics.get("line_coverage_pct"),
    "branch_coverage_pct": metrics.get("branch_coverage_pct"),
    "instruction_coverage_pct": metrics.get("instruction_coverage_pct"),
    "mutation_score_pct": metrics.get("mutation_score_pct"),
    "mutation_score_strict_killed_only_pct": metrics.get("mutation_score_strict_killed_only_pct"),
    "mutation_total": metrics.get("mutation_total"),
    "mutation_killed": metrics.get("mutation_killed"),
    "mutation_survived": metrics.get("mutation_survived"),
    "mutation_timed_out": metrics.get("mutation_timed_out"),
    "jacoco_parse_error": metrics.get("jacoco_parse_error"),
    "pit_parse_error": metrics.get("pit_parse_error"),
}

p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
PY
}

PIT_VERSION="$(detect_pit_version)"

for REP in $(seq 1 "$REPEATS"); do
  REP_ID="1-$REP"
  RUN_DIR="$SUT_OUT/$REP_ID"
  GENERATION_DIR="$RUN_DIR/generation"
  ATTEMPTS_DIR="$GENERATION_DIR/attempts"
  RUNNER="$RUN_DIR/runner"
  LOGS_DIR="$RUN_DIR/logs"
  METRICS_DIR="$RUN_DIR/metrics"
  STATUS_JSON="$METRICS_DIR/status.json"

  mkdir -p "$GENERATION_DIR" "$ATTEMPTS_DIR" "$RUNNER" "$LOGS_DIR" "$METRICS_DIR"

  export SUT_NAME RUN_ID REP_ID REP RUN_DIR SUT_DIR TARGET_CLASS TARGET_FQCN TEST_CLASS RUN_MUTATION
  export GENERATION_EXIT_CODE="" GENERATION_ATTEMPTS="" GENERATION_EMPTY_ATTEMPTS="" GENERATION_FINAL_ATTEMPT=""
  export NORMALIZE_EXIT_CODE="" MVN_TEST_EXIT_CODE="" PIT_EXIT_CODE=""

  echo "===== $SUT_NAME rep=$REP_ID ====="

  rm -rf "$RUNNER"
  mkdir -p "$RUNNER"
  cp -a "$SUT_DIR/." "$RUNNER/"
  mkdir -p "$RUNNER/src/test/java/mypkg"

  write_runner_pom "$RUNNER" "$PIT_VERSION"

  python3 "$REPO_ROOT/tools/render_quixbugs_java_prompt.py" \
    --sut-name "$SUT_NAME" \
    --sut-dir "$SUT_DIR" \
    --target-file "$TARGET_FILE" \
    --target-class "$TARGET_CLASS" \
    --test-class "$TEST_CLASS" \
    --template "$PROMPT_TEMPLATE" \
    --out "$GENERATION_DIR/final_prompt.txt" \
    > "$LOGS_DIR/render_prompt.log" 2>&1

  TRACE="$GENERATION_DIR/generation_retry_trace.tsv"
  echo -e "attempt\texit_code\tbytes\tnonempty\tstate" > "$TRACE"

  GENERATION_ATTEMPTS=0
  GENERATION_EMPTY_ATTEMPTS=0
  GENERATION_EXIT_CODE=1
  GENERATION_FINAL_ATTEMPT=0

  for ATTEMPT in $(seq 1 "$GEN_EMPTY_RETRY_MAX"); do
    GENERATION_ATTEMPTS="$ATTEMPT"
    RAW_ATTEMPT="$ATTEMPTS_DIR/attempt_${ATTEMPT}.raw.java"
    STDERR_ATTEMPT="$ATTEMPTS_DIR/attempt_${ATTEMPT}.stderr.log"

    set +e
    timeout "$GEN_TIMEOUT_S" "$GENERATOR_CMD" "$GENERATION_DIR/final_prompt.txt" > "$RAW_ATTEMPT" 2> "$STDERR_ATTEMPT"
    RC=$?
    set -e

    BYTES="$(wc -c < "$RAW_ATTEMPT" 2>/dev/null || echo 0)"
    if [ "$RC" -ne 0 ]; then
      echo -e "$ATTEMPT\t$RC\t$BYTES\t0\tnonzero_exit" >> "$TRACE"
      GENERATION_EXIT_CODE="$RC"
      break
    fi

    if [ "$BYTES" -gt 0 ] && grep -q '[^[:space:]]' "$RAW_ATTEMPT"; then
      cp "$RAW_ATTEMPT" "$GENERATION_DIR/raw_output.java"
      echo -e "$ATTEMPT\t0\t$BYTES\t1\tnonempty_success" >> "$TRACE"
      GENERATION_EXIT_CODE=0
      GENERATION_FINAL_ATTEMPT="$ATTEMPT"
      break
    fi

    GENERATION_EMPTY_ATTEMPTS=$((GENERATION_EMPTY_ATTEMPTS + 1))
    echo -e "$ATTEMPT\t0\t$BYTES\t0\tempty_retry" >> "$TRACE"
    sleep "$GENERATION_RETRY_SLEEP_S"
  done

  export GENERATION_EXIT_CODE GENERATION_ATTEMPTS GENERATION_EMPTY_ATTEMPTS GENERATION_FINAL_ATTEMPT

  if [ "$GENERATION_EXIT_CODE" -ne 0 ] || [ "$GENERATION_FINAL_ATTEMPT" -eq 0 ]; then
    write_status "generation_failed" "generation did not produce a usable non-empty output" "$STATUS_JSON"
    echo "[REP $REP_ID] status=generation_failed"
    continue
  fi

  set +e
  python3 "$REPO_ROOT/tools/normalize_java_test.py" \
    --raw "$GENERATION_DIR/raw_output.java" \
    --out "$RUNNER/src/test/java/mypkg/$TEST_CLASS.java" \
    --package mypkg \
    --test-class "$TEST_CLASS" \
    --meta-json "$GENERATION_DIR/normalization_meta.json" \
    > "$LOGS_DIR/normalize.log" 2>&1
  NORMALIZE_EXIT_CODE=$?
  set -e
  export NORMALIZE_EXIT_CODE

  if [ "$NORMALIZE_EXIT_CODE" -ne 0 ]; then
    write_status "normalization_failed" "generated Java test could not be normalized" "$STATUS_JSON"
    echo "[REP $REP_ID] status=normalization_failed"
    continue
  fi

  COMPAT_JSON="$METRICS_DIR/java_test_compat_fix.json"
  python3 "$REPO_ROOT/tools/fix_generated_java_test_compat.py" \
    --test-file "$RUNNER/src/test/java/mypkg/$TEST_CLASS.java" \
    --out-json "$COMPAT_JSON" \
    > "$LOGS_DIR/java_test_compat_fix.log" 2>&1 || true

  cd "$RUNNER" || exit 1

  set +e
  timeout "$MVN_TEST_TIMEOUT_S" mvn -q -Dtest="$TEST_CLASS" test jacoco:report > "$LOGS_DIR/mvn_test_jacoco.log" 2>&1
  MVN_TEST_EXIT_CODE=$?
  set -e
  export MVN_TEST_EXIT_CODE

  if [ "$MVN_TEST_EXIT_CODE" -ne 0 ]; then
    SANITIZE_JSON="$METRICS_DIR/junit_sanitization.json"

    python3 "$REPO_ROOT/tools/sanitize_junit4_from_surefire.py" \
      --test-file "$RUNNER/src/test/java/mypkg/$TEST_CLASS.java" \
      --surefire-dir "$RUNNER/target/surefire-reports" \
      --out-json "$SANITIZE_JSON" \
      > "$LOGS_DIR/junit_sanitization.log" 2>&1 || true

    SANITIZED_IGNORED_COUNT="$(python3 -c 'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get("ignored_count") or 0)' "$SANITIZE_JSON" 2>/dev/null || echo 0)"
    SANITIZED_EFFECTIVE_COUNT="$(python3 -c 'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get("effective_test_methods_after") or 0)' "$SANITIZE_JSON" 2>/dev/null || echo 0)"

    export SANITIZED_IGNORED_COUNT
    export SANITIZED_EFFECTIVE_COUNT

    if [ "${SANITIZED_IGNORED_COUNT:-0}" -gt 0 ] && [ "${SANITIZED_EFFECTIVE_COUNT:-0}" -gt 0 ]; then
      echo "[REP $REP_ID] Maven failed; sanitized $SANITIZED_IGNORED_COUNT failing generated test(s); rerunning Maven/Jacoco"

      cd "$RUNNER" || exit 1
      set +e
      timeout "$MVN_TEST_TIMEOUT_S" mvn -q -Dtest="$TEST_CLASS" test jacoco:report > "$LOGS_DIR/mvn_test_jacoco_after_sanitization.log" 2>&1
      MVN_TEST_EXIT_CODE=$?
      set -e
      export MVN_TEST_EXIT_CODE

      if [ "$MVN_TEST_EXIT_CODE" -ne 0 ]; then
        cd "$REPO_ROOT" || exit 1
        write_status "test_fail_after_sanitization" "generated JUnit suite still failed after sanitizing failing tests" "$STATUS_JSON"
        echo "[REP $REP_ID] status=test_fail_after_sanitization"
        continue
      fi
    else
      cd "$REPO_ROOT" || exit 1
      write_status "test_fail" "generated JUnit suite failed Maven test/Jacoco stage and no sanitizable failing tests were found" "$STATUS_JSON"
      echo "[REP $REP_ID] status=test_fail"
      continue
    fi
  fi

  PIT_EXIT_CODE=""
  if [ "$RUN_MUTATION" = "1" ]; then
    set +e
    timeout "$PIT_TIMEOUT_S" mvn -q org.pitest:pitest-maven:mutationCoverage \
      -DtargetClasses="$TARGET_FQCN" \
      -DtargetTests="mypkg.$TEST_CLASS" \
      -DtimestampedReports=false \
      -DoutputFormats=XML,HTML \
      > "$LOGS_DIR/pit.log" 2>&1
    PIT_EXIT_CODE=$?
    set -e
    export PIT_EXIT_CODE
  fi

  cd "$REPO_ROOT" || exit 1

  python3 "$REPO_ROOT/tools/extract_java_metrics.py" \
    --runner "$RUNNER" \
    --target-class "$TARGET_FQCN" \
    --out-json "$METRICS_DIR/java_metrics.json" \
    > "$LOGS_DIR/extract_java_metrics.log" 2>&1

  if [ "$RUN_MUTATION" = "1" ] && [ "${PIT_EXIT_CODE:-1}" -ne 0 ]; then
    write_status "mutation_fail" "PIT exited non-zero or timed out" "$STATUS_JSON"
    echo "[REP $REP_ID] status=mutation_fail"
    continue
  fi

  write_status "ok" "ok" "$STATUS_JSON"

  line="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("line_coverage_pct"))' "$METRICS_DIR/java_metrics.json")"
  branch="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("branch_coverage_pct"))' "$METRICS_DIR/java_metrics.json")"
  mutation="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("mutation_score_pct"))' "$METRICS_DIR/java_metrics.json")"

  if [ "$RUN_MUTATION" = "1" ]; then
    echo "[REP $REP_ID] status=ok line=$line branch=$branch mutation=$mutation"
  else
    echo "[REP $REP_ID] status=ok line=$line branch=$branch mutation=NA"
  fi
done

echo
echo "===== ONE_SUT DONE: $SUT_NAME ====="
find "$SUT_OUT" -path '*/metrics/status.json' | sort
