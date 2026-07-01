public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.fruitDistribution("5 apples and 6 oranges",19) == 8,
                s.fruitDistribution("5 apples and 6 oranges",21) == 10,
                s.fruitDistribution("0 apples and 1 oranges",3) == 2,
                s.fruitDistribution("1 apples and 0 oranges",3) == 2,
                s.fruitDistribution("2 apples and 3 oranges",100) == 95,
                s.fruitDistribution("2 apples and 3 oranges",5) == 0,
                s.fruitDistribution("1 apples and 100 oranges",120) == 19
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
