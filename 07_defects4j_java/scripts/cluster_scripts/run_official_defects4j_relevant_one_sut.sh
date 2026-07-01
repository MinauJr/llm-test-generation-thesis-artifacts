#!/usr/bin/env bash
set -u

SUT_ID="${SUT_ID:?missing SUT_ID}"
SUT_DIR="${SUT_DIR:?missing SUT_DIR}"
OUT_BASE="${OUT_BASE:?missing OUT_BASE}"

D4J="${D4J:-/home/jpaiva/datasets/defect4j/defects4j/framework/bin/defects4j}"
NONAI_JAVA="${NONAI_JAVA:-/home/jpaiva/projetos/nonAI/java_workflow}"

JACOCO_AGENT="${JACOCO_AGENT:-$NONAI_JAVA/tools/_jacoco/jacocoagent.jar}"
JACOCO_CLI="${JACOCO_CLI:-$NONAI_JAVA/tools/_jacoco/jacococli.jar}"

TEST_SET="${TEST_SET:-relevant}"

COMPILE_TIMEOUT_S="${COMPILE_TIMEOUT_S:-240}"
TEST_TIMEOUT_S="${TEST_TIMEOUT_S:-300}"
COVERAGE_TIMEOUT_S="${COVERAGE_TIMEOUT_S:-120}"
PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-420}"

RUN_DIR="$OUT_BASE/$SUT_ID/run_0001"
RAW_DIR="$RUN_DIR/raw"
LOG_DIR="$RUN_DIR/logs"
METRICS_DIR="$RUN_DIR/metrics"
TR_DIR="$RUN_DIR/pit_runner"

mkdir -p "$RAW_DIR" "$LOG_DIR" "$METRICS_DIR" "$TR_DIR"

STATUS_JSON="$METRICS_DIR/status.json"

echo "===== RUN OFFICIAL DEFECTS4J DATASET TESTS: $SUT_ID ====="
echo "SUT_DIR=$SUT_DIR"
echo "OUT_BASE=$OUT_BASE"
echo "TEST_SET=$TEST_SET"

status="unknown"
compile_exit=""
test_exit=""
coverage_exit=""
pit_exit=""
line_pct="null"
branch_pct="null"
mutation_score_pct="null"

