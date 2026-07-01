public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.primeFib(1) == 2,
                s.primeFib(2) == 3,
                s.primeFib(3) == 5,
                s.primeFib(4) == 13,
                s.primeFib(5) == 89,
                s.primeFib(6) == 233,
                s.primeFib(7) == 1597,
                s.primeFib(8) == 28657,
                s.primeFib(9) == 514229,
                s.primeFib(10) == 433494437
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
