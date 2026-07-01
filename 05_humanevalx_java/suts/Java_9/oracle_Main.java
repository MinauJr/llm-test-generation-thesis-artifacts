public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.rollingMax(new ArrayList<>(List.of())).equals(List.of()),
                s.rollingMax(new ArrayList<>(Arrays.asList(1, 2, 3, 4))).equals(Arrays.asList(1, 2, 3, 4)),
                s.rollingMax(new ArrayList<>(Arrays.asList(4, 3, 2, 1))).equals(Arrays.asList(4, 4, 4, 4)),
                s.rollingMax(new ArrayList<>(Arrays.asList(3, 2, 3, 100, 3))).equals(Arrays.asList(3, 3, 3, 100, 100))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
