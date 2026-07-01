public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        Map<Object, Object> map1 = new HashMap<>();
        map1.put("p", "pineapple");
        map1.put("b", "banana");
        Map<Object, Object> map2 = new HashMap<>();
        map2.put("p", "pineapple");
        map2.put("A", "banana");
        map2.put("B", "banana");
        Map<Object, Object> map3 = new HashMap<>();
        map3.put("p", "pineapple");
        map3.put(5, "banana");
        map3.put("a", "banana");
        Map<Object, Object> map4 = new HashMap<>();
        map4.put("Name", "John");
        map4.put("Age", "36");
        map4.put("City", "Houston");
        Map<Object, Object> map5 = new HashMap<>();
        map5.put("STATE", "NC");
        map5.put("ZIP", "12345");
        Map<Object, Object> map6 = new HashMap<>();
        map6.put("fruit", "Orange");
        map6.put("taste", "Sweet");
        Map<Object, Object> map7 = new HashMap<>();
        List<Boolean> correct = Arrays.asList(
                s.checkDictCase(map1),
                !s.checkDictCase(map2),
                !s.checkDictCase(map3),
                !s.checkDictCase(map4),
                s.checkDictCase(map5),
                s.checkDictCase(map6),
                !s.checkDictCase(map7)
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
