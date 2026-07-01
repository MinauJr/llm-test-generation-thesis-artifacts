public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.evenOddCount(7).equals(Arrays.asList(0, 1)),
                s.evenOddCount(-78).equals(Arrays.asList(1, 1)),
                s.evenOddCount(3452).equals(Arrays.asList(2, 2)),
                s.evenOddCount(346211).equals(Arrays.asList(3, 3)),
                s.evenOddCount(-345821).equals(Arrays.asList(3, 3)),
                s.evenOddCount(-2).equals(Arrays.asList(1, 0)),
                s.evenOddCount(-45347).equals(Arrays.asList(2, 3)),
                s.evenOddCount(0).equals(Arrays.asList(1, 0))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
