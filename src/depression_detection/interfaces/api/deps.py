from depression_detection.bootstrap.container import get_container


def get_qa_service():
    return get_container().qa_service()


def get_reading_service():
    return get_container().reading_service()


def get_movie_service():
    return get_container().movie_service()


def get_prediction_service():
    return get_container().prediction_service()


def get_interview_service():
    return get_container().interview_service()


def get_debug_service():
    return get_container().debug_service()
