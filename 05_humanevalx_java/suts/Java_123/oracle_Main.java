public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.getOddCollatz(14).equals(Arrays.asList(1, 5, 7, 11, 13, 17)),
                s.getOddCollatz(5).equals(Arrays.asList(1, 5)),
                s.getOddCollatz(12).equals(Arrays.asList(1, 3, 5)),
                s.getOddCollatz(1).equals(List.of(1))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
