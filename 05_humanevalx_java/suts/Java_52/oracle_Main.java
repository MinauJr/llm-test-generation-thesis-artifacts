public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.belowThreshold(new ArrayList<>(Arrays.asList(1, 2, 4, 10)), 100),
                !s.belowThreshold(new ArrayList<>(Arrays.asList(1, 20, 4, 10)), 5),
                s.belowThreshold(new ArrayList<>(Arrays.asList(1, 20, 4, 10)), 21),
                s.belowThreshold(new ArrayList<>(Arrays.asList(1, 20, 4, 10)), 22),
                s.belowThreshold(new ArrayList<>(Arrays.asList(1, 8, 4, 10)), 11),
                !s.belowThreshold(new ArrayList<>(Arrays.asList(1, 8, 4, 10)), 10)
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
