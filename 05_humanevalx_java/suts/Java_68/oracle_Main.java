public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.pluck(new ArrayList<>(Arrays.asList(4, 2, 3))).equals(Arrays.asList(2, 1)),
                s.pluck(new ArrayList<>(Arrays.asList(1, 2, 3))).equals(Arrays.asList(2, 1)),
                s.pluck(new ArrayList<>(List.of())).equals(List.of()),
                s.pluck(new ArrayList<>(Arrays.asList(5, 0, 3, 0, 4, 2))).equals(Arrays.asList(0, 1)),
                s.pluck(new ArrayList<>(Arrays.asList(1, 2, 3, 0, 5, 3))).equals(Arrays.asList(0, 3)),
                s.pluck(new ArrayList<>(Arrays.asList(5, 4, 8, 4, 8))).equals(Arrays.asList(4, 1)),
                s.pluck(new ArrayList<>(Arrays.asList(7, 6, 7, 1))).equals(Arrays.asList(6, 1)),
                s.pluck(new ArrayList<>(Arrays.asList(7, 9, 7, 1))).equals(List.of())
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
