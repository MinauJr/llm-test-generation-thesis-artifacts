public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.isSorted(new ArrayList<>(List.of(5))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 3, 2, 4, 5))) == false,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5, 6))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5, 6, 7))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 3, 2, 4, 5, 6, 7))) == false,
                s.isSorted(new ArrayList<>(List.of())) == true,
                s.isSorted(new ArrayList<>(List.of(1))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(3, 2, 1))) == false,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 2, 2, 3, 4))) == false,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 3, 3, 3, 4))) == false,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 2, 3, 3, 4))) == true,
                s.isSorted(new ArrayList<>(Arrays.asList(1, 2, 3, 4))) == true
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
