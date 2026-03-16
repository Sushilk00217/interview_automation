import logging
import uuid
from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.models.question import Question, CategoryEnum, DifficultyEnum, QuestionType
from app.db.sql.models.coding_problem import CodingProblem, TestCase

logger = logging.getLogger(__name__)

async def seed_coding_problems(session: AsyncSession):
    """Seed the Question Bank with initial set of coding problems."""
    logger.info("Seeding Coding Problems...")
    
    # No longer skipping if already populated; we want to ensure latest starter code is there
    # stmt = select(literal(1)).select_from(CodingProblem).limit(1)
    # result = await session.execute(stmt)
    # if result.scalar() is not None:
    #     logger.info("[coding_seed] Coding problems already populated. Skipping.")
    #     return

    BOILERPLATES = {
        "Two Sum": {
            "python3": "import sys, json\n\ndef two_sum(nums, target):\n    # Your code here\n    pass\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 2:\n        nums = json.loads(lines[0])\n        target = json.loads(lines[1])\n        result = two_sum(nums, target)\n        print(json.dumps(result).replace(' ', ''))",
            "javascript": "const fs = require('fs');\n\nfunction twoSum(nums, target) {\n    // Your code here\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 2) {\n    const nums = JSON.parse(input[0]);\n    const target = JSON.parse(input[1]);\n    const result = twoSum(nums, target);\n    console.log(JSON.stringify(result).replace(/ /g, ''));\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // Your code here\n        return new int[]{};\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line1 = reader.readLine();\n        String line2 = reader.readLine();\n        if (line1 != null && line2 != null) {\n            String[] parts = line1.replace(\"[\", \"\").replace(\"]\", \"\").split(\",\");\n            int[] nums = new int[parts.length];\n            for (int i = 0; i < parts.length; i++) nums[i] = Integer.parseInt(parts[i].trim());\n            int target = Integer.parseInt(line2.trim());\n            \n            Solution sol = new Solution();\n            int[] res = sol.twoSum(nums, target);\n            System.out.print(\"[\");\n            for (int i = 0; i < res.length; i++) {\n                System.out.print(res[i]);\n                if (i < res.length - 1) System.out.print(\",\");\n            }\n            System.out.println(\"]\");\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <vector>\n#include <string>\n#include <sstream>\n\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // Your code here\n        return {};\n    }\n};\n\nint main() {\n    string line1, line2;\n    if (getline(cin, line1) && getline(cin, line2)) {\n        vector<int> nums;\n        string cleaned = line1.substr(1, line1.length() - 2);\n        stringstream ss(cleaned);\n        string item;\n        while (getline(ss, item, ',')) {\n            nums.push_back(stoi(item));\n        }\n        int target = stoi(line2);\n        \n        Solution sol;\n        vector<int> res = sol.twoSum(nums, target);\n        cout << \"[\";\n        for (size_t i = 0; i < res.size(); i++) {\n            cout << res[i] << (i < res.size() - 1 ? \",\" : \"\");\n        }\n        cout << \"]\" << endl;\n    }\n    return 0;\n}"
        },
        "Palindrome Number": {
            "python3": "import sys, json\n\ndef is_palindrome(x):\n    # Your code here\n    pass\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 1:\n        x = int(lines[0])\n        result = is_palindrome(x)\n        print(\"true\" if result else \"false\")",
            "javascript": "const fs = require('fs');\n\nfunction isPalindrome(x) {\n    // Your code here\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 1) {\n    const x = parseInt(input[0]);\n    const result = isPalindrome(x);\n    console.log(result ? \"true\" : \"false\");\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass Solution {\n    public boolean isPalindrome(int x) {\n        // Your code here\n        return false;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line = reader.readLine();\n        if (line != null) {\n            int x = Integer.parseInt(line.trim());\n            Solution sol = new Solution();\n            boolean res = sol.isPalindrome(x);\n            System.out.println(res ? \"true\" : \"false\");\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <string>\n\nusing namespace std;\n\nclass Solution {\npublic:\n    bool isPalindrome(int x) {\n        // Your code here\n        return false;\n    }\n};\n\nint main() {\n    string line;\n    if (getline(cin, line)) {\n        int x = stoi(line);\n        Solution sol;\n        bool res = sol.isPalindrome(x);\n        cout << (res ? \"true\" : \"false\") << endl;\n    }\n    return 0;\n}"
        },
        "FizzBuzz": {
            "python3": "import sys, json\n\ndef fizz_buzz(n):\n    # Your code here\n    pass\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 1:\n        n = int(lines[0])\n        result = fizz_buzz(n)\n        print(json.dumps(result).replace(' ', ''))",
            "javascript": "const fs = require('fs');\n\nfunction fizzBuzz(n) {\n    // Your code here\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 1) {\n    const n = parseInt(input[0]);\n    const result = fizzBuzz(n);\n    console.log(JSON.stringify(result).replace(/ /g, ''));\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass Solution {\n    public List<String> fizzBuzz(int n) {\n        // Your code here\n        return new ArrayList<>();\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line = reader.readLine();\n        if (line != null) {\n            int n = Integer.parseInt(line.trim());\n            Solution sol = new Solution();\n            List<String> res = sol.fizzBuzz(n);\n            System.out.print(\"[\");\n            for (int i = 0; i < res.size(); i++) {\n                System.out.print(\"\\\"\" + res.get(i) + \"\\\"\");\n                if (i < res.size() - 1) System.out.print(\",\");\n            }\n            System.out.println(\"]\");\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <vector>\n#include <string>\n\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<string> fizzBuzz(int n) {\n        // Your code here\n        return {};\n    }\n};\n\nint main() {\n    string line;\n    if (getline(cin, line)) {\n        int n = stoi(line);\n        Solution sol;\n        vector<string> res = sol.fizzBuzz(n);\n        cout << \"[\";\n        for (size_t i = 0; i < res.size(); i++) {\n            cout << \"\\\"\" << res[i] << \"\\\"\" << (i < res.size() - 1 ? \",\" : \"\");\n        }\n        cout << \"]\" << endl;\n    }\n    return 0;\n}"
        },
        "Merge Two Sorted Lists": {
            "python3": "import sys, json\n\nclass ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef merge_two_lists(list1, list2):\n    # Your code here\n    pass\n\ndef build_list(arr):\n    dummy = ListNode()\n    curr = dummy\n    for val in arr:\n        curr.next = ListNode(val)\n        curr = curr.next\n    return dummy.next\n\ndef serialize_list(node):\n    res = []\n    while node:\n        res.append(node.val)\n        node = node.next\n    return res\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 2:\n        l1_arr = json.loads(lines[0])\n        l2_arr = json.loads(lines[1])\n        result = merge_two_lists(build_list(l1_arr), build_list(l2_arr))\n        print(json.dumps(serialize_list(result)).replace(' ', ''))",
            "javascript": "const fs = require('fs');\n\nfunction ListNode(val, next) {\n    this.val = (val===undefined ? 0 : val)\n    this.next = (next===undefined ? null : next)\n}\n\nfunction mergeTwoLists(list1, list2) {\n    // Your code here\n}\n\nfunction buildList(arr) {\n    let dummy = new ListNode();\n    let curr = dummy;\n    for (let val of arr) {\n        curr.next = new ListNode(val);\n        curr = curr.next;\n    }\n    return dummy.next;\n}\n\nfunction serializeList(node) {\n    let res = [];\n    while (node) {\n        res.push(node.val);\n        node = node.next;\n    }\n    return res;\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 2) {\n    const l1Arr = JSON.parse(input[0]);\n    const l2Arr = JSON.parse(input[1]);\n    const result = mergeTwoLists(buildList(l1Arr), buildList(l2Arr));\n    console.log(JSON.stringify(serializeList(result)).replace(/ /g, ''));\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass ListNode {\n    int val;\n    ListNode next;\n    ListNode() {}\n    ListNode(int val) { this.val = val; }\n    ListNode(int val, ListNode next) { this.val = val; this.next = next; }\n}\n\nclass Solution {\n    public ListNode mergeTwoLists(ListNode list1, ListNode list2) {\n        // Your code here\n        return null;\n    }\n\n    public static ListNode buildList(int[] arr) {\n        ListNode dummy = new ListNode();\n        ListNode curr = dummy;\n        for (int val : arr) {\n            curr.next = new ListNode(val);\n            curr = curr.next;\n        }\n        return dummy.next;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line1 = reader.readLine();\n        String line2 = reader.readLine();\n        if (line1 != null && line2 != null) {\n            String[] p1 = line1.replace(\"[\", \"\").replace(\"]\", \"\").split(\",\");\n            int[] arr1 = new int[p1.length == 1 && p1[0].isEmpty() ? 0 : p1.length];\n            if (arr1.length > 0) for (int i = 0; i < p1.length; i++) arr1[i] = Integer.parseInt(p1[i].trim());\n\n            String[] p2 = line2.replace(\"[\", \"\").replace(\"]\", \"\").split(\",\");\n            int[] arr2 = new int[p2.length == 1 && p2[0].isEmpty() ? 0 : p2.length];\n            if (arr2.length > 0) for (int i = 0; i < p2.length; i++) arr2[i] = Integer.parseInt(p2[i].trim());\n            \n            Solution sol = new Solution();\n            ListNode res = sol.mergeTwoLists(buildList(arr1), buildList(arr2));\n            \n            System.out.print(\"[\");\n            while (res != null) {\n                System.out.print(res.val);\n                if (res.next != null) System.out.print(\",\");\n                res = res.next;\n            }\n            System.out.println(\"]\");\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <vector>\n#include <string>\n#include <sstream>\n\nusing namespace std;\n\nstruct ListNode {\n    int val;\n    ListNode *next;\n    ListNode() : val(0), next(nullptr) {}\n    ListNode(int x) : val(x), next(nullptr) {}\n    ListNode(int x, ListNode *next) : val(x), next(next) {}\n};\n\nclass Solution {\npublic:\n    ListNode* mergeTwoLists(ListNode* list1, ListNode* list2) {\n        // Your code here\n        return nullptr;\n    }\n};\n\nListNode* buildList(const vector<int>& arr) {\n    ListNode dummy;\n    ListNode* curr = &dummy;\n    for (int val : arr) {\n        curr->next = new ListNode(val);\n        curr = curr->next;\n    }\n    return dummy.next;\n}\n\nint main() {\n    string line1, line2;\n    if (getline(cin, line1) && getline(cin, line2)) {\n        vector<int> arr1, arr2;\n        \n        string cleaned1 = line1.substr(1, line1.length() - 2);\n        if (!cleaned1.empty()) {\n            stringstream ss1(cleaned1);\n            string item;\n            while (getline(ss1, item, ',')) arr1.push_back(stoi(item));\n        }\n\n        string cleaned2 = line2.substr(1, line2.length() - 2);\n        if (!cleaned2.empty()) {\n            stringstream ss2(cleaned2);\n            string item;\n            while (getline(ss2, item, ',')) arr2.push_back(stoi(item));\n        }\n        \n        Solution sol;\n        ListNode* res = sol.mergeTwoLists(buildList(arr1), buildList(arr2));\n        cout << \"[\";\n        while (res != nullptr) {\n            cout << res->val << (res->next ? \",\" : \"\");\n            res = res->next;\n        }\n        cout << \"]\" << endl;\n    }\n    return 0;\n}"
        },
        "Longest Substring Without Repeating Characters": {
            "python3": "import sys, json\n\ndef length_of_longest_substring(s):\n    # Your code here\n    pass\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 1:\n        s = json.loads(lines[0])\n        result = length_of_longest_substring(s)\n        print(result)",
            "javascript": "const fs = require('fs');\n\nfunction lengthOfLongestSubstring(s) {\n    // Your code here\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 1) {\n    const s = JSON.parse(input[0]);\n    const result = lengthOfLongestSubstring(s);\n    console.log(result);\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass Solution {\n    public int lengthOfLongestSubstring(String s) {\n        // Your code here\n        return 0;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line = reader.readLine();\n        if (line != null) {\n            // Remove surround quotes\n            if (line.length() >= 2 && line.startsWith(\"\\\"\") && line.endsWith(\"\\\"\")) {\n                line = line.substring(1, line.length() - 1);\n            }\n            Solution sol = new Solution();\n            int res = sol.lengthOfLongestSubstring(line);\n            System.out.println(res);\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <string>\n\nusing namespace std;\n\nclass Solution {\npublic:\n    int lengthOfLongestSubstring(string s) {\n        // Your code here\n        return 0;\n    }\n};\n\nint main() {\n    string line;\n    if (getline(cin, line)) {\n        if (line.length() >= 2 && line.front() == '\"' && line.back() == '\"') {\n            line = line.substr(1, line.length() - 2);\n        }\n        Solution sol;\n        int res = sol.lengthOfLongestSubstring(line);\n        cout << res << endl;\n    }\n    return 0;\n}"
        },
        "Valid Anagram": {
            "python3": "import sys, json\n\ndef is_anagram(s, t):\n    # Your code here\n    pass\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if len(lines) >= 2:\n        s = json.loads(lines[0])\n        t = json.loads(lines[1])\n        result = is_anagram(s, t)\n        print(\"true\" if result else \"false\")",
            "javascript": "const fs = require('fs');\n\nfunction isAnagram(s, t) {\n    // Your code here\n}\n\nconst input = fs.readFileSync('/dev/stdin', 'utf-8').trim().split('\\n');\nif (input.length >= 2) {\n    const s = JSON.parse(input[0]);\n    const t = JSON.parse(input[1]);\n    const result = isAnagram(s, t);\n    console.log(result ? \"true\" : \"false\");\n}",
            "java": "import java.util.*;\nimport java.io.*;\n\nclass Solution {\n    public boolean isAnagram(String s, String t) {\n        // Your code here\n        return false;\n    }\n\n    public static void main(String[] args) throws IOException {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        String line1 = reader.readLine();\n        String line2 = reader.readLine();\n        if (line1 != null && line2 != null) {\n            if (line1.length() >= 2) line1 = line1.substring(1, line1.length() - 1);\n            if (line2.length() >= 2) line2 = line2.substring(1, line2.length() - 1);\n            Solution sol = new Solution();\n            boolean res = sol.isAnagram(line1, line2);\n            System.out.println(res ? \"true\" : \"false\");\n        }\n    }\n}",
            "cpp": "#include <iostream>\n#include <string>\n\nusing namespace std;\n\nclass Solution {\npublic:\n    bool isAnagram(string s, string t) {\n        // Your code here\n        return false;\n    }\n};\n\nint main() {\n    string line1, line2;\n    if (getline(cin, line1) && getline(cin, line2)) {\n        if (line1.length() >= 2) line1 = line1.substr(1, line1.length() - 2);\n        if (line2.length() >= 2) line2 = line2.substr(1, line2.length() - 2);\n        Solution sol;\n        bool res = sol.isAnagram(line1, line2);\n        cout << (res ? \"true\" : \"false\") << endl;\n    }\n    return 0;\n}"
        }
    }

    problems_data = [
        {
            "title": "Two Sum",
            "description": "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`. You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.",
            "difficulty": DifficultyEnum.EASY,
            "category": CategoryEnum.DATA_STRUCTURES,
            "starter_code": BOILERPLATES["Two Sum"],
            "test_cases": [
                {"input": "[2,7,11,15]\n9", "expected_output": "[0,1]", "is_hidden": False, "order": 1},
                {"input": "[3,2,4]\n6", "expected_output": "[1,2]", "is_hidden": False, "order": 2},
                {"input": "[3,3]\n6", "expected_output": "[0,1]", "is_hidden": True, "order": 3}
            ]
        },
        {
            "title": "Palindrome Number",
            "description": "Given an integer `x`, return `true` if `x` is a palindrome, and `false` otherwise. An integer is a palindrome when it reads the same forward and backward.",
            "difficulty": DifficultyEnum.EASY,
            "category": CategoryEnum.DATA_STRUCTURES,
            "starter_code": BOILERPLATES["Palindrome Number"],
            "test_cases": [
                {"input": "121", "expected_output": "true", "is_hidden": False, "order": 1},
                {"input": "-121", "expected_output": "false", "is_hidden": False, "order": 2},
                {"input": "10", "expected_output": "false", "is_hidden": True, "order": 3},
                {"input": "1221", "expected_output": "true", "is_hidden": True, "order": 4}
            ]
        },
        {
            "title": "FizzBuzz",
            "description": "Given an integer `n`, return a list of strings (1-indexed) where:\n- `answer[i] == \"FizzBuzz\"` if `i` is divisible by 3 and 5.\n- `answer[i] == \"Fizz\"` if `i` is divisible by 3.\n- `answer[i] == \"Buzz\"` if `i` is divisible by 5.\n- `answer[i] == i` (as a string) if none of the above conditions are true.",
            "difficulty": DifficultyEnum.EASY,
            "category": CategoryEnum.PYTHON,
            "starter_code": BOILERPLATES["FizzBuzz"],
            "test_cases": [
                {"input": "3", "expected_output": "[\"1\",\"2\",\"Fizz\"]", "is_hidden": False, "order": 1},
                {"input": "5", "expected_output": "[\"1\",\"2\",\"Fizz\",\"4\",\"Buzz\"]", "is_hidden": False, "order": 2},
                {"input": "15", "expected_output": "[\"1\",\"2\",\"Fizz\",\"4\",\"Buzz\",\"Fizz\",\"7\",\"8\",\"Fizz\",\"Buzz\",\"11\",\"Fizz\",\"13\",\"14\",\"FizzBuzz\"]", "is_hidden": True, "order": 3}
            ]
        },
        {
            "title": "Merge Two Sorted Lists",
            "description": "You are given the heads of two sorted linked lists `list1` and `list2`. Merge the two lists into one sorted list. The list should be made by splicing together the nodes of the first two lists. Return the head of the merged linked list. (For the sake of this problem, assume inputs are lists of integers).",
            "difficulty": DifficultyEnum.EASY,
            "category": CategoryEnum.DATA_STRUCTURES,
            "starter_code": BOILERPLATES["Merge Two Sorted Lists"],
            "test_cases": [
                {"input": "[1,2,4]\n[1,3,4]", "expected_output": "[1,1,2,3,4,4]", "is_hidden": False, "order": 1},
                {"input": "[]\n[]", "expected_output": "[]", "is_hidden": False, "order": 2},
                {"input": "[]\n[0]", "expected_output": "[0]", "is_hidden": True, "order": 3}
            ]
        },
        {
            "title": "Longest Substring Without Repeating Characters",
            "description": "Given a string `s`, find the length of the longest substring without repeating characters.",
            "difficulty": DifficultyEnum.MEDIUM,
            "category": CategoryEnum.DATA_STRUCTURES,
            "starter_code": BOILERPLATES["Longest Substring Without Repeating Characters"],
            "test_cases": [
                {"input": "\"abcabcbb\"", "expected_output": "3", "is_hidden": False, "order": 1},
                {"input": "\"bbbbb\"", "expected_output": "1", "is_hidden": False, "order": 2},
                {"input": "\"pwwkew\"", "expected_output": "3", "is_hidden": True, "order": 3},
                {"input": "\"\"", "expected_output": "0", "is_hidden": True, "order": 4}
            ]
        },
        {
            "title": "Valid Anagram",
            "description": "Given two strings `s` and `t`, return `true` if `t` is an anagram of `s`, and `false` otherwise. An Anagram is a word or phrase formed by rearranging the letters of a different word or phrase, typically using all the original letters exactly once.",
            "difficulty": DifficultyEnum.EASY,
            "category": CategoryEnum.DATA_STRUCTURES,
            "starter_code": BOILERPLATES["Valid Anagram"],
            "test_cases": [
                {"input": "\"anagram\"\n\"nagaram\"", "expected_output": "true", "is_hidden": False, "order": 1},
                {"input": "\"rat\"\n\"car\"", "expected_output": "false", "is_hidden": False, "order": 2},
                {"input": "\"a\"\n\"a\"", "expected_output": "true", "is_hidden": True, "order": 3}
            ]
        }
    ]

    for p in problems_data:
        # 1. Check if problem already exists by title
        stmt = select(CodingProblem).where(CodingProblem.title == p["title"])
        result = await session.execute(stmt)
        existing_problem = result.scalars().first()

        if existing_problem:
            logger.info(f"[coding_seed] Updating existing problem: {p['title']}")
            # Update CodingProblem
            existing_problem.description = p["description"]
            existing_problem.difficulty = p["difficulty"].value
            existing_problem.starter_code = p["starter_code"]
            
            # Update associated Question
            stmt_q = select(Question).where(Question.id == existing_problem.question_id)
            res_q = await session.execute(stmt_q)
            question = res_q.scalars().first()
            if question:
                question.text = p["description"]
                question.category = p["category"]
                question.difficulty = p["difficulty"]
            
            # Sync Test Cases: simpler to replace since we have cascade delete-orphan
            from sqlalchemy import delete
            await session.execute(delete(TestCase).where(TestCase.problem_id == existing_problem.id))
            
            for tc in p["test_cases"]:
                new_tc = TestCase(
                    problem_id=existing_problem.id,
                    input=tc["input"],
                    expected_output=tc["expected_output"],
                    is_hidden=tc["is_hidden"],
                    order=tc["order"]
                )
                session.add(new_tc)

        else:
            logger.info(f"[coding_seed] Creating new problem: {p['title']}")
            # 1. Create Question
            question = Question(
                text=p["description"],
                category=p["category"],
                difficulty=p["difficulty"],
                question_type=QuestionType.CODING,
                tags=["coding", p["category"].value.lower()]
            )
            session.add(question)
            await session.flush() # Get question.id

            # 2. Create CodingProblem
            coding_problem = CodingProblem(
                question_id=question.id,
                title=p["title"],
                description=p["description"],
                difficulty=p["difficulty"].value,
                starter_code=p["starter_code"],
                time_limit_sec=900
            )
            session.add(coding_problem)
            await session.flush() # Get coding_problem.id

            # 3. Create TestCases
            for tc in p["test_cases"]:
                test_case = TestCase(
                    problem_id=coding_problem.id,
                    input=tc["input"],
                    expected_output=tc["expected_output"],
                    is_hidden=tc["is_hidden"],
                    order=tc["order"]
                )
                session.add(test_case)

    await session.commit()
    logger.info(f"[OK] Seeded/Updated {len(problems_data)} coding problems into the bank.")
