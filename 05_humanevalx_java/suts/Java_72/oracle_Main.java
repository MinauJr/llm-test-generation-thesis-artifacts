public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.willItFly(new ArrayList<>(Arrays.asList(3, 2, 3)), 9),
                !s.willItFly(new ArrayList<>(Arrays.asList(1, 2)), 5),
                s.willItFly(new ArrayList<>(List.of(3)), 5),
                !s.willItFly(new ArrayList<>(Arrays.asList(3, 2, 3)), 1),
                !s.willItFly(new ArrayList<>(Arrays.asList(1, 2, 3)), 6),
                s.willItFly(new ArrayList<>(List.of(5)), 5)
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
