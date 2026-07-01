public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.intersperse(new ArrayList<>(List.of()), 7).equals(List.of()),
                s.intersperse(new ArrayList<>(Arrays.asList(5, 6, 3, 2)), 8).equals(Arrays.asList(5, 8, 6, 8, 3, 8, 2)),
                s.intersperse(new ArrayList<>(Arrays.asList(2, 2, 2)), 2).equals(Arrays.asList(2, 2, 2, 2, 2))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
