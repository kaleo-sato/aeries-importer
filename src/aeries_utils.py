import re
from collections.abc import Iterable

from bs4 import BeautifulSoup
import requests

GRADEBOOK_URL = 'https://aeries.musd.org/gradebook'
GRADEBOOK_HTML_ID = 'ValidGradebookList'
GRADEBOOK_LIST_ATTRIBUTE = 'data-validgradebookandterm'
GRADEBOOK_NAME_PATTERN = r'^([1-6]) - '
GRADEBOOK_AND_TERM_TAG_NAME = 'data-validgradebookandterm'
LIST_VIEW_ID = 'GbkDash-list-view'


def extract_gradebook_ids_from_html(periods: list[int],
                                    aeries_cookie: str) -> Iterable[int]:
    headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
               'Cookie': f's={aeries_cookie}'}
    response = requests.get(GRADEBOOK_URL, headers=headers)
    beautiful_soup = BeautifulSoup(response.text, 'html.parser')

    return _get_periods_to_gradebook_and_term(periods=periods,
                                              beautiful_soup=beautiful_soup)


def _get_periods_to_gradebook_and_term(periods: list[int],
                                       beautiful_soup: BeautifulSoup) -> dict[int, str]:
    # Parse HTML for gradebook numbers and terms, e.g. '4532451/S'
    gradebook_list_tags = beautiful_soup.find(id=GRADEBOOK_HTML_ID).find_all('li')
    gradebook_and_terms = [tag.get(GRADEBOOK_AND_TERM_TAG_NAME) for tag in gradebook_list_tags]

    # Use gradebook numbers and terms to map to the period num and filter by periods supplied.
    # Parse the list view of the gradebooks to reduce false positive searches for the gradebook link.
    periods_to_gradebook_and_term = dict()
    for gradebook_and_term in gradebook_and_terms:
        class_name = (beautiful_soup
                      .find(id=LIST_VIEW_ID)
                      .find(href=re.compile(f'gradebook/{gradebook_and_term}/ScoresByClass')).string)
        period_num_match = re.match(GRADEBOOK_NAME_PATTERN, class_name)

        if not period_num_match:
            raise ValueError(f'Unexpected naming convention for Aeries class: {class_name}. '
                             'Expected it to start with "[1-6] - "')

        period_num = int(period_num_match.group(1))
        if period_num in periods:
            periods_to_gradebook_and_term[period_num] = gradebook_and_term

    if len(periods_to_gradebook_and_term) != len(periods):
        raise ValueError(
            'Periods specified were not matched to the Aeries class gradebook.\n'
            f'Periods wanted: {", ".join(str(period) for period in sorted(periods))}\n'
            f'Periods found in Aeries: {", ".join(str(period) for period in sorted(periods_to_gradebook_and_term))}'
        )

    return periods_to_gradebook_and_term
