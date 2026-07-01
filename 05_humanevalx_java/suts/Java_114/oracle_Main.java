public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.minSubArraySum(Arrays.asList(2, 3, 4, 1, 2, 4)) == 1,
                s.minSubArraySum(Arrays.asList(-1, -2, -3)) == -6,
                s.minSubArraySum(Arrays.asList(-1, -2, -3, 2, -10)) == -14,
                s.minSubArraySum(List.of(-999999999)) == -999999999,
                s.minSubArraySum(Arrays.asList(0, 10, 20, 1000000)) == 0,
                s.minSubArraySum(Arrays.asList(-1, -2, -3, 10, -5)) == -6,
                s.minSubArraySum(Arrays.asList(100, -1, -2, -3, 10, -5)) == -6,
                s.minSubArraySum(Arrays.asList(10, 11, 13, 8, 3, 4)) == 3,
                s.minSubArraySum(Arrays.asList(100, -33, 32, -1, 0, -2)) == -33,
                s.minSubArraySum(List.of(-10)) == -10,
                s.minSubArraySum(List.of(7)) == 7,
                s.minSubArraySum(Arrays.asList(1, -1)) == -1
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
