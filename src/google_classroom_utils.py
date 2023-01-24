import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

from arrow import Arrow

COURSEWORK_PAGE_SIZE = 1000
COURSEWORK_SUBMISSION_PAGE_SIZE = 100

EMAIL_ADDRESS_PATTERN = r'^[A-Za-z]{2}([0-9]+)@student\.musd\.org$'
EMAIL_ADDRESS_PATTERN_COMPILE = re.compile(EMAIL_ADDRESS_PATTERN)


@dataclass(frozen=True)
class GoogleClassroomAssignment:
    submissions: dict[int, Optional[float]]
    assignment_name: str
    point_total: int
    category: str


def get_submissions(classroom_service, periods: Iterable[int]) -> dict[int, list[GoogleClassroomAssignment]]:
    """
    Gets all student submissions of assignments for the periods specified. Returns the result as a mapping of period
    to list of assignment data, which contains assignment metadata and submissions.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of periods to filter for.
    :return: The submission data for the Google Classroom.
    """
    periods_to_course_ids = _get_periods_to_course_ids(classroom_service=classroom_service,
                                                       periods=periods)

    periods_to_assignments: dict[int, list[GoogleClassroomAssignment]] = defaultdict(list)
    for period, course_id in periods_to_course_ids.items():
        user_ids_to_student_ids = _get_user_ids_to_student_ids(classroom_service=classroom_service,
                                                               course_id=course_id)

        coursework_ids_to_assignment_data = _get_all_published_coursework(classroom_service=classroom_service,
                                                                          course_id=course_id)

        for coursework_id, assignment_data in coursework_ids_to_assignment_data.items():
            user_ids_to_grades = _get_grades_for_coursework(classroom_service=classroom_service,
                                                            course_id=course_id,
                                                            coursework_id=coursework_id)
            for user_id, grade in user_ids_to_grades.items():
                student_id = user_ids_to_student_ids[user_id]
                assignment_data.submissions[student_id] = grade

            periods_to_assignments[period].append(assignment_data)

    return periods_to_assignments


def _get_periods_to_course_ids(classroom_service,
                               periods: Iterable[int]) -> dict[int, int]:
    """
    Returns period number mapped to the id.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of periods to filter for.
    :return: The period number mapped to its corresponding Course Id.
    """
    courses = classroom_service.courses().list().execute().get('courses', [])
    valid_courses = {course['section']: course['id']
                     for course in courses if 'Period ' in course.get('section', '')
                     and course.get('courseState') == 'ACTIVE'}

    periods_to_course_ids: dict[int, int] = {}
    for period in periods:
        section_name = f'Period {period}'
        if section_name not in valid_courses:
            raise ValueError(f'{section_name} is not a valid period number.')
        periods_to_course_ids[period] = valid_courses[section_name]

    return periods_to_course_ids


def _get_user_ids_to_student_ids(classroom_service, course_id: int) -> dict[int, int]:
    """
    Returns Google service user id mapped to the student id.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id to fetch student emails from.
    :return: The student user id mapped to their student id.
    """
    students = classroom_service.courses().students().list(courseId=course_id).execute().get('students', [])
    user_ids_to_student_ids: dict[int, int] = {}

    for student in students:
        email = student['profile']['emailAddress']
        google_id = student['userId']

        match = EMAIL_ADDRESS_PATTERN_COMPILE.match(email)

        if not match:
            raise ValueError(f'Student email address is in an unexpected format: {email}')
        user_ids_to_student_ids[google_id] = int(match.group(1))
    return user_ids_to_student_ids


def _get_all_published_coursework(classroom_service, course_id: int) -> dict[int, GoogleClassroomAssignment]:
    """
    Returns a mapping of assignment id to assignment metadata for published coursework in the given course_id.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id to get all published coursework for.
    :return: The assignment id mapped to assignment metadata
    """
    coursework = (classroom_service
                  .courses()
                  .courseWork()
                  .list(courseId=course_id,
                        pageSize=COURSEWORK_PAGE_SIZE,
                        orderBy='dueDate desc')
                  .execute()
                  .get('courseWork', []))

    coursework_assignments = {}
    for coursework_obj in coursework:
        if not _is_current_semester(coursework_obj['dueDate']['month']):
            break

        coursework_assignments[coursework_obj['id']] = GoogleClassroomAssignment(
            submissions={},
            assignment_name=coursework_obj['title'],
            point_total=coursework_obj['maxPoints'],
            category=coursework_obj['gradeCategory']['name']
        )

    return coursework_assignments


def _is_current_semester(month: int) -> bool:
    """
    Determine if the coursework's month due date is within the same semester as the current time.
    """
    current_time = Arrow.now()
    if 1 <= current_time.month <= 6:
        return 1 <= month <= 6
    else:
        return 7 <= month <= 12


def _get_grades_for_coursework(classroom_service,
                               course_id: int,
                               coursework_id: int) -> dict[int, Optional[float]]:
    """
    Returns the grades for the assignment as a map of user id to the point total.
    If the grade is None, that means that the assignment is not graded. This could mean that grading is unfinished, or
    that the student is excused from this work.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id that is relevant to the coursework id.
    :param coursework_id: The Coursework Id to get all student submissions for.
    :return: The student user id mapped to their grade for the assignment.
    """
    student_submissions = (classroom_service
                           .courses()
                           .courseWork()
                           .studentSubmissions()
                           .list(courseId=course_id,
                                 courseWorkId=coursework_id,
                                 pageSize=COURSEWORK_SUBMISSION_PAGE_SIZE)
                           .execute()
                           .get('studentSubmissions', []))
    return {submission['userId']: submission.get('assignedGrade') for submission in student_submissions}
