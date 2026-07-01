public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.derivative(new ArrayList<>(Arrays.asList(3, 1, 2, 4, 5))).equals(Arrays.asList(1, 4, 12, 20)),
                s.derivative(new ArrayList<>(Arrays.asList(1, 2, 3))).equals(Arrays.asList(2, 6)),
                s.derivative(new ArrayList<>(Arrays.asList(3, 2, 1))).equals(Arrays.asList(2, 2)),
                s.derivative(new ArrayList<>(Arrays.asList(3, 2, 1, 0, 4))).equals(Arrays.asList(2, 2, 0, 16)),
                s.derivative(List.of(1)).equals(List.of())
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
