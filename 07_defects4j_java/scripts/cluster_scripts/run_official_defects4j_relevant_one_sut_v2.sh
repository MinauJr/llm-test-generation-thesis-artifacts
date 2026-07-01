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
TEST_TIMEOUT_S="${TEST_TIMEOUT_S:-420}"
COVERAGE_TIMEOUT_S="${COVERAGE_TIMEOUT_S:-180}"
PIT_TIMEOUT_S="${PIT_TIMEOUT_S:-900}"
WRAPPER_TEST_TIMEOUT_S="${WRAPPER_TEST_TIMEOUT_S:-300}"

RUN_DIR="$OUT_BASE/$SUT_ID/run_0001"
RAW_DIR="$RUN_DIR/raw"
LOG_DIR="$RUN_DIR/logs"
METRICS_DIR="$RUN_DIR/metrics"
TR_DIR="$RUN_DIR/pit_runner"

rm -rf "$RUN_DIR"
mkdir -p "$RAW_DIR" "$LOG_DIR" "$METRICS_DIR" "$TR_DIR"

STATUS_JSON="$METRICS_DIR/status.json"

status="unknown"
compile_exit=""
test_exit=""
coverage_exit=""
wrapper_test_exit=""
pit_exit=""
line_pct="null"
branch_pct="null"
mutation_score_pct="null"
total_mutants="null"
killed_mutants="null"
warnings_json="[]"
note=""