write_status() {
python3 - "$STATUS_JSON" "$SUT_ID" "$SUT_DIR" "$TEST_SET" "$status" "$compile_exit" "$test_exit" "$coverage_exit" "$pit_exit" "$line_pct" "$branch_pct" "$mutation_score_pct" <<'PY'
import json
import sys
from pathlib import Path

out, sut_id, sut_dir, test_set, status, compile_exit, test_exit, coverage_exit, pit_exit, line_pct, branch_pct, mut_pct = sys.argv[1:]

def conv_exit(x):
    if x in ("", "null", "None"):
        return None
    try:
        return int(x)
    except Exception:
        return x

def conv_float(x):
    if x in ("", "null", "None"):
        return None
    try:
        return float(x)
    except Exception:
        return x

data = {
    "sut_id": sut_id,
    "sut_dir": sut_dir,
    "test_set": test_set,
    "status": status,
    "ok": status == "ok",
    "compile_exit_code": conv_exit(compile_exit),
    "test_exit_code": conv_exit(test_exit),
    "coverage_exit_code": conv_exit(coverage_exit),
    "pit_exit_code": conv_exit(pit_exit),
    "line_pct": conv_float(line_pct),
    "branch_pct": conv_float(branch_pct),
    "mutation_score_pct": conv_float(mut_pct),
}

Path(out).write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

if [ ! -d "$SUT_DIR" ]; then
  status="missing_sut_dir"
  write_status
  exit 0
fi

if [ ! -x "$D4J" ]; then
  status="missing_defects4j"
  write_status
  exit 0
fi

if [ ! -f "$JACOCO_AGENT" ] || [ ! -f "$JACOCO_CLI" ]; then
  status="missing_jacoco_tools"
  write_status
  exit 0
fi

d4j_export() {
  local prop="$1"
  local out="$2"
  local log_base="$3"
  (
    cd "$SUT_DIR" || exit 2
    "$D4J" export -p "$prop" -o "$out"
  ) > "$LOG_DIR/export_${log_base}.stdout.log" 2> "$LOG_DIR/export_${log_base}.stderr.log"
}

echo "===== EXPORT DEFECTS4J METADATA ====="
d4j_export classes.modified "$RAW_DIR/classes.modified.txt" "classes_modified"
d4j_export classes.relevant "$RAW_DIR/classes.relevant.txt" "classes_relevant"
d4j_export tests.all "$RAW_DIR/tests.all.txt" "tests_all"
d4j_export tests.relevant "$RAW_DIR/tests.relevant.txt" "tests_relevant"
d4j_export tests.trigger "$RAW_DIR/tests.trigger.txt" "tests_trigger"
d4j_export dir.src.classes "$RAW_DIR/dir.src.classes.txt" "dir_src_classes"
d4j_export dir.src.tests "$RAW_DIR/dir.src.tests.txt" "dir_src_tests"
d4j_export dir.bin.classes "$RAW_DIR/dir.bin.classes.txt" "dir_bin_classes"
d4j_export dir.bin.tests "$RAW_DIR/dir.bin.tests.txt" "dir_bin_tests"
d4j_export cp.compile "$RAW_DIR/cp.compile.txt" "cp_compile"
d4j_export cp.test "$RAW_DIR/cp.test.txt" "cp_test"

DIR_SRC_CLASSES="$(cat "$RAW_DIR/dir.src.classes.txt" 2>/dev/null | head -n 1 | tr -d '\r')"
DIR_SRC_TESTS="$(cat "$RAW_DIR/dir.src.tests.txt" 2>/dev/null | head -n 1 | tr -d '\r')"
DIR_BIN_CLASSES="$(cat "$RAW_DIR/dir.bin.classes.txt" 2>/dev/null | head -n 1 | tr -d '\r')"
DIR_BIN_TESTS="$(cat "$RAW_DIR/dir.bin.tests.txt" 2>/dev/null | head -n 1 | tr -d '\r')"

echo "DIR_SRC_CLASSES=$DIR_SRC_CLASSES" | tee "$RAW_DIR/resolved_dirs.txt"
echo "DIR_SRC_TESTS=$DIR_SRC_TESTS" | tee -a "$RAW_DIR/resolved_dirs.txt"
echo "DIR_BIN_CLASSES=$DIR_BIN_CLASSES" | tee -a "$RAW_DIR/resolved_dirs.txt"
echo "DIR_BIN_TESTS=$DIR_BIN_TESTS" | tee -a "$RAW_DIR/resolved_dirs.txt"

echo "===== DEFECTS4J COMPILE ====="
(
  cd "$SUT_DIR" || exit 2
  timeout "$COMPILE_TIMEOUT_S" "$D4J" compile
) > "$LOG_DIR/compile.stdout.log" 2> "$LOG_DIR/compile.stderr.log"
compile_exit="$?"

if [ "$compile_exit" != "0" ]; then
  status="compile_fail"
  write_status
  exit 0
fi

echo "===== DEFECTS4J TEST WITH JACOCO: $TEST_SET ====="
JACOCO_EXEC="$RAW_DIR/jacoco.exec"
rm -f "$JACOCO_EXEC"

if [ "$TEST_SET" = "relevant" ]; then
  TEST_CMD=( "$D4J" test -r )
elif [ "$TEST_SET" = "all" ]; then
  TEST_CMD=( "$D4J" test )
else
  echo "Unsupported TEST_SET=$TEST_SET" > "$LOG_DIR/test.stderr.log"
  status="unsupported_test_set"
  write_status
  exit 0
fi

(
  cd "$SUT_DIR" || exit 2
  export JAVA_TOOL_OPTIONS="-javaagent:$JACOCO_AGENT=destfile=$JACOCO_EXEC,append=true"
  timeout "$TEST_TIMEOUT_S" "${TEST_CMD[@]}"
) > "$LOG_DIR/test.stdout.log" 2> "$LOG_DIR/test.stderr.log"
test_exit="$?"

if [ "$test_exit" != "0" ]; then
  status="official_tests_fail"
  write_status
  exit 0
fi

echo "===== JACOCO REPORT OVER CLASSES.MODIFIED ====="

CLASSFILES_ARGS=()
while IFS= read -r cls; do
  cls="$(echo "$cls" | tr -d '\r' | xargs)"
  [ -n "$cls" ] || continue
  rel="${cls//.//}"
  f="$SUT_DIR/$DIR_BIN_CLASSES/$rel.class"
  if [ -f "$f" ]; then
    CLASSFILES_ARGS+=(--classfiles "$f")
  else
    # fallback for inner classes or unusual layouts
    d="$(dirname "$f")"
    b="$(basename "$f" .class)"
    if [ -d "$d" ]; then
      for candidate in "$d/$b"*.class; do
        [ -f "$candidate" ] && CLASSFILES_ARGS+=(--classfiles "$candidate")
      done
    fi
  fi
done < "$RAW_DIR/classes.modified.txt"

if [ "${#CLASSFILES_ARGS[@]}" -eq 0 ]; then
  CLASSFILES_ARGS=(--classfiles "$SUT_DIR/$DIR_BIN_CLASSES")
fi

mkdir -p "$RAW_DIR/jacoco_report"

timeout "$COVERAGE_TIMEOUT_S" java -jar "$JACOCO_CLI" report "$JACOCO_EXEC" \
  "${CLASSFILES_ARGS[@]}" \
  --sourcefiles "$SUT_DIR/$DIR_SRC_CLASSES" \
  --xml "$RAW_DIR/jacoco_report/jacoco.xml" \
  --csv "$RAW_DIR/jacoco_report/jacoco.csv" \
  --html "$RAW_DIR/jacoco_report/html" \
  > "$LOG_DIR/jacoco_report.stdout.log" 2> "$LOG_DIR/jacoco_report.stderr.log"
coverage_exit="$?"

if [ "$coverage_exit" != "0" ] || [ ! -f "$RAW_DIR/jacoco_report/jacoco.xml" ]; then
  status="coverage_fail"
  write_status
  exit 0
fi

python3 - "$RAW_DIR/jacoco_report/jacoco.xml" "$METRICS_DIR/coverage_metrics.json" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

xml_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

root = ET.parse(xml_path).getroot()

def pct(counter_type):
    total_missed = 0
    total_covered = 0
    for c in root.findall("counter"):
        if c.attrib.get("type") == counter_type:
            total_missed += int(c.attrib.get("missed", "0"))
            total_covered += int(c.attrib.get("covered", "0"))
    total = total_missed + total_covered
    if total == 0:
        return 100.0
    return 100.0 * total_covered / total

data = {
    "line_pct": round(pct("LINE"), 4),
    "branch_pct": round(pct("BRANCH"), 4),
}
out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps(data))
PY

