from app.schemas import InterviewQuestion


# 固定访谈题库集中定义，前后端都以 question_id 为稳定主键。
INTERVIEW_QUESTIONS = [
    InterviewQuestion(question_id=1, question_text="你今天过得怎么样？"),
    InterviewQuestion(question_id=2, question_text="你的家乡是哪里的？"),
    InterviewQuestion(question_id=3, question_text="你最喜欢你家乡的哪些美食景点呐？"),
    InterviewQuestion(question_id=4, question_text="你跟你的家人、同事、同学、朋友，关系处得怎么样，可以仔细说下吗？"),
    InterviewQuestion(question_id=5, question_text="你觉得你的性格内向还是外向一些呐？"),
    InterviewQuestion(question_id=6, question_text="最近2周，你的心情怎么样？"),
    InterviewQuestion(question_id=7, question_text="你对你目前的学习或工作的兴趣如何呐？"),
    InterviewQuestion(question_id=8, question_text="你容不容易责备自己，感到自己连累了其他人呐？有的话，请你仔细讲一下当时的状态。"),
    InterviewQuestion(question_id=9, question_text="有没有哪段时间，你觉得自己的行动、思考或说话都比较迟钝？有的话，可以仔细说一下吗？"),
    InterviewQuestion(question_id=10, question_text="你是否经常感到紧张、焦虑，担心，惶恐不安？如果是，可以仔细说一下吗？"),
    InterviewQuestion(question_id=11, question_text="有没有哪段时间，你感到兴奋或亢奋、或者精力旺盛？有的话，请你仔细讲一下当时的状态。"),
    InterviewQuestion(question_id=12, question_text="有没有哪段时间，连续几天持续地感到烦躁易怒，以至于与人争论，吵架或打架，或者对着外人大吼？有的话，请你仔细讲一下。"),
    InterviewQuestion(question_id=13, question_text="有没有哪段时间，你总喜欢滔滔不绝地讲话，说话快得让人难以理解？有的话，请你仔细讲一下。"),
    InterviewQuestion(question_id=14, question_text="好的。有没有哪段时间，你觉得自己思维比以往格外活跃，脑子格外聪明？有的话，请你仔细讲一下。"),
]


# 预先建立索引，避免在主流程中频繁线性查找题目。
QUESTION_INDEX = {item.question_id: item for item in INTERVIEW_QUESTIONS}
