# aeries-importer
Import grades from Google Classroom to Aeries.

## Prerequisites:
* Python 3
* Pip
* virutalenv
* Make your Google Chrome shortcut allow remote port debugging:
  * i.e. `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir=/Users/kaleo.sato/Library/Application\ Support/Google/Chrome/Profile\ 1`
  * You can go to `chrome://version/` in the browser to find the exact path to the profile of your commonly-used Chrome window.
* Have Kaleo add your email to the [list of test users](https://console.cloud.google.com/apis/credentials/consent?authuser=1&project=aeries-importer).
  * This is to enable Google authentication for Google Classroom.
* Download the credentials.json file from the Google Cloud application (talk to Kaleo again for this file).
* You _must_ specify period numbers in the Section of each of your classes on Google Classroom. e.g.`Period 1`. This is necessary to:
  * Determine which active courses actually belong to you and contain student work that needs to be imported
  * Link a specific period to the correct gradebook an Aeries

## Setup Instructions
1. Login to Aeries on Chrome. Must have port 9222 open/enabled for Chrome debugging.
2. Save `aeries-importer` to your home directory. Save the `credentials.json` file here.
3. Run the `run.sh` file or `run.bat` file if on Windows.
4. When prompted, specify period numbers in a comma-separated list: `1,2,4`

## Execution Notes and Tips
* Zeros are imported as "MI" on Aeries to indicate in red coloring to students that their assignment grade needs attention.
* Aeries Assignments are automatically created and populated with the correct grades, using Google Classroom as the Source of Truth. Aeries assignments are uniquely identitifed by the Name, so do not create assignments with the same name on Google Classroom to avoid naming collisions.
* Assignments on Aeries are never deleted for safety. I don't want a bug in this program to result in a malformed gradebook that is hard to manually fix. This means that if you rename an assignment on Google Classroom after its grades have already been imported, you will end up with a new copy of that assignment's grades on Aeries (as assignments are uniquely identified by their name, as stated above). Make sure to manually delete duplicated assignments on Aeries if you run into this problem.
* Always spend the 5-10 extra minutes to manually check if the grades are consistent after importing. You may catch honest grading errors in Google Classroom, e.g. the classic 95/10 error instead of 9.5/10. These errors are easier to spot on Aeries since extra credit scores are highlighted in green.
* It is recommended to import frequently as opposed to procrastinating until many assignments need to be imported. This should reduce the number of assignments you need to manually audit in case a student's grade is different on Google Classroom and Aeries.
* You can also login to the Training Sandbox on Aeries to import grades there as a test run. Simply choose that Database instead of the Milpitas USD one before logging into Aeries and obtaining the s-cookie.
* Excused Assignments are not supported by the Google Classroom API, and will import as whatever score you had previously returned to the student. To truly import this assignment as an empty grade, return an empty score on Google Classroom before marking it as Excused.

## Disclaimer:
I developed this with many frail assumptions about the data format in mind. The Aeries API is limited to IT department
of the school district. As a result, I do not have access to a more supported, robust, way to query and manipulate data
to work with Aeries. The methodology described below for Aeries may be fragile and prone to breaking upon random updates
to Aeries' website, and in the worst case scenario, might perform grade updates in an undesired manner.

Because of this, I highly recommend backing up your gradebook before running this script, in case something goes massively
wrong. In the case that you come across a bug, feel free to raise an issue in the Github project, but do not expect me
to get around to responding or fixing it within a timely manner.

## Algorithm

### Google Classroom
1. For each period, get a list of all assignment submissions for all published assignments and questions. Students are
   identified by the student id, which is extracted manually from their email name format.

### Aeries
1. HTML parse the scoresByClass page to get a mapping of student ID and student number.
2. HTML parse the Gradebook IDs by scanning the list of gradebooks page for Gradebook ID.
3. HTML parse the Student Numbers by scanning the list class overall grades page for a mapping from student ID to number.
4. HTML parse list of assignments in each Gradebook to get a list of Assignment IDs, name, point total, and category.
5. HTML parse the categories page for each gradebook to get the class weights for each category.

## Join Algorithm
1. Iterate over period num to assignment name to student submissions.
2. Get student number from student ID of submission.
3. Match submission to Aeries assignment based on period num and name. Create a new assignment if it doesn't exist in Aeries.

## Update Algorithm:
1. Use Milpitas School code: 341
2. Use Gradebook ID, Student num, School Code, Assignment number to send a request to update the grade in Aeries.
