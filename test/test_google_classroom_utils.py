from unittest.mock import Mock

from pytest import raises

from google_classroom_utils import get_periods_to_course_ids, get_user_ids_to_student_emails, \
    get_all_published_coursework, get_grades_for_coursework


def test_get_periods_to_course_ids():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'id': 20}]}
    assert get_periods_to_course_ids(classroom_service=mock_classroom_service,
                                     periods=[1, 2]) == {1: 10, 2: 20}


def test_get_periods_to_course_ids_invalid_period():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'id': 20}]}

    with raises(ValueError, match=r'Period 3 is not a valid period number.'):
        get_periods_to_course_ids(classroom_service=mock_classroom_service,
                                  periods=[1, 2, 3])


def test_get_user_ids_to_student_emails():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.return_value = {
        'students': [{'userId': 33, 'profile': {'emailAddress': 'foo@example.com'}},
                     {'userId': 51, 'profile': {'emailAddress': 'something@gmail.org'}}]
    }

    assert get_user_ids_to_student_emails(classroom_service=mock_classroom_service, course_id=11) == {
        33: 'foo@example.com',
        51: 'something@gmail.org'
    }


def test_get_all_published_coursework():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.courseWork.return_value.list.return_value.execute.return_value = {
        'courseWork': [{'id': 10, 'title': 'Biology'},
                       {'id': 20, 'title': 'Math'}]
    }

    assert get_all_published_coursework(classroom_service=mock_classroom_service, course_id=11) == [
        (10, 'Biology'),
        (20, 'Math')
    ]


def test_get_grades_for_coursework():
    mock_classroom_service = Mock()
    (mock_classroom_service
     .courses.return_value
     .courseWork.return_value
     .studentSubmissions.return_value
     .list.return_value
     .execute.return_value) = {
        'studentSubmissions': [{'userId': 10, 'assignedGrade': 20.3},
                               {'userId': 20}]
    }

    assert get_grades_for_coursework(classroom_service=mock_classroom_service,
                                     course_id=11,
                                     coursework_id=33) == {10: 20.3, 20: None}