write_status() {
python3 - "$STATUS_JSON" \
  "$SUT_ID" "$SUT_DIR" "$TEST_SET" "$status" \
  "$compile_exit" "$test_exit" "$coverage_exit" "$wrapper_test_exit" "$pit_exit" \
  "$line_pct" "$branch_pct" "$mutation_score_pct" "$total_mutants" "$killed_mutants" \
  "$warnings_json" "$note" <<'PY'
import json
import sys
from pathlib import Path

(
    out, sut_id, sut_dir, test_set, status,
    compile_exit, test_exit, coverage_exit, wrapper_test_exit, pit_exit,
    line_pct, branch_pct, mut_pct, total_mutants, killed_mutants,
    warnings_json, note
) = sys.argv[1:]

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

def conv_int(x):
    if x in ("", "null", "None"):
        return None
    try:
        return int(x)
    except Exception:
        return x

try:
    warnings = json.loads(warnings_json)
except Exception:
    warnings = []

data = {
    "sut_id": sut_id,
    "sut_dir": sut_dir,
    "test_set": test_set,
    "status": status,
    "ok": status == "ok",
    "compile_exit_code": conv_exit(compile_exit),
    "official_test_exit_code": conv_exit(test_exit),
    "coverage_exit_code": conv_exit(coverage_exit),
    "pit_wrapper_test_exit_code": conv_exit(wrapper_test_exit),
    "pit_exit_code": conv_exit(pit_exit),
    "line_pct": conv_float(line_pct),
    "branch_pct": conv_float(branch_pct),
    "mutation_score_pct": conv_float(mut_pct),
    "total_mutants": conv_int(total_mutants),
    "killed_mutants": conv_int(killed_mutants),
    "warnings": warnings,
    "note": note,
}
Path(out).write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

add_warnings() {
python3 - "$METRICS_DIR/coverage_metrics.json" "$METRICS_DIR/mutation_metrics.json" "$METRICS_DIR/warnings.json" <<'PY'
import json
import sys
from pathlib import Path

cov_path = Path(sys.argv[1])
mut_path = Path(sys.argv[2])
out_path = Path(sys.argv[3])

warnings = []

if cov_path.exists():
    cov = json.loads(cov_path.read_text())
    if cov.get("line_pct") == 0:
        warnings.append("line_pct_is_zero")
    if cov.get("branch_pct") == 0:
        warnings.append("branch_pct_is_zero")

if mut_path.exists():
    mut = json.loads(mut_path.read_text())
    if mut.get("mutation_score_pct") == 0:
        warnings.append("mutation_score_pct_is_zero")
    if mut.get("total_mutants") == 0:
        warnings.append("total_mutants_is_zero")

out_path.write_text(json.dumps(warnings), encoding="utf-8")
print(json.dumps(warnings))
PY
}

d4j_export() {
  local prop="$1"
  local out="$2"
  local log_base="$3"
  (
    cd "$SUT_DIR" || exit 2
    "$D4J" export -p "$prop" -o "$out"
  ) > "$LOG_DIR/export_${log_base}.stdout.log" 2> "$LOG_DIR/export_${log_base}.stderr.log"
}

echo "===== OFFICIAL DEFECTS4J DATASET TESTS V2: $SUT_ID ====="
echo "SUT_DIR=$SUT_DIR"
echo "OUT_BASE=$OUT_BASE"
echo "TEST_SET=$TEST_SET"

if [ ! -d "$SUT_DIR" ]; then
  status="missing_sut_dir"
  note="SUT directory does not exist"
  write_status
  exit 0
fi

if [ ! -x "$D4J" ]; then
  status="missing_defects4j"
  note="Defects4J executable missing"
  write_status
  exit 0
fi

if [ ! -f "$JACOCO_AGENT" ] || [ ! -f "$JACOCO_CLI" ]; then
  status="missing_jacoco_tools"
  note="JaCoCo agent or CLI missing"
  write_status
  exit 0
fi

echo "===== EXPORT METADATA ====="
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

{
  echo "DIR_SRC_CLASSES=$DIR_SRC_CLASSES"
  echo "DIR_SRC_TESTS=$DIR_SRC_TESTS"
  echo "DIR_BIN_CLASSES=$DIR_BIN_CLASSES"
  echo "DIR_BIN_TESTS=$DIR_BIN_TESTS"
} > "$RAW_DIR/resolved_dirs.txt"

RELEVANT_COUNT="$(grep -v '^[[:space:]]*$' "$RAW_DIR/tests.relevant.txt" 2>/dev/null | wc -l | tr -d ' ')"
MODIFIED_COUNT="$(grep -v '^[[:space:]]*$' "$RAW_DIR/classes.modified.txt" 2>/dev/null | wc -l | tr -d ' ')"

if [ "$RELEVANT_COUNT" = "0" ]; then
  status="no_relevant_tests"
  note="tests.relevant is empty"
  write_status
  exit 0
fi

if [ "$MODIFIED_COUNT" = "0" ]; then
  status="no_modified_classes"
  note="classes.modified is empty"
  write_status
  exit 0
fi

echo "===== DEFECTS4J COMPILE ====="
(
  cd "$SUT_DIR" || exit 2
  timeout "$COMPILE_TIMEOUT_S" "$D4J" compile
) > "$LOG_DIR/compile.stdout.log" 2> "$LOG_DIR/compile.stderr.log"
compile_exit="$?"

if [ "$compile_exit" != "0" ]; then
  status="compile_fail"
  note="defects4j compile failed"
  write_status
  exit 0
fi

echo "===== DEFECTS4J TEST WITH JACOCO: tests.relevant ====="
JACOCO_EXEC="$RAW_DIR/jacoco.exec"
rm -f "$JACOCO_EXEC"

(
  cd "$SUT_DIR" || exit 2
  export JAVA_TOOL_OPTIONS="-javaagent:$JACOCO_AGENT=destfile=$JACOCO_EXEC,append=true"
  timeout "$TEST_TIMEOUT_S" "$D4J" test -r
) > "$LOG_DIR/official_tests.stdout.log" 2> "$LOG_DIR/official_tests.stderr.log"
test_exit="$?"

if [ "$test_exit" != "0" ]; then
  status="official_tests_fail"
  note="defects4j test -r failed"
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
  note="JaCoCo report failed"
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
    missed = 0
    covered = 0
    for c in root.findall("counter"):
        if c.attrib.get("type") == counter_type:
            missed += int(c.attrib.get("missed", "0"))
            covered += int(c.attrib.get("covered", "0"))
    total = missed + covered
    if total == 0:
        return 100.0
    return round(100.0 * covered / total, 4)

data = {
    "line_pct": pct("LINE"),
    "branch_pct": pct("BRANCH"),
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

echo "===== PREPARE PIT RUNNER WITH WRAPPER ====="

mkdir -p "$TR_DIR/target/classes" "$TR_DIR/target/test-classes" "$TR_DIR/src/main/java/d4j/official" "$TR_DIR/src/test/java/d4j/official"

if [ -d "$SUT_DIR/$DIR_BIN_CLASSES" ]; then
  cp -a "$SUT_DIR/$DIR_BIN_CLASSES/." "$TR_DIR/target/classes/"
fi

if [ -d "$SUT_DIR/$DIR_BIN_TESTS" ]; then
  cp -a "$SUT_DIR/$DIR_BIN_TESTS/." "$TR_DIR/target/test-classes/"
fi

echo "===== COPY TEST RESOURCES FOR PIT RUNNER ====="
mkdir -p "$TR_DIR/src/test/resources"

python3 - "$SUT_DIR" "$DIR_SRC_TESTS" "$TR_DIR/target/test-classes" "$TR_DIR/src/test/resources" <<'PYRES'
from pathlib import Path
import shutil
import sys

sut_dir = Path(sys.argv[1])
dir_src_tests = sys.argv[2]
target_test_classes = Path(sys.argv[3])
resources_out = Path(sys.argv[4])

resources_out.mkdir(parents=True, exist_ok=True)

def copy_non_code_tree(src: Path, dst_root: Path):
    if not src.exists():
        return
    for p in src.rglob("*"):
        if p.is_dir():
            continue
        # Avoid copying compiled classes or Java source files as resources.
        if p.suffix in {".class", ".java"}:
            continue
        rel = p.relative_to(src)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)

# 1) Resources already materialised by Defects4J into target/test-classes.
copy_non_code_tree(target_test_classes, resources_out)

# 2) Resources from the original test source tree, preserving useful relative paths.
src_tests = sut_dir / dir_src_tests
copy_non_code_tree(src_tests, resources_out)

# 3) Common Maven-style resources directory, when present.
for candidate in [
    sut_dir / "src/test/resources",
    sut_dir / "src/test/resource",
    sut_dir / "test/resources",
    sut_dir / "test/resource",
]:
    copy_non_code_tree(candidate, resources_out)

print(f"resources_out={resources_out}")
print(f"resource_files={sum(1 for x in resources_out.rglob('*') if x.is_file())}")
PYRES

cat > "$TR_DIR/src/main/java/d4j/official/PitProductionAnchor.java" <<'JAVA'
package d4j.official;

public final class PitProductionAnchor {
    private PitProductionAnchor() {}
    public static int anchor() {
        return 1;
    }
}
JAVA

cat > "$TR_DIR/src/test/java/d4j/official/PitTestAnchorTest.java" <<'JAVA'
package d4j.official;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class PitTestAnchorTest {
    @Test
    public void testAnchor() {
        assertEquals(1, PitProductionAnchor.anchor());
    }
}
JAVA

python3 - "$RAW_DIR/tests.relevant.txt" "$TR_DIR/src/test/java/d4j/official/RelevantTestsWrapperTest.java" <<'PY'
from pathlib import Path
import sys

tests_file = Path(sys.argv[1])
out = Path(sys.argv[2])

tests = [x.strip() for x in tests_file.read_text(encoding="utf-8").splitlines() if x.strip()]
class_lines = "\n".join(f'            Class.forName("{t}"),' for t in tests)

out.write_text(f'''package d4j.official;

import org.junit.Test;
import org.junit.runner.JUnitCore;
import org.junit.runner.Result;
import org.junit.runner.notification.Failure;

import static org.junit.Assert.fail;

public class RelevantTestsWrapperTest {{

    @Test
    public void runDefects4JRelevantTests() throws Exception {{
        Class<?>[] classes = new Class<?>[] {{
{class_lines}
        }};

        Result result = JUnitCore.runClasses(classes);

        if (!result.wasSuccessful()) {{
            StringBuilder sb = new StringBuilder();
            for (Failure failure : result.getFailures()) {{
                sb.append(failure.toString()).append("\\n");
            }}
            fail("Defects4J relevant tests failed inside PIT wrapper:\\n" + sb.toString());
        }}
    }}
}}
''', encoding="utf-8")
PY

python3 - "$TR_DIR/pom.xml" "$RAW_DIR/classes.modified.txt" "$RAW_DIR/cp.test.txt" "$SUT_DIR" "$SUT_ID" "$LOG_DIR/pit_extra_documentls_jars.txt" <<'PY'
import html
import sys
import zipfile
from pathlib import Path

pom = Path(sys.argv[1])
classes_modified = [x.strip() for x in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if x.strip()]
cp_test_file = Path(sys.argv[3])
sut_dir = Path(sys.argv[4])
sut_id = sys.argv[5]
extra_documentls_log = Path(sys.argv[6])

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

# Extra compatibility JARs for older Defects4J projects.
# JxPath uses the legacy org.w3c.dom.ls.DocumentLS type, which is not available
# in the Java 11 runtime used by the PIT runner. Defects4J's Ant classpath can
# still provide it through project libraries, so we reproduce that here.
def jar_contains_class(jar_path: Path, class_file: str) -> bool:
    try:
        with zipfile.ZipFile(jar_path) as zf:
            return class_file in set(zf.namelist())
    except Exception:
        return False

project_id = sut_id.split("_", 1)[0]
search_roots = [
    sut_dir,
    Path("/home/jpaiva/datasets/defect4j/defects4j/framework/projects") / project_id,
]

extra_documentls = []
required_class = "org/w3c/dom/ls/DocumentLS.class"

for root in search_roots:
    if not root.exists():
        continue
    for jar in root.rglob("*.jar"):
        jp = str(jar)
        if jp in seen:
            continue
        if jar_contains_class(jar, required_class):
            seen.add(jp)
            deps.append(jp)
            extra_documentls.append(jp)

extra_documentls_log.parent.mkdir(parents=True, exist_ok=True)
extra_documentls_log.write_text("\n".join(extra_documentls) + ("\n" if extra_documentls else ""), encoding="utf-8")

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
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>2.22.2</version>
        <configuration>
          <failIfNoSpecifiedTests>false</failIfNoSpecifiedTests>
          <failIfNoTests>false</failIfNoTests>
          <includes>
            <include>**/RelevantTestsWrapperTest.class</include>
            <include>**/RelevantTestsWrapperTest.java</include>
          </includes>
        </configuration>
      </plugin>

      <plugin>
        <groupId>org.pitest</groupId>
        <artifactId>pitest-maven</artifactId>
        <version>1.15.8</version>
        <configuration>
          <targetClasses>
{target_classes_xml}
          </targetClasses>
          <targetTests>
              <param>d4j.official.RelevantTestsWrapperTest</param>
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

echo "===== WRAPPER MAVEN TEST ====="
(
  cd "$TR_DIR" || exit 2
  timeout "$WRAPPER_TEST_TIMEOUT_S" mvn -q -Dtest=d4j.official.RelevantTestsWrapperTest test
) > "$LOG_DIR/pit_wrapper_test.stdout.log" 2> "$LOG_DIR/pit_wrapper_test.stderr.log"
wrapper_test_exit="$?"

if [ "$wrapper_test_exit" != "0" ]; then
  status="pit_wrapper_test_fail"
  note="RelevantTestsWrapperTest failed before PIT"
  warnings_json="$(add_warnings)"
  write_status
  exit 0
fi

echo "===== PIT MUTATION TESTING ====="
(
  cd "$TR_DIR" || exit 2
  rm -rf target/pit-reports
  timeout "$PIT_TIMEOUT_S" mvn -q -DtrimStackTrace=false org.pitest:pitest-maven:1.15.8:mutationCoverage
) > "$LOG_DIR/pit.stdout.log" 2> "$LOG_DIR/pit.stderr.log"
pit_exit="$?"

PIT_XML="$(find "$TR_DIR" -type f -name "mutations.xml" | head -n 1)"

if [ "$pit_exit" != "0" ] || [ -z "$PIT_XML" ] || [ ! -f "$PIT_XML" ]; then
  status="pit_fail"
  note="PIT failed or mutations.xml missing"
  warnings_json="$(add_warnings)"
  write_status
  exit 0
fi

python3 - "$PIT_XML" "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

xml_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

root = ET.parse(xml_path).getroot()
total = 0
killed = 0
detected = 0
statuses = Counter()

# PIT reports the mutation score using detected mutants.
# Besides KILLED, PIT also treats TIMED_OUT and MEMORY_ERROR as detected/killed
# in the summary line, e.g. "Generated 47 mutations Killed 42".
detected_statuses = {"KILLED", "TIMED_OUT", "MEMORY_ERROR"}

for m in root.findall(".//mutation"):
    total += 1
    status = m.attrib.get("status", "UNKNOWN")
    statuses[status] += 1
    if status == "KILLED":
        killed += 1
    if status in detected_statuses:
        detected += 1

score = 100.0 if total == 0 else 100.0 * detected / total

data = {
    "total_mutants": total,
    "killed_mutants": detected,
    "raw_killed_status_mutants": killed,
    "detected_mutants": detected,
    "mutation_score_pct": round(score, 4),
    "statuses": dict(statuses),
}
out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps(data))
PY

mutation_score_pct="$(python3 - "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["mutation_score_pct"])
PY
)"
total_mutants="$(python3 - "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["total_mutants"])
PY
)"
killed_mutants="$(python3 - "$METRICS_DIR/mutation_metrics.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["killed_mutants"])
PY
)"

warnings_json="$(add_warnings)"
status="ok"
note="completed"
write_status

echo "===== FINAL STATUS $SUT_ID ====="
cat "$STATUS_JSON"
