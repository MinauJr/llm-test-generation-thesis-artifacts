public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.matchParens(Arrays.asList("()(", ")")).equals("Yes"),
                s.matchParens(Arrays.asList(")", ")")).equals("No"),
                s.matchParens(Arrays.asList("(()(())", "())())")).equals("No"),
                s.matchParens(Arrays.asList(")())", "(()()(")).equals("Yes"),
                s.matchParens(Arrays.asList("(())))", "(()())((")).equals("Yes"),
                s.matchParens(Arrays.asList("()", "())")).equals("No"),
                s.matchParens(Arrays.asList("(()(", "()))()")).equals("Yes"),
                s.matchParens(Arrays.asList("((((", "((())")).equals("No"),
                s.matchParens(Arrays.asList(")(()", "(()(")).equals("No"),
                s.matchParens(Arrays.asList(")(", ")(")).equals("No")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
