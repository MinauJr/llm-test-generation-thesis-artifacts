#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

[[ -f ".build_ok" ]] && exit 0

DATASET_LIB="/home/jpaiva/datasets/SF110/SF110-20130704/lib"
EXTRACTOR="/home/jpaiva/datasets/scripts/sf110_extract_target_classes.py"

rm -f CLASSPATH.txt TARGET_CLASSES.txt SUT_ARTIFACT.txt

# 1) Preferir JAR do projeto (fora de ./lib), escolhe o maior
JARFILE="$(find "$ROOT" -maxdepth 5 -type f -name "*.jar" ! -path "$ROOT/lib/*" -printf '%s\t%p\n' 2>/dev/null | sort -nr | head -n 1 | cut -f2- || true)"

# 2) Se não houver JAR, procurar um dir com .class
CLASSDIR=""
if [[ -z "$JARFILE" ]]; then
  for d in bin target/classes build/classes classes out/production dist build; do
    if [[ -d "$ROOT/$d" ]]; then
      if find "$ROOT/$d" -type f -name "*.class" -print -quit 2>/dev/null | grep -q .; then
        CLASSDIR="$ROOT/$d"
        break
      fi
    fi
  done
fi

if [[ -z "$JARFILE" && -z "$CLASSDIR" ]]; then
  echo "[!] sem JAR e sem .class"
  exit 1
fi

# 3) Artefacto + classpath
CP=""
if [[ -n "$JARFILE" ]]; then
  echo "$JARFILE" > SUT_ARTIFACT.txt
  CP="$JARFILE"
else
  echo "$CLASSDIR" > SUT_ARTIFACT.txt
  CP="$CLASSDIR"
fi

# libs do projeto
if [[ -d "$ROOT/lib" ]]; then
  while IFS= read -r j; do CP="$CP:$j"; done < <(find "$ROOT/lib" -type f -name "*.jar" 2>/dev/null)
fi

# libs globais do SF110 (exclui evosuite.jar; junit fica ok)
if [[ -d "$DATASET_LIB" ]]; then
  while IFS= read -r j; do
    [[ "$(basename "$j")" == "evosuite.jar" ]] && continue
    CP="$CP:$j"
  done < <(find "$DATASET_LIB" -type f -name "*.jar" 2>/dev/null)
fi

echo "$CP" > CLASSPATH.txt

# 4) TARGET_CLASSES (via script python externo)
if [[ -n "$JARFILE" ]]; then
  python3 "$EXTRACTOR" --jar "$JARFILE" > TARGET_CLASSES.txt
else
  python3 "$EXTRACTOR" --classdir "$CLASSDIR" > TARGET_CLASSES.txt
fi

if [[ ! -s TARGET_CLASSES.txt ]]; then
  echo "[!] TARGET_CLASSES vazio"
  exit 1
fi

echo OK > .build_ok
echo "[i] OK: $(wc -l < TARGET_CLASSES.txt) classes"
