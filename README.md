# aeries-importer
Import grades from Google Classroom to Aeries.

Setup Google authentication using steps here: https://developers.google.com/classroom/quickstart/go

### Algorithm

1. Export a manual mapping of student emails to their Aeries Student ID by querying the Aeries database.
2. Crawl the list of gradebooks for Gradebook ID.
3. Crawl the list of assignments in each Gradebook to get a list of Assignment IDs.
4. Fetch all student grades for published assignments and questions.
Match students via email address to their Aeries Student ID using the manual mapping.
5. Match assignments to their Aeries Assignment ID by crawling the Gradebook for the class.
6. Milpitas School code: 341
7. Use Gradebook ID, Student ID, School Code, Assignment number to patch the grade in Aeries.
8. Validate that the overall grades are accurate and consistent.