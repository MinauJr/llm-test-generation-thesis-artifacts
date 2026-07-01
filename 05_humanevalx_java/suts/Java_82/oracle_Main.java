public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.primeLength("Hello") == true,
                s.primeLength("abcdcba") == true,
                s.primeLength("kittens") == true,
                s.primeLength("orange") == false,
                s.primeLength("wow") == true,
                s.primeLength("world") == true,
                s.primeLength("MadaM") == true,
                s.primeLength("Wow") == true,
                s.primeLength("") == false,
                s.primeLength("HI") == true,
                s.primeLength("go") == true,
                s.primeLength("gogo") == false,
                s.primeLength("aaaaaaaaaaaaaaa") == false,
                s.primeLength("Madam") == true,
                s.primeLength("M") == false,
                s.primeLength("0") == false
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
