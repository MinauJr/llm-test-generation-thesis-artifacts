public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.bf("Jupiter", "Neptune").equals(Arrays.asList("Saturn", "Uranus")),
                s.bf("Earth", "Mercury").equals(List.of("Venus")),
                s.bf("Mercury", "Uranus").equals(Arrays.asList("Venus", "Earth", "Mars", "Jupiter", "Saturn")),
                s.bf("Neptune", "Venus").equals(Arrays.asList("Earth", "Mars", "Jupiter", "Saturn", "Uranus")),
                s.bf("Earth", "Earth").equals(List.of()),
                s.bf("Mars", "Earth").equals(List.of()),
                s.bf("Jupiter", "Makemake").equals(List.of())
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
