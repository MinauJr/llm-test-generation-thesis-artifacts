public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                (int) s.compareOne(1, 2).get() == 2,
                (double) s.compareOne(1, 2.5).get() == 2.5,
                (int) s.compareOne(2, 3).get() == 3,
                (int) s.compareOne(5, 6).get() == 6,
                (String) s.compareOne(1, "2,3").get() == "2,3",
                (String) s.compareOne("5,1", "6").get() == "6",
                (String) s.compareOne("1", "2").get() == "2",
                s.compareOne("1", 1).isEmpty()
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
