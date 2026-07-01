public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.wordsInSentence("This is a test" ), "is" ),
                Objects.equals(s.wordsInSentence("lets go for swimming" ), "go for" ),
                Objects.equals(s.wordsInSentence("there is no place available here" ), "there is no place" ),
                Objects.equals(s.wordsInSentence("Hi I am Hussein" ), "Hi am Hussein" ),
                Objects.equals(s.wordsInSentence("go for it" ), "go for it" ),
                Objects.equals(s.wordsInSentence("here" ), "" ),
                Objects.equals(s.wordsInSentence("here is" ), "is" )
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
