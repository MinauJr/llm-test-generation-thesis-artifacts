public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.solution(Arrays.asList(5, 8, 7, 1)) == 12,
                s.solution(Arrays.asList(3, 3, 3, 3, 3)) == 9,
                s.solution(Arrays.asList(30, 13, 24, 321)) == 0,
                s.solution(Arrays.asList(5, 9)) == 5,
                s.solution(Arrays.asList(2, 4, 8)) == 0,
                s.solution(Arrays.asList(30, 13, 23, 32)) == 23,
                s.solution(Arrays.asList(3, 13, 2, 9)) == 3
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
