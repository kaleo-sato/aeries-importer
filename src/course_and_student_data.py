from collections.abc import Iterable


def get_periods_to_course_ids(classroom_service,
                              periods: Iterable[int]) -> dict[int, int]:
    """
    Returns period number mapped to the id.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of periods to filter for.
    :return: The period number mapped to its corresponding Course Id.
    """
    courses = classroom_service.courses().list().execute().get('courses', [])
    valid_courses = {course['section']: course['id']
                     for course in courses if 'Period ' in course['section']}

    periods_to_course_ids: dict[int, int] = {}
    for period in periods:
        section_name = f'Period {period}'
        if section_name not in valid_courses:
            raise ValueError(f'{section_name} is not a valid period number.')
        periods_to_course_ids[period] = valid_courses[section_name]

    return periods_to_course_ids


def get_user_ids_to_student_emails(classroom_service, course_id: int) -> dict[int, str]:
    """
    Returns user id mapped to the email.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id to fetch student emails from.
    :return: The student user id mapped to their emails.
    """
    students = classroom_service.courses().students().list(courseId=course_id).execute().get('students', [])
    return {student['userId']: student['profile']['emailAddress'] for student in students}
