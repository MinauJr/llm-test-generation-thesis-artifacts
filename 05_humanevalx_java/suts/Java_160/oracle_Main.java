public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.doAlgebra(new ArrayList<>(Arrays.asList("**", "*", "+")), new ArrayList<>(Arrays.asList(2, 3, 4, 5))) == 37,
                s.doAlgebra(new ArrayList<>(Arrays.asList("+", "*", "-")), new ArrayList<>(Arrays.asList(2, 3, 4, 5))) == 9,
                s.doAlgebra(new ArrayList<>(Arrays.asList("/", "*")), new ArrayList<>(Arrays.asList(7, 3, 4))) == 8,
                s.doAlgebra(new ArrayList<>(Arrays.asList("+", "**", "**")), new ArrayList<>(Arrays.asList(7, 5, 3, 2))) == 1953132
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
