public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.checkIfLastCharIsALetter("apple" ) == false,
                s.checkIfLastCharIsALetter("apple pi e" ) == true,
                s.checkIfLastCharIsALetter("eeeee" ) == false,
                s.checkIfLastCharIsALetter("A" ) == true,
                s.checkIfLastCharIsALetter("Pumpkin pie " ) == false,
                s.checkIfLastCharIsALetter("Pumpkin pie 1" ) == false,
                s.checkIfLastCharIsALetter("" ) == false,
                s.checkIfLastCharIsALetter("eeeee e " ) == false,
                s.checkIfLastCharIsALetter("apple pie" ) == false,
                s.checkIfLastCharIsALetter("apple pi e " ) == false
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
