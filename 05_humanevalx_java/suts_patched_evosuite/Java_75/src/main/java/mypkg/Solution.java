package mypkg;

import java.util.*;
import java.lang.*;

public class Solution {
    /**
    Write a function that returns true if the given number is the multiplication of 3 prime numbers
    and false otherwise.
    Knowing that (a) is less then 100.
    Example:
    isMultiplyPrime(30) == true
    30 = 2 * 3 * 5
     */
    public boolean isMultiplyPrime(int a) {
        for (int i = 2; i < 101; i++) {
            if (!isPrime(i)) {
                continue;
            }
            for (int j = i; j < 101; j++) {
                if (!isPrime(j)) {
                    continue;
                }
                for (int k = j; k < 101; k++) {
                    if (!isPrime(k)) {
                        continue;
                    }
                    if (i * j * k == a) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    private static boolean isPrime(int n) {
        for (int j = 2; j < n; j++) {
            if (n % j == 0) {
                return false;
            }
        }
        return true;
    }
}