line_pct="$(python3 - "$METRICS_DIR/coverage_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["line_pct"])
PY
)"
branch_pct="$(python3 - "$METRICS_DIR/coverage_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["branch_pct"])
PY
)"

echo "===== PREPARE PIT RUNNER ====="

mkdir -p "$TR_DIR/target/classes" "$TR_DIR/target/test-classes"

if [ -d "$SUT_DIR/$DIR_BIN_CLASSES" ]; then
  cp -a "$SUT_DIR/$DIR_BIN_CLASSES/." "$TR_DIR/target/classes/"
fi

if [ -d "$SUT_DIR/$DIR_BIN_TESTS" ]; then
  cp -a "$SUT_DIR/$DIR_BIN_TESTS/." "$TR_DIR/target/test-classes/"
fi

python3 - "$TR_DIR/pom.xml" "$RAW_DIR/classes.modified.txt" "$RAW_DIR/tests.relevant.txt" "$RAW_DIR/cp.test.txt" "$SUT_DIR" <<'PY'
import html
import sys
from pathlib import Path

pom = Path(sys.argv[1])
classes_modified = [x.strip() for x in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if x.strip()]
tests_relevant = [x.strip() for x in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if x.strip()]
cp_test_file = Path(sys.argv[4])
sut_dir = Path(sys.argv[5])

