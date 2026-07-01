public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.getClosestVowel("yogurt").equals("u"),
                s.getClosestVowel("full").equals("u"),
                s.getClosestVowel("easy").equals(""),
                s.getClosestVowel("eAsy").equals(""),
                s.getClosestVowel("ali").equals(""),
                s.getClosestVowel("bad").equals("a"),
                s.getClosestVowel("most").equals("o"),
                s.getClosestVowel("ab").equals(""),
                s.getClosestVowel("ba").equals(""),
                s.getClosestVowel("quick").equals(""),
                s.getClosestVowel("anime").equals("i"),
                s.getClosestVowel("Asia").equals(""),
                s.getClosestVowel("Above").equals("o")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
