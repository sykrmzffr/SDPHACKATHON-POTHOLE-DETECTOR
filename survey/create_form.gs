/**
 * JalanSense: Township Road Condition Survey
 * Creates the Google Form (and a linked response sheet) in your own Google account.
 *
 * How to use (2 minutes):
 *   1. Go to https://script.google.com  →  New project
 *   2. Delete the sample code, paste this whole file, click Save.
 *   3. Select the function "createSurvey" and click Run.
 *      Approve the permission prompt (it only creates a form + sheet in your Drive).
 *   4. Open View → Logs (or "Execution log"): copy the "Share link".
 *
 * The question titles are kept identical to the columns the survey dashboard
 * (web/survey.html) reads, so the Google Forms CSV export loads straight in.
 */
function createSurvey() {
  var form = FormApp.create('JalanSense: Township Road Condition Survey / Tinjauan Keadaan Jalan Taman');
  form.setDescription(
    'We are UiTM students building JalanSense, a system that detects potholes automatically using sensors on ' +
    'township vehicles and residents\' phones. This 3-minute survey helps us understand road conditions in ' +
    'Sime Darby Property townships. Responses are anonymous and used only for our hackathon project.\n\n' +
    'Kami pelajar UiTM yang membangunkan JalanSense, sistem pengesanan lubang jalan automatik. Tinjauan 3 minit ' +
    'ini adalah tanpa nama dan hanya untuk projek hackathon kami.'
  );
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setShowLinkToRespondAgain(false);

  // ---------------- Section 1: About you
  form.addMultipleChoiceItem()
    .setTitle('Consent')
    .setHelpText('I agree that my anonymous answers may be used for this student project. / Saya bersetuju jawapan saya digunakan untuk projek ini.')
    .setChoiceValues(['I agree / Saya setuju'])
    .setRequired(true);

  form.addListItem()
    .setTitle('Township')
    .setHelpText('Which Sime Darby Property township do you live in or travel through most? / Taman mana yang paling kerap anda gunakan?')
    .setChoiceValues(['City of Elmina', 'Denai Alam', 'Bukit Jelutong', 'Bandar Bukit Raja', 'Ara Damansara',
                      'USJ Heights', 'Subang Bestari', 'Bandar Ainsworth', 'Nilai Impian', 'Other / Lain-lain'])
    .setRequired(true);

  form.addTextItem()
    .setTitle('Area or precinct')
    .setHelpText('Optional, e.g. precinct or nearest landmark. Please do not give your house address. / Pilihan.');

  form.addMultipleChoiceItem()
    .setTitle('Your connection to the township')
    .setChoiceValues(['Resident (owner)', 'Resident (tenant)', 'Work or study here', 'Visitor / pass through'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Main way you travel inside the township')
    .setChoiceValues(['Car', 'Motorcycle', 'Bicycle / e-scooter', 'Walking', 'Bus / shuttle', 'Wheelchair / stroller'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Age group')
    .setChoiceValues(['18-24', '25-34', '35-44', '45-54', '55+'])
    .setRequired(true);

  // ---------------- Section 2: Road condition
  form.addPageBreakItem().setTitle('Road condition / Keadaan jalan');

  form.addScaleItem()
    .setTitle('Overall road condition')
    .setHelpText('How would you rate the roads in your township overall?')
    .setBounds(1, 5).setLabels('Very poor / Sangat teruk', 'Excellent / Sangat baik')
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('How often do you notice potholes or uneven road?')
    .setChoiceValues(['Daily', 'Weekly', 'Monthly', 'Rarely', 'Never'])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Which problems have you seen?')
    .setChoiceValues(['Potholes', 'Uneven or badly patched surface', 'Sunken drain or manhole covers',
                      'Cracked surface', 'Damaged speed bumps', 'Faded road markings', 'Waterlogging after rain'])
    .showOtherOption(true);

  form.addCheckboxItem()
    .setTitle('In the last 12 months, has a bad road caused you any of these?')
    .setChoiceValues(['Tyre or rim damage', 'Suspension or alignment problem', 'Near-accident or fall',
                      'Had to swerve suddenly', 'Had to slow down a lot', 'None of these'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Roughly how much have you spent on vehicle repairs caused by bad roads in the last 12 months?')
    .setChoiceValues(['RM 0', 'Below RM 100', 'RM 100 - 300', 'RM 300 - 1,000', 'Above RM 1,000', 'Not sure']);

  form.addParagraphTextItem()
    .setTitle('Where is the worst spot you know?')
    .setHelpText('Optional: road name or landmark, e.g. "junction near the school". / Pilihan.');

  // ---------------- Section 3: Reporting
  form.addPageBreakItem().setTitle('Reporting problems / Membuat aduan');

  form.addMultipleChoiceItem()
    .setTitle('Have you ever reported a road problem?')
    .setChoiceValues(['Yes, to the developer or estate management', 'Yes, to the local council or MyJalan',
                      'No, I did not know where to report', 'No, I did not think it would be fixed', 'No, never needed to'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('If you reported it, how long until it was repaired?')
    .setChoiceValues(['Less than 1 week', '1 - 4 weeks', 'More than 1 month', 'Never repaired', 'Did not report / not sure']);

  form.addScaleItem()
    .setTitle('Satisfaction with how road problems are handled')
    .setBounds(1, 5).setLabels('Very unsatisfied', 'Very satisfied')
    .setRequired(true);

  // ---------------- Section 4: JalanSense idea
  form.addPageBreakItem().setTitle('Our idea / Idea kami')
    .setHelpText('JalanSense puts a small sensor on township shuttles, patrol cars and waste trucks. It detects potholes automatically, ' +
                 'with GPS, so the estate team can fix them sooner. Residents can also help by running a web app on their phone while driving.');

  form.addScaleItem()
    .setTitle('Support for sensors on township vehicles')
    .setHelpText('How much do you support putting pothole sensors on township service vehicles?')
    .setBounds(1, 5).setLabels('Do not support', 'Strongly support')
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('Would you run a pothole-detecting app on your phone while driving?')
    .setChoiceValues(['Yes', 'Maybe', 'No'])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('Any concerns about the phone app?')
    .setChoiceValues(['Battery use', 'Location privacy', 'Mobile data use', 'I do not drive', 'No concerns']);

  form.addParagraphTextItem()
    .setTitle('Any other comments?');

  form.setConfirmationMessage('Thank you! Terima kasih for helping make township roads safer.');

  var sheet = SpreadsheetApp.create('JalanSense Survey Responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  Logger.log('Share link (send this to residents): ' + form.getPublishedUrl());
  Logger.log('Edit link (team only): ' + form.getEditUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
}
