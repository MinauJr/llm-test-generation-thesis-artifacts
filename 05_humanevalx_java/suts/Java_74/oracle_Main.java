public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.totalMatch(new ArrayList<>(List.of()), new ArrayList<>(List.of())).equals(List.of()),
                s.totalMatch(new ArrayList<>(Arrays.asList("hi", "admin")), new ArrayList<>(Arrays.asList("hi", "hi"))).equals(Arrays.asList("hi", "hi")),
                s.totalMatch(new ArrayList<>(Arrays.asList("hi", "admin")), new ArrayList<>(Arrays.asList("hi", "hi", "admin", "project"))).equals(Arrays.asList("hi", "admin")),
                s.totalMatch(new ArrayList<>(List.of("4")), new ArrayList<>(Arrays.asList("1", "2", "3", "4", "5"))).equals(List.of("4")),
                s.totalMatch(new ArrayList<>(Arrays.asList("hi", "admin")), new ArrayList<>(Arrays.asList("hI", "Hi"))).equals(Arrays.asList("hI", "Hi")),
                s.totalMatch(new ArrayList<>(Arrays.asList("hi", "admin")), new ArrayList<>(Arrays.asList("hI", "hi", "hi"))).equals(Arrays.asList("hI", "hi", "hi")),
                s.totalMatch(new ArrayList<>(Arrays.asList("hi", "admin")), new ArrayList<>(Arrays.asList("hI", "hi", "hii"))).equals(Arrays.asList("hi", "admin")),
                s.totalMatch(new ArrayList<>(List.of()), new ArrayList<>(List.of("this"))).equals(List.of()),
                s.totalMatch(new ArrayList<>(List.of("this")), new ArrayList<>(List.of())).equals(List.of())
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
