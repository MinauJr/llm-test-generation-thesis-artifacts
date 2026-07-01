public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.simplify("1/5", "5/1") == true,
                s.simplify("1/6", "2/1") == false,
                s.simplify("5/1", "3/1") == true,
                s.simplify("7/10", "10/2") == false,
                s.simplify("2/10", "50/10") == true,
                s.simplify("7/2", "4/2") == true,
                s.simplify("11/6", "6/1") == true,
                s.simplify("2/3", "5/2") == false,
                s.simplify("5/2", "3/5") == false,
                s.simplify("2/4", "8/4") == true,
                s.simplify("2/4", "4/2") == true,
                s.simplify("1/5", "5/1") == true,
                s.simplify("1/5", "1/5") == false
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
