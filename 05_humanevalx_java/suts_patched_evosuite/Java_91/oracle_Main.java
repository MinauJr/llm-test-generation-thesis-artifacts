public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.isBored("Hello world") == 0,
                s.isBored("Is the sky blue?") == 0,
                s.isBored("I love It !") == 1,
                s.isBored("bIt") == 0,
                s.isBored("I feel good today. I will be productive. will kill It") == 2,
                s.isBored("You and I are going for a walk") == 0
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
