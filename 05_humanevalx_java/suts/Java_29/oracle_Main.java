public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.filterByPrefix(new ArrayList<>(List.of()), "john").equals(List.of()),
                s.filterByPrefix(new ArrayList<>(Arrays.asList("xxx", "asd", "xxy", "john doe", "xxxAAA", "xxx")), "xxx").equals(Arrays.asList("xxx", "xxxAAA", "xxx"))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