deps = []
seen = set()
for raw in cp_test_file.read_text(encoding="utf-8").split(":"):
    p = raw.strip()
    if not p.endswith(".jar"):
        continue
    name = Path(p).name.lower()
    if "junit" in name or "hamcrest" in name:
        continue
    if p in seen:
        continue
    seen.add(p)
    deps.append(p)

dep_xml = []
for i, p in enumerate(deps, 1):
    dep_xml.append(f"""
    <dependency>
      <groupId>defects4j.cp</groupId>
      <artifactId>cpdep{i}</artifactId>
      <version>1.0</version>
      <scope>system</scope>
      <systemPath>{html.escape(p)}</systemPath>
    </dependency>""")

target_classes_xml = "\n".join(f"              <param>{html.escape(c)}</param>" for c in classes_modified)
target_tests_xml = "\n".join(f"              <param>{html.escape(t)}</param>" for t in tests_relevant)
if not target_tests_xml:
    target_tests_xml = "              <param>*Test</param>"

pom.write_text(f"""<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>d4j.official</groupId>
  <artifactId>official-tests-pit-runner</artifactId>
  <version>1.0-SNAPSHOT</version>

  <properties>
    <maven.compiler.source>1.8</maven.compiler.source>
    <maven.compiler.target>1.8</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.12</version>
      <scope>test</scope>
    </dependency>
{''.join(dep_xml)}
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.pitest</groupId>
        <artifactId>pitest-maven</artifactId>
        <version>1.15.8</version>
        <configuration>
          <targetClasses>
{target_classes_xml}
          </targetClasses>
          <targetTests>
{target_tests_xml}
          </targetTests>
          <outputFormats>
            <param>XML</param>
          </outputFormats>
          <timestampedReports>false</timestampedReports>
          <failWhenNoMutations>false</failWhenNoMutations>
          <mutationThreshold>0</mutationThreshold>
          <coverageThreshold>0</coverageThreshold>
          <threads>1</threads>
          <timeoutFactor>2.0</timeoutFactor>
          <timeoutConstant>8000</timeoutConstant>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
""", encoding="utf-8")
PY

echo "===== PIT MUTATION TESTING ====="
(
  cd "$TR_DIR" || exit 2
  timeout "$PIT_TIMEOUT_S" mvn -q org.pitest:pitest-maven:1.15.8:mutationCoverage
) > "$LOG_DIR/pit.stdout.log" 2> "$LOG_DIR/pit.stderr.log"
pit_exit="$?"

PIT_XML="$TR_DIR/target/pit-reports/mutations.xml"

if [ "$pit_exit" != "0" ] || [ ! -f "$PIT_XML" ]; then
  status="pit_fail"
  write_status
  exit 0
fi

python3 - "$PIT_XML" "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

xml_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

root = ET.parse(xml_path).getroot()

total = 0
killed = 0
survived = 0
statuses = {}

for m in root.findall(".//mutation"):
    total += 1
    status = m.attrib.get("status", "UNKNOWN")
    statuses[status] = statuses.get(status, 0) + 1
    if status == "KILLED":
        killed += 1
    elif status == "SURVIVED":
        survived += 1

score = 100.0 if total == 0 else 100.0 * killed / total

data = {
    "total_mutants": total,
    "killed_mutants": killed,
    "survived_mutants": survived,
    "statuses": statuses,
    "mutation_score_pct": round(score, 4),
}
out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps(data))
PY

mutation_score_pct="$(python3 - "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["mutation_score_pct"])
PY
)"

status="ok"
write_status

echo "===== FINAL STATUS ====="
cat "$STATUS_JSON"
