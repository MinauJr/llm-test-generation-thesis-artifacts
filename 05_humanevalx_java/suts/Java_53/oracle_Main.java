public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        Random rand = new Random(42);
        List<Boolean> correct = Arrays.asList(
                s.add(0, 1) == 1,
                s.add(1, 0) == 1,
                s.add(2, 3) == 5,
                s.add(5, 7) == 12,
                s.add(7, 5) == 12
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
        for (int i = 0; i < 100; i++) {
            int x = rand.nextInt(1000), y = rand.nextInt(1000);
            if (s.add(x, y) != x + y) {
                throw new AssertionError();
            }
        }
    }
}
