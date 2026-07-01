public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.listSort(new ArrayList<>(Arrays.asList("aa", "a", "aaa"))).equals(List.of("aa")),
                s.listSort(new ArrayList<>(Arrays.asList("school", "AI", "asdf", "b"))).equals(Arrays.asList("AI", "asdf", "school")),
                s.listSort(new ArrayList<>(Arrays.asList("d", "b", "c", "a"))).equals(List.of()),
                s.listSort(new ArrayList<>(Arrays.asList("d", "dcba", "abcd", "a"))).equals(Arrays.asList("abcd", "dcba")),
                s.listSort(new ArrayList<>(Arrays.asList("AI", "ai", "au"))).equals(Arrays.asList("AI", "ai", "au")),
                s.listSort(new ArrayList<>(Arrays.asList("a", "b", "b", "c", "c", "a"))).equals(List.of()),
                s.listSort(new ArrayList<>(Arrays.asList("aaaa", "bbbb", "dd", "cc"))).equals(Arrays.asList("cc", "dd", "aaaa", "bbbb"))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
