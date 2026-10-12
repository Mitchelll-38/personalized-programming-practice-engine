"""Original, intentionally small Java exercises and synthetic demo history."""

EXERCISES = [
    {"problem_id": "java-sum", "title": "Sum two integers", "problem_text": "Write a Java method int sum(int a, int b) that returns the sum. Consider zero and negative inputs.", "concept_ids": ["variables", "arithmetic"], "prerequisites": []},
    {"problem_id": "java-even", "title": "Identify an even number", "problem_text": "Write a Java method boolean isEven(int n) using the remainder operator. Explain what it returns for zero and negative even numbers.", "concept_ids": ["arithmetic", "conditionals"], "prerequisites": ["variables"]},
    {"problem_id": "java-max", "title": "Choose the larger value", "problem_text": "Write a Java method int max(int a, int b) using an if statement. Equal inputs should return that value.", "concept_ids": ["conditionals"], "prerequisites": ["variables"]},
    {"problem_id": "java-count", "title": "Count positive entries", "problem_text": "Write a Java method int countPositive(int[] values) that counts entries greater than zero. An empty array should produce zero.", "concept_ids": ["loops", "arrays", "conditionals"], "prerequisites": ["variables", "conditionals"]},
    {"problem_id": "java-total", "title": "Total an array", "problem_text": "Write a Java method int total(int[] values) that sums every entry with a loop. Return zero for an empty array.", "concept_ids": ["loops", "arrays", "arithmetic"], "prerequisites": ["variables", "arithmetic"]},
    {"problem_id": "java-find", "title": "Find the first matching index", "problem_text": "Write a Java method int firstIndex(int[] values, int target) that returns the first matching index, or -1 when absent. Stop once a match is found.", "concept_ids": ["loops", "arrays", "conditionals"], "prerequisites": ["loops", "arrays"]},
    {"problem_id": "java-vowels", "title": "Count lowercase vowels", "problem_text": "Write a Java method int countVowels(String text) that counts the lowercase characters a, e, i, o, u. Assume text is non-null; an empty string returns zero.", "concept_ids": ["strings", "loops", "conditionals"], "prerequisites": ["loops", "conditionals"]},
    {"problem_id": "java-reverse", "title": "Reverse a string", "problem_text": "Write a Java method String reverse(String text) using a loop and StringBuilder. Assume text contains ASCII characters and is non-null.", "concept_ids": ["strings", "loops"], "prerequisites": ["loops", "strings"]},
]

BY_ID = {exercise["problem_id"]: exercise for exercise in EXERCISES}
CONCEPT_IDS = sorted({concept for exercise in EXERCISES for concept in exercise["concept_ids"]})
SEED_HISTORY = [
    {"problem_id": "java-sum", "correct": True, "attempt_number": 1},
    {"problem_id": "java-even", "correct": False, "attempt_number": 1},
    {"problem_id": "java-even", "correct": True, "attempt_number": 2},
    {"problem_id": "java-max", "correct": True, "attempt_number": 1},
]
