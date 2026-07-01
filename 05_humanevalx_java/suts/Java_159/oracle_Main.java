public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.eat(5, 6, 10).equals(Arrays.asList(11, 4)),
                s.eat(4, 8, 9).equals(Arrays.asList(12, 1)),
                s.eat(1, 10, 10).equals(Arrays.asList(11, 0)),
                s.eat(2, 11, 5).equals(Arrays.asList(7, 0)),
                s.eat(4, 5, 7).equals(Arrays.asList(9, 2)),
                s.eat(4, 5, 1).equals(Arrays.asList(5, 0))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
