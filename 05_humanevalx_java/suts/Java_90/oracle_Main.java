public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.nextSmallest(new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5))).get() == 2,
                s.nextSmallest(new ArrayList<>(Arrays.asList(5, 1, 4, 3, 2))).get() == 2,
                s.nextSmallest(new ArrayList<>(List.of())).isEmpty(),
                s.nextSmallest(new ArrayList<>(Arrays.asList(1, 1))).isEmpty(),
                s.nextSmallest(new ArrayList<>(Arrays.asList(1, 1, 1, 1, 0))).get() == 1,
                s.nextSmallest(new ArrayList<>(Arrays.asList(1, (int) Math.pow(0.0, 0.0)))).isEmpty(),
                s.nextSmallest(new ArrayList<>(Arrays.asList(-35, 34, 12, -45))).get() == -35
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
