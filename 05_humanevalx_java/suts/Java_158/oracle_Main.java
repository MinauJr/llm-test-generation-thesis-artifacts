public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.findMax(new ArrayList<>(Arrays.asList("name", "of", "string"))).equals("string"),
                s.findMax(new ArrayList<>(Arrays.asList("name", "enam", "game"))).equals("enam"),
                s.findMax(new ArrayList<>(Arrays.asList("aaaaaaa", "bb", "cc"))).equals("aaaaaaa"),
                s.findMax(new ArrayList<>(Arrays.asList("abc", "cba"))).equals("abc"),
                s.findMax(new ArrayList<>(Arrays.asList("play", "this", "game", "of", "footbott"))).equals("footbott"),
                s.findMax(new ArrayList<>(Arrays.asList("we", "are", "gonna", "rock"))).equals("gonna"),
                s.findMax(new ArrayList<>(Arrays.asList("we", "are", "a", "mad", "nation"))).equals("nation"),
                s.findMax(new ArrayList<>(Arrays.asList("this", "is", "a", "prrk"))).equals("this"),
                s.findMax(new ArrayList<>(List.of("b"))).equals("b"),
                s.findMax(new ArrayList<>(Arrays.asList("play", "play", "play"))).equals("play")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
