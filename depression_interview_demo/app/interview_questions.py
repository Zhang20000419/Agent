from app.schemas import InterviewQuestion


INTERVIEW_QUESTIONS = [
    InterviewQuestion(question_id=1, question_text="过去两周，你是否经常感到情绪低落、沮丧或者绝望？"),
    InterviewQuestion(question_id=2, question_text="过去两周，你是否对平时感兴趣的事情失去了兴趣或愉快感？"),
    InterviewQuestion(question_id=3, question_text="最近你的睡眠情况怎么样，比如失眠、早醒或睡得过多？"),
    InterviewQuestion(question_id=4, question_text="最近你的食欲或体重有没有明显变化？"),
    InterviewQuestion(question_id=5, question_text="最近你是否常常感到疲劳、没精力或做什么都很吃力？"),
    InterviewQuestion(question_id=6, question_text="最近你是否觉得自己很失败，或者让自己和家人失望？"),
    InterviewQuestion(question_id=7, question_text="最近你在注意力集中、看书、工作或做决定时是否变得困难？"),
    InterviewQuestion(question_id=8, question_text="最近你的动作或说话速度是否明显变慢，或者相反变得烦躁坐立不安？"),
    InterviewQuestion(question_id=9, question_text="最近你是否有过“活着没意思”、伤害自己或不如死了的想法？"),
    InterviewQuestion(question_id=10, question_text="最近这些情绪或状态对你的学习、工作或社交影响大吗？"),
    InterviewQuestion(question_id=11, question_text="这些状态一般从什么时候开始的？"),
    InterviewQuestion(question_id=12, question_text="在这一段时间里，这些感受是偶尔出现，还是经常出现？"),
    InterviewQuestion(question_id=13, question_text="当这些感受出现时，通常会持续多久？"),
    InterviewQuestion(question_id=14, question_text="你觉得这些问题的严重程度更接近轻微、中等还是严重？"),
    InterviewQuestion(question_id=15, question_text="最近有没有什么支持因素，让你感觉稍微好一点？"),
    InterviewQuestion(question_id=16, question_text="你是否愿意继续寻求帮助，比如和家人、朋友或专业人员沟通？"),
]


QUESTION_INDEX = {item.question_id: item for item in INTERVIEW_QUESTIONS}
