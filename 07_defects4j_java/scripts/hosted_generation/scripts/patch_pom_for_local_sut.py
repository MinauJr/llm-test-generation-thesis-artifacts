#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pom", required=True)
    ap.add_argument("--group-id", required=True)
    ap.add_argument("--artifact-id", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    pom = Path(args.pom)
    txt = pom.read_text(encoding="utf-8")

    dep_block = f"""    <dependency>
      <groupId>{args.group_id}</groupId>
      <artifactId>{args.artifact_id}</artifactId>
      <version>{args.version}</version>
      <scope>test</scope>
    </dependency>
"""

    plugin_block = f"""      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-dependency-plugin</artifactId>
        <version>3.6.1</version>
        <executions>
          <execution>
            <id>unpack-sut</id>
            <phase>process-classes</phase>
            <goals><goal>unpack</goal></goals>
            <configuration>
              <artifactItems>
                <artifactItem>
                  <groupId>{args.group_id}</groupId>
                  <artifactId>{args.artifact_id}</artifactId>
                  <version>{args.version}</version>
                  <type>jar</type>
                  <outputDirectory>${{project.build.outputDirectory}}</outputDirectory>
                </artifactItem>
              </artifactItems>
              <overWriteReleases>false</overWriteReleases>
              <overWriteSnapshots>true</overWriteSnapshots>
            </configuration>
          </execution>
        </executions>
      </plugin>
"""

    deps_anchor = "  <dependencies>\n"
    if dep_block not in txt:
        if deps_anchor not in txt:
            raise SystemExit("dependencies anchor not found")
        txt = txt.replace(deps_anchor, deps_anchor + dep_block, 1)

    surefire_anchor = """      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>"""
    if plugin_block not in txt:
        if surefire_anchor not in txt:
            raise SystemExit("surefire plugin anchor not found")
        txt = txt.replace(surefire_anchor, plugin_block + surefire_anchor, 1)

    pom.write_text(txt, encoding="utf-8")
    print("PATCHED_POM")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
