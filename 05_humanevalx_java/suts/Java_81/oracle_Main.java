public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.numericalLetterGrade(new ArrayList<>(Arrays.asList(4.0, 3.0, 1.7, 2.0, 3.5))).equals(Arrays.asList("A+", "B", "C-", "C", "A-")),
                s.numericalLetterGrade(new ArrayList<>(List.of(1.2))).equals(List.of("D+")),
                s.numericalLetterGrade(new ArrayList<>(List.of(0.5))).equals(List.of("D-")),
                s.numericalLetterGrade(new ArrayList<>(List.of(0.0))).equals(List.of("E")),
                s.numericalLetterGrade(new ArrayList<>(Arrays.asList(1.0, 0.3, 1.5, 2.8, 3.3))).equals(Arrays.asList("D", "D-", "C-", "B", "B+")),
                s.numericalLetterGrade(new ArrayList<>(Arrays.asList(0.0, 0.7))).equals(Arrays.asList("E", "D-"))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
