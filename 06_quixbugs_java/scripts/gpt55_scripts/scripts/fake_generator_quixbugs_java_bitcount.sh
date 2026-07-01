#!/usr/bin/env bash
set -euo pipefail

cat <<'JAVA'
package mypkg;

import org.junit.Test;
import static org.junit.Assert.*;

public class BITCOUNTGPT4oTest {

    @Test
    public void testBitcountZero() {
        assertEquals(0, BITCOUNT.bitcount(0));
    }

    @Test
    public void testBitcountOne() {
        assertEquals(1, BITCOUNT.bitcount(1));
    }

    @Test
    public void testBitcountTwo() {
        assertEquals(1, BITCOUNT.bitcount(2));
    }

    @Test
    public void testBitcountThree() {
        assertEquals(2, BITCOUNT.bitcount(3));
    }

    @Test
    public void testBitcountLargeNumber() {
        assertEquals(8, BITCOUNT.bitcount(255));
    }
}
JAVA
