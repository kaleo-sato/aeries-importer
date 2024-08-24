from unittest.mock import Mock, patch, call

from arrow import Arrow

from aeries_utils import AeriesCategory, AeriesClassroomData
from validator import Validator, OverallGradeDiscrepancy


def test_validator_generate_discrepancy_report():
    periods = [1, 2]

    google_classroom_data = Mock()
    aeries_data = Mock()
    aeries_data.periods_to_gradebook_information = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1, name='Practice', weight=0.5),
                        'Performance': AeriesCategory(id=2, name='Performance', weight=0.5)},
            end_term_dates={'S': Arrow(2021, 6, 4), 'F': Arrow(2021, 6, 4)}),
        2: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1, name='Practice', weight=0.3),
                        'Participation': AeriesCategory(id=2, name='Participation', weight=0.7)},
            end_term_dates={'S': Arrow(2021, 6, 4), 'F': Arrow(2021, 6, 4)}
        )
    }
    validator = Validator(periods=periods, google_classroom_data=google_classroom_data, aeries_data=aeries_data)

    mock_google_classroom_grades = {
        1: 90,
        2: 80,
        3: 70,
        4: 60
    }

    mock_aeries_grades = {
        1: 90.15,
        2: 80,
        3: 100,
        4: 69.9
    }

    with patch.object(google_classroom_data, 'get_overall_grades',
                      return_value=mock_google_classroom_grades) as mock_get_overall_grades:
        with patch.object(aeries_data, 'extract_overall_grades_from_html',
                          return_value=mock_aeries_grades) as mock_extract_overall_grades_from_html:
            validator.generate_discrepancy_report()
            assert validator.periods_to_student_overall_grade_discrepancies == {
                1: {
                    1: OverallGradeDiscrepancy(google_classroom_overall_grade=90,
                                               aeries_overall_grade=90.15),
                    3: OverallGradeDiscrepancy(google_classroom_overall_grade=70,
                                               aeries_overall_grade=100),
                    4: OverallGradeDiscrepancy(google_classroom_overall_grade=60,
                                               aeries_overall_grade=69.9)
                },
                2: {
                    1: OverallGradeDiscrepancy(google_classroom_overall_grade=90,
                                               aeries_overall_grade=90.15),
                    3: OverallGradeDiscrepancy(google_classroom_overall_grade=70,
                                               aeries_overall_grade=100),
                    4: OverallGradeDiscrepancy(google_classroom_overall_grade=60,
                                               aeries_overall_grade=69.9)
                }
            }

            mock_get_overall_grades.assert_has_calls([
                call(period=1, categories_to_weights={'Practice': 0.5, 'Performance': 0.5}),
                call(period=2, categories_to_weights={'Practice': 0.3, 'Participation': 0.7})
            ])
            mock_extract_overall_grades_from_html.assert_has_calls([
                call(period=1),
                call(period=2)
            ])


def test_log_discrepancies_empty():
    periods = [1, 2]

    google_classroom_data = Mock()
    aeries_data = Mock()
    validator = Validator(periods=periods, google_classroom_data=google_classroom_data, aeries_data=aeries_data)

    with patch('click.echo') as mock_echo:
        validator.log_discrepancies()
        mock_echo.assert_not_called()


def test_log_discrepancies():
    periods = [1, 2]

    google_classroom_data = Mock()
    aeries_data = Mock()
    validator = Validator(periods=periods, google_classroom_data=google_classroom_data, aeries_data=aeries_data)
    validator.periods_to_student_overall_grade_discrepancies = {
        1: {
            1: OverallGradeDiscrepancy(google_classroom_overall_grade=90,
                                       aeries_overall_grade=90.15),
            3: OverallGradeDiscrepancy(google_classroom_overall_grade=70,
                                       aeries_overall_grade=100),
            4: OverallGradeDiscrepancy(google_classroom_overall_grade=60,
                                       aeries_overall_grade=69.9)
        },
        2: {}
    }

    with patch.object(google_classroom_data, 'get_student_ids_to_names',
                      return_value={1: {1: 'Alice', 3: 'Bob', 4: 'Charlie'},
                                    2: {1: 'Alice', 3: 'Bob', 4: 'Dave'}}) as mock_get_student_ids_to_names:
        with patch('click.echo') as mock_echo:
            validator.log_discrepancies()
            mock_echo.assert_has_calls([
                call('***Discrepancies between Google Classroom and Aeries overall grades:***'),
                call('Period 1:'),
                call('\tStudent                           Google Classroom    Aeries'),
                call('\tAlice                                        90.00     90.15'),
                call('\tBob                                          70.00       100'),
                call('\tCharlie                                      60.00      69.9')
            ])
